# TCA-System V2.0 项目说明

## 2026-05-26 最新演示版本说明

当前版本已经可以作为队长/组长阶段性演示版本使用。演示主线是：

```text
学生答题/聊天 -> 系统评估与触发 -> 教师端实时提醒 -> TCA 教师 Override -> 学生端接收指导 -> 管理端导出实验数据
```

本轮新增演示材料：

- `reports/TCA-System-demo-highlights-20260526.docx`
  - 给队长看的图文说明文档。
  - 包含项目简介、当前亮点、演示路径、学生端/教师端/管理端截图、验收清单和关键改动文件。
  - 注意：`reports/` 默认不进 GitHub，用于本地汇报材料。

本轮关键代码修改：

- `backend/api/teacher.py`
  - `/api/teacher/intervene` 增加 TCA 权限校验。
  - 只有 TCA 组学生允许教师发送 Override。
  - SA、EXP、AI-AUTO 组学生后端返回拒绝，避免只靠前端禁用造成权限漏洞。
- `backend/api/student.py`
  - `/api/student/list` 增加教师端需要的状态字段：
    - `current_agent`
    - `pending_count`
    - `last_message`
    - `last_activity`
  - 教师端学生列表可以展示当前 Agent、待处理标记、最后消息和上次活动时间。
- `backend/api/admin.py`
  - 批量导入学生增强校验：
    - 学号非数字
    - 学号长度异常
    - CSV 内重复学号
    - 姓名为空
    - 组别非法
    - 前测成绩不在 0-100
  - `/api/admin/students/import` 响应新增：
    - `success_count`
    - `failed_count`
    - `errors`
  - 新增实验数据导出接口：
    - `GET /api/admin/export/experiment-data.csv`
    - 导出学生分组、聊天记录、评估记录、触发事件、教师干预记录。
- `frontend/static/teacher.html`
  - 增加教师端全局实时通知条。
  - 通知支持“查看详情”和“忽略”。
  - 学生列表增强展示：
    - 当前组别
    - 当前 Agent
    - 当前题号
    - 待处理数量
    - 最后消息
    - 上次活动时间
  - TCA 组显示完整干预面板并允许发送。
  - 非 TCA 组显示“仅观察，不可干预”，禁用干预按钮和输入框。
  - 修复学生列表排序，TCA 组优先显示。
- `frontend/static/admin.html`
  - 批量导入后，如果有失败行，会在导入预览区域显示每行失败原因。
  - 新增“导出实验数据 (CSV)”按钮。
- `test_product_flows.py`
  - 新增产品链路测试：
    - 学生求助 -> 教师看到请求和详情 -> TCA 教师干预 -> 学生收到 Override。
    - SA / EXP / AI-AUTO 非 TCA 组无法被教师干预。
    - 管理端导入合法/非法 CSV 行，返回明确错误。
    - 管理端可导出实验数据 CSV。

当前可以实现和展示的功能：

| 模块 | 当前能力 | 如何体现 |
|:---|:---|:---|
| 学生端 | 学生答题、与 Guide/Tutor 对话、TCA 组查看教师指导入口 | 登录 `20240003 / 123456`，进入学生端查看题目、对话框和“教师指导”入口 |
| 智能规则 | Evaluator 规则评估、错误累计、L1/L2/L3 触发、AI-AUTO 自动切换、TCA 教师提醒 | 学生发送“我不会”等求助词，教师端出现待处理请求和诊断信息 |
| 教师端监控 | 查看所有学生状态、最后消息、上次活动、当前题号、当前 Agent、待处理数量 | 登录 `100001 / teacher123`，查看教师端左侧学生列表 |
| TCA Override | 教师对 TCA 组学生发送提示或切换 Tutor，学生端实时收到 | 教师端选中王芳/TCA，发送提示；学生端出现教师指导 |
| 权限边界 | 教师可观察所有学生，但只能干预 TCA 组 | 教师端选中张明/SA，干预面板禁用并显示“仅观察，不可干预” |
| 管理端 | 学生分组、批量导入、学生编辑删除、导出分组/实验数据 | 登录 `900001 / admin123`，查看管理端分组、导入和导出按钮 |
| 实验数据导出 | 导出学生、聊天、评估、触发、教师干预核心数据 | 管理端点击“导出实验数据 (CSV)”或访问 `/api/admin/export/experiment-data.csv` |
| 部署 | Docker 云端部署，GitHub 主线同步 | 服务器执行 `git pull` 后 `docker compose up -d --build` |

本轮验证命令：

```bash
python test_flask.py
python test_websocket.py
python test_product_flows.py
```

已验证结果：

- Flask 基础路由和默认账号通过。
- WebSocket 事件注册和连接测试通过。
- 产品链路测试通过。
- 教师端、管理端静态页面 JavaScript 语法检查通过。

仍然暂缓或后续继续做的内容：

