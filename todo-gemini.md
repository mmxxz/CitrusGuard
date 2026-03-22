# Gemini 开发待办清单 (本地 MVP)

本文件由 Gemini Agent 创建并维护，用于跟踪 CitrusGuard 前端 MVP 版本的开发进度。

**核心目标**：构建一个结构清晰、可扩展、基于**模拟数据**的前端应用，为后续接入真实后端 API 做好准备。

---

### Phase 1: 项目基础与结构重构 (P0)
- [x] **1.1:** 创建标准化的项目目录结构 (`pages`, `components`, `services`, `types`, `hooks`, `lib`)
- [x] **1.2:** 安装并配置 React Router (`react-router-dom`)
- [x] **1.3:** 安装并配置 Zustand 用于全局状态管理
- [x] **1.4:** 安装 Axios 用于 API 请求

### Phase 2: 组件化与页面拆分 (P0)
- [x] **2.1:** 拆分 `App.tsx`，创建基础路由和包含底部导航的 `Layout` 组件
- [x] **2.2:** 将 "战略沙盘" 逻辑迁移到 `pages/Dashboard.tsx`
- [x] **2.3:** 将 "风险预警" 逻辑迁移到 `pages/Alerts.tsx`
- [x] **2.4:** 将 "诊断实验室" 逻辑迁移到 `pages/Diagnosis.tsx`
- [x] **2.5:** 将 "病例档案" 逻辑迁移到 `pages/Cases.tsx`
- [x] **2.6:** 将可复用 UI (如 `SmartOrchard`, `RiskCard`, `ChatMessage`) 拆分为独立的组件

### Phase 3: 数据服务层 (P0)
- [x] **3.1:** 在 `types/index.ts` 中定义核心 TypeScript 接口 (Orchard, Alert, DiagnosisSession 等)
- [x] **3.2:** 创建 `services/mock.ts` 并填充符合接口的模拟数据
- [x] **3.3:** 创建 `services/apiClient.ts`，封装 Axios 并导出调用模拟数据的 API 函数
- [x] **3.4:** 创建 Zustand store (`useAppStore`) 管理全局状态 (如用户信息、当前果园)

### Phase 4: UI 与模拟数据对接 (P1)
- [x] **4.1:** 在 Dashboard 页面接入 mock service 获取健康度、天气和简报
- [x] **4.2:** 在 Alerts 页面接入 mock service 展示风险列表
- [x] **4.3:** 在 Diagnosis 页面模拟诊断对话流程
- [x] **4.4:** 在 Cases 页面接入 mock service 展示病例列表

### Phase 5: 用户引导与果园管理 (P1)
- [x] **5.1:** 创建 `pages/Welcome.tsx` 启动与引导页
- [x] **5.2:** 创建可复用的 `pages/OrchardSetup.tsx` 用于创建和编辑果园信息
- [x] **5.3:** 更新应用路由 (`App.tsx`)，添加 `/welcome` 和 `/orchard-setup` 路由
- [x] **5.4:** 实现首次使用逻辑：利用 `localStorage` 判断是否已完成引导，并自动跳转
- [x] **5.5:** 在 `Dashboard.tsx` 页面顶部新增 "我的果园" 入口，链接到编辑模式
- [x] **5.6:** 更新 `apiClient.ts`，添加模拟保存果园信息的函数

### Phase 6: 登录与注册流程 (P1)
- [x] **6.1:** 将 `Welcome.tsx` 重构为 `pages/Login.tsx`，包含手机号/密码输入和登录按钮。
- [x] **6.2:** 创建新的 `pages/Register.tsx` 页面（复用 `OrchardSetup.tsx` 的表单样式）。
- [x] **6.3:** 更新 `apiClient.ts`，添加模拟的 `login` 和 `register` 函数。
- [x] **6.4:** 更新路由 (`App.tsx`)，将 `/welcome` 替换为 `/login` 和 `/register`。
- [x] **6.5:** 调整 `OnboardingWrapper` 逻辑，使其在用户未登录时重定向到 `/login`。
- [x] **6.6:** 确保 `Login.tsx` 和 `OrchardSetup.tsx` 的布局尺寸和 UI 风格与应用核心页面保持一致。

### Phase 7: UI/UX 优化 (P1)
- [x] **7.1:** 重构诊断页面为全屏聊天布局，移除主导航栏。

### Phase 8: Diagnosis UX & Feature Enhancement (P1)
- [x] **8.1:** Constrain the width of `Diagnosis.tsx` to `max-w-md` to match the rest of the application's layout.
- [x] **8.2:** Implement a pop-up action menu when the "+" button is clicked, offering "拍照" and "从相册选择".
- [x] **8.3:** Add the logic to trigger the system camera or file selector and handle the selected image.
- [x] **8.4:** Display a preview of the selected image in the chat window before sending.
- [x] **8.5:** Update `apiClient.ts` to simulate image upload and include the image URL in the diagnosis message.

---

## 进展记录
- **2025-09-19:** 完成 Phase 1，项目基础结构与依赖配置完毕。
- **2025-09-19:** 完成 Phase 2，完成页面拆分与初步组件化。
- **2025-09-19:** 完成 Phase 3，数据服务层、类型与状态管理搭建完毕。
- **2025-09-19:** 完成 Phase 4，所有页面均已接入模拟数据服务。
- **2025-09-19:** 完成 Phase 5，实现了新用户引导流程与果园信息编辑功能。
- **2025-09-19:** 完成 Phase 6，重构为登录/注册流程，并统一了 UI 风格。
- **2025-09-19:** 完成 Phase 7，优化诊断实验室为全屏沉浸式聊天界面。
- **2025-09-19:** 完成 Phase 8，为诊断实验室添加了图片上传功能并优化了布局。

---

## 问题与解决方案
*(此处将记录开发过程中遇到的问题及其解决方法)*
