产品规划总结 (Product Plan Summary)
1. 项目名称 (Project Name)
CitrusGuard AI (1)
2. 项目愿景 (Project Vision)
我们的愿景是打造一个名为 
CitrusGuard AI 的智能果园管理代理系统 (2)。它不仅仅是一个工具，而是扮演着一位全天候在线的“AI农艺师”或果园“智能二把手”的角色 (3)。
该系统深度融合了果园的各项个性化信息，包括地理位置、实时天气、历史病虫害记录、土壤条件等，从而实现从被动管理到主动预警的根本性转变 (4)。最终目标是为果农提供贯穿“
预防、识别、治理、评估”全周期的智能决策辅助，成为他们最可靠的管理伙伴 (5)。
3. 核心用户 (Core User)
经过深入分析，我们将核心用户群体进行更精准的定位：
- 主要核心用户 (Primary Core User): 中小型商业种植户及科技驱动的家庭农场主。
  - 特征: 他们是农业生产的直接决策者和执行者，面临着巨大的经营风险和技术挑战。他们规模不足以聘请全职农艺师，但又迫切需要科学、精准的管理指导来提升产量和效益。他们对能带来明确投资回报的新技术持开放态度。
- 扩展用户 (Extended Users):
  - 农业技术员、农业合作社技术负责人 (6)。他们可以利用本系统作为效率倍增工具，为多个果园提供更高质量的远程指导和管理服务。
  - 农业服务公司 (7)。可作为未来生态平台中的合作伙伴。
4. 核心痛点解决 (Core Problems Solved)
本产品旨在解决当前果园管理中的四大核心痛点：
- 从被动管理到主动预警：改变以往问题发生后才补救的模式，转向基于数据预测的前瞻性预防 (8)。
- 从诊断困难到AI辅助诊断：利用AI多模态识别能力，解决因病虫害症状复杂、相似而导致的误判难题 (9)。
- 从信息孤岛到多维信息融合：整合图像、环境、气象及历史农事数据，进行综合性、立体化决策 (10)。
- 从人力密集到智能化管理：通过智能预警和精准诊断，减少果农频繁实地巡查的负担，显著提升管理效率 (11)。
5. 核心竞争力 (Core Competency)
产品的核心竞争力并非单一的AI技术，而是将多维度的超本地化数据，智能合成为高度可信、可执行的农业决策建议的能力。
具体体现在三个方面：
  1. 深度数据融合能力: 能够实时融合分析用户上传的视觉信息、第三方天气数据、果园历史档案和专业知识库，形成一个动态的、完整的果园“数字画像” (12)。
  2. 超个性化决策支持: 所有的诊断和建议都基于特定果园的独特环境和历史状况，而非提供通用的解决方案。
  3. 系统化的信任构建: 通过展示AI分析的置信度、提供清晰的推理依据，并设置“专家复核”通道作为保障，逐步与用户建立牢固的信任关系 (13)。
6. 商业模式 (Business Model)
我们采用分阶段的商业化路径：
- 第一阶段：打造核心产品价值 (Build Core Product Value)
  - 目标: 专注于为核心用户提供极致的产品体验，成为其日常管理不可或缺的工具，以此建立高粘性的用户基础。
  - 模式: 采用免费增值 (Freemium)模式，例如提供有限次的免费诊断 (14)，或针对高级功能（如全年风险预测、数据看板等）的
  - 低成本订阅制，以降低用户使用门槛，快速积累用户。
- 第二阶段：构建农业生态平台 (Build an Ecosystem Platform)
  - 目标: 在拥有坚实的用户基础后，引入果园管理的上下游服务商。
  - 模式: 转型为平台模式，通过为用户精准对接农资供应商、农业服务公司、专家咨询服务等，开拓增值服务和佣金收入，实现商业价值的规模化放大。

2. 用户故事（User Story）
角色
用户故事
验收标准
优先级
种植户
作为种植户，我希望每天查看果园健康仪表盘，以便快速了解果园整体状况
能够在主页面看到果园健康度评分、天气信息、AI简报，数据更新及时
P0
种植户
作为种植户，我希望拍照识别叶片病害，以便快速确认问题类型
上传照片后5秒内得到AI识别结果，准确率达到85%以上
P0
种植户
作为种植户，我希望与AI进行对话式诊断，以便描述复杂症状获得准确建议
支持文字和语音输入，AI能理解症状描述并给出针对性建议
P0
种植户
作为种植户，我希望接收病害风险预警，以便提前采取预防措施
基于天气、历史数据等因素提前1-3天发出风险预警
P1
种植户
作为种植户，我希望查看历史诊断记录，以便总结种植经验
能够按时间、病害类型查询历史记录，支持导出功能
P1
种植户
作为种植户，我希望记录农事操作，以便跟踪处理效果
能够记录施药、施肥等操作，关联具体诊断记录
P2
3. 功能需求详述
3.1 功能架构总览
模块名称
核心功能
主要特性
依赖关系
战略沙盘
果园健康监控仪表盘
实时数据展示、AI简报生成、健康度评估
用户管理、数据分析
风险预警中心
智能预警系统
多维数据分析、风险等级评估、预警推送
气象数据、历史数据
诊断实验室
AI病害诊断
图像识别、对话式诊断、治疗建议
AI模型、知识库
病例档案库
历史记录管理
诊断记录、农事日志、数据统计
数据存储、用户管理
用户管理
账户与设置管理
注册登录、个人信息、果园配置
基础服务模块
3.2 详细功能说明
功能项
功能描述
用户交互
系统行为
限制条件
异常处理
用户注册
新用户创建账户
输入手机号、密码、验证码，设置果园基本信息
验证信息有效性，创建用户档案，发送欢迎消息
手机号唯一，密码强度要求
手机号重复提示，验证码失效重发
用户登录
已注册用户账户验证
输入手机号和密码，可选择记住登录状态
验证凭据，生成访问令牌，跳转主页
连续失败5次锁定30分钟
密码错误提示，账户锁定通知
健康度仪表盘
果园整体健康状况展示
查看健康度评分、趋势图表、关键指标
实时计算健康度，展示可视化图表，生成简要分析
需要完成果园初始化配置
数据缺失时显示历史均值
天气信息展示
当前及未来天气预报
查看当天天气，滑动查看7天预报
获取地理位置天气数据，分析对果园的影响
需要位置授权
定位失败使用手动设置位置
AI每日简报
智能生成的果园管理建议
阅读AI生成的简报内容，查看详细建议
分析多维数据生成个性化简报
需要足够的历史数据支撑
数据不足时提供通用建议
图像诊断
通过拍照识别病害
拍照或选择相册图片，等待识别结果
AI模型分析图像，返回病害类型和置信度
图片清晰度要求，支持常见图片格式
识别失败提示重新拍照
对话诊断
通过描述症状进行诊断
文字或语音描述症状，与AI进行多轮对话
理解用户描述，提出针对性问题，给出诊断建议
需要网络连接
连接中断时保存对话状态
风险预警
基于多维数据的风险预测
查看预警列表，点击查看详细风险分析
分析天气、历史病害、季节性因素，计算风险等级
需要完整的环境数据
数据异常时降级为通用预警
诊断记录查询
历史诊断记录管理
按时间、病害类型筛选记录，查看详情
检索历史数据，展示列表和详情页面
记录保存期限为2年
查询超时时分页加载
农事记录
记录农事操作活动
添加施药、施肥等操作记录，关联诊断记录
保存操作信息，建立与诊断的关联关系
操作类型预定义
保存失败时本地缓存
4. 交互流程设计
4.1 主要业务流程
4.1.1 用户注册流程
1. 进入注册页面
  - 触发条件：首次安装应用或点击注册按钮
  - 用户操作：点击"立即注册"按钮
  - 系统反馈：跳转到注册页面