- 题库表和题目从数据库读取：本阶段继续使用内置默认题库，不影响当前演示。
- Vue3 + Element Plus 完整重构：目前保留为 V2.0 前端工程方向，云端仍默认运行 `frontend/static` 产品页。
- 更细的 EXP 解释模板库：当前已有通用提示，后续可按题型和错误类型扩充。
- 多人正式实验数据库：SQLite 对本地和小规模演示够用，正式多人并发建议后续迁移 MySQL/PostgreSQL。

## 最新部署策略：云端默认运行产品演示版

当前项目按“产品先可用”的策略调整部署方式：

- 云服务器 Docker 默认运行 `frontend/static`，这是目前已接入后端 API 的学生端、教师端、管理端。
- Flask 后端启动后会托管 `frontend/static`，并将 `/login`、`/student`、`/teacher`、`/admin` 映射到对应 `.html` 页面。
- `frontend/vue-app` 保留为 Vue3 + Element Plus + 组件化的 V2.0 重构工程，但当前不作为云端默认入口，避免线上展示未接真实接口的骨架页面。
- 如需测试 Vue 重构版，可在 `.env` 设置 `TCA_FRONTEND_MODE=vue`，并先构建 `frontend/vue-app/dist`。
- 后续本地改代码后，推到 GitHub；服务器只需要 `git pull` + `docker compose up -d --build`。

相关改动文件：

- `Dockerfile`：改回 Python 产品镜像，默认 `TCA_FRONTEND_MODE=static`。
- `backend/app.py`：静态文件服务改为默认 `frontend/static`，并支持 `/student` 等短路径映射。
- `.dockerignore`：排除 `frontend/vue-app/node_modules/` 和 `frontend/vue-app/dist/`。
- `frontend/vue-app/`：V2.0 前端重构工程入口，暂不作为正式演示入口。

服务器更新命令：

```bash
cd /root/tca-system-v2.0-github
git pull
docker compose up -d --build
docker compose ps
docker compose logs --tail=80
```

云端访问地址：

```text
http://服务器IP:8501/
http://服务器IP:8501/login
http://服务器IP:8501/student
http://服务器IP:8501/teacher
http://服务器IP:8501/admin
```

注意：

- 现在云端主入口可以使用 `/login` 或 `/`，也兼容 `/login.html`。
- Docker 云端默认跑 `frontend/static` 产品页；Vue 重构完成前不要切换线上默认入口。
- `.env` 仍然只放服务器，不上传 GitHub。

## 项目简介

TCA-System 是一个面向 K-12 学习场景的“教师可控多智能体 AI 辅导系统”原型。系统用学生端、教师端、管理端三类页面串起一个教学实验流程：

- 学生端负责答题、与 Agent 对话、接收提示或教师干预。
- 教师端负责查看学生求助、系统触发事件、学生历史对话，并决定是否干预或切换 Agent。
- 管理端负责查看数据库中的学生、教师/管理员、分组统计和系统日志，并提供创建账号、导出分组数据等管理入口。

当前版本的“智能功能”包含两层：第一层是规则驱动的评估和触发链路，系统会评估答案、累计错误状态、识别求助关键词，并根据 SA、EXP、AI-AUTO、TCA 四组规则决定是否提示学生、自动切换 Agent 或通知教师；第二层是 ECNU LLM API 适配层，配置 `ECNU_LLM_API_KEY` 后，Guide/Tutor/Evaluator 可以调用真实模型。未配置 Key 或接口失败时，系统自动回退到规则模板。

## 本轮主要修改

### 0.1 对照视觉规范 v2.0 与技术规格 V1.5 的最新调整

本轮重新对照了：

- `01_设计文档/🎨_视觉设计规范_v2.0.md`
- `00_项目总览/01_核心文档/TCA-System 技术规格说明书_V1.5.md`

结论：技术规格 V1.5 明确要求当前实现以 Flask + SQLite + flask-socketio 为主，不直接升级 Vue3 + FastAPI + MySQL。视觉规范 v2.0 中 Vue3/Element Plus/Pinia 属于后续蓝图，但其中的品牌色、Agent 标签、消息气泡、通知动画、组别色可以安全迁移到当前静态 HTML 版本。

本轮已补：

- 登录页 `frontend/static/login.html`
  - 使用品牌渐变背景 `#667eea -> #764ba2`。
  - 登录卡片改为 20px 圆角和更明显的卡片阴影。
  - 登录按钮改为 `#2E86AB -> #4CAF50` 渐变按钮，并加入 hover 上移与阴影。
  - 输入框聚焦色改为视觉规范中的 `#2E86AB`。
