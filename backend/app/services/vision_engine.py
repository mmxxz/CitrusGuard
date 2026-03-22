"""
柑橘视觉识别引擎 (CitrusHVT 本地推理封装)
==========================================
加载训练好的 best.pt 权重，对上传图片执行本地推理。
返回 Top-K 预测、粗类别、OOD 能量分值（用于拒识判断）。

训练与复现（非运行时依赖）:
    backend/training/convnext/citrushvt-full-training-5.ipynb

使用方式:
    from app.services.vision_engine import vision_engine
    result = vision_engine.predict_from_url("http://...")
    result = vision_engine.predict_from_path("/path/to/img.jpg")
"""

import os
import math
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import io

logger = logging.getLogger(__name__)

# ================================================================
# 模型架构（与训练 Notebook 保持一致）
# ================================================================

# 延迟导入 torch 以便在无 GPU 环境中先初始化其它服务
_torch_loaded = False
_nn = None
_F = None
_torch = None

def _ensure_torch():
    global _torch_loaded, _nn, _F, _torch
    if _torch_loaded:
        return True
    try:
        import torch
        import torch.nn as nn
        import torch.nn.functional as F
        _torch = torch
        _nn = nn
        _F = F
        _torch_loaded = True
        return True
    except ImportError:
        logger.warning("PyTorch 未安装，视觉引擎将不可用，将降级到多模态 LLM")
        return False