2. 填写基本信息
  - 前置条件：进入注册页面
  - 用户操作：输入手机号、密码、确认密码
  - 系统反馈：实时验证输入格式，显示密码强度提示
3. 手机验证
  - 前置条件：基本信息验证通过
  - 用户操作：点击"获取验证码"，输入收到的验证码
  - 系统反馈：发送验证码，显示60秒倒计时，验证码校验
4. 果园信息配置
  - 前置条件：手机验证通过
  - 用户操作：输入果园名称、位置、种植品种、面积
  - 系统反馈：地图选择位置，自动匹配气候区域
5. 完成注册
  - 前置条件：所有信息填写完整
  - 用户操作：点击"完成注册"
  - 系统反馈：创建账户，自动登录，跳转主页
4.1.2 AI诊断流程
6. 进入诊断模式
  - 触发条件：发现疑似病害需要诊断
  - 用户操作：点击底部导航"诊断实验室"
  - 系统反馈：展示诊断选项（拍照诊断、对话诊断）
7. 图像诊断路径
  - 用户操作：选择"拍照诊断"，拍摄或选择图片
  - 系统反馈：显示图片预览，确认后开始AI分析
  - 处理逻辑：调用图像识别模型，返回识别结果
8. 对话诊断路径
  - 用户操作：选择"对话诊断"，描述观察到的症状
  - 系统反馈：AI提出针对性问题，引导用户描述
  - 处理逻辑：多轮对话收集症状信息，综合分析诊断
9. 诊断结果展示
  - 前置条件：AI分析完成
  - 系统反馈：显示病害类型、置信度、症状描述、治疗建议
  - 用户操作：查看详细信息，选择保存或分享
10. 后续操作
  - 用户操作：保存诊断记录，添加农事操作计划
  - 系统反馈：记录保存成功，建议设置提醒
4.1.3 风险预警流程
11. 数据收集分析
  - 触发条件：系统定时任务（每日凌晨2点）
  - 系统行为：收集天气数据、分析历史病害模式
  - 处理逻辑：运行风险评估算法，计算各类风险等级
12. 风险等级判定
  - 系统行为：根据算法结果确定风险等级（低、中、高、极高）
  - 处理逻辑：考虑天气变化、季节性因素、历史发病规律
13. 预警推送
  - 触发条件：风险等级达到中等及以上
  - 系统行为：生成预警消息，推送给相关用户
  - 用户感知：收到推送通知，查看预警详情
14. 预警处理
  - 用户操作：点击预警通知，查看详细风险分析
  - 系统反馈：展示风险类型、影响评估、建议措施
  - 用户操作：标记已读或添加预防性农事操作
4.2 异常流程处理
异常场景
触发条件
用户感知
系统处理
恢复机制
网络连接失败
设备无网络或网络不稳定
显示"网络连接异常"提示
启用离线模式，缓存用户操作
网络恢复后自动同步数据
AI识别失败
图片质量差或系统异常
显示"识别失败，请重新拍照"
记录失败日志，建议对话诊断
用户重新上传或切换诊断方式
定位获取失败
用户拒绝位置权限或GPS异常
提示"无法获取位置信息"
使用用户设置的默认位置
引导用户手动设置位置
验证码发送失败
短信服务异常或手机号异常
显示"验证码发送失败"
记录失败原因，尝试重发
提供客服联系方式
数据同步失败
服务器异常或数据冲突
显示"数据同步异常"
本地数据备份，标记同步状态
用户手动触发重新同步
登录会话过期
Token过期或安全策略触发
显示"登录已过期，请重新登录"
清除本地凭据，跳转登录页
用户重新登录恢复会话
5. 界面规范
5.1 应用路由架构
路由路径
页面名称
功能描述
访问权限
/welcome
欢迎页
应用介绍和引导
公开
/auth/register
注册页
用户注册流程
公开
/auth/login
登录页
用户登录
公开
/auth/forgot
忘记密码页
密码重置
公开
/home
战略沙盘（主页）
果园健康仪表盘
登录用户
/warning
风险预警中心
预警信息和风险分析
登录用户
/diagnosis
诊断实验室
AI病害诊断
登录用户
/diagnosis/camera
拍照诊断页
图像识别诊断
登录用户
/diagnosis/chat
对话诊断页
交互式诊断
登录用户
/diagnosis/result/:id
诊断结果页
诊断结果详情
登录用户
/records
病例档案库
历史记录管理
登录用户
/records/detail/:id
记录详情页
单条记录详情
登录用户
/profile
个人中心
用户信息管理
登录用户
/profile/orchard
果园设置页
果园信息配置
登录用户
/profile/settings
应用设置页
通知、隐私等设置
登录用户
/about
关于页面
应用信息和版本
公开
/privacy
隐私政策页
隐私条款
公开
/terms
用户协议页
服务条款
公开
5.2 公用UI组件规范
5.2.1 底部导航栏（Tab Bar）
- 使用范围: 主要功能页面（/home, /warning, /diagnosis, /records, /profile）
- 布局结构: 固定在屏幕底部，高度64px，背景色白色，顶部1px边框
- 导航项目:
  - 战略沙盘：图标+文字，选中时图标变色为主题绿色
  - 风险预警：图标+文字，有新预警时显示红色圆点
  - 诊断实验室：图标+文字，中间位置突出显示
  - 病例档案：图标+文字
  - 个人中心：图标+文字
- 交互规范: 点击切换页面，当前页面图标高亮显示
5.2.2 顶部导航栏（Navigation Bar）
- 使用范围: 所有页面（根据页面类型调整样式）
- 主页样式: 透明背景，白色文字，显示果园名称和设置按钮
- 子页面样式: 白色背景，深色文字，显示页面标题和返回按钮
- 高度: 88px（包含状态栏高度44px + 导航栏44px）
5.2.3 加载组件
- 骨架屏: 用于数据加载时的占位显示
- 加载指示器: 圆形进度指示器，主题绿色
- 下拉刷新: 自定义样式的下拉刷新动画
前端全景设计方案 (Comprehensive Frontend Design Plan)
1. 设计理念：从“指挥室”到“数字孪生伙伴”
我们摒弃传统后台管理系统的仪表盘式设计，将设计理念从“环境指挥室 (Ambient Command Center)” (1) 升维至“有生命感的数字孪生伙伴 (Living Digital Twin Companion)”。核心目标是创造一种直观、主动且富有情感连接的交互体验，让用户感觉自己不是在操作一个软件，而是在与一位了解他果园一切的智能助手并肩作战。
2. 核心隐喻：会呼吸的“智慧果园”
界面的核心是用户果园的具象化、可视化载体，我们称之为“智慧果园”。
- 动态视觉中心: 主界面中央是一个代表用户果园的动态视觉元素（例如一棵风格化的果树）。
- 状态实时反馈:
  - 健康度: 它的繁茂或衰败程度直接与后台计算的“健康度”分数挂钩。
  - 环境同步: 实时同步天气API数据 (2)，在界面上呈现晴、雨、多云等相应动效。
  - 物候期同步: 根据用户档案中的current_phenology（当前物候期）字段 (3)，在树上展示花、果、新梢等不同阶段的视觉特征。
