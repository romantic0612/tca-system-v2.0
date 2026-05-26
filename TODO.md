# TODO

- ECNU LLM API 适配层已接入，Guide/Tutor/Evaluator 会在配置 `ECNU_LLM_API_KEY` 后调用真实模型；未配置或调用失败时自动回退到规则模板。后续需要做线上环境变量配置和真实接口联调。
- Docker 部署资料已补齐：`Dockerfile`、`docker-compose.yml`、`.env.example`、`.dockerignore` 和 `DEPLOYMENT.md` 已创建。后续重点是在云服务器复制 `.env.example` 为 `.env`，写入真实 ECNU API Key，并完成 150.158.3.192:8501 的联调验收。