def _build_model_classes():
    """在确认 torch 可用后才定义模型类（与 backend/training/convnext/citrushvt-full-training-5.ipynb 架构一致）"""
    import torch
    import torch.nn as nn
    import torch.nn.functional as F

    # ── 小波茎（与 notebook 保持一致）────────────────────────────────────────
    class HaarDWT(nn.Module):
        def __init__(self):
            super().__init__()
            low  = torch.tensor([1.0 / math.sqrt(2.0),  1.0 / math.sqrt(2.0)])
            high = torch.tensor([1.0 / math.sqrt(2.0), -1.0 / math.sqrt(2.0)])
            filters = torch.stack([
                torch.outer(low, low), torch.outer(low, high),
                torch.outer(high, low), torch.outer(high, high),
            ], dim=0)
            self.register_buffer('filters', filters.reshape(4, 1, 2, 2), persistent=False)

        def forward(self, x):
            b, c, h, w = x.shape
            filters = self.filters.to(dtype=x.dtype)
            y = F.conv2d(x.reshape(b * c, 1, h, w), filters, stride=2)
            y = y.reshape(b, c, 4, h // 2, w // 2)
            return y[:, :, 0], y[:, :, 1], y[:, :, 2], y[:, :, 3]

    class WaveConvBlock(nn.Module):
        def __init__(self, channels, hidden_channels=32, dropout=0.0):
            super().__init__()
            self.dwt = HaarDWT()
            self.low_conv  = nn.Sequential(nn.Conv2d(channels,     hidden_channels,     3, padding=1, bias=False), nn.BatchNorm2d(hidden_channels),     nn.GELU())
            self.freq_conv = nn.Sequential(nn.Conv2d(channels * 3, hidden_channels * 2, 1, bias=False), nn.BatchNorm2d(hidden_channels * 2), nn.GELU())
            fused = channels + hidden_channels + hidden_channels * 2
            self.mix = nn.Sequential(nn.Conv2d(fused, channels, 3, padding=1, bias=False), nn.BatchNorm2d(channels), nn.GELU(), nn.Dropout(dropout))

        def forward(self, x):
            ll, lh, hl, hh = self.dwt(x)
            low  = F.interpolate(self.low_conv(ll),  size=x.shape[-2:], mode='bilinear', align_corners=False)
            freq = F.interpolate(self.freq_conv(torch.cat([lh, hl, hh], dim=1)), size=x.shape[-2:], mode='bilinear', align_corners=False)
            return self.mix(torch.cat([x, low, freq], dim=1)) + x

    class WaveletStem(nn.Module):
        def __init__(self, in_channels=3, hidden_channels=48, num_blocks=2, dropout=0.0):
            super().__init__()
            self.blocks   = nn.ModuleList([WaveConvBlock(in_channels, hidden_channels, dropout) for _ in range(num_blocks)])
            self.out_norm = nn.BatchNorm2d(in_channels)
        def forward(self, x):
            for blk in self.blocks:
                x = blk(x)
            return self.out_norm(x)

    # ── 本地特征提取（与 notebook 完全一致：Conv2d fusion + mean pooling）──────
    class LocalFeatureExtractor(nn.Module):
        def __init__(self, backbone_name='convnext_tiny.fb_in22k_ft_in1k',
                     img_size=224, pretrained=False, drop_path=0.1,
                     use_wavelet=True, use_multiscale=True, local_dim=256):
            super().__init__()
            import timm
            self.use_wavelet    = use_wavelet
            self.use_multiscale = use_multiscale
            self.wavelet_stem   = WaveletStem(num_blocks=2, dropout=0.05) if use_wavelet else nn.Identity()
            backbone_kwargs = dict(pretrained=pretrained, features_only=True,
                                   out_indices=(1, 2, 3), drop_path_rate=drop_path)
            if 'vit' in backbone_name or 'swin' in backbone_name:
                backbone_kwargs['img_size'] = img_size
            self.backbone = timm.create_model(backbone_name, **backbone_kwargs)
            feature_channels = self.backbone.feature_info.channels()
            fusion_in = sum(feature_channels[-3:]) if use_multiscale else feature_channels[-1]
            # 与 notebook 相同：Conv2d(fusion_in, local_dim, 1) + BN + GELU
            self.fusion = nn.Sequential(
                nn.Conv2d(fusion_in, local_dim, 1, bias=False),
                nn.BatchNorm2d(local_dim),
                nn.GELU(),
            )
            self.out_dim = local_dim

        def forward(self, x):
            x = self.wavelet_stem(x)
            features = self.backbone(x)[-3:]
            if self.use_multiscale:
                target_hw = features[0].shape[-2:]
                processed = [F.interpolate(f, size=target_hw, mode='bilinear', align_corners=False) for f in features]
                fused = torch.cat(processed, dim=1)
            else:
                fused = features[-1]
            pooled = self.fusion(fused).mean(dim=(-2, -1))
            return pooled, features

    # ── 全局特征提取（ViT-Tiny，仅 full/hybrid baseline 使用）──────────────────
    class GlobalFeatureExtractor(nn.Module):
        def __init__(self, vit_name='vit_tiny_patch16_224', img_size=224):
            super().__init__()
            import timm
            self.vit     = timm.create_model(vit_name, pretrained=False, num_classes=0)
            self.out_dim = getattr(self.vit, 'embed_dim', 192)
        def forward(self, x):
            return self.vit(x)

    # ── 跨分支门控（仅 full baseline with gate 使用）──────────────────────────
    class CrossBranchGate(nn.Module):
        def __init__(self, local_dim, global_dim, d_model=384):
            super().__init__()
            self.proj_local  = nn.Linear(local_dim, d_model)
            self.proj_global = nn.Linear(global_dim, d_model)
            self.gate         = nn.Sequential(nn.Linear(d_model * 2, d_model), nn.Sigmoid())
            self.out_norm     = nn.LayerNorm(d_model)
        def forward(self, f_local, f_global):
            l, g = self.proj_local(f_local), self.proj_global(f_global)
            gv = self.gate(torch.cat([l, g], dim=-1))
            return self.out_norm(gv * l + (1 - gv) * g)

    # ── 主模型（与 notebook 完全一致，通过 baseline 参数控制架构）──────────────
    class CitrusHVT(nn.Module):
        def __init__(self, num_classes=18, d_model=384, local_dim=256,
                     vit_name='vit_tiny_patch16_224', img_size=224, drop_path=0.1,
                     baseline='cnn_only', use_hierarchical=False, num_coarse_classes=4):
            super().__init__()
            self.num_classes    = num_classes
            self.use_hierarchical = use_hierarchical
            _b = baseline.lower()

            self.use_local  = _b not in {'global_only'}
            self.use_global = _b not in {'cnn_only', 'wavecnn_only'}
            use_wavelet     = _b not in {'cnn_only', 'no_dwt'}
            use_multiscale  = _b not in {'no_multiscale'}

            if self.use_local:
                self.local_branch = LocalFeatureExtractor(
                    img_size=img_size, pretrained=False, drop_path=drop_path,
                    use_wavelet=use_wavelet, use_multiscale=use_multiscale, local_dim=local_dim,
                )
            else:
                self.local_branch = None

            if self.use_global:
                self.global_branch = GlobalFeatureExtractor(vit_name=vit_name, img_size=img_size)
            else:
                self.global_branch = None

            gate_disabled = _b in {'concat', 'no_gate'} or not (self.use_local and self.use_global)
            self.use_gate = not gate_disabled

            if self.use_local and not self.use_global:
                projector_in = local_dim
            elif self.use_global and not self.use_local:
                projector_in = self.global_branch.out_dim
            elif self.use_gate:
                self.gate = CrossBranchGate(local_dim, self.global_branch.out_dim, d_model=d_model)
                projector_in = d_model
            else:
                projector_in = local_dim + self.global_branch.out_dim

            self.projector = nn.Sequential(
                nn.LayerNorm(projector_in),
                nn.Linear(projector_in, d_model),
                nn.GELU(),
            )
            self.classifier = nn.Linear(d_model, num_classes)

            if use_hierarchical:
                self.coarse_classifier = nn.Sequential(
                    nn.Linear(d_model, d_model // 2), nn.GELU(),
                    nn.Dropout(0.1), nn.Linear(d_model // 2, num_coarse_classes),
                )

        def forward(self, x):
            f_local = self.local_branch(x)[0] if self.use_local else None
            f_global = self.global_branch(x) if self.use_global else None
            if self.use_local and not self.use_global:
                fused = f_local
            elif self.use_global and not self.use_local:
                fused = f_global
            elif self.use_gate:
                fused = self.gate(f_local, f_global)
            else:
                fused = torch.cat([f_local, f_global], dim=-1)
            proj   = self.projector(fused)
            logits = self.classifier(proj)
            return {'logits': logits, 'embedding': proj}

    return CitrusHVT


# ================================================================
# 标准类别列表（按字母序，与数据集 Citrus_Final_Dataset 文件夹顺序一致）
# 数据集共 17 类，不含 HLB（黄龙病）
# ================================================================
CITRUS_CLASSES_18 = [          # 保持变量名兼容，实际 17 类
    "Algal_Leaf_Spot",         # 0  青苔病
    "Anthracnose",             # 1  炭疽病
    "Aphids",                  # 2  蚜虫
    "Brown_Spot",              # 3  褐斑病
    "Citrus_Canker",           # 4  溃疡病
    "Deficiency_Iron",         # 5  缺铁症
    "Deficiency_Magnesium",    # 6  缺镁症
    "Deficiency_Manganese",    # 7  缺锰症
    "Deficiency_Nitrogen",     # 8  缺氮症
    "Deficiency_Zinc",         # 9  缺锌症
    "Greasy_Spot",             # 10 脂点黄斑病
    "Healthy",                 # 11 健康
    "Leaf_Miner",              # 12 潜叶蛾
    "Melanose",                # 13 树脂病
    "Red_Spider",              # 14 红蜘蛛
    "Scale_Insect",            # 15 吹绵蚧
    "Sooty_Mold",              # 16 煤烟病
]

# 英文 -> 中文显示名
EN_TO_ZH = {
    "Algal_Leaf_Spot": "青苔病",
    "Anthracnose": "炭疽病",
    "Aphids": "蚜虫",
    "Brown_Spot": "褐斑病",
    "Citrus_Canker": "溃疡病",
    "Deficiency_Iron": "缺铁症",
    "Deficiency_Magnesium": "缺镁症",
    "Deficiency_Manganese": "缺锰症",
    "Deficiency_Nitrogen": "缺氮症",
    "Deficiency_Zinc": "缺锌症",
    "Greasy_Spot": "脂点黄斑病",
    "Healthy": "健康",
    "Leaf_Miner": "潜叶蛾",
    "Melanose": "树脂病",
    "Red_Spider": "红蜘蛛",
    "Scale_Insect": "吹绵蚧",
    "Sooty_Mold": "煤烟病",
}

# 细类 -> 粗类（健康/病害/虫害/缺素）
FINE_TO_COARSE = {
    "Algal_Leaf_Spot": "病害",
    "Anthracnose": "病害",
    "Brown_Spot": "病害",
    "Citrus_Canker": "病害",
    "Greasy_Spot": "病害",
    "Melanose": "病害",
    "Sooty_Mold": "病害",
    "Aphids": "虫害",
    "Leaf_Miner": "虫害",
    "Red_Spider": "虫害",
    "Scale_Insect": "虫害",
    "Deficiency_Iron": "缺素",
    "Deficiency_Magnesium": "缺素",
    "Deficiency_Manganese": "缺素",
    "Deficiency_Nitrogen": "缺素",
    "Deficiency_Zinc": "缺素",
    "Healthy": "健康",
}

# 模糊推理引擎使用的疾病中文名（用于快通路对照）
VISION_TO_FUZZY_MAP = {
    "Anthracnose": "炭疽病",
    "Citrus_Canker": "溃疡病",
    "Greasy_Spot": "脂点黄斑病",
    "Red_Spider": "红蜘蛛",
    "Leaf_Miner": "潜叶蛾",
    "Aphids": None,
    "Scale_Insect": None,
    "Melanose": None,
    "Brown_Spot": None,
    "Algal_Leaf_Spot": None,
    "Sooty_Mold": None,
    "Healthy": None,
    "Deficiency_Iron": None,
    "Deficiency_Magnesium": None,
    "Deficiency_Manganese": None,
    "Deficiency_Nitrogen": None,
    "Deficiency_Zinc": None,
}

# OOD 能量阈值（能量分数 < threshold 认为 in-distribution）
OOD_ENERGY_THRESHOLD = -15.0


class VisionEngine:
    """
    CitrusHVT 本地推理引擎

    第一次调用 predict_* 时延迟加载权重，不阻塞服务启动。
    """

    MODEL_PATH = Path(__file__).parent.parent.parent / "models" / "convnext" / "best.pt"

    def __init__(self):
        self._model = None
        self._class_names: List[str] = CITRUS_CLASSES_18
        self._device = "cpu"
        self._ready = False
        self._load_error: Optional[str] = None

    # ----------------------------------------------------------
    # 初始化 / 加载
    # ----------------------------------------------------------
    def _load(self):
        if self._ready or self._load_error:
            return
        if not _ensure_torch():
            self._load_error = "PyTorch 未安装"
            return
        try:
            import torch
            from torchvision import transforms as T

            self._device = "cuda" if torch.cuda.is_available() else "cpu"
            logger.info(f"[VisionEngine] 使用设备: {self._device}")

            if not self.MODEL_PATH.exists():
                self._load_error = f"模型文件不存在: {self.MODEL_PATH}"
                logger.warning(f"[VisionEngine] {self._load_error}")
                return

            checkpoint = torch.load(str(self.MODEL_PATH), map_location="cpu", weights_only=False)
            state_dict = checkpoint.get("model", checkpoint)

            # ── 从 checkpoint key/shape 精确推断所有架构参数 ─────────────────
            # classifier = Linear(d_model, num_classes)  →  weight [num_classes, d_model]
            if "classifier.weight" in state_dict:
                num_classes = state_dict["classifier.weight"].shape[0]
                d_model     = state_dict["classifier.weight"].shape[1]
            else:
                num_classes = len(CITRUS_CLASSES_18)
                d_model     = 384

            # local_dim：local_branch.fusion.0 = Conv2d(fusion_in, local_dim, 1)
            #   → weight [local_dim, fusion_in, 1, 1]
            if "local_branch.fusion.0.weight" in state_dict:
                local_dim = state_dict["local_branch.fusion.0.weight"].shape[0]
            elif "gate.proj_local.weight" in state_dict:
                # 旧版：从 gate 的 proj_local 推断
                local_dim = state_dict["gate.proj_local.weight"].shape[1]
            else:
                local_dim = 256

            # baseline 推断：
            #   cnn_only  → 无 global_branch, 无 gate
            #   full+gate → 有 gate.proj_local
            #   full+concat → 有 global_branch, 无 gate
            has_global = any(k.startswith("global_branch.") for k in state_dict)
            has_gate   = "gate.proj_local.weight" in state_dict
            if not has_global:
                # 纯 CNN（可能有/无小波茎）
                has_wavelet_stem = any(k.startswith("local_branch.wavelet_stem.blocks") for k in state_dict
                                       if not k.endswith(".out_norm.weight") and "Identity" not in k)
                baseline = "wavecnn_only" if has_wavelet_stem else "cnn_only"
            elif has_gate:
                baseline = "full"
            else:
                baseline = "concat"

            # 层次分类头
            use_hierarchical   = "coarse_classifier.3.weight" in state_dict
            num_coarse_classes = (state_dict["coarse_classifier.3.weight"].shape[0]
                                  if use_hierarchical else 4)

            logger.info(
                f"[VisionEngine] checkpoint 推断: baseline={baseline}, num_classes={num_classes}, "
                f"d_model={d_model}, local_dim={local_dim}, "
                f"use_hierarchical={use_hierarchical}, num_coarse_classes={num_coarse_classes}"
            )

            # 构建模型（与 notebook 保持一致的架构）
            CitrusHVT = _build_model_classes()
            model = CitrusHVT(
                num_classes=num_classes,
                d_model=d_model,
                local_dim=local_dim,
                baseline=baseline,
                use_hierarchical=use_hierarchical,
                num_coarse_classes=num_coarse_classes,
            )
            model.load_state_dict(state_dict, strict=False)
            model.eval()
            model.to(self._device)
            self._model = model

            # 更新 class_names（如果 num_classes 与标准列表不符，使用索引）
            if num_classes == len(CITRUS_CLASSES_18):
                self._class_names = CITRUS_CLASSES_18
            else:
                logger.warning(f"[VisionEngine] num_classes={num_classes} 与标准类别数 {len(CITRUS_CLASSES_18)} 不符，使用索引作为标签")
                self._class_names = [f"class_{i}" for i in range(num_classes)]

            self._transforms = T.Compose([
                T.Resize(256),
                T.CenterCrop(224),
                T.ToTensor(),
                T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
            ])
            self._ready = True
            logger.info(f"[VisionEngine] 模型加载成功，{num_classes} 类")

        except Exception as e:
            self._load_error = str(e)
            logger.error(f"[VisionEngine] 模型加载失败: {e}", exc_info=True)

    # ----------------------------------------------------------
    # 图像预处理 & 推理
    # ----------------------------------------------------------
    def _preprocess(self, pil_img) -> "torch.Tensor":
        return self._transforms(pil_img).unsqueeze(0).to(self._device)

    def _infer(self, tensor) -> Dict[str, Any]:
        import torch
        with torch.no_grad():
            out = self._model(tensor)
            logits = out["logits"]
            probs = torch.softmax(logits, dim=-1)[0]
            energy = -torch.logsumexp(logits, dim=-1).item()

        probs_np = probs.cpu().numpy().tolist()
        top_k = 3
        indices = sorted(range(len(probs_np)), key=lambda i: probs_np[i], reverse=True)[:top_k]

        top_k_results = []
        for idx in indices:
            name = self._class_names[idx] if idx < len(self._class_names) else f"class_{idx}"
            zh_name = EN_TO_ZH.get(name, name)
            coarse = FINE_TO_COARSE.get(name, "未知")
            top_k_results.append({
                "rank": len(top_k_results) + 1,
                "class_en": name,
                "class_zh": zh_name,
                "coarse_class": coarse,
                "probability": round(probs_np[idx], 4),
            })

        top1 = top_k_results[0]
        is_ood = energy < OOD_ENERGY_THRESHOLD

        return {
            "top_k": top_k_results,
            "top1_class": top1["class_en"],
            "top1_class_zh": top1["class_zh"],
            "top1_coarse": top1["coarse_class"],
            "top1_prob": top1["probability"],
            "energy_score": round(energy, 4),
            "is_ood": is_ood,
            "fuzzy_disease_key": VISION_TO_FUZZY_MAP.get(top1["class_en"]),
        }

    # ----------------------------------------------------------
    # 公开接口
    # ----------------------------------------------------------
    def predict_from_pil(self, pil_img) -> Dict[str, Any]:
        self._load()
        if not self._ready:
            return {"error": self._load_error or "模型未就绪", "available": False}
        try:
            tensor = self._preprocess(pil_img.convert("RGB"))
            result = self._infer(tensor)
            result["available"] = True
            return result
        except Exception as e:
            logger.error(f"[VisionEngine] 推理失败: {e}", exc_info=True)
            return {"error": str(e), "available": False}

    def predict_from_bytes(self, image_bytes: bytes) -> Dict[str, Any]:
        try:
            from PIL import Image
            pil_img = Image.open(io.BytesIO(image_bytes))
            return self.predict_from_pil(pil_img)
        except Exception as e:
            return {"error": f"图像解码失败: {e}", "available": False}

    def predict_from_path(self, path: str) -> Dict[str, Any]:
        try:
            from PIL import Image
            return self.predict_from_pil(Image.open(path))
        except Exception as e:
            return {"error": f"读取文件失败: {e}", "available": False}

    def predict_from_url(self, url: str, timeout: int = 10) -> Dict[str, Any]:
        """支持 http(s) URL 和本地 /uploads/ URL"""
        try:
            from PIL import Image
            # 本地文件（uploads 目录）
            if url.startswith("/") or url.startswith("file://"):
                local = url.replace("file://", "")
                return self.predict_from_path(local)

            # 检查是否是 data:image/... base64
            if url.startswith("data:image"):
                import base64
                header, b64data = url.split(",", 1)
                image_bytes = base64.b64decode(b64data)
                return self.predict_from_bytes(image_bytes)

            # HTTP(S)
            import requests as req_lib
            resp = req_lib.get(url, timeout=timeout)
            resp.raise_for_status()
            return self.predict_from_bytes(resp.content)

        except Exception as e:
            return {"error": f"URL 获取失败: {e}", "available": False}

    @property
    def is_available(self) -> bool:
        self._load()
        return self._ready


# 全局单例
vision_engine = VisionEngine()