- 交互式预警: 当特定风险（如红蜘蛛）等级升高时，树的相应部位（如叶片）会出现微弱的、可交互的视觉异常（如红点闪烁），引导用户关注。
3. 核心页面设计 (Core Page Designs)
通用设计元素 (General Design Elements):
- 字体: San Francisco (或类似)
- 颜色: 大量留白，少量柔和的自然色（绿色、棕色、淡蓝），强调色为活力绿/橙。
- 图标: 线性（Line Icon），风格统一，有适度填充，圆角。
- 控件: 扁平按钮，Switch/Toggle，滑块等。
- 动画: 预期流畅的过渡和微交互。
3.1. 战略沙盘 (Strategy Board) - 主仪表盘
这是用户打开应用看到的第一屏，旨在“一瞥即知”果园全局状态。
- 布局与组件:
  - 顶部状态栏: 左侧为实时天气图标和温度；右侧为核心指标“果园健康度”（百分比形式），当有新预警时，健康度旁会出现一个醒目的红点。
  - 中央视觉区: “智慧果园”的动态视觉模型。
  - AI助手简报: 位于视觉区下方，以卡片形式展示 (4)，每日生成一句友好且关键的提醒，如：“早上好，王先生。今天湿度较高，请重点关注溃疡病的潜在风险。” (5)。
  - 快捷操作栏: 两个最核心的操作按钮：“[开始诊断]”和“[记录农事]”，方便用户快速触达核心功能。
- 交互逻辑:
  - 点击“健康度”或红点，会平滑过渡到“风险预警中心”。
  - 点击“智慧果园”上的视觉异常热区，可直接筛选并展示相关的风险预警。
3.2. 风险预警中心 (Risk Alert Center)
当用户需要了解健康度下降的具体原因时进入此页面。
- 布局与组件:
  - 以信息流卡片列表的形式，清晰展示所有当前的风险预警。
  - 每张卡片都是一个“风险雷达 (Risk Radar)”  的条目，包含：
    - 风险项: 如“溃疡病”、“红蜘蛛”、“缺氮症”
    - 风险等级与置信度: “高”、“中”、“低” (7)。
- 核心原因: 简明扼要地解释AI做出此判断的依据，如“基于未来72小时高温高湿天气预报”、“根据近期叶片黄化历史记录”。
- 交互逻辑:
  - 每张卡片下方有两个操作按钮：
    - “[忽略]”：用户认为此风险不重要，点击后该预警暂时关闭，健康度会小幅回升，并记录用户行为以优化模型。
    - “[前往确认]”：用户认为需要跟进，点击后直接跳转至“诊断实验室”，并自动开启一段对话：“AI助手，我来确认一下[溃疡病]的风险。”
3.3. 诊断实验室 (Diagnosis Lab)
核心的人机交互诊断界面，采用现代对话式（Chat-based）UI。
- 布局与组件:
  - 对话区域: 展示用户与AI之间的交互历史，包括文本、图片和AI的分析卡片 (8)。
  - 多模态输入栏: 提供“上传图片/拍照”、“文字输入”入口。
  - Agent进度可视化: 当用户发送诊断请求后，在对话区会出现一个临时的状态提示框，实时展示Agent的工作流进度，建立用户信任感。例如：
AI 正在思考中...
[✓] 图像特征分析
[✓] 同步果园天气与历史数据
[ ] 检索知识库与相似病例
[ ] 生成初步诊断...
  - 交互式诊断卡片: 当AI判断信息不足需要追问时，会发送一张结构化的卡片 (9)，包含清晰的问题和选项（如单选、多选），用户直接在卡片上点选即可完成回答，而非手动输入。
- 交互逻辑:
  - 整个诊断流程是一问一答的对话形式。用户输入信息，AI进行分析，可能追问，用户补充信息，AI再分析，直至最终给出结构化的诊断报告。
  - 诊断报告包含：主要诊断、置信度、次要可能性、详细的防治建议和后续观察计划。
顶部导航栏:
- 左侧: 返回箭头图标。
- 标题: "诊断实验室" (居中大标题)。
对话区域:
- 气泡样式:
  - 用户消息: 右侧，浅绿色/蓝色填充，圆角。
  - AI消息: 左侧，浅灰色填充，圆角。
- 内容类型:
  - 文本消息: 普通文字。
  - 图片消息: 用户上传的图片以缩略图形式嵌入气泡。
  - Agent进度提示: 当AI工作时，显示一个实时更新的进度条/文字提示框（居中），如：
AI 正在进行分析...
✔️ 图像特征识别 (3s)
✔️ 获取果园历史数据 (1s)
⏳ 综合评估中... (预计 5s)
  - AI追问卡片: AI发送的结构化问卷。
    - 卡片标题：“请补充以下信息以帮助我更精准诊断”
    - 问题：如“病害主要发生部位？”
    - 选项：圆角按钮或列表项，用户点击即选中。
    - 底部按钮：“[确认提交]”
- AI诊断结果卡片: 诊断完成后，AI发送一张结构化的结果卡片（可展开/收起）。
  - 主要诊断: "柑橘红蜘蛛" (醒目字体，带置信度)
  - 次要可能性: "柑橘锈螨" (小字，带置信度)
  - 防治建议: 分点列出具体措施，如“喷施阿维菌素...”
  - 后续观察: 提醒用户需注意的事项。
  - 底部按钮：“[记录至档案]” (绿色填充)
底部输入栏:
- 文本输入框: 线性边框，无背景，左侧有“+”图标（展开多媒体选项），右侧有发送图标。
- 多媒体选项: 点击“+”弹出浮动菜单，包含“[拍照]”、“[从相册选择]”等图标。
风格: 清晰的对话流、反馈及时、易于操作。
3.4. 病例档案库 (Case File Library)
自动沉淀每一次诊断和农事操作，形成果园的“健康档案”。
- 布局与组件:
  - 以时间线或卡片列表的形式，展示所有历史“病例”。提供按病害类型、日期等维度的筛选和搜索功能。
- 交互逻辑与数据闭环:
  - 每次诊断完成后，系统会自动生成一个“病例档案”，存入此库。
  - 用户可以在对应的病例下，点击“+ 记录我的防治”，来记录自己的农事操作（对应后端farm_operations表）。
  - 在记录防治措施后，用户还可以进行“后续反馈”，上传防治后的图片，并评价防治效果（effectiveness_rating） (12)。
  - 闭环：用户的这次反馈，会作为高质量的已验证数据，被系统吸收，用于优化historical_cases（历史病例表） (13)，从而使AI的未来诊断更加精准，形成一个完美的数据飞轮。
  - 系统会基于防治记录和后续观察计划，在合适的时间（如7天后）发送推送通知，提醒用户进行效果评估，引导用户完成数据闭环。
