# 150 生产演示线同步说明

这个目录是 150 服务器当前生产演示代码的本地副本。

## 定位

- 本地目录：`C:\Users\SJGLC\Desktop\fwt\02_系统开发\tca-system-prod-150`
- 服务器：`150.158.3.192`
- 服务器目录：`/opt/tca-system-v2.0`
- 线上入口：`http://150.158.3.192:8502/login.html`

## 同步关系

```text
本地生产副本 tca-system-prod-150  <->  150 服务器 /opt/tca-system-v2.0
```

150 是生产演示线，不建议直接从 GitHub 拉最新开发代码覆盖。

## 当前来源

本目录由 150 服务器当前实际运行目录打包迁移而来：

```text
/opt/tca-system-v2.0
```

打包时排除了：

- `.git`
- `data/`
- `__pycache__/`
- `*.pyc`
- `frontend/vue-app/node_modules/`
- `reports/`
- `release/`

保留了 `.env` 和 `.env.*.backup`，因为它们属于生产部署配置。不要把这些文件提交到 GitHub 或发给别人。

## 推荐操作规则

1. 150 只放稳定演示版。
2. 修改 150 前，先备份服务器目录或本地目录。
3. 小修可以从本地改完后上传到 150。
4. 大功能先在 114/GitHub 开发线验证，通过后再手动同步到 150。
5. 不要在 150 上随便执行 `git pull` 覆盖生产演示代码。

## 本地上传到 150 的基本流程

在本地确认代码后，可以打包上传：

```powershell
tar -czf tca-prod-150-update.tar.gz -C "C:\Users\SJGLC\Desktop\fwt\02_系统开发\tca-system-prod-150" .
scp -i "C:\Users\SJGLC\.ssh\tca_tencent_key.pem" tca-prod-150-update.tar.gz ubuntu@150.158.3.192:/tmp/
```

服务器上解包并重建：

```bash
cd /opt/tca-system-v2.0
tar -xzf /tmp/tca-prod-150-update.tar.gz
sudo docker build -t tca-system-v20_tca-system:latest .
sudo docker rm -f tca-system
sudo docker run -d --name tca-system --restart unless-stopped --env-file .env -e TCA_FRONTEND_MODE=vue -e MYSQL_HOST=tca-mysql --network tca-system-v20_default -p 8502:5000 -v /opt/tca-system-v2.0/data:/app/data tca-system-v20_tca-system:latest
```

## 验证

```bash
curl http://127.0.0.1:8502/login.html
sudo docker ps
```

公网打开：

```text
http://150.158.3.192:8502/login.html
```