- 学生端 `frontend/static/student.html`
  - 页面背景改为品牌渐变。
  - 对话区改为浅色渐变背景。
  - 用户消息气泡改为青绿渐变，AI 消息气泡保持白底边框。
  - Guide/Tutor Agent 标签改为视觉规范中的紫色/青绿色渐变标签。
  - 教师 Override 通知条加入右侧滑入动画。
  - 教师 Override 卡片保留醒目左边框和反馈按钮。
  - TCA 求助按钮改为毛玻璃感按钮，仅 TCA 组显示。
- 教师端 `frontend/static/teacher.html`
  - 页面背景改为教师端浅灰渐变。
  - 卡片圆角和阴影对齐视觉规范。
  - 组别标识色对齐：SA 灰、EXP 蓝紫、AI-AUTO 青、TCA 紫。
  - 待处理紧急项加入红色左边框和脉冲提示。
  - 干预发送按钮改为青绿渐变按钮。
- 管理端 `frontend/static/admin.html`
  - 页面背景、卡片圆角、按钮渐变、组别统计色做了视觉规范对齐。
- 后端规则 `backend/core/intelligence.py`、`backend/api/student.py`
  - EXP 组解释改为仅在触发规则时出现，避免每次答题都显示解释。
  - AI-AUTO 组解释改为仅触发时出现。
  - AI-AUTO 补齐“连续 3 轮正确/稳定后 Tutor 自动回切 Guide”的核心逻辑，并写入 `agent_switches`。

当前对照完成度估计：

| 模块 | 完成度 | 说明 |
|:---|:---:|:---|
| V1.5 技术栈路线 | 90% | 已按 Flask + SQLite + flask-socketio 路线实现；未做 Streamlit 外壳，当前是静态 HTML + Flask API。 |
| 四组实验条件 | 85% | SA/EXP/AI-AUTO/TCA 主逻辑已具备；AI-AUTO 回切已补；后续可继续细化 EXP 高质量模板库。 |
| Evaluator / error_streak / L1-L2-L3 | 80% | 规则版已实现，ECNU LLM 可配置；L3 停滞依赖前端传入 `time_spent`，后续可加真实停留计时。 |
| TCA 教师 Override | 85% | 教师提醒、详情、干预、学生端三层显示、反馈写库已具备；后续可细化教师“仅解释/切换/切换+解释/不干预”四按钮语义。 |
| WebSocket 实时链路 | 80% | 教师端/学生端实时推送已具备，并有轮询兜底；后续可加统一 Toast 组件和连接状态提示。 |
| 管理端数据库驱动 | 80% | 学生/教师/管理员、CSV 导入、分组、编辑删除、导出已具备；Excel 直接导入未做。 |
| 视觉设计规范 v2.0 | 55% | 品牌色、渐变、按钮、Agent 标签、组别色、消息气泡已部分迁移；未做 Vue3 组件化、Element Plus、完整毛玻璃组件系统。 |
| 部署 | 75% | Docker 文件和部署文档已具备，本地/服务器可跑；服务器 GitHub 443 网络不稳定时需手动上传文件或 zip。 |

剩余主要差距：

- 视觉规范 v2.0 中的 Vue3 + Element Plus + 组件化目录目前没有做，因为这属于 V2.0 重构，不是当前 V1.5 主线。
- EXP 组“高质量解释模板库”目前是通用提示，后续可按题型/错误类型扩充模板。
- L3 停滞检测目前后端支持，但前端还没有完整记录学生每题真实停留秒数。
- 教师端 Override 仍是“选择 Agent + 输入文本”的通用表单，后续可拆成四类明确动作：仅解释、切换、切换+解释、不干预。
- WebSocket Toast 视觉系统还没完全组件化，目前是页面内局部通知和列表提醒。
- SQLite 对原型和小规模演示可靠，若正式多人并发实验，建议后续按 V2.0 蓝图迁移 MySQL。

### 0.2 V2.0 Vue3 + Element Plus 前端工程骨架

根据视觉设计规范 v2.0 的 Vue3 + Vite + Pinia + TypeScript + Element Plus 目标，本轮新增了独立前端工程：

- `frontend/vue-app/package.json`
- `frontend/vue-app/vite.config.ts`
- `frontend/vue-app/tsconfig.json`
- `frontend/vue-app/src/main.ts`
- `frontend/vue-app/src/router/index.ts`
- `frontend/vue-app/src/stores/auth.ts`
- `frontend/vue-app/src/api/http.ts`
- `frontend/vue-app/src/styles/_variables.scss`
- `frontend/vue-app/src/styles/global.scss`
- `frontend/vue-app/src/styles/element-overrides.scss`
- `frontend/vue-app/src/components/common/GradientButton.vue`
- `frontend/vue-app/src/components/common/AgentBadge.vue`
- `frontend/vue-app/src/components/common/GroupBadge.vue`
- `frontend/vue-app/src/components/common/MessageBubble.vue`
- `frontend/vue-app/src/components/common/WebSocketToast.vue`
- `frontend/vue-app/src/views/LoginView.vue`
- `frontend/vue-app/src/views/StudentView.vue`
- `frontend/vue-app/src/views/TeacherView.vue`
- `frontend/vue-app/src/views/AdminView.vue`