4. 状态管理与响应式设计
- 状态管理: 鉴于交互的复杂性（如诊断会话状态、动态健康度、实时天气等），我们将采用 Zustand 作为状态管理库 。它能轻量级地管理全局状态，如currentUser、currentOrchard、activeDiagnosisSession等，并确保各组件间状态同步。
- 响应式设计: 遵循移动优先原则。通过自定义Hook（如useResponsiveLayout）来判断设备类型 (15)，并为移动端设计专用的底部标签导航栏（首页、诊断、记录、我的），确保在不同尺寸屏幕上都有一致且优秀的用户体验 (16)。
5. 前端技术栈
为实现上述设计，我们将沿用方案中选定的现代化技术栈：
- 核心框架: React + TypeScript + Vite (17)
- UI与样式: Tailwind CSS + shadcn/ui (18)
- 状态管理: Zustand (19)
- 路由: React Router (20)
- HTTP客户端: Axios (21)
- 部署平台: Vercel (22)




我们将遵循以下步骤来敲定前后端API、Agent设计（沿用）以及后端和数据库设计：
1. 梳理前端需求对应的后端功能点
2. 定义前后端 API 接口 (RESTful API Design)
3. 重申 Agent 设计方案 (沿用原始方案)
4. 后端服务设计 (FastAPI + Agent Orchestration)
5. 数据库设计 (PostgreSQL + Vector Database)

---


前后端 API 接口 (RESTful API Design)

我们将采用 RESTful API 风格，使用 JSON 作为数据交换格式。
通用规则：
- 所有请求需携带认证 Token (JWT)。
- 使用标准 HTTP 状态码。

2.1. 用户认证与管理 (User Authentication & Management)

- POST /users/register
  - 描述：用户注册。
  - 请求：{ "username": "string", "password": "string", "phone_number": "string" }
  - 响应：{ "message": "注册成功", "user_id": "uuid" }
- POST /users/login
  - 描述：用户登录。
  - 请求：{ "username": "string", "password": "string" }
  - 响应：{ "access_token": "string", "token_type": "bearer", "user_id": "uuid" }
- GET /users/me
  - 描述：获取当前用户信息。
  - 请求：(通过 JWT 获取用户 ID)
  - 响应：{ "user_id": "uuid", "username": "string", "phone_number": "string", "created_at": "datetime" }
- PUT /users/me
  - 描述：更新当前用户信息。
  - 请求：{ "phone_number": "string | null", "password": "string | null" }
  - 响应：{ "message": "用户信息更新成功" }

2.2. 果园管理 (Orchard Management)

- POST /orchards
  - 描述：创建新果园。
  - 请求：{ "name": "string", "location": { "latitude": float, "longitude": float, "address_detail": "string" }, "main_variety": "string", "avg_tree_age": int, "soil_type": "string", "last_harvest_date": "date" }
  - 响应：{ "message": "果园创建成功", "orchard_id": "uuid" }
- GET /orchards
  - 描述：获取当前用户的所有果园列表。
  - 请求：(无)
  - 响应：[ { "orchard_id": "uuid", "name": "string", "location": {...}, "health_score": float, "has_new_alerts": boolean, "current_weather": {...}, "current_phenology": "string", ... } ]
- GET /orchards/{orchard_id}
  - 描述：获取指定果园的详细信息。
  - 请求：(无)
  - 响应：{ "orchard_id": "uuid", "name": "string", "location": {...}, "health_score": float, "has_new_alerts": boolean, "current_weather": {...}, "current_phenology": "string", "historical_alerts": [...], ... }
- PUT /orchards/{orchard_id}
  - 描述：更新指定果园信息。
  - 请求：{ "name": "string | null", "location": {...} | null, "main_variety": "string | null", ... }
  - 响应：{ "message": "果园信息更新成功" }
- DELETE /orchards/{orchard_id}
  - 描述：删除指定果园。
  - 请求：(无)
  - 响应：{ "message": "果园删除成功" }

2.3. 健康度与预警 (Health Score & Alerts)

- GET /orchards/{orchard_id}/health_overview
  - 描述：获取果园健康度、当前天气和AI简报。
  - 请求：(无)
  - 响应：{ "health_score": float, "has_new_alerts": boolean, "current_weather": { "condition": "string", "temperature": float, "humidity": float, "precipitation": float, "wind_speed": float }, "ai_daily_briefing": "string" }
- GET /orchards/{orchard_id}/alerts
  - 描述：获取果园的风险预警列表。
  - 请求：{ "status": "active | ignored | all" } (查询参数)
  - 响应：[ { "alert_id": "uuid", "type": "string", "risk_level": "high | medium | low", "confidence": float, "reason": "string", "generated_at": "datetime", "status": "active | ignored" } ]
- POST /orchards/{orchard_id}/alerts/{alert_id}/ignore
  - 描述：忽略某个预警。
  - 请求：(无)
  - 响应：{ "message": "预警已忽略" }

2.4. AI 诊断 (AI Diagnosis)

- POST /orchards/{orchard_id}/diagnosis/start
  - 描述：启动新的诊断会话。
  - 请求：{ "initial_description": "string | null", "image_urls": ["url1", "url2"] | null } (用户初始描述和/或图片)
  - 响应：{ "session_id": "uuid", "initial_response": { "type": "text | clarification", "content": "string", "options": [] } } (AI的首次响应，可能是文本或追问卡片)
- POST /orchards/{orchard_id}/diagnosis/{session_id}/continue
  - 描述：继续诊断会话（用户回复）。
  - 请求：{ "user_input": { "type": "text | option_selected | image_upload", "content": "string | selected_option_value", "image_urls": ["url1"] | null } }
  - 响应：{ "session_id": "uuid", "ai_response": { "type": "text | clarification | diagnosis_result", "content": "string", "options": [] } }
  - 注意：Agent工作流进度信息可以通过WebSocket实时推送，或者在每次响应中包含当前进度状态。这里假设在响应中包含。
    - "current_progress": { "step": "string", "percentage": float, "status": "pending | in_progress | completed" }
- GET /orchards/{orchard_id}/diagnosis/{session_id}/result
  - 描述：获取诊断结果（当诊断流程结束时）。
  - 请求：(无)
  - 响应：{ "diagnosis_id": "uuid", "primary_diagnosis": "string", "confidence": float, "secondary_diagnoses": [{"name": "string", "confidence": float}], "prevention_advice": "string", "treatment_advice": "string", "follow_up_plan": "string", "generated_at": "datetime" }

2.5. 农事操作与历史病例 (Farm Operations & Historical Cases)

- GET /orchards/{orchard_id}/cases
  - 描述：获取果园的历史病例列表。
  - 请求：{ "status": "all | pending_feedback" } (查询参数)
  - 响应：[ { "diagnosis_id": "uuid", "primary_diagnosis": "string", "generated_at": "datetime", "image_url_thumbnail": "string", "farm_operation_id": "uuid | null", "operation_type": "string | null", "effectiveness_rating": "string | null" } ]
- GET /orchards/{orchard_id}/cases/{diagnosis_id}
  - 描述：获取特定诊断病例的详情。
  - 请求：(无)
  - 响应：{ "diagnosis_id": "uuid", "primary_diagnosis": "string", ..., "associated_operation": { "operation_id": "uuid", "type": "string", "description": "string", "materials_used": [...], "operation_date": "date", "image_urls": [...] } | null }
- POST /orchards/{orchard_id}/cases/{diagnosis_id}/operation
  - 描述：为某个诊断病例记录农事操作。
  - 请求：{ "type": "string", "description": "string", "materials_used": ["item1", "item2"], "operation_date": "date", "image_urls": ["url1", "url2"] | null }
  - 响应：{ "message": "农事操作记录成功", "operation_id": "uuid" }
