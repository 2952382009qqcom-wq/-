# 法律社区、案例与推荐架构

## 边界

三个业务域通过 Flask Blueprint 与原有法律智能体解耦：

- `core/community`：公开讨论、匿名求助、评论、互动、举报与通知。
- `core/cases`：只展示完成来源核验的结构化真实案例。
- `core/chat`：持久化一对一私聊与 Socket.IO 实时事件。
- `core/recommendations`：隐私最小化行为事件、用户领域画像与混合排序。
- `core/search`：Meilisearch 可选适配层、数据库回退与索引 outbox。

公开内容与私聊使用不同数据模型。匿名帖子序列化时不返回作者 ID；平台数据库仍保留作者关系，以支持本人编辑和管理员审计。

## 主要数据表

| 领域 | 表 | 用途 |
| --- | --- | --- |
| 社区 | `community_categories`, `community_posts`, `community_comments` | 分类、帖子与两级回复 |
| 互动 | `community_post_likes`, `community_comment_likes`, `community_post_favorites` | 幂等点赞/收藏关系 |
| 治理 | `community_reports`, `moderation_actions`, `notifications` | 举报、审计动作与回复通知 |
| 互通 | `community_post_origins`, `community_post_case_links` | AI 会话来源凭证与帖子—案例关联 |
| 案例 | `legal_cases`, `case_categories`, `case_tags`, `case_law_references` | 结构化案例、分类、标签和法条线索 |
| 案例关系 | `legal_case_categories`, `legal_case_tags`, `case_relations`, `case_favorites` | 多对多分类、相关案例和收藏 |
| 私聊 | `chat_threads`, `chat_participants`, `chat_messages`, `user_blocks` | 一对一会话、成员、消息与屏蔽 |
| 推荐 | `user_activity_events`, `user_interest_profiles`, `recommendation_impressions` | 衰减画像、开关和可解释曝光记录 |
| 检索 | `search_index_outbox` | SQL 到可选搜索服务的可靠同步 |

## 推荐策略

当前 `latest-legal-concept-v4` 读取用户正在查看或最近一次法律咨询的脱敏会话，并以最新一条能识别出明确法律领域的问题为主，避免先前话题污染后续追问。系统将“抢劫”“正当防卫”等口语扩展为稳定法律概念，再进行同领域召回、概念精确匹配和时间衰减排序。推荐优先近 8 年案例，老案例只有明确概念命中才保留；没有可靠命中时返回空结果，不使用热门案例补位。画像仍只记录领域和对象 ID，不记录咨询原文。用户关闭个性化后清空其事件并停止继续记录；数据规模达到协同过滤门槛后，可在不改变 API 的情况下接入 `implicit`。

## 开源方案选择

- FlaskBB（BSD-3-Clause）：参考其 Blueprint、服务层、讨论与治理边界，不复制 UI 或源文件。
- Flask-SocketIO（MIT）+ Redis：复用成熟房间、鉴权和多进程广播模型；断线时 REST API 降级。
- Meilisearch Community Edition（MIT）：作为可选全文检索服务；不可用时回退 SQL。
- implicit（MIT）：保留为后续有足够行为数据时的协同过滤升级路径，当前不引入额外运行复杂度。
- LeCaRD/LeCaRDv2（MIT）：仅作检索评测参考，不作为真实案例生产数据源。

具体版本、许可证和上游地址见 `THIRD_PARTY_NOTICES.md`。
