## 完成：Issue 13 — Django 站内信与短信通知触发

### 变更摘要

- **分支**：`feature/apartment-rental/step-14`（基于 step-13）
- **最新 commit**：`3b74cfa`

### 新增接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/messages` | 站内信列表（按时间倒序，分页） |
| POST | `/api/v1/messages/{id}/read` | 标记站内信已读 |
| GET | `/api/v1/messages/unread-count` | 未读消息数量 |

### 核心改动

1. **消息模块接口**（`apps/messages_app/`）
   - 新增 `serializers.py`、`views.py`、`urls.py`、`tests.py`
   - 列表接口仅返回当前登录用户的消息，包含 `related_apartment_id` 与 `related_audit_id`
   - 标记已读接口只能操作自己的消息，重复标记幂等

2. **审核驳回触发通知**（`apps/audits/views.py`）
   - 驳回时自动调用 `_send_reject_message`，向商家发送未读站内信
   - 站内信 `type` 为 `first_rejected` 或 `change_rejected`，标题/内容包含驳回原因
   - 同时通过 `core.sms.send_sms` 发送 mock 短信并记录 `SmsLog`，`status='mock'`

3. **稳定性修复**
   - 修复 `audits`、`favorites`、`messages_app` 列表在 TestCase 中因 `created_at` 相同导致排序不稳定的问题，增加 `-id` 次级排序

### 测试

- 全量 131 条测试用例全部通过
- 新增 16 条消息模块测试，覆盖：列表、字段、权限、标记已读、未读数、驳回触发站内信、驳回触发短信日志

### 数据表

- 无新增表，沿用已有的 `messages` 与 `sms_logs` 表

### 需前端/测试关注

- 站内信列表接口已可用，前端可直接对接「我的消息」页
- 未读数接口可用于个人中心红点提示