- PUT /orchards/{orchard_id}/operations/{operation_id}/feedback
  - 描述：反馈农事操作的效果。
  - 请求：{ "effectiveness_rating": "excellent | good | fair | poor", "feedback_details": "string | null", "follow_up_image_urls": ["url1", "url2"] | null }
  - 响应：{ "message": "防治效果反馈成功" }
- POST /orchards/{orchard_id}/operations
  - 描述：独立记录农事操作 (不关联任何病例)。
  - 请求：{ "type": "string", "description": "string", "materials_used": ["item1", "item2"], "operation_date": "date", "image_urls": ["url1", "url2"] | null }
  - 响应：{ "message": "农事操作记录成功", "operation_id": "uuid" }

2.6. 文件上传 (File Upload)

- POST /upload/image
  - 描述：上传图片到云存储服务（如OSS），返回图片URL。
  - 请求：multipart/form-data 包含图片文件。
  - 响应：{ "image_url": "string" }
  - 注意：前端应先调用此接口获取图片URL，再将URL传递给其他API。

Agent 设计方案 
1. Agent 核心架构：混合动态 Agent 框架 (Final Blueprint)
1.1. 核心设计哲学：安全源于结构，智能源于动态
- 结构化的“安全核心” (LangGraph Workflow):
  - 用途: 专注于产品中风险最高、需要绝对可靠和可预测的核心任务——交互式病害诊断。这包括从初步症状识别到最终给出防治建议的全过程。
  - 特点: 流程固定、逻辑严谨、状态可追溯、交互可控。类似于医院的“急诊标准作业程序 (SOP)”，确保在关键决策点上不会出现灾难性的误判，为用户的生产安全提供坚实的护栏。
  - 技术实现: 基于 LangGraph 的有向无环图 (DAG)。
- 动态的“创意引擎” (Dynamic Actor Model):
  - 用途: 处理开放式的、创造性的、非结构化的任务，例如生成“AI每日简报”、回答用户宽泛的提问、或未来可能增加的数据分析报告。这些任务的风险较低，更侧重于信息的聚合、理解和创造性输出。
  - 特点: 灵活、自适应、可扩展。它不遵循固定流程，而是根据任务目标，动态地规划步骤、组装能力，更像一个真正“思考”的实体。
  - 技术实现: 自主规划（Planner）、动态 Actor 组装（ActorFactory）、ReAct 循环 Actor。
- 主从关系: 这两种模式并非独立运行，而是主从关系。“创意引擎”被封装成一个强大的工具，可以在“安全核心”工作流的特定节点被调用（例如，LangGraph 节点可以调用 dynamic_task_executor 来生成某个复杂段落），或者被独立的 API 端点直接调用（例如，仪表盘的“AI每日简报”）。
1.2. 框架组件详解
A. LangGraph “安全核心” (用于交互式病害诊断)
- OrchardState (core/state.py)：作为共享状态，将包含诊断流程所需的所有上下文：
  - user_query: (str) 用户当前输入或最近的描述。
  - image_urls: (List[str]) 用户上传的图片 URL。
  - orchard_profile: (Dict) 从 Supabase 获取的果园档案（位置、品种、土壤等）。
  - realtime_weather: (Dict) 实时天气数据。
  - historical_cases_retrieved: (List[Dict]) 从向量数据库检索的相似历史病例。
  - initial_diagnosis_suggestion: (Dict) Vision API 的初步诊断结果。
  - intermediate_reasoning: (str) Agent 链式推理的中间步骤和思考过程。
  - clarification_needed: (bool) 标志是否需要向用户追问。
  - clarification_question: (str) 具体追问的问题。
  - final_diagnosis_report: (Dict) 结构化的最终诊断结果及建议。
  - confidence_score: (float) 当前诊断的置信度。
  - workflow_step: (str) 当前 LangGraph 所在的节点名称，用于前端进度反馈。
- 最终工作流 (core/graph.py):
  - Node 1: fetch_orchard_profile
    - 功能: 从 Supabase 数据库获取 OrchardState.orchard_id 对应的果园档案（如位置、品种、树龄、土壤类型、历史农事概况等）。
    - 输出: 更新 OrchardState.orchard_profile。
  - Node 2: run_image_diagnosis
    - 功能: 调用 Vision API（例如 OpenAI GPT-4V），对 OrchardState.image_urls 进行初步视觉证据分析，识别可能的病虫害症状。
    - 输出: 更新 OrchardState.initial_diagnosis_suggestion。
  - Node 3: parallel_dynamic_context_acquisition (并行节点)
    - 3a: fetch_weather_data
      - 功能: 使用 OrchardState.orchard_profile 中的果园位置信息，调用第三方天气 API 获取实时及未来天气数据。
      - 输出: 更新 OrchardState.realtime_weather。
    - 3b: retrieve_historical_cases
      - 功能: 使用 OrchardState.initial_diagnosis_suggestion 和 OrchardState.user_query 作为查询，从向量数据库检索相似的历史病例。
      - 输出: 更新 OrchardState.historical_cases_retrieved。
  - Node 4: reflect_and_evaluate_initial (推理与评估 - 首次反思)
    - 功能: 融合 orchard_profile, image_diagnosis, weather_data, historical_cases_retrieved, user_query 等所有上下文，进行第一次批判性审视。Agent 评估当前信息是否足以做出高置信度的诊断。
    - 输出: 更新 OrchardState.intermediate_reasoning 和 OrchardState.confidence_score。
  - ROUTER: decision_on_diagnosis_path
    - 功能: 根据 OrchardState.confidence_score 决定下一步路由：
      - 若置信度高 (confidence_score > threshold_high) 且信息充足 -> 路由到 generate_final_report。
      - 若置信度中等或低 (confidence_score <= threshold_high) 或信息缺失 -> 路由到 initiate_clarification。
  - Node 5: initiate_clarification (鉴别诊断/追问)
    - 功能: 基于 OrchardState.intermediate_reasoning 中识别出的信息缺口，生成向用户追问的问题（例如，结构化卡片中的选项），设置 OrchardState.clarification_needed = True。此时 LangGraph 暂停，等待用户输入。
    - 输出: 更新 OrchardState.clarification_question。
  - Node 6: reflect_and_evaluate_secondary (推理与评估 - 二次反思)
    - 功能: 在用户提供追问的答案后，将新的用户输入与 OrchardState 中所有上下文融合，进行最终推理，更新诊断置信度。
    - 输出: 更新 OrchardState.intermediate_reasoning 和 OrchardState.confidence_score。
  - Node 7: retrieve_treatment_knowledge (知识库检索)
    - 功能: 根据 OrchardState 中已确定的诊断结果，从专业知识库（向量数据库或其他）中检索匹配的防治方案和农事管理建议。
    - 输出: 更新 OrchardState.treatment_knowledge_retrieved。
  - Node 8: generate_final_report
    - 功能: 汇总所有信息（确诊结果、防治方案、后续管理建议、置信度、关键证据等），生成结构化的最终诊断报告。
    - 输出: 更新 OrchardState.final_diagnosis_report。

B. 动态“创意引擎” (用于“AI每日简报”、宽泛问答等)

