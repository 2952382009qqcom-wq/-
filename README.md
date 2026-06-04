# 明鉴 - AI 法律 SaaS 平台

明鉴是一个基于 Flask 的法律文书智能助手原型，支持法条检索、合同风险审查、文书生成和用户/API 权限管理。

## 安全说明

- 不要提交 `.env`、数据库文件、日志、输出文件或本地虚拟环境。
- 首次部署前复制 `.env.example` 为 `.env`，并设置真实的 `LLM_API_KEY`、强 `ADMIN_PASSWORD` 和随机 `SECRET_KEY`。
- 生产环境请设置 `CORS_ORIGINS` 为实际站点域名。
- 用户 API Key 会存储在数据库中；正式生产环境建议进一步接入密钥加密或云端密钥管理。

## 本地运行

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python app.py
```

然后访问 `http://localhost:5000`。

## 必要数据

运行时需要：

- `data/provisions.json`
- `data/contract_risks.json`