设计规范已落地的部分：

- 品牌渐变背景 `#667eea -> #764ba2`。
- 按钮渐变 `#2E86AB -> #4CAF50`。
- Guide/Tutor/Evaluator 三类 Agent Badge。
- SA/EXP/AI-AUTO/TCA 四组 GroupBadge。
- 用户/AI/系统/教师四类 MessageBubble。
- WebSocketToast 滑入通知组件。
- Element Plus 主题变量覆盖。
- Vue Router 四个视图：登录、学生端、教师端、管理端。
- Pinia 登录状态 Store。
- Axios API Client，开发环境 `/api` 代理到 Flask 后端。

当前策略：

- `frontend/static` 仍是当前可部署演示版本，不删除、不替换。
- `frontend/vue-app` 是 V2.0 前端重构入口，供后续前端同学继续实现真实数据绑定和交互。
- Docker 仍默认运行 Flask + 静态 HTML，避免影响当前服务器演示。

验证方式：

```bash
cd frontend/vue-app
npm install
npm run build
```

已验证：`npm run build` 通过。构建中出现的 chunk size warning 来自 Element Plus 打包体积，不影响运行，后续可通过路由懒加载和手动分包优化。

更新后的完成度估计：

| 模块 | 完成度 | 说明 |
|:---|:---:|:---|
| V1.5 技术栈路线 | 90% | Flask + SQLite + flask-socketio 演示主线保持稳定。 |
| 四组实验条件 | 85% | 主逻辑已具备，AI-AUTO 回切已补。 |
| TCA 教师 Override | 85% | 当前静态版已可演示完整闭环。 |
| 视觉设计规范 v2.0 | 70% | 设计 token、Element Plus、Vue 组件骨架已落地；还需把真实业务交互从静态 HTML 迁移进 Vue。 |
| V2.0 前端工程化 | 60% | Vue3 工程可构建，组件和视图骨架已完成；真实 API 绑定和页面细节仍需继续。 |

### 0. 最新补充：教师 Override 学生端三层显示闭环

本轮按设计文档《TCA-System_设计方案_教师Override学生端显示》的要求，补齐了教师干预在学生端的显示、持久化、实时同步和反馈闭环。

涉及文件：

- `backend/api/student.py`
- `backend/api/teacher.py`
- `backend/core/database/schema.py`
- `frontend/static/student.html`

已实现：

- 数据库层：
  - `chat_messages` 新增 `override_id` 字段，用于把一条教师干预消息和 `teacher_overrides` 记录关联起来。
  - `teacher_overrides` 新增 `feedback`、`feedback_at` 字段，用于记录学生对教师指导的反馈。
  - `init_database()` 已加入兼容旧库的 `ALTER TABLE` 迁移逻辑，旧服务器数据库重启后也会自动补列。
- 教师端发送干预：
  - 教师点击发送干预后，会同时写入 `teacher_overrides` 和 `chat_messages`。
  - 写入 `chat_messages` 时保存对应的 `override_id`。
  - WebSocket 推送 `teacher_override` 时带上 `override_id`、`override_type`、`intervention_type`、`question_id`、`timestamp` 等信息。
- 学生端新增接口：
  - `GET /api/student/overrides`：获取当前学生收到的教师 Override 列表，并支持 `last_override_id` 拉取新消息。
  - `POST /api/student/overrides/<override_id>/feedback`：学生提交“有帮助 / 不清楚”反馈，写回数据库。
  - `GET /api/student/history` 返回聊天历史时，现在会带上 `override_id`，前端可用于去重和定位。
- 学生端三层显示机制：
  - 第一层：顶部通知条。收到新的教师 Override 后，学生端顶部出现“教师发来新的指导”，支持“查看 / 稍后 / 关闭”。
  - 第二层：对话区教师 Override 卡片。卡片显示教师 Override 类型、切换目标或干预类型、完整日期时间、题号、教师编号、内容和反馈按钮。
  - 第三层：右侧教师指导历史入口。显示历史指导数量，可展开查看历史指导摘要，并点击跳转到对应卡片。
- 实时性与兜底：
  - 在线时通过 WebSocket 立即收到教师干预。
  - 同时保留 5 秒轮询 `/api/student/overrides` 作为兜底，避免 WebSocket 断线或错过消息。
  - 通过 `override_id` 去重，避免同一条教师干预因 WebSocket 和历史回填重复显示。
- 学生反馈：
  - 学生可在教师 Override 卡片上点击“有帮助”或“不清楚”。
  - 反馈会写入 `teacher_overrides.feedback` 和 `teacher_overrides.feedback_at`。

如何体现已经实现：