- 实现方式: 我们会创建一个名为 dynamic_task_executor 的 Python 函数/类（位于 dynamic_agents/executor.py）。
- 输入: 接收一个自然语言描述的高级任务，例如“为王先生的果园生成一份友好且专业的今日健康简报。”
- 内部机制:
  1. Planner (dynamic_agents/planner.py):
    - 功能: 接收高级任务，并将其拆解为一系列逻辑清晰、可执行的子任务列表 TODO。
    - 示例任务分解:
      - 任务: "生成今日健康简报"
      - TODO:
        1. 获取当前用户果园信息。
        2. 获取果园实时天气预报。
        3. 评估当前天气对果园的潜在风险（基于历史数据和知识库）。
        4. 生成针对性的风险预警和建议。
        5. 以友好、专业的语言撰写简报文本。
  2. ActorFactory (dynamic_agents/actor_factory.py):
    - 功能: 遍历 TODO 列表，为每个子任务动态组装一个最合适的 Actor。每个 Actor 是一个独立的 LLM 代理实例，预设了特定的 system_prompt 和可用的 tools。
    - 示例 Actor 组装:
      - 为“获取果园信息”组装一个内置了 get_orchard_profile_tool 的 Actor。
      - 为“获取天气数据”组装一个内置了 get_weather_forecast_tool 的 Actor。
      - 为“评估风险”组装一个内置了 risk_evaluation_tool（可能调用了 LangGraph 的健康度/预警计算服务）和 knowledge_retrieval_tool 的 Actor。
      - 为“撰写报告”组装一个拥有优秀写作 Prompt 的 Actor，侧重于语言风格和总结能力。
  3. Actor (dynamic_agents/actor.py):
    - 功能: 每个被创建的 Actor 使用自己的 ReAct 循环来执行分配的子任务。它会思考、选择工具、执行工具、观察结果，并反复迭代直到完成子任务。
    - 核心: 内部封装 LLM 调用，Prompt 工程，以及对外部 tools 的调用。
  4. 结果聚合: 当所有子任务完成后，dynamic_task_executor 会聚合所有 Actor 的输出，返回最终的、组合好的结果（例如，一段完整的简报文本）。

1.3. 最终实施清单 (v4.0 - 定稿)

- [项目初始化] 创建完整的项目目录结构，包括 agents, core, services, utils 和新增的 dynamic_agents 目录。
- [依赖与配置] 完成 requirements.txt 的编写和 .env 文件的配置（API keys, DB URLs等）。
- [数据库实现] 根据最终的数据库设计方案，在 Supabase（PostgreSQL + PGVector）中创建所有数据表。
- [服务层实现] 在 services/ 目录中，全面封装对数据库（Supabase Python Client）、AI 模型（OpenAI SDK/LangChain）、第三方天气 API 的调用。确保所有服务都是可重用和高可用的。
- [LangGraph 核心实现]
  - 在 core/state.py 中定义最终的 OrchardState。
  - 在 agents/ 目录中，实现所有诊断流程所需的工具节点 (e.g., fetch_orchard_profile, run_image_diagnosis, fetch_weather_data, retrieve_historical_cases, retrieve_treatment_knowledge) 和推理节点 (e.g., reflect_and_evaluate_initial, reflect_and_evaluate_secondary, initiate_clarification, generate_final_report)。
  - 在 core/graph.py 中，严格按照 v3.0 工作流，构建、连接并编译 LangGraph 图，确保包含交互（等待用户输入）和暂停机制。
- [动态引擎实现]
  - 在 dynamic_agents/ 目录中，分别实现 planner.py, actor_factory.py, actor.py。
  - 创建一个主入口 executor.py，实现 dynamic_task_executor 函数，将上述动态流程串联起来。
- [API 层实现]
  - 在 app.py 中，实现与 LangGraph 核心交互的 /orchards/{orchard_id}/diagnosis/start 和 /orchards/{orchard_id}/diagnosis/{session_id}/continue 端点。这些端点将直接调用 LangGraph 图。
  - 在 app.py 中，实现直接调用 dynamic_task_executor 的 /orchards/{orchard_id}/daily_briefing 端点。
  - 实现所有其他辅助 API（用户管理、果园管理、风险预警、农事记录等）。
- [文件存储] 配置并集成对象存储服务（如 Supabase Storage 或 AWS S3）用于图片上传和管理。


后端功能点
- 用户管理与认证：注册、登录、个人信息管理。
- 果园信息管理：创建、编辑、查询果园档案。
- 实时数据获取：天气预报、历史天气、农事日历。
- 健康度与预警计算：基于多种因素（天气、历史病虫害、物候期）动态计算果园健康度，并生成风险预警。
- AI 诊断流程：
  - 接收用户上传的图片和文本描述。
  - 整合果园上下文信息。
  - 通过 Agent 工作流进行多轮交互式诊断（包括追问、鉴别诊断）。
  - 生成结构化的诊断报告。
  - 记录诊断结果。
- 农事操作记录：创建、查询、编辑农事操作记录，包括防治措施及其效果反馈。
- 历史病例管理：查询、管理历史诊断和防治记录。
- 数据分析与可视化支持：为前端的健康度、趋势图等提供数据。
- 推送通知：例如提醒用户评估防治效果、每日简报。
后端服务设计 (FastAPI + Agent Orchestration)
[cite_start]我们将使用 FastAPI 框架，因为它高性能、易于开发且原生支持异步操作 [cite: 17]。
- 技术栈: Python, FastAPI, Pydantic, SQLAlchemy, Langchain/LangGraph, OpenAI SDK (或本地LLM), OpenCV (图像处理), PostgreSQL, PGVector, Redis。
- 模块划分:
  1. main.py: FastAPI 应用入口，注册路由。
  2. api/v1/: API 路由定义 (按照我们上面敲定的接口)。
    - users.py
    - orchards.py
    - alerts.py
    - diagnosis.py
    - cases.py
    - upload.py
  3. schemas/: Pydantic 模型定义，用于请求/响应数据验证和序列化。
  4. crud/: 数据库操作（Create, Read, Update, Delete）层，与 SQLAlchemy ORM 交互。
    - user.py
    - orchard.py
    - alert.py
    - diagnosis.py
    - farm_operation.py
    - historical_case.py
  5. services/: 业务逻辑层。
    - auth_service.py: 用户认证、JWT 生成与验证。
    - weather_service.py: 调用第三方天气 API。
    - risk_calculation_service.py: 负责果园健康度及预警的计算逻辑。
    - file_upload_service.py: 处理图片上传到 OSS。
    - langgraph_service.py: 负责 LangGraph 核心的初始化、状态管理、执行诊断工作流的接口。
    - dynamic_agent_service.py: 负责调用 dynamic_task_executor 处理动态任务。
  6. agents/: 各个 Agent 的实现。
    - 工具节点 (e.g., fetch_orchard_profile, run_image_diagnosis, fetch_weather_data, retrieve_historical_cases, retrieve_treatment_knowledge) 
    - 推理节点 (e.g., reflect_and_evaluate_initial, reflect_and_evaluate_secondary, initiate_clarification, generate_final_report)。
  7. core/: 核心工具和配置。
    - database.py: 数据库连接、Session 管理。
    - config.py: 环境配置。
    - security.py: 密码哈希等安全工具。
    - orchard_state.py: LangGraph 的 OrchardState 定义。
  8. utils/: 辅助工具函数。
    - image_processing.py: 图像预处理。
    - embedding_generator.py: 生成文本/图像 embedding。
    - notifications.py: 推送通知服务。
  9. vector_db/: 向量数据库交互模块。
    - vector_store.py: 基于 PGVector 或 ChromaDB 的向量存储接口。
