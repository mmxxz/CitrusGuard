# CitrusGuard 前端开发待办清单 (对接阶段)

本文件由 Gemini Agent 创建并维护，用于跟踪 CitrusGuard 前端与后端 API 的对接进度。

---

### Phase 9: Backend Integration - Authentication & Setup (PO)
- [x] **9.1:** Create `.env.local` file in the `project` directory and set `VITE_API_BASE_URL=http://127.0.0.1:8000`.
- [x] **9.2:** Update `apiClient.ts` to use Axios for real API calls. Implement a global Axios instance that attaches the JWT token to all requests.
- [x] **9.3:** Connect `Login.tsx` and `Register.tsx` pages to the real backend endpoints. Manage JWT token in `localStorage`.
- [x] **9.4:** Connect `OrchardSetup.tsx` to the `POST /orchards` and `PUT /orchards/{id}` endpoints.

### Phase 10: Backend Integration - Core Features (P0)
- [x] **10.1:** Connect `Dashboard.tsx` to the live `health_overview` and `alerts` endpoints.
- [x] **10.2:** Connect `Alerts.tsx` to the live `GET /orchards/{id}/alerts` endpoint.
- [x] **10.3:** Connect `Cases.tsx` to the live `GET /orchards/{id}/cases` endpoint.

### Phase 11: Backend Integration - Diagnosis Workflow (P0)
- [x] **11.1:** Update the `Diagnosis.tsx` page to use the real `POST /upload/image` endpoint.
- [x] **11.2:** Connect the "start" and "continue" diagnosis logic to the real backend API endpoints.
- [x] **11.3:** Implement a WebSocket client (`services/ws.ts`) and connect it in `Diagnosis.tsx` to receive and display real-time progress updates.
- [x] **11.4:** Implement logic to handle different AI response types (`clarification`, `diagnosis_result`) and fetch the final report from the `GET /{session_id}/result` endpoint.

### Phase 12: 数据闭环 - 农事记录 (P1)
- [x] **12.1:** 在 `types/index.ts` 中添加 `FarmOperation` 相关类型定义。
- [x] **12.2:** 在 `apiClient.ts` 中添加 `recordFarmOperation` API 函数。
- [x] **12.3:** 创建一个可复用的 `components/FarmOperationForm.tsx` 组件，用于填写防治措施。
- [x] **12.4:** 在 `Diagnosis.tsx` 中实现一个模态框（Modal），当用户点击 `ResultCard` 上的“记录至病例档案”按钮时，该模态框会弹出，并包含农事记录表单。
- [x] **12.5:** 将表单的提交逻辑连接到 `recordFarmOperation` API 调用，并在成功后关闭模态框，并更新病例档案页面。


### Phase 13: UX 优化与数据闭环完善 (P1)
- [ ] **13.1: 优化进度反馈**
    - [ ] 在 `Diagnosis.tsx` 的 WebSocket 处理器中，创建一个映射（Map），将后端发送的节点名称翻译成用户友好的文本。
- [ ] **13.2: 完善“记录至档案”**
    - [ ] 修改 `ResultCard.tsx` 中的 `onRecord` 函数，使其调用一个新的 `POST /cases/{diagnosis_id}/archive` API。
    - [ ] 成功后，提示用户“已存入病例档案”，并提供跳转链接。
- [ ] **13.3: 创建病例详情与反馈页面 (`pages/CaseDetail.tsx`)**
    - [ ] 创建一个新的页面，用于展示单个病例的详细信息。
    - [ ] 在此页面下方，集成 `FarmOperationForm.tsx` 组件，允许用户记录相关的农事操作。
    - [ ] 在农事操作记录下方，添加一个新的“效果反馈”表单。
- [ ] **13.4: 更新后端 API 以支持反馈**
    - [ ] 在 `backend` 中，实现 `POST /operations/{operation_id}/feedback` API 端点。
---

## 进展记录
- **2025-09-19:** 完成 Phase 9，实现了完整的前后端认证与果园设置流程对接。
- **2025-09-20:** 完成 Phase 10，实现了核心功能页面与后端 API 的对接。
- **2025-09-20:** 修复了所有前后端集成问题，包括模块导入错误、类型定义缺失、用户注册数据格式、循环导入、安全问题和数据库约束问题。应用程序现在完全正常运行。
- **2025-09-20:** 完成 Phase 11，成功对接了包含图片上传、实时进度和卡片渲染的完整诊断工作流。
- **2025-09-20:** 完成 Phase 12，实现了将诊断结果记录为农事操作的数据闭环功能。

---

## 问题与解决方案
- **CORS Error**: 前端无法访问后端 API，因为缺少 CORS 头。**解决方案**: 在 `main.py` 中添加 FastAPI 的 `CORSMiddleware`，允许来自前端源 (`http://localhost:5173`) 的请求。
- **404 Not Found for /users/me**: 前端 `useAppStore` 尝试获取当前用户信息失败。**解决方案**: 在后端 `api/v1/users.py` 中添加 `/me` 端点，并修复 `useAppStore` 中的数据获取逻辑。
- **422 Unprocessable Entity on Register**: 用户注册失败，因为前端发送的 `phone` 字段与后端期望的 `email` 格式不匹配。**解决方案**: 将前端注册表单从手机号改为邮箱，确保数据格式一致。
- **前端代码误删**: 在一次重构中，`Diagnosis.tsx` 的输入栏和上传功能被意外移除。**解决方案**: 通过代码比对和恢复，将完整功能的 JSX 代码重新写入文件。