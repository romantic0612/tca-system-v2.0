# TCA-System Vue Frontend

这是按视觉设计规范 v2.0 新增的 Vue3 + Vite + Pinia + TypeScript + Element Plus 前端骨架。

当前状态：

- 已建立 V2.0 组件化目录。
- 已接入品牌色、Agent 色、组别色、渐变按钮、消息气泡、Toast 等设计 token。
- 已预留登录页、学生端、教师端、管理端视图。
- 暂不替换现有 `frontend/static` 演示页面，避免影响 Flask + Docker 当前部署。

本地运行：

```bash
cd frontend/vue-app
npm install
npm run dev
```

需要先启动 Flask 后端：

```bash
python start.py
```

Vite 开发环境会把 `/api` 和 `/socket.io` 代理到 `http://127.0.0.1:5000`。