- 异步处理: 大部分 I/O 密集型操作（如数据库查询、第三方 API 调用、LLM 请求）都将设计为异步，充分利用 FastAPI 的性能优势。
- WebSockets (可选但推荐): 对于诊断过程中的 Agent 进度反馈，使用 WebSocket 可以提供更实时的用户体验，避免长轮询。API POST /orchards/{orchard_id}/diagnosis/{session_id}/continue 的响应可以保持不变，WebSocket 专门用于推送进度更新。
数据库设计 (PostgreSQL + Vector Database)
[cite_start]我们将使用 PostgreSQL 作为主关系型数据库 [cite: 25]，并利用其 PGVector 扩展来存储向量嵌入，以支持 RAG（Retrieval Augmented Generation）和语义搜索。
5.1. 关系型数据库 (PostgreSQL)
表结构设计：
1. users (用户表)
  - user_id (UUID, PK)
  - username (VARCHAR, UNIQUE)
  - password_hash (VARCHAR)
  - phone_number (VARCHAR, UNIQUE)
  - created_at (TIMESTAMP)
  - updated_at (TIMESTAMP)
2. orchards (果园档案表)
  - orchard_id (UUID, PK)
  - user_id (UUID, FK -> users.user_id)
  - name (VARCHAR)
  - location_latitude (FLOAT)
  - location_longitude (FLOAT)
  - address_detail (TEXT)
  - main_variety (VARCHAR)
  - avg_tree_age (INT)
  - soil_type (VARCHAR)
  - last_harvest_date (DATE)
  - current_phenology (VARCHAR, 实时物候期，可由AI或用户更新)
  - health_score (FLOAT, 实时计算的健康分数)
  - has_new_alerts (BOOLEAN, 标志是否有未处理预警)
  - created_at (TIMESTAMP)
  - updated_at (TIMESTAMP)
3. alerts (风险预警表)
  - alert_id (UUID, PK)
  - orchard_id (UUID, FK -> orchards.orchard_id)
  - type (VARCHAR, e.g., "病害", "虫害", "营养不良", "环境风险")
  - risk_item (VARCHAR, e.g., "溃疡病", "红蜘蛛")
  - risk_level (VARCHAR, e.g., "high", "medium", "low")
  - confidence (FLOAT, AI对风险判断的置信度)
  - reason (TEXT, AI给出预警的原因简述)
  - generated_at (TIMESTAMP)
  - status (VARCHAR, e.g., "active", "ignored", "resolved")
  - ignored_at (TIMESTAMP, null if not ignored)
4. diagnosis_sessions (诊断会话表)
  - session_id (UUID, PK)
  - orchard_id (UUID, FK -> orchards.orchard_id)
  - user_id (UUID, FK -> users.user_id)
  - start_time (TIMESTAMP)
  - end_time (TIMESTAMP, null if ongoing)
  - status (VARCHAR, e.g., "ongoing", "completed", "cancelled")
  - initial_query (TEXT)
  - initial_image_urls (ARRAY of TEXT)
5. diagnosis_messages (诊断会话消息表 - 存储对话历史)
  - message_id (UUID, PK)
  - session_id (UUID, FK -> diagnosis_sessions.session_id)
  - sender (VARCHAR, e.g., "user", "ai")
  - content_text (TEXT)
  - content_image_urls (ARRAY of TEXT)
  - message_type (VARCHAR, e.g., "text", "image", "clarification_question", "diagnosis_result")
  - timestamp (TIMESTAMP)
  - agent_workflow_state (JSONB, 可存储每次AI回复时的Agent中间状态，用于调试或回溯)
6. diagnoses (最终诊断结果表)
  - diagnosis_id (UUID, PK)
  - session_id (UUID, FK -> diagnosis_sessions.session_id, UNIQUE)
  - orchard_id (UUID, FK -> orchards.orchard_id)
  - primary_diagnosis (VARCHAR)
  - confidence (FLOAT)
  - secondary_diagnoses (JSONB, 存储 [{"name": "string", "confidence": float}])
  - prevention_advice (TEXT)
  - treatment_advice (TEXT)
  - follow_up_plan (TEXT)
  - original_image_urls (ARRAY of TEXT)
  - generated_at (TIMESTAMP)
7. farm_operations (农事操作记录表)
  - operation_id (UUID, PK)
  - orchard_id (UUID, FK -> orchards.orchard_id)
  - user_id (UUID, FK -> users.user_id)
  - diagnosis_id (UUID, FK -> diagnoses.diagnosis_id, NULLABLE, 可关联或不关联)
  - type (VARCHAR, e.g., "spraying", "fertilizing", "irrigation", "pruning", "other")
  - description (TEXT)
  - materials_used (ARRAY of VARCHAR, e.g., ["波尔多液", "阿维菌素"])
  - operation_date (DATE)
  - image_urls (ARRAY of TEXT, 操作前后的图片)
  - effectiveness_rating (VARCHAR, e.g., "excellent", "good", "fair", "poor", NULL if no feedback)
  - feedback_details (TEXT, NULL if no feedback)
  - follow_up_image_urls (ARRAY of TEXT, 防治后的图片)
  - created_at (TIMESTAMP)
  - updated_at (TIMESTAMP)

5.2. 向量数据库 (PGVector / ChromaDB)
- 作用：用于存储知识库文档、历史病例描述和图像特征的向量嵌入，支持 RAG 流程中的语义检索。
- 选项：
  1. PGVector (推荐)：直接作为 PostgreSQL 扩展，方便管理和集成。在 historical_cases 和 knowledge_base_documents 等表中增加 embedding 列（vector 类型）。
  2. ChromaDB：轻量级、嵌入式向量数据库，适合快速迭代和本地开发，生产环境可考虑独立部署。
  3. Pinecone/Weaviate/Milvus：更专业的托管或自建向量数据库，适合大规模、高并发场景，初期可能过度复杂。

增强 RAG 数据存储 (PGVector)

- historical_cases_embeddings:
  - id (UUID, PK)
  - diagnosis_id (UUID, FK -> diagnoses.diagnosis_id)
  - orchard_id (UUID, FK -> orchards.orchard_id)
  - symptom_description (TEXT, 从 diagnosis_messages 聚合的用户症状描述)
  - diagnosis_result_text (TEXT, 最终诊断和防治建议)
  - image_feature_vector (vector(N), 原始诊断图片的关键特征向量)
  - text_embedding (vector(M), 症状+诊断结果的文本向量)
  - metadata (JSONB, 存储病害类型、品种、地区、操作效果等，用于 RAG 过滤和排序)。
- knowledge_base_embeddings:
  - id (UUID, PK)
  - document_title (TEXT)
  - content_chunk (TEXT, 知识库文档的细分块)
  - embedding (vector(M), 文本块的向量)
  - source (VARCHAR, 知识来源，如“农业部文档”、“专家经验”)
  - topic (VARCHAR, 如“柑橘溃疡病防治”、“红蜘蛛生命周期”)
  - metadata (JSONB, 用于更精细的检索)。
