# TCA-System V2.0

TCA-System V2.0 是一个面向 K-12 学习场景的教师可控多智能体 AI 辅导系统原型。系统包含学生端、教师端和管理端，用于支持学生答题与求助、AI 辅导、教师干预、实验分组和课堂过程数据管理。

## 当前能力

- 学生端：答题、聊天求助、接收 Guide/Tutor 回复和教师实时干预。
- 教师端：查看学生求助与系统触发事件，查看详情，选择保持现状或发送干预。
- 管理端：从数据库读取学生/教师/管理员数据，支持学生创建、编辑、删除、CSV 批量导入、批量分组和分组导出。
- 智能规则：支持 Evaluator 答案评估、`error_streak` 错误累计、L1/L2/L3 触发、AI-AUTO 自动切换和 TCA 教师 Override。
- LLM 接入：支持通过环境变量接入 ECNU OpenAI-compatible API；未配置或调用失败时自动回退到规则/模板。
- Docker 部署：已提供 `Dockerfile`、`docker-compose.yml`、`.env.example` 和部署说明。

## 目录结构

```text
backend/          Flask API、数据库、智能规则、WebSocket
frontend/static/  学生端、教师端、管理端、登录页
config/           配置读取
Dockerfile        Docker 镜像构建
docker-compose.yml
.env.example      环境变量模板，不包含真实 Key
DEPLOYMENT.md     服务器部署说明
Agents.md         项目阶段说明和验收记录
```

## 本地运行

建议使用 Python 3.12。

```bash
pip install -r requirements.txt
python start.py
```

访问：

```text
http://127.0.0.1:5000/login.html
```

新数据库默认管理员：

```text
管理员：900001 / admin123
```

学生和教师账号可在管理端创建或通过 CSV 导入。

## Docker 运行

复制环境变量模板：

```bash
cp .env.example .env
```

编辑 `.env`，至少填写：

```env
SECRET_KEY=replace-with-random-secret
ECNU_LLM_API_KEY=replace-with-real-ecnu-api-key
```

启动：

```bash
docker compose up -d --build
```

默认访问：

```text
http://127.0.0.1:8501/login.html
```

服务器部署时，如果安全组已放通 `8501`，访问：

```text
http://150.158.3.192:8501/login.html
```

## 环境变量

真实 `.env` 不提交 GitHub，只在本地或服务器保存。

```env
HOST_PORT=8501
HOST=0.0.0.0
PORT=5000
DEBUG=false
SECRET_KEY=replace-with-random-secret
DATABASE_PATH=/app/data/tca_system.db
ECNU_LLM_ENABLED=true
ECNU_LLM_BASE_URL=https://chat.ecnu.edu.cn/open/api/v1
ECNU_LLM_API_KEY=replace-with-real-ecnu-api-key
ECNU_LLM_GUIDE_MODEL=ecnu-plus
ECNU_LLM_TUTOR_MODEL=ecnu-plus
ECNU_LLM_EVALUATOR_MODEL=ecnu-max
ECNU_LLM_TIMEOUT=20
```

## 测试

```bash
python test_flask.py
```

Windows 控制台如果遇到中文或符号编码问题，可先执行：

```powershell
$env:PYTHONIOENCODING='utf-8'
python test_flask.py
```

## 部署文档

完整服务器步骤见 [DEPLOYMENT.md](DEPLOYMENT.md)。

## 安全说明

- 不要提交 `.env`、`.env.server`、数据库文件或真实 API Key。
- 公开仓库中只保留 `.env.example` 作为模板。
- 如果 ECNU API Key 泄露，需要立即更换。
