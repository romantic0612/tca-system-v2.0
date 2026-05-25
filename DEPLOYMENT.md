# TCA-System V2.0 服务器 Docker 部署说明

目标访问地址：

```text
http://150.158.3.192:8501/
```

## 一、需要给组长的文件

建议把整个 `tca-system-v2.0` 项目目录打包发给组长，但注意不要把真实 `.env` 发到公开群或提交到 Git。

必须包含：

- `backend/`
- `frontend/`
- `config/`
- `requirements.txt`
- `start.py`
- `Dockerfile`
- `docker-compose.yml`
- `.env.example`
- `DEPLOYMENT.md`
- `Agents.md`

可选包含：

- `data/tca_system.db`

如果包含当前 `data/tca_system.db`，服务器部署后会带本地演示账号和演示数据：

```text
学生：20240001 / 123456
学生：20240002 / 123456
学生：20240003 / 123456
学生：20240004 / 123456
教师：100001 / teacher123
管理员：900001 / admin123
```

如果不包含 `data/tca_system.db`，系统会自动创建新数据库，只保留默认管理员：

```text
管理员：900001 / admin123
```

学生和教师需要在管理端创建或 CSV 导入。

## 二、服务器前置条件

服务器需要安装：

- Docker
- Docker Compose

Ubuntu/Debian 示例：

```bash
sudo apt update
sudo apt install -y docker.io docker-compose-plugin
sudo systemctl enable --now docker
```

检查：

```bash
docker --version
docker compose version
```

## 三、上传项目到服务器

在本地把项目压缩：

```powershell
Compress-Archive -Path .\tca-system-v2.0 -DestinationPath .\tca-system-v2.0.zip
```

上传到服务器，例如：

```bash
scp tca-system-v2.0.zip root@150.158.3.192:/opt/
```

服务器上解压：

```bash
cd /opt
unzip tca-system-v2.0.zip
cd tca-system-v2.0
```

如果压缩包里多了一层目录，请进入真正包含 `Dockerfile` 的目录。

## 四、配置 .env

服务器上复制模板：

```bash
cp .env.example .env
```

编辑 `.env`：

```bash
nano .env
```

至少需要改：

```env
HOST_PORT=8501
HOST=0.0.0.0
PORT=5000
DEBUG=false

SECRET_KEY=请换成一段随机长字符串
DATABASE_PATH=/app/data/tca_system.db

ECNU_LLM_ENABLED=true
ECNU_LLM_BASE_URL=https://chat.ecnu.edu.cn/open/api/v1
ECNU_LLM_API_KEY=填入真实ECNU_API_Key
ECNU_LLM_GUIDE_MODEL=ecnu-plus
ECNU_LLM_TUTOR_MODEL=ecnu-plus
ECNU_LLM_EVALUATOR_MODEL=ecnu-max
ECNU_LLM_TIMEOUT=20
```

注意：

- `.env` 不要提交 Git。
- `.env` 不要发公开群。
- 如果 ECNU API Key 泄露，需要及时更换。

## 五、启动服务

在服务器项目目录执行：

```bash
docker compose up -d --build
```

查看容器状态：

```bash
docker compose ps
```

查看日志：

```bash
docker compose logs -f
```

看到类似下面信息说明 Flask 已启动：

```text
TCA-System V2.0 - 教师可控多智能体AI辅导系统
地址: http://0.0.0.0:5000
WebSocket: 已启用
```

## 六、放通服务器端口

云服务器安全组需要放通 TCP `8501`。

服务器系统防火墙如果开启，也需要放通：

```bash
sudo ufw allow 8501/tcp
```

## 七、访问页面

浏览器访问：

```text
http://150.158.3.192:8501/login.html
```

常用页面：

```text
管理端：http://150.158.3.192:8501/admin.html
教师端：http://150.158.3.192:8501/teacher.html
学生端：http://150.158.3.192:8501/student.html
```

默认账号：

```text
管理员：900001 / admin123
```

如果带了当前数据库，也可以用：

```text
教师：100001 / teacher123
学生：20240001 / 123456
```

## 八、验收步骤

### 1. 管理端

1. 登录 `900001 / admin123`。
2. 打开管理端。
3. 查看学生列表是否从数据库加载。
4. 测试 CSV 批量导入。
5. 测试批量随机分组。
6. 测试编辑/删除学生。

### 2. 学生端

1. 用学生账号登录。
2. 在聊天框输入：

```text
我不会，这道题没思路
```

3. 检查是否出现模型回复。

### 3. 教师端

1. 用教师账号登录。
2. 查看待处理请求。
3. 点击详情。
4. 发送教师干预。
5. 回到学生端，确认学生端能看到教师通知。

### 4. LLM 验收

学生聊天接口应返回：

```text
response_source=llm
```

学生提交答案接口应返回：

```text
evaluation_source=llm
```

如果返回 `template` 或 `rule`，说明 ECNU API Key 没配置成功，或接口请求失败。

## 九、更新代码

如果后续重新上传新代码：

```bash
cd /opt/tca-system-v2.0
docker compose down
docker compose up -d --build
```

如果需要看日志：

```bash
docker compose logs -f
```

## 十、常见问题

### 页面打不开

检查：

```bash
docker compose ps
docker compose logs --tail=100
```

确认云服务器安全组已放通 `8501`。

### LLM 没有生效

检查 `.env`：

```bash
cat .env
```

确认：

```env
ECNU_LLM_ENABLED=true
ECNU_LLM_API_KEY=真实Key
```

然后重启：

```bash
docker compose restart
```

### 数据没有保存

确认 `docker-compose.yml` 里有：

```yaml
volumes:
  - ./data:/app/data
```

这样 SQLite 数据库会保存在服务器项目目录的 `data/` 下。