1. 启动系统后，用学生账号登录学生端，例如 `20240001 / 123456`。
2. 另开教师端，用教师账号登录，例如 `100001 / teacher123`。
3. 在教师端选择该学生，输入干预内容并发送。
4. 学生端应立即出现顶部通知条。
5. 点击“查看”后，学生端对话区应出现教师 Override 卡片。
6. 学生端右侧“教师指导”历史入口数量增加。
7. 点击卡片上的“有帮助 / 不清楚”，反馈按钮会变成选中状态。
8. 刷新学生端后，教师干预仍能从聊天历史中恢复显示，说明不是临时前端状态。
9. 可用接口验证：

```bash
curl -b cookie.txt "http://127.0.0.1:5000/api/student/overrides?limit=10"
```

验证命令：

```bash
python test_flask.py
```

额外已验证：

- 学生页内联 JavaScript 语法检查通过。
- 本地测试过“教师发送干预 -> 生成 override_id -> 学生查询 overrides -> 聊天历史带 override_id -> 学生反馈写库”的完整链路。

### 1. 智能规则主线

新增或整理了后端智能规则层，核心文件是 `backend/core/intelligence.py`。

已实现：

- `RuleEvaluator`：对学生答案做规则评估，返回是否正确、错误类型、分数、建议和标准答案。
- `error_streak`：根据错误类型、实验组权重、连续同类错误累计学习困难程度。
- L1/L2/L3 触发：
  - L1：错误累计达到阈值。
  - L2：聊天中出现“不会、不懂、不知道、卡住”等求助关键词。
  - L3：停滞时间达到阈值。
- 分组策略：
  - SA：固定 Guide，只记录评估，不主动解释，不自动切换。
  - EXP：固定 Guide，但可给系统解释提示。
  - AI-AUTO：触发后自动切换到 Tutor。
  - TCA：触发后通知教师端，由教师决定是否干预。
- 触发事件会写入 `trigger_events`，Agent 自动切换会写入 `agent_switches`。

### 2. ECNU LLM API 接入

新增 `backend/core/llm_client.py`，按 ECNU 智能体接口文档接入 OpenAI-compatible API。

已实现：

- 从环境变量读取配置，不在代码中保存明文 API Key。
- `ECNU_LLM_API_KEY` 配置后启用真实模型调用。
- Guide/Tutor 使用 `ecnu-plus`。
- Evaluator 使用 `ecnu-max`。
- 调用失败、超时、未配置 Key 时自动回退到现有规则模板。
- 学生聊天接口返回 `response_source`，可区分 `llm` 或 `template`。
- 学生提交答案接口返回 `evaluation_source`，可区分 `llm` 或 `rule`。

需要的环境变量：

```bash
ECNU_LLM_API_KEY=你的ECNU接口Key
ECNU_LLM_ENABLED=true
ECNU_LLM_BASE_URL=https://chat.ecnu.edu.cn/open/api/v1
```

后续 Docker 部署约定：

- 使用 `.env` 文件向容器注入 `ECNU_LLM_API_KEY`、`ECNU_LLM_ENABLED`、`ECNU_LLM_BASE_URL`、`SECRET_KEY`、`DATABASE_PATH`、`HOST`、`PORT` 等配置。
- `.env` 属于本地/服务器私密配置文件，不提交到 Git，不写进代码。
- 代码只读取环境变量，因此本地、测试服务器、正式服务器可以使用同一份代码，但配置不同的 `.env`。
- 推荐准备一个 `.env.example` 作为模板，只写变量名和占位说明，不写真实 Key。

示例 `.env`：

```env
ECNU_LLM_API_KEY=replace-with-real-key
ECNU_LLM_ENABLED=true
ECNU_LLM_BASE_URL=https://chat.ecnu.edu.cn/open/api/v1
SECRET_KEY=replace-with-random-secret
DATABASE_PATH=/app/data/tca_system.db
HOST=0.0.0.0
PORT=5000
DEBUG=false
```

### 3. 学生端

涉及页面：`frontend/static/student.html`

已实现：

- 学生进度、当前题目、当前 Agent、聊天记录从后端接口加载。
- 提交答案会进入 Evaluator 评估链路。
- 学生聊天会识别求助关键词，例如“我不会”“还是不会”等。
- 回车可以发送聊天消息。
- TCA 组或触发条件满足时，相关事件可推送到教师端待处理列表。

### 4. 教师端

涉及页面：`frontend/static/teacher.html`

已实现：

- 教师端从后端读取待处理请求和学生列表。
- 学生触发 L1/L2/L3 后会写入数据库中的待处理请求，教师即使晚进入页面也能看到。
- “详情”按钮已接入后端事件详情接口。
- 事件详情已从原始 JSON 改为更适合教师阅读的结构化信息：
  - 事件类型
  - 触发层级
  - 触发强度
  - 错误类型
  - 错误累计
  - L1/L2/L3 诊断
  - 建议处理