数据流与存储：
- 用户上传图片：先通过文件上传API存到OSS，得到URL。
- AI 诊断过程中：
  - ImageAnalysisAgent：对图片进行特征提取，生成图像 embedding，存储到 diagnosis_messages 对应的记录中，或专门的 diagnosis_image_embeddings 表。
  - ReportGenerationAgent：生成的诊断结果和防治建议存入 diagnoses 表。
- 用户记录农事操作：存入 farm_operations 表。
- 数据闭环：当用户在 farm_operations 表中记录了防治效果，系统将 diagnoses 表和 farm_operations 表的相关信息聚合，生成高质量的 historical_cases_embeddings 数据，并将其文本和图像特征向量化，存入向量数据库，以供未来的 RAG 检索。

---

前端实现对齐与落地计划 (Frontend Alignment & Rollout Plan)

1. 现有前端实现与技术栈
- 核心栈：React 18 + TypeScript + Vite + Tailwind CSS；图标使用 `lucide-react`。
- 目录结构：`project/src/App.tsx` 为单文件型页面容器，通过本地状态 `currentPage` 模拟路由，页面包含：
  - `dashboard`（战略沙盘/主页）：天气、健康度、智慧果园可视化、AI 简报、快捷操作。
  - `alerts`（风险预警中心）：风险列表、忽略/前往确认。
  - `diagnosis`（诊断实验室）：对话式诊断流、进度提示、发送输入。
  - `cases`（病例档案库）：病例卡片、记录防治入口。
- 样式：`index.css` 仅启用 Tailwind 指令；布局已针对移动端做居中和内容卡片化。

2. 与 PRD 的页面与组件映射（MVP 分层）
- 路由层（当前为本地状态占位）：
  - `/home` -> `dashboard`
  - `/warning` -> `alerts`
  - `/diagnosis` -> `diagnosis`
  - `/records` -> `cases`
- 组件与能力对齐：
  - 智慧果园可视化 -> `SmartOrchard` 内部 SVG 与风险红点；点击跳转 `alerts`。
  - AI 简报 -> `dashboard` 卡片；后续由 `/orchards/{id}/health_overview` 的 `ai_daily_briefing` 字段驱动。
  - 风险卡片 -> `alerts` 列表；“前往确认”应触发创建诊断会话并预填引导文案。
  - 对话诊断 -> `diagnosis` 的消息列表与进度提示；后续用会话 API 驱动、WebSocket 推送进度。
  - 病例档案卡 -> `cases` 列表；接入 `/cases` API 后渲染真实数据。

3. 前后端 API 契约对齐（前端调用约定）
- 鉴权：采用 JWT；在前端以 `Authorization: Bearer <token>` 传递。
- 关键接口接入顺序（从无后端到有后端的演进）：
  - 阶段A（假数据/Mock 就绪）：保留现有本地假数据，抽象 `services/apiClient.ts`、`services/mock.ts`。
  - 阶段B（只读接入）：
    - GET `/orchards/{orchard_id}/health_overview` 显示健康度、天气、AI 简报。
    - GET `/orchards/{orchard_id}/alerts` 渲染风险列表。
    - POST `/upload/image` 返回图片 URL（供后续诊断输入）。
  - 阶段C（诊断工作流）：
    - POST `/orchards/{orchard_id}/diagnosis/start` 创建会话，落盘初始 AI 响应；前端跳转 `diagnosis` 并写入第一条 AI 消息。
    - POST `/orchards/{orchard_id}/diagnosis/{session_id}/continue` 续写对话；若响应为追问卡片，渲染为交互式卡片；若为结果，展示结果卡并提供“记录至档案”。
    - GET `/orchards/{orchard_id}/diagnosis/{session_id}/result` 在会话结束时拉取结构化报告。
    - WebSocket：订阅 Agent 进度，实时替换 `progress` 消息内容。
  - 阶段D（病例与农事闭环）：
    - GET `/orchards/{orchard_id}/cases` 渲染病例列表；
    - POST `/orchards/{orchard_id}/cases/{diagnosis_id}/operation` 记录防治；
    - PUT `/orchards/{orchard_id}/operations/{operation_id}/feedback` 填写防治效果，触发“数据闭环”。

4. 前端待落地的工程事项
- 路由化：引入 React Router，将 `currentPage` 拆解为真实路由，按 PRD 路由规范命名；保留移动端底部 Tab。
- 状态管理：引入 Zustand，集中管理 `currentUser`、`currentOrchard`、`activeDiagnosisSession`、`alerts`、`cases` 等，全局可订阅。
- 服务层：新增 `services/`：
  - `apiClient.ts`：Axios 实例、拦截器、鉴权头、错误统一处理。
  - `orchards.ts`、`alerts.ts`、`diagnosis.ts`、`cases.ts`、`upload.ts`：封装各 API。
  - `ws.ts`：封装进度 WebSocket 客户端（自动重连、心跳）。
- 组件化拆分：将 `App.tsx` 拆成 `pages/`（Dashboard/Alerts/Diagnosis/Cases）与 `components/`（SmartOrchard、RiskCard、ChatMessage、ProgressToast 等）。
- 环境与配置：新增 `.env`/`.env.local`，包含后端 BASE_URL、WS_URL、Supabase/S3 等配置占位。
- 类型与契约：在 `types/` 内定义与 PRD 一致的 TypeScript 接口，与后端 Pydantic 同名字段对齐。

5. 与 PRD 的交互细节对齐补充
- 诊断进度展示：将当前的纯文本进度升级为结构化步骤组件，映射 `current_progress.step/percentage/status`；若有 WebSocket 推送则覆盖轮询。
- 追问卡片：为响应中的 `type: clarification` 添加卡片组件，支持单选/多选，提交后直接调用 `continue`。
- 结果卡片：结构化呈现主要诊断、次要可能性、防治建议、后续观察；提供“记录至档案”与“返回预警中心”。
- 错误与离线：对 API 失败采用 Toast + 降级显示；诊断输入在离线时本地暂存，恢复后自动重试。

6. 运行与构建
- 开发：`npm run dev` 在 `http://localhost:5173`；需准备 `.env.local`：
  - `VITE_API_BASE_URL=https://api.example.com`
  - `VITE_WS_URL=wss://api.example.com/ws`
  - `VITE_STORAGE_BUCKET=supabase://...`（或 S3/OSS）
- 构建：`npm run build`，产物位于 `project/dist`；可部署到 Vercel/Netlify，启用 SPA 重定向（`dist/_redirects` 已存在）。

7. 短期里程碑（两周）
- D1-D2：抽象服务层、类型定义、环境变量；保留 Mock，打通只读接口 `health_overview` 与 `alerts`。
- D3-D5：落地 React Router + 页面拆分 + Zustand；Dashboard/Alerts 接入真实数据。
- D6-D8：诊断工作流接入 `start/continue/result`；实现进度 WebSocket；追问卡片与结果卡片组件。
- D9-D10：病例库列表、记录防治与反馈表单；错误处理与离线策略；打包与部署配置。

8. 未来增强（与后端/Agent 深度联动）
- Supabase Auth 集成与多果园切换；
- 图像上传压缩与多图管理；
- embedding/RAG 检索可解释性标签回显到结果卡；
- 通知订阅与效果评估提醒（7天自动推送）；
- A/B 提示词策略与置信度校准可视化。