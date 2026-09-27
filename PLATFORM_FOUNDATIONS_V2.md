# 明鉴平台能力 v2

本次改动在既有 Flask、SQLAlchemy、Socket.IO、社区、案例与法律助手上增量扩展；没有替换现有页面、视觉风格或核心接口，也不包含服务器部署、真实密钥、数据库文件、日志或用户数据。

## 1. 个性化案例推荐

- `core/recommendations/recall.py` 按领域画像、收藏相似、近期浏览/咨询领域、Meilisearch 关键词、热门和最新案例分层召回。Meilisearch 不可用时自动退回数据库检索。
- `config.py` 集中管理排序权重和算法版本；排序综合领域、文本、收藏、近期行为、热度、时效、来源可信度、探索、离线协同分数、重复曝光和负反馈，并做领域多样化。
- 响应保留旧 `algorithm=hybrid-v1` 兼容字段，同时返回 `algorithm_version=layered-v2`。
- 事件元数据采用白名单，绝不记录咨询正文、聊天内容、姓名、地址或设备标识。关闭个性化时停止记录并清除行为和曝光数据。
- `collaborative.py` 只读取离线、带版本的模型产物；用户数或事件数不足时自动回退。模型训练、验证、发布和回滚不在 Web 请求中执行。
- `tools/evaluate_recommendations.py` 输出 Precision@K、Recall@K、NDCG@K、MRR、覆盖率和领域多样性。

## 2. 站内聊天

消息先写数据库再广播。每个会话具有单调 `sequence`；`client_message_id` 保证重试幂等。HTTP 与 Socket 都支持回复，Socket 提供服务端 ACK 和按序号增量同步。接口还支持游标分页、未读/送达/已读、正在输入、在线状态、编辑、两分钟撤回、搜索、举报、屏蔽和“仅自己删除”。

聊天正文支持有限 Markdown，并经过白名单清洗；外链强制 `nofollow noopener noreferrer`。附件只允许明确的 MIME/扩展名组合，限制大小，使用随机对象键，下载强制 attachment、`nosniff` 和沙箱 CSP。本地存储仅用于开发/测试，生产可在同一接口后接对象存储。

管理员 API 可以审核举报、处理消息、禁言或封禁，并写审计记录。聊天和社区数据不会自动进入 AI 上下文、长期记忆或推荐系统；匿名社区帖的序列化结果不含作者 ID。

## 3. 离线通知

通知采用 `notification_outbox` 事务型发件箱。独立 Celery worker 负责投递，临时失败指数退避，超过上限转永久失败；无效令牌会停用，幂等键防止重复入队。站内通知始终可用，推送适配器包括 Web Push、Android FCM 和可扩展 APNs 边界。

推送令牌只保存 SHA-256 摘要和基于应用密钥加密的密文，日志不得输出令牌。默认锁屏仅显示“明鉴有新消息/打开明鉴查看详情”；用户可以修改渠道、安静时段和是否显示通用文案。

Android WebView 已加入 FCM 服务、令牌注册和点击路由。`google-services.json` 必须由项目管理员在本地提供，已被 `.gitignore` 排除。

## 4. AI 工作记忆、摘要与长期记忆

长期记忆默认关闭，只有用户主动开启并确认保存后才创建。用户可查看、编辑、删除、清空、导出，并能看到来源、类型、置信度、保存原因和最近使用时间。系统不会自动保存敏感信息、第三方隐私、匿名帖或聊天内容。

检索严格按 `user_id` 隔离，先按法律领域和关键词，再使用后台生成的本地向量作补充。对话摘要是带源消息区间的抽取式摘要；否定、更正和冲突会保留标记，不让模型自行决定哪条事实为真。

进入模型的内容被明确分为：`[SYSTEM POLICY]`、`[CURRENT TASK]`、`[CONVERSATION SUMMARY]`、`[RELEVANT USER MEMORIES]`、`[RECENT MESSAGES]`、`[ATTACHMENT EVIDENCE]`。后五区全部按不可信数据处理，附件、用户文字和工具结果不能改变系统规则。

## 5. 后台任务

选用 Celery + Redis：项目已使用 Redis 作为 Socket.IO 多进程消息队列，复用后可以获得成熟的重试、定时任务、Linux 运行和监控能力。Windows 本地开发可使用：

```powershell
celery -A worker.celery worker --pool=solo --loglevel=INFO
celery -A worker.celery beat --loglevel=INFO
```

生产 Linux 可使用 prefork worker。通知重试、搜索索引重建、摘要重建、记忆向量和推荐模型版本发布均在 worker 边界内；Flask 请求只写数据库或读取已发布产物。

## 6. 数据库与回滚

- 首个迁移已冻结为静态 Alembic DDL，不再导入运行时模型。
- `20260927_platform_foundations_v2` 为旧安装增加字段、约束和表，保留全部现有行。
- 先备份，再在预发布数据库运行 `flask db upgrade`。支持 SQLite 开发/测试和 MySQL 8 生产。
- 数据库降级故意不删除消息、通知和记忆。若应用版本需要回滚，先回滚代码；新增表和可空/带默认值字段保留，不影响旧版读取。这是比破坏性 `downgrade` 更安全的回滚策略。

## 7. 新增主要 API

- `POST /api/cases/<id>/events`
- `GET/POST /api/chat/threads/<id>/messages`、`POST .../attachments`
- `PUT /api/chat/messages/<id>`、`POST .../recall`、`DELETE /api/chat/messages/<id>`、`POST .../report`
- `GET /api/chat/threads/<id>/search` 与管理员审核/制裁接口
- `GET/POST/DELETE /api/notifications/*`
- `GET/PUT /api/memory/settings`，`GET/POST/DELETE /api/memory/items`，`GET /api/memory/export`

## 8. 仍需外部配置的风险边界

- FCM、Web Push、APNs 和对象存储需要部署方提供账号与密钥；仓库不含这些秘密。
- 协同过滤在数据达到阈值并完成离线验证前保持关闭；当前会自动使用内容推荐。
- 多进程 Socket.IO 和 Celery 需要可用的 Redis。Redis 暂不可用时，HTTP 聊天和站内通知仍可用，但跨进程实时广播/异步推送会延迟。
- 法律内容仍需核验来源和现行效力；推荐理由不是法律结论。