- 教师可以选择保持现状或干预。
- 教师可以忽略单条请求或全部已读，状态会写回数据库，刷新后不会重复出现。
- 教师干预可以实时推送给学生端，并写入 `teacher_overrides` 与 `chat_messages`。
- 学生端会轮询聊天历史，离线或错过 WebSocket 时也能补看到教师干预。
- 教师切换 Agent 会写入 `agent_switches`。

### 5. 管理端

涉及页面和接口：

- `frontend/static/admin.html`
- `backend/api/admin.py`
- `backend/app.py`
- `backend/core/database/schema.py`
- `init_db.py`
- `frontend/static/login.html`
- `start.py`

已实现：

- 新增管理端 API：
  - `GET /api/admin/dashboard`
  - `POST /api/admin/students`
  - `POST /api/admin/teachers`
  - `GET /api/admin/export/assignments.csv`
- 管理端学生表、用户表、日志表和分组统计全部从数据库接口读取。
- 管理端不再使用前端硬编码的默认学生数组。
- 管理端支持 CSV 批量导入学生，字段包括学号、姓名、班级、前测成绩、组别。
- 管理端支持批量随机分组写入数据库：
  - 简单随机分配
  - 按班级块随机分配
  - 按前测成绩分层随机分配
- 管理端支持学生编辑和删除。
- 登录页去掉默认学生/教师快捷入口，只保留管理员入口。
- 应用启动时不再自动种 4 个学生样例，只保留默认管理员账号：
  - `900001 / admin123`
- CSV 导出从数据库读取 `student_assignments`。
- 管理端顶部账号和角色从登录 session 中读取，不再写死 `admin`。

注意：当前本机 SQLite 数据库里如果还能看到张明、李华、王芳、赵强，是因为旧数据库已经存在这些历史种子数据，不是前端硬编码。新建空库时系统不会再自动生成这些学生。

### 6. 待办记录

新增 `TODO.md`，记录目前还没有完成或需要部署联调的关键事项：

- ECNU LLM API 适配层已接入，但需要配置 `ECNU_LLM_API_KEY` 后才能真实调用。
- Docker 部署资料已补齐，包含 `Dockerfile`、`docker-compose.yml`、`.env.example`、`.dockerignore` 和 `DEPLOYMENT.md`；后续需要在云服务器填写 `.env` 并完成联调。

## 当前可以实现的功能

### 1. 登录与角色跳转

可以实现：

- 管理员登录后进入管理端。
- 学生、教师账号如果存在于数据库中，也可以正常登录并跳转到对应页面。

如何体现：

1. 打开 `http://127.0.0.1:5000/login.html`。
2. 使用管理员账号 `900001 / admin123` 登录。
3. 页面跳转到 `admin.html`，顶部显示当前管理员账号和角色。

后端验证：

```bash
python test_flask.py
```

测试中会验证认证接口、基础路由和数据库连接。

### 2. 学生答题评估

可以实现：

- 学生提交答案后，后端会判断答案是否正确。
- 配置 `ECNU_LLM_API_KEY` 后，优先由 ECNU Evaluator 模型评估。
- 未配置 Key 或接口失败时，回退到本地规则 Evaluator。
- 错误答案会被标记为 `concept`、`calculation`、`format` 等错误类型。
- 系统会给出分数、错误提示和建议。
- 评估记录写入 `evaluation_records`。

如何体现：

1. 使用数据库中的学生账号登录学生端。
2. 在题目答案框中输入错误答案并提交。
3. 学生端会显示评分、错误类型、错误累计等信息。
4. 接口返回中查看 `evaluation_source`：`llm` 表示模型评估，`rule` 表示规则兜底。
5. 数据库表 `evaluation_records` 会新增记录。

### 3. error_streak 错误累计

可以实现：

- 学生连续答错时，`student_states.error_streak` 会增长。
- 不同错误类型有不同权重。
- 不同实验组有不同累计倍率，TCA 更敏感，SA 更保守。
- 答对后错误累计会下降。

如何体现：

1. 学生连续提交错误答案。
2. 学生端提示中可看到错误累计变化。
3. 教师端事件详情中也会显示错误累计。
4. 数据库 `student_states.error_streak` 会更新。

### 4. L1/L2/L3 触发规则

可以实现：

- L1：答题错误累计达到阈值时触发。
- L2：学生聊天出现求助关键词时触发。
- L3：停滞时间达到阈值时触发。
- 触发结果写入 `trigger_events`。

如何体现：

1. 学生端输入“我不会”“不懂”“还是不会”等消息。
2. 或连续提交错误答案。
3. 教师端待处理请求列表会出现相应事件。
4. 点击教师端“详情”，可以看到 L1/L2/L3 的诊断内容。

### 5. AI-AUTO 自动切换

可以实现：

- AI-AUTO 组学生触发规则后，系统自动将当前 Agent 切换到 Tutor。
- 切换记录写入 `agent_switches`。

