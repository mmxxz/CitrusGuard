# CitrusHVT 训练（ConvNeXt）

- **`citrushvt-full-training-5.ipynb`**：完整训练流程；产出权重请导出为 `best.pt` 并放到 **`backend/models/convnext/best.pt`**，供后端 `VisionEngine` 加载。

推理代码与 notebook 中的模型定义应对齐；若改架构，需同步更新 `app/services/vision_engine.py` 中的 `_build_model_classes()`。
