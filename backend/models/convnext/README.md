# CitrusHVT 推理权重（ConvNeXt）

运行时由 `app/services/vision_engine.py` 加载本目录下的 **`best.pt`**。

## 文件说明

| 文件 | 说明 |
|------|------|
| `best.pt` | 训练得到的最佳检查点（约 325MB） |

## 上传到 GitHub

单文件超过 [100MB 限制](https://docs.github.com/repositories/working-with-files/managing-large-files/about-git-large-file-storage) 时，请使用 **Git LFS**：

```bash
git lfs install
git lfs track "backend/models/convnext/best.pt"
git add .gitattributes backend/models/convnext/best.pt
```

若仓库根目录已有 `.gitattributes` 且包含上述 track 规则，直接 `git add` 即可。

## 训练脚本

训练与复现实验见：**`backend/training/convnext/citrushvt-full-training-5.ipynb`**（与 `vision_engine.py` 中模型结构保持一致）。