如何体现：

1. 使用 AI-AUTO 组学生登录。
2. 通过错误答案或“我不会”等消息触发规则。
3. 学生端当前 Agent 变为 Tutor。
4. 管理端日志或数据库 `agent_switches` 中可看到切换记录。

### 6. TCA 教师干预

可以实现：

- TCA 组学生触发规则后，不自动替学生决定下一步，而是提醒教师。
- 教师端待处理请求显示学生动态。
- 教师可以查看详情、忽略、保持现状或发送干预内容。
- 干预内容会实时发送给学生端，并写入 `teacher_overrides` 和 `chat_messages`。
- 学生端如果当时不在线，重新进入题目后也会从历史记录补拉教师干预消息。

如何体现：

1. 使用 TCA 组学生登录学生端。
2. 输入“我不会”或连续答错。
3. 打开教师端，待处理请求中会出现该学生事件。
4. 点击“详情”，查看结构化诊断。
5. 在教师干预区输入提示并发送。
6. 在线学生端聊天区会立即收到教师干预消息。
7. 刷新或重新进入学生端，仍能在聊天历史中看到教师干预消息。

### 7. 教师端事件详情

可以实现：

- 教师端点击待处理请求的“详情”后，会加载后端事件详情。
- 待处理请求不是只靠 WebSocket 临时显示，而是持久化到数据库。
- 老师什么时候打开教师端，都可以重新加载尚未处理的学生问题。
- 不再只显示原始 JSON，而是显示教师可读的诊断信息。

如何体现：

1. 教师端出现待处理请求。
2. 点击“详情”。
3. 右侧对话历史和事件详情区域显示触发原因、错误累计、建议处理等信息。
4. 点击“忽略”或“全部已读”后，待处理状态会写回数据库。

### 8. 管理端数据库仪表盘

可以实现：

- 管理端从数据库读取学生、用户、日志。
- 分组统计从 `student_assignments` 实时计算。
- 可以创建单个学生账号。
- 可以 CSV 批量导入学生账号，已存在学生会更新，不存在学生会新增。
- 可以编辑学生姓名、班级、前测成绩、实验组。
- 可以删除学生及其关联答题、聊天、触发、干预记录。
- 可以将批量随机分组结果写入数据库。
- 可以创建教师或管理员账号。
- 可以导出学生分组 CSV。

如何体现：

1. 登录管理员账号 `900001 / admin123`。
2. 打开 `admin.html`。
3. 查看学生表，表格行显示“来自数据库”。
4. 新建学生后，页面刷新并从数据库重新加载。
5. 上传 CSV 文件导入学生，确认新增/更新数量。
6. 点击“执行分组”，刷新后确认组别已写入数据库。
7. 编辑或删除学生，刷新后确认结果仍从数据库读取。
8. 点击“导出分组结果 (CSV)”，下载数据库中的分组数据。

### 9. WebSocket 实时链路

可以实现：

- 学生端、教师端之间的部分通知和干预通过 WebSocket 同步。
- 教师干预发送后，学生端可以收到消息。

如何体现：

```bash
python test_websocket.py
```

或同时打开学生端和教师端，触发求助/干预流程，看两端消息同步。

### 10. ECNU LLM 调用链路

可以实现：

- Guide/Tutor 聊天回复调用 ECNU LLM。
- Evaluator 答案评估调用 ECNU LLM。
- 接口失败时自动回退，不影响系统演示。

如何体现：

1. 在启动服务前设置环境变量 `ECNU_LLM_API_KEY`。
2. 启动 `python start.py`。
3. 学生端发送聊天消息。
4. 查看 `/api/student/chat` 响应中的 `response_source`：
   - `llm`：真实模型回复。
   - `template`：模板兜底。
5. 学生提交答案。
6. 查看 `/api/student/submit-answer` 响应中的 `evaluation_source`：
   - `llm`：真实模型评估。
   - `rule`：规则兜底。

## 当前不能误说已经完成的部分

### 1. 真实大模型需要配置 Key 后才会调用

当前已经有 ECNU LLM API 适配层，但代码库不保存明文 API Key。没有配置 `ECNU_LLM_API_KEY` 时，Guide/Tutor/Evaluator 仍会走规则模板兜底。因此如果页面仍显示 `response_source=template` 或 `evaluation_source=rule`，说明尚未完成本机/服务器环境变量配置或接口调用失败。

后续联调重点：

- 在部署环境设置 `ECNU_LLM_API_KEY`。
- 用真实学生聊天验证 `response_source=llm`。
- 用真实答题验证 `evaluation_source=llm`。
- 根据队长要求继续细化 Prompt。

### 2. Excel 直接导入暂未支持

当前管理端已支持 CSV 批量导入。Excel 文件需要先另存为 CSV 后再导入，后续如需要可再加入 Excel 解析依赖。

### 3. Docker 部署需要服务器联调

Docker 部署文件已经补齐：`Dockerfile`、`docker-compose.yml`、`.env.example`、`.dockerignore` 和 `DEPLOYMENT.md`。当前还不能说已经完成线上部署，因为需要在服务器 `150.158.3.192` 上配置真实 `.env`、构建容器、开放 `8501` 端口并验证学生端、教师端、管理端和 ECNU LLM 调用。

## 推荐验收流程

1. 启动服务：

```bash
python start.py
```

2. 跑后端基础测试：

```bash
python test_flask.py
```

3. 跑 WebSocket 测试：

```bash
python test_websocket.py
```

4. 管理端验收：

- 登录 `900001 / admin123`。
- 确认学生、用户、日志从数据库加载。
- 新建一个学生账号。
- 用 CSV 批量导入学生。
- 执行简单随机/块随机/分层随机分组，确认组别写入数据库。
- 编辑一个学生，确认刷新后仍保留。
- 删除一个测试学生，确认关联数据清理。
- 导出 CSV。

5. 学生端验收：

- 用数据库中已有学生账号登录。
- 提交错误答案。
- 输入“我不会”。
- 确认出现评估、错误累计和触发行为。

6. 教师端验收：

- 用数据库中已有教师账号登录。
- 查看待处理请求。
- 点击“详情”。
- 发送干预。
- 回到学生端确认收到教师消息。

7. AI-AUTO/TCA 对照验收：

- AI-AUTO 组：触发后应自动切换 Tutor。
- TCA 组：触发后应提醒教师，由教师决定是否干预。
- SA 组：应保持 Guide，不主动解释、不自动切换。
- EXP 组：应保持 Guide，但可以显示解释提示。

8. ECNU LLM 验收：

- 设置 `ECNU_LLM_API_KEY`。
- 学生端发起聊天，确认接口返回 `response_source=llm`。
- 学生提交答案，确认接口返回 `evaluation_source=llm`。
- 临时移除 Key 再试一次，确认系统能回退到 `template`/`rule`。

9. Docker 部署验收：

- 准备服务器 `.env`，写入 ECNU API Key 和 Flask 配置。
- 容器启动时加载 `.env`。
- 进入学生端聊天，确认 `response_source=llm`。
- 提交答案，确认 `evaluation_source=llm`。
- 确认 `.env` 没有被提交到代码仓库。

## 一句话状态总结

当前系统已经从“页面骨架”推进到“数据库驱动 + 管理端批量数据维护 + 规则智能评估 + ECNU LLM 可配置接入 + 教师可控干预 + Docker 部署资料齐备”的可演示原型；剩余重点主要是云服务器联调、端口/环境变量配置，以及按队长反馈继续细化 Prompt 和实验数据字段。
# 2026-05-27 生产分支智能链路更新

本文件顶部记录 150 生产线最新状态，后面的历史段落可能包含早期编码问题，仅作旧记录参考。

## 150 当前已补齐内容

- 统一三层规则入口：`backend/core/intelligence.py` 是运行时唯一实现，`backend/core/trigger_rules.py` 和 `backend/core/trigger_engine.py` 只做兼容导出，不再维护两套并行逻辑。
- 新增正式 Evaluator 位置：`agents/evaluator.py`，支持本地等价判定、非答案过滤、ECNU LLM JSON 评估和规则兜底。
- Prompt 去重：Guide、Tutor、Evaluator Prompt 统一放在 `agents/prompt_templates.py`。
- 结构化等价性判定：`60`、`60°`、数值等价答案会先由本地规则判定，减少 LLM 误判。
- 置信度联动：`confidence` 会传入触发引擎，低置信度时提高 L1 阈值，降低误触发风险。
- 主动求助消歧：`我不会`、`帮帮我` 会触发 L2；`我并不是不会`、`不用帮我，我再试试` 不触发 L2。
- L3 停滞阈值调整为中等题 60 秒，并保留简单题 30 秒、难题 120 秒的扩展入口。
- 后端核心智能链路中文乱码已清理：`backend/core/intelligence.py`、`backend/core/llm_client.py`、`agents/*`、`backend/api/student.py` 的运行时提示已改为 UTF-8 中文。

## 已验证

- 本地通过：`python test_product_flows.py`
- 本地通过：`$env:PYTHONIOENCODING='utf-8'; python test_flask.py`
- 本地通过：`$env:PYTHONIOENCODING='utf-8'; python test_websocket.py`
- 150 容器内验证通过：求助关键词触发、否定求助不触发、L1/L2/L3 仲裁、`60°` 等价判定正确。

## 150 同步状态

- 服务器：`150.158.3.192`
- 线上目录：`/opt/tca-system-v2.0`
- 线上端口：`8502`
- GitHub 分支：`prod-150`
- 最新目标：保持 150 服务器代码、本地 `tca-system-prod-150`、GitHub `prod-150` 三者一致。
