# 上海本地公寓出租平台 Web 端 — 架构设计方案

> 更新说明：根据最新要求，后端框架已从 FastAPI + SQLAlchemy 调整为 **Python + Django + Django REST Framework**；前端沿用 Vue3 + Vant 方案。以下子 Issue 已同步更新。

## 一、需求梳理与边界确认

### 1. 核心目标
为上海本地公寓出租业务搭建一套租客/商家/管理员三端共用的 Web 平台，完成「房源发布 → 平台审核 → 租户检索 → 收藏管理 → 驳回通知」的核心业务闭环。

### 2. 功能范围

**P0 必做功能**
- 账号体系：手机号 + 短信验证码注册、密码/验证码登录、忘记密码、登录后强制身份选择（租客/商家）。
- 三级角色与权限隔离：租客、商家、管理员；非对应角色访问专属接口返回 403。
- 预置数据：上海 16 区 + 街道/镇两级行政区划、户型/设施/租期/支付方式/朝向/内外窗系统字典、管理员账号 `admin123/3816832z`。
- 房源发布（商家）：公寓基础信息 + 多房型 + 多组租期租金方案，提交后进入「首次提交审核」。
- 房源列表与组合筛选：仅展示「已上架」房源，支持名称、行政区、街道、户型、租期、价格区间筛选。
- 房源详情与户型详情：只读展示、收藏按钮、图片轮播。
- 个人中心：按角色展示菜单；租客/商家/管理员的收藏、消息、修改密码；商家的「已上架房源」与「房源详情编辑页」。
- 商家编辑与变更审核：修改公寓名称或所在位置时生成「变更审核单」，原房源保持不变，审核通过后生效。
- 管理员审核：首次审核、变更审核两类列表/详情，支持通过/驳回，变更字段高亮。
- 通知机制：审核驳回时同时发送站内信与短信（审核通过不主动通知）。
- 非功能：统一响应体/错误码、密码加密、验证码频控、图片本地存储、逻辑删除、H5 优先响应式。

**P1 迭代功能**
- 图片存储从本地切换至阿里云 OSS（预留配置项）。
- 短信服务接入真实阿里云短信（当前仅预留配置，开发环境降级为 mock）。
- 列表支持更多排序、未读消息红点、批量删除操作。

**P2 远期功能**
- 在线签约、租金支付、IM 聊天。
- 地图找房、智能推荐、数据报表后台。

### 3. 不在范围内
- 邮箱找回密码、第三方 OAuth 登录。
- 在线签约、电子合同、支付、IM 实时聊天。
- 多城市/多语言、地图可视化找房。
- 商家入驻资质认证、财务对账、运营后台报表。

### 4. 假设与说明
- **管理员账号**：管理员使用 `username/password` 登录；`users` 表额外增加 `username` 字段给管理员专用，普通用户仅用 `phone`。
- **短信服务**：V1.0 不接入真实阿里云短信，发送动作在开发环境降级为控制台/mock，但验证码生成、有效期、频控逻辑完整保留。
- **图片存储**：V1.0 默认本地文件系统，接口预留存储适配层，后续可切换 OSS。
- **身份切换**：首次登录后必须且只能选择一次身份；V1.0 不支持用户自由切换身份。
- **变更审核触发条件**：「所在位置」包括行政区、街道/镇、详细门牌号；任一发生变化即触发变更审核。
- **删除规则**：所有删除均为逻辑删除；删除房源时同步逻辑删除关联的未批准审核单；单独删除变更审核单不影响原房源。
- **行政区划数据**：以上海市民政局官方区划为基准初始化，实际种子文件包含 16 区及对应街道/镇数据。

---

## 二、技术选型与整体架构

### 1. 技术栈选型

| 层级 | 选型 | 说明 |
| ---- | ---- | ---- |
| 后端语言/框架 | Python 3.11 + Django + Django REST Framework | 生态成熟、文档完善、Admin 后台开箱即用，适合单人快速开发。 |
| 数据库 | PostgreSQL 15 | 支持 JSON、部分唯一索引、稳定可靠；开发/生产统一。 |
| ORM/迁移 | Django ORM + Django migrations | 与 Django 深度集成，迁移命令简单。 |
| 鉴权 | JWT（python-jose）+ passlib（bcrypt） | Token 鉴权 + 密码加密。 |
| 前端框架 | Vue 3 + TypeScript + Vite | 国内社区活跃，H5 开发效率高。 |
| UI 组件库 | Vant 4（移动端组件）+ Tailwind CSS | Vant 适合 H5，Tailwind 处理响应式与自定义样式。 |
| 状态管理 | Pinia | Vue 官方推荐，TypeScript 支持好。 |
| 路由 | Vue Router 4 | 单页应用路由。 |
| 部署 | Docker Compose（后端 + DB + Nginx 静态前端） | 本地一键启动，便于独立开发者交付。 |

### 2. 整体架构图

```
┌─────────────────────────────────────────────────────────────┐
│                         前端 (Vue3 + Vant)                   │
│   页面视图 → 业务组件 → API 封装 → Pinia 状态 → 路由/鉴权     │
└──────────────────────────┬──────────────────────────────────┘
                           │ RESTful API / JWT
┌──────────────────────────▼──────────────────────────────────┐
│                   后端 (Django + DRF)                        │
│   控制层 (Views/ViewSets) → 序列化 (Serializers) → 数据层    │
│  业务层/工具：权限、统一响应、文件存储、短信 mock、验证码工具  │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                    PostgreSQL (持久化)                       │
│         用户 / 房源 / 房型 / 审核 / 收藏 / 消息 / 字典        │
└─────────────────────────────────────────────────────────────┘
```

### 3. 项目目录结构

**后端 `my_multica_server`**
```
my_multica_server/
├── config/                     # Django 配置包
│   ├── settings.py             # 主配置
│   ├── urls.py                 # 根路由
│   └── wsgi.py / asgi.py
├── apps/
│   ├── users/                  # 用户、鉴权、验证码、短信日志
│   ├── districts/              # 行政区划
│   ├── dicts/                  # 系统字典
│   ├── apartments/             # 房源、房型、租金方案
│   ├── audits/                 # 审核记录
│   ├── favorites/              # 收藏
│   ├── messages/               # 站内信
│   └── uploads/                # 图片上传
├── core/                       # 公共层
│   ├── response.py             # 统一响应体
│   ├── exceptions.py           # 业务异常
│   ├── permissions.py          # 权限类
│   ├── security.py             # JWT、密码
│   ├── storage.py              # 存储适配
│   └── sms.py                  # 短信 mock/适配
├── seed_data/                  # 初始化 JSON/CSV
├── manage.py
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

**前端 `my_multica_web`**
```
my_multica_web/
├── src/
│   ├── api/                    # 按模块封装的 axios 请求
│   ├── assets/                 # 静态资源
│   ├── components/
│   │   ├── common/             # 通用组件（Header、Loading、Toast 等）
│   │   └── business/           # 业务组件（ApartmentCard、RoomTypeCard 等）
│   ├── views/
│   │   ├── auth/               # 登录、注册、忘记密码、身份选择
│   │   ├── home/               # 房源列表
│   │   ├── apartment/          # 房源详情、户型详情
│   │   ├── profile/            # 个人中心、收藏、消息、改密、商家房源
│   │   └── admin/              # 审核列表、审核详情
│   ├── router/                 # 路由配置与权限守卫
│   ├── stores/                 # Pinia 状态（auth、apartment、favorite、message、ui）
│   ├── utils/                  # 工具函数、常量、校验
│   ├── styles/                 # 全局样式、Tailwind 配置
│   ├── App.vue
│   └── main.ts
├── public/
├── index.html
├── package.json
├── vite.config.ts
├── tailwind.config.js
├── tsconfig.json
└── nginx.conf
```

---

## 三、数据库设计

### 1. 整体 ER 关系说明
- 一个 `user` 可以是租客、商家或管理员；商家拥有多个 `apartment`。
- 一个 `apartment` 包含多个 `room_type`；一个 `room_type` 包含多组 `rental_plan`。
- `apartment` 的发布/编辑通过 `audit_record` 记录审核流程；变更审核通过快照 JSON 保存待生效数据。
- `favorite` 关联用户与公寓；`message` 关联用户、公寓与审核单。
- `district` 自关联形成行政区 → 街道/镇两级树；`system_dict` 存储所有下拉枚举。
- `verify_code` 与 `sms_log` 分别保存验证码记录与短信发送日志。

### 2. 逐表详细设计

#### `users` — 用户表
| 字段 | 类型 | 长度/精度 | 必填 | 默认值 | 注释 |
| ---- | ---- | ---- | ---- | ---- | ---- |
| id | BIGINT | - | 是 | 自增 | 主键 |
| username | VARCHAR | 50 | 否 | NULL | 管理员登录账号，普通用户为空 |
| phone | VARCHAR | 11 | 否 | NULL | 普通用户手机号 |
| hashed_password | VARCHAR | 255 | 是 | - | bcrypt 加密后的密码 |
| role | VARCHAR | 20 | 是 | - | tenant/landlord/admin |
| is_active | BOOLEAN | - | 是 | true | 是否启用 |
| created_at | TIMESTAMPTZ | - | 是 | now() | 创建时间 |
| updated_at | TIMESTAMPTZ | - | 是 | now() | 更新时间 |
| deleted_at | TIMESTAMPTZ | - | 否 | NULL | 逻辑删除时间 |

- **主键**：id
- **索引/唯一**：username 唯一（允许 NULL）；phone 唯一（允许 NULL）；role 索引
- **关联**：无

#### `districts` — 行政区划表
| 字段 | 类型 | 长度/精度 | 必填 | 默认值 | 注释 |
| ---- | ---- | ---- | ---- | ---- | ---- |
| id | BIGINT | - | 是 | 自增 | 主键 |
| parent_id | BIGINT | - | 否 | NULL | 父级区划 ID，NULL 表示市辖区 |
| name | VARCHAR | 50 | 是 | - | 区划名称 |
| level | SMALLINT | - | 是 | - | 1=行政区，2=街道/镇 |
| code | VARCHAR | 20 | 否 | NULL | 官方编码 |
| sort | INT | - | 是 | 0 | 排序 |
| created_at | TIMESTAMPTZ | - | 是 | now() | - |

- **主键**：id
- **索引**：parent_id、level
- **关联**：自关联 parent_id → districts(id)

#### `system_dicts` — 系统字典表
| 字段 | 类型 | 长度/精度 | 必填 | 默认值 | 注释 |
| ---- | ---- | ---- | ---- | ---- | ---- |
| id | BIGINT | - | 是 | 自增 | 主键 |
| category | VARCHAR | 30 | 是 | - | 字典分类 |
| code | VARCHAR | 30 | 是 | - | 字典编码 |
| label | VARCHAR | 50 | 是 | - | 展示文案 |
| sort | INT | - | 是 | 0 | 排序 |
| is_active | BOOLEAN | - | 是 | true | 是否启用 |
| created_at | TIMESTAMPTZ | - | 是 | now() | - |

- **主键**：id
- **唯一**：(category, code)
- **索引**：category
- **初始数据**：layout_type、facility、lease_term、payment_method、window_type、orientation

#### `apartments` — 公寓房源表
| 字段 | 类型 | 长度/精度 | 必填 | 默认值 | 注释 |
| ---- | ---- | ---- | ---- | ---- | ---- |
| id | BIGINT | - | 是 | 自增 | 主键 |
| landlord_id | BIGINT | - | 是 | - | 商家用户 ID |
| name | VARCHAR | 50 | 是 | - | 公寓名称（2-50 字） |
| cover_image | VARCHAR | 500 | 是 | - | 公寓总览图 URL |
| description | TEXT | - | 是 | - | 公寓描述（≤500 字） |
| district_id | BIGINT | - | 是 | - | 行政区 ID |
| street_id | BIGINT | - | 是 | - | 街道/镇 ID |
| detail_address | VARCHAR | 200 | 是 | - | 详细门牌号 |
| contact_phone | VARCHAR | 11 | 是 | - | 联系电话 |
| status | VARCHAR | 30 | 是 | draft | draft/pending_first_review/first_rejected/published |
| min_monthly_rent | INT | - | 否 | NULL | 所有房型最低月租金（缓存） |
| created_at | TIMESTAMPTZ | - | 是 | now() | - |
| updated_at | TIMESTAMPTZ | - | 是 | now() | - |
| deleted_at | TIMESTAMPTZ | - | 否 | NULL | 逻辑删除时间 |

- **主键**：id
- **索引**：landlord_id、(status, deleted_at)、(district_id, deleted_at)、min_monthly_rent
- **关联**：landlord_id → users(id)；district_id/street_id → districts(id)

#### `room_types` — 房型表
| 字段 | 类型 | 长度/精度 | 必填 | 默认值 | 注释 |
| ---- | ---- | ---- | ---- | ---- | ---- |
| id | BIGINT | - | 是 | 自增 | 主键 |
| apartment_id | BIGINT | - | 是 | - | 所属公寓 |
| name | VARCHAR | 50 | 是 | - | 房型名称 |
| images | JSON | - | 是 | [] | 房型图片 URL 数组（最多 5 张） |
| facilities | JSON | - | 是 | [] | 设施编码数组 |
| layout_type | VARCHAR | 30 | 是 | - | 户型编码 |
| window_type | VARCHAR | 30 | 是 | - | 内外窗编码 |
| orientation | VARCHAR | 30 | 是 | - | 朝向编码 |
| floor | INT | - | 是 | - | 楼层 |
| sort | INT | - | 是 | 0 | 展示排序 |
| created_at | TIMESTAMPTZ | - | 是 | now() | - |
| updated_at | TIMESTAMPTZ | - | 是 | now() | - |
| deleted_at | TIMESTAMPTZ | - | 否 | NULL | 逻辑删除时间 |

- **主键**：id
- **索引**：(apartment_id, deleted_at)
- **关联**：apartment_id → apartments(id)

#### `rental_plans` — 租期租金方案表
| 字段 | 类型 | 长度/精度 | 必填 | 默认值 | 注释 |
| ---- | ---- | ---- | ---- | ---- | ---- |
| id | BIGINT | - | 是 | 自增 | 主键 |
| room_type_id | BIGINT | - | 是 | - | 所属房型 |
| lease_term | VARCHAR | 30 | 是 | - | 租期编码 |
| monthly_rent | INT | - | 是 | - | 月租金（元） |
| payment_method | VARCHAR | 30 | 是 | - | 支付方式编码 |
| created_at | TIMESTAMPTZ | - | 是 | now() | - |
| updated_at | TIMESTAMPTZ | - | 是 | now() | - |
| deleted_at | TIMESTAMPTZ | - | 否 | NULL | 逻辑删除时间 |

- **主键**：id
- **索引**：(room_type_id, deleted_at)
- **关联**：room_type_id → room_types(id)

#### `audit_records` — 审核记录表
| 字段 | 类型 | 长度/精度 | 必填 | 默认值 | 注释 |
| ---- | ---- | ---- | ---- | ---- | ---- |
| id | BIGINT | - | 是 | 自增 | 主键 |
| apartment_id | BIGINT | - | 是 | - | 关联房源 |
| type | VARCHAR | 30 | 是 | - | first_review / change_review |
| status | VARCHAR | 30 | 是 | pending | pending / approved / rejected |
| submitted_data | JSON | - | 是 | - | 提交时完整房源快照 |
| original_data | JSON | - | 否 | NULL | 变更审核时原房源快照 |
| changed_fields | JSON | - | 否 | [] | 变更字段名列表，供前端高亮 |
| reject_reason | VARCHAR | 500 | 否 | NULL | 驳回原因 |
| reviewer_id | BIGINT | - | 否 | NULL | 审核管理员 ID |
| created_at | TIMESTAMPTZ | - | 是 | now() | 提交时间 |
| updated_at | TIMESTAMPTZ | - | 是 | now() | - |
| deleted_at | TIMESTAMPTZ | - | 否 | NULL | 逻辑删除时间 |

- **主键**：id
- **索引**：(apartment_id, deleted_at)、(type, status, deleted_at)、reviewer_id
- **关联**：apartment_id → apartments(id)；reviewer_id → users(id)

#### `favorites` — 收藏表
| 字段 | 类型 | 长度/精度 | 必填 | 默认值 | 注释 |
| ---- | ---- | ---- | ---- | ---- | ---- |
| id | BIGINT | - | 是 | 自增 | 主键 |
| user_id | BIGINT | - | 是 | - | 用户 ID |
| apartment_id | BIGINT | - | 是 | - | 公寓 ID |
| created_at | TIMESTAMPTZ | - | 是 | now() | - |
| deleted_at | TIMESTAMPTZ | - | 否 | NULL | 逻辑删除时间 |

- **主键**：id
- **唯一**：(user_id, apartment_id) WHERE deleted_at IS NULL
- **索引**：(user_id, deleted_at)、apartment_id
- **关联**：user_id → users(id)；apartment_id → apartments(id)

#### `messages` — 站内信表
| 字段 | 类型 | 长度/精度 | 必填 | 默认值 | 注释 |
| ---- | ---- | ---- | ---- | ---- | ---- |
| id | BIGINT | - | 是 | 自增 | 主键 |
| user_id | BIGINT | - | 是 | - | 接收用户 |
| type | VARCHAR | 30 | 是 | - | first_rejected / change_rejected |
| title | VARCHAR | 100 | 是 | - | 标题 |
| content | TEXT | - | 是 | - | 内容 |
| related_apartment_id | BIGINT | - | 是 | - | 关联房源 |
| related_audit_id | BIGINT | - | 否 | NULL | 关联审核单 |
| is_read | BOOLEAN | - | 是 | false | 是否已读 |
| created_at | TIMESTAMPTZ | - | 是 | now() | - |
| deleted_at | TIMESTAMPTZ | - | 否 | NULL | 逻辑删除时间 |

- **主键**：id
- **索引**：(user_id, is_read, deleted_at)、related_apartment_id
- **关联**：user_id → users(id)；related_apartment_id → apartments(id)；related_audit_id → audit_records(id)

#### `verify_codes` — 短信验证码表
| 字段 | 类型 | 长度/精度 | 必填 | 默认值 | 注释 |
| ---- | ---- | ---- | ---- | ---- | ---- |
| id | BIGINT | - | 是 | 自增 | 主键 |
| phone | VARCHAR | 11 | 是 | - | 手机号 |
| purpose | VARCHAR | 20 | 是 | - | register/login/reset_password/change_password |
| code | VARCHAR | 6 | 是 | - | 验证码 |
| used | BOOLEAN | - | 是 | false | 是否已使用 |
| expired_at | TIMESTAMPTZ | - | 是 | - | 过期时间（5 分钟） |
| created_at | TIMESTAMPTZ | - | 是 | now() | - |

- **主键**：id
- **索引**：(phone, purpose, created_at)

#### `sms_logs` — 短信发送日志表
| 字段 | 类型 | 长度/精度 | 必填 | 默认值 | 注释 |
| ---- | ---- | ---- | ---- | ---- | ---- |
| id | BIGINT | - | 是 | 自增 | 主键 |
| phone | VARCHAR | 11 | 是 | - | 接收手机号 |
| template_code | VARCHAR | 50 | 否 | NULL | 短信模板 CODE |
| params | JSON | - | 否 | NULL | 模板参数 |
| status | VARCHAR | 20 | 是 | - | pending/success/failed/mock |
| response | TEXT | - | 否 | NULL | 发送结果/错误 |
| created_at | TIMESTAMPTZ | - | 是 | now() | - |

- **主键**：id
- **索引**：(phone, created_at)

### 3. 初始数据
- 管理员账号：`username=admin123`，密码 `3816832z`，`role=admin`。
- 上海行政区划：`districts` 表初始化 16 个行政区及下属街道/镇。
- 系统字典：`layout_type`（一室、两室一厅…）、`facility`（空调、洗衣机…）、`lease_term`（1 个月、半年、1 年、18 个月、2 年）、`payment_method`（押一付一、押一付三）、`window_type`（内窗、外窗）、`orientation`（东、南、西、北、东南、西南、东北、西北）。

---

## 四、后端接口清单

### 统一响应结构与错误码

**统一返回体**
```json
{
  "code": 0,
  "message": "success",
  "data": {}
}
```

**错误码规范**
| code | 含义 |
| ---- | ---- |
| 0 | 成功 |
| 400001 | 参数校验失败 |
| 400002 | 业务规则校验失败 |
| 401001 | 未登录或 Token 失效 |
| 403001 | 无权限访问 |
| 404001 | 资源不存在 |
| 409001 | 资源冲突（如重复收藏） |
| 429001 | 请求过于频繁（验证码频控） |
| 500001 | 服务器内部错误 |

### 认证模块

| 方法 | 路径 | 描述 | 权限 |
| ---- | ---- | ---- | ---- |
| POST | /api/v1/auth/sms-code | 发送短信验证码 | 公开，频控 |
| POST | /api/v1/auth/register | 手机号验证码注册 | 公开 |
| POST | /api/v1/auth/login-by-password | 手机号 + 密码登录 | 公开 |
| POST | /api/v1/auth/login-by-code | 手机号 + 验证码登录 | 公开 |
| POST | /api/v1/auth/select-role | 首次登录选择身份 | 需登录，role 为空 |
| POST | /api/v1/auth/reset-password | 忘记密码重置 | 公开 |
| POST | /api/v1/auth/change-password | 修改密码 | 需登录 |
| POST | /api/v1/auth/admin-login | 管理员账号登录 | 公开 |
| GET | /api/v1/auth/me | 获取当前登录用户 | 需登录 |

**主要请求/返回示例**
- `POST /api/v1/auth/sms-code`
  - 请求：{phone, purpose}
  - 返回：{expires_in: 300}
- `POST /api/v1/auth/login-by-password`
  - 请求：{phone, password}
  - 返回：{access_token, refresh_token, user: {id, phone, role}}
- `POST /api/v1/auth/select-role`
  - 请求：{role: "tenant" | "landlord"}
  - 返回：更新后的 user
- `POST /api/v1/auth/reset-password` / `change-password`
  - 请求：{phone?, sms_code, new_password}
  - 返回：成功标识

### 字典与行政区划模块

| 方法 | 路径 | 描述 | 权限 |
| ---- | ---- | ---- | ---- |
| GET | /api/v1/districts | 获取行政区划树或按 parent_id 获取子级 | 公开 |
| GET | /api/v1/dicts | 按 category 获取系统字典 | 公开 |

- `/api/v1/districts?level=1` 返回 16 区；`/api/v1/districts?parent_id=xxx` 返回街道/镇。
- `/api/v1/dicts?category=layout_type` 返回 [{code, label, sort}]。

### 图片上传模块

| 方法 | 路径 | 描述 | 权限 |
| ---- | ---- | ---- | ---- |
| POST | /api/v1/uploads/image | 单张图片上传 | 需登录 |

- 请求：multipart/form-data，file 字段，限制 5MB，仅允许 jpg/png/webp。
- 返回：{url, path}

### 公共房源模块

| 方法 | 路径 | 描述 | 权限 |
| ---- | ---- | ---- | ---- |
| GET | /api/v1/apartments | 房源列表（仅已上架） | 公开 |
| GET | /api/v1/apartments/{id} | 房源详情 | 公开 |
| GET | /api/v1/apartments/{id}/room-types | 房源下所有房型 | 公开 |
| GET | /api/v1/room-types/{id} | 户型详情 | 公开 |

- `GET /api/v1/apartments` 查询参数：keyword, district_id, street_id, layout_type, lease_term, min_price, max_price, page, page_size。
- 返回：{items, total, page, page_size}，item 包含 id, name, cover_image, district_name, street_name, min_monthly_rent。
- 详情返回公寓信息、房型卡片列表、当前登录用户是否已收藏（若已登录）。

### 收藏模块

| 方法 | 路径 | 描述 | 权限 |
| ---- | ---- | ---- | ---- |
| GET | /api/v1/favorites | 我的收藏列表 | 需登录 |
| POST | /api/v1/favorites | 收藏房源 | 需登录 |
| DELETE | /api/v1/favorites/{apartment_id} | 取消收藏 | 需登录 |

- 列表 item 同公共房源列表。

### 商家房源模块

| 方法 | 路径 | 描述 | 权限 |
| ---- | ---- | ---- | ---- |
| POST | /api/v1/merchant/apartments | 发布房源并提交首次审核 | 商家 |
| GET | /api/v1/merchant/apartments | 已上架房源列表 | 商家 |
| GET | /api/v1/merchant/apartments/{id} | 自有房源详情（可编辑） | 商家 |
| PUT | /api/v1/merchant/apartments/{id} | 编辑房源，触发/不触发变更审核 | 商家 |
| DELETE | /api/v1/merchant/apartments/{id} | 逻辑删除房源 | 商家 |
| GET | /api/v1/merchant/audits | 审核/变更单列表 | 商家 |

- 发布/编辑请求体结构：
  ```json
  {
    "name": "",
    "cover_image": "",
    "description": "",
    "district_id": 0,
    "street_id": 0,
    "detail_address": "",
    "contact_phone": "",
    "room_types": [
      {
        "name": "",
        "images": [],
        "facilities": [],
        "layout_type": "",
        "window_type": "",
        "orientation": "",
        "floor": 0,
        "rental_plans": [
          {"lease_term": "", "monthly_rent": 0, "payment_method": ""}
        ]
      }
    ]
  }
  ```
- 编辑时后端比对 `name`、`district_id`、`street_id`、`detail_address`；任一变化生成 `change_review` 审核单，原房源不变；否则直接更新。

### 管理员审核模块

| 方法 | 路径 | 描述 | 权限 |
| ---- | ---- | ---- | ---- |
| GET | /api/v1/admin/audits | 审核单列表 | 管理员 |
| GET | /api/v1/admin/audits/{id} | 审核详情 | 管理员 |
| POST | /api/v1/admin/audits/{id}/approve | 通过审核 | 管理员 |
| POST | /api/v1/admin/audits/{id}/reject | 驳回审核 | 管理员 |

- 列表查询参数：type（first_review/change_review）、status（pending/rejected）、page、page_size。
- 变更审核详情返回 `original_data`、`submitted_data`、`changed_fields`，供前端红色高亮变更字段。
- 驳回请求：{reject_reason}。

### 消息模块

| 方法 | 路径 | 描述 | 权限 |
| ---- | ---- | ---- | ---- |
| GET | /api/v1/messages | 站内信列表 | 需登录 |
| POST | /api/v1/messages/{id}/read | 标记已读 | 需登录 |
| GET | /api/v1/messages/unread-count | 未读数 | 需登录 |

---

## 五、前端模块与页面划分

### 1. 页面路由清单

| 路由 | 页面名称 | 所属模块 |
| ---- | ---- | ---- |
| /login | 登录页 | 认证 |
| /register | 注册页 | 认证 |
| /forgot-password | 忘记密码页 | 认证 |
| /select-role | 身份选择页 | 认证 |
| /apartments | 房源列表页 | 首页 |
| /apartments/:id | 房源详情页 | 房源 |
| /room-types/:id | 户型详情页 | 房源 |
| /profile | 个人中心首页 | 个人中心 |
| /profile/favorites | 我的收藏页 | 个人中心 |
| /profile/messages | 我的消息页 | 个人中心 |
| /profile/change-password | 修改密码页 | 个人中心 |
| /profile/my-apartments | 已上架房源页 | 商家 |
| /profile/apartments/create | 房源发布页 | 商家 |
| /profile/apartments/:id/edit | 房源编辑页 | 商家 |
| /admin/audits | 审核列表页 | 管理员 |
| /admin/audits/:id | 审核详情页 | 管理员 |
| /404 | 404 页面 | 公共 |

### 2. 核心组件划分

**通用组件**
- MobileLayout：H5 底部安全区 + 顶部导航/返回栏 + 内容区。
- Loading / Toast / Empty：全局加载、提示、空状态。
- ImageUploader：单图/多图上传、预览、删除、排序。
- SearchBar：带清除的搜索输入。
- FilterDrawer：筛选抽屉，支持多条件。
- DistrictCascader：行政区 → 街道两级联动选择。
- BackTop：返回顶部。

**业务组件**
- ApartmentCard：房源列表卡片（封面、名称、位置、最低租金）。
- RoomTypeCard：房型卡片（首图、名称、户型、楼层、最低租金）。
- RentPlanList：租期租金方案列表。
- FacilityTagList：房屋设施标签组。
- FavoriteButton：收藏/取消收藏按钮。
- AuditCard：审核单卡片（类型、状态、时间）。
- MessageItem：站内信条目（已读/未读）。

### 3. 状态管理划分（Pinia）

- `authStore`：token、refresh_token、userInfo、role、登录/注册/登出/选择身份。
- `apartmentStore`：列表查询条件、分页、当前房源详情、当前户型详情。
- `favoriteStore`：收藏列表、收藏/取消收藏。
- `messageStore`：消息列表、未读数、标记已读。
- `uiStore`：全局 loading、toast、网络错误提示。

---

## 六、分阶段可执行 Issue 清单

以下 Issue 按「后端 → 前端 → 测试」分阶段，每条可直接作为 Multica Issue 下发。

### 阶段一：后端开发

#### Issue 1
【Issue 标题】Django DRF 后端项目初始化与基础配置
【优先级】P0
【指派角色】后端开发
【详细描述】依据「二、技术选型与整体架构」创建 Django + Django REST Framework 后端工程结构，配置环境变量、CORS、日志、统一响应体、统一异常处理、Docker Compose（后端 + PostgreSQL）。
【验收标准】
1. `docker-compose up` 可启动后端与数据库。
2. 访问 `/health` 返回健康状态。
3. 统一响应体与错误码符合第四章约定。

#### Issue 2
【Issue 标题】Django ORM 数据库建模与迁移脚本
【优先级】P0
【指派角色】后端开发
【详细描述】依据「三、数据库设计」完成 11 张表（users、districts、system_dicts、apartments、room_types、rental_plans、audit_records、favorites、messages、verify_codes、sms_logs）的 Django ORM 模型与 migrations。
【验收标准】
1. `python manage.py migrate` 成功创建所有表、索引、外键、唯一约束。
2. 所有逻辑删除字段 `deleted_at` 存在。
3. 部分唯一索引（如 favorites 用户+房源未删除）生效。

#### Issue 3
【Issue 标题】Django 预置数据脚本：行政区划、系统字典、管理员账号
【优先级】P0
【指派角色】后端开发
【详细描述】依据「三、初始数据」编写种子脚本，初始化上海行政区划、系统字典、管理员账号 `admin123/3816832z`。
【验收标准】
1. 启动脚本后数据库存在 16 个行政区及下属街道/镇。
2. 所有下拉字典数据完整。
3. 管理员账号可登录（后续接管理员登录接口验证）。

#### Issue 4
【Issue 标题】Django DRF 短信验证码与频控模块
【优先级】P0
【指派角色】后端开发
【详细描述】实现验证码生成、存储（verify_codes 表）、校验、5 分钟有效期、1 分钟限发 1 次、1 小时限发 10 次；V1.0 发送动作使用 mock（控制台/日志），但预留阿里云短信配置项。
【验收标准】
1. `/api/v1/auth/sms-code` 接口符合频控规则。
2. 验证码 5 分钟内有效，使用一次后失效。
3. 超频返回 429001。

#### Issue 5
【Issue 标题】Django DRF 用户注册/登录/身份选择接口
【优先级】P0
【指派角色】后端开发
【详细描述】实现注册、手机号+密码登录、手机号+验证码登录、首次登录身份选择、忘记密码、修改密码接口，密码 bcrypt 加密。
【验收标准】
1. 注册成功后用户 role 为空，登录返回 role 为空时需前端跳转身份选择。
2. 密码错误、验证码错误返回明确错误码。
3. 接口符合第四章认证模块约定。

#### Issue 6
【Issue 标题】Django DRF 管理员登录与权限隔离
【优先级】P0
【指派角色】后端开发
【详细描述】实现管理员账号登录接口；封装 JWT 鉴权依赖与角色校验依赖，确保商家接口拒绝租客/管理员，管理员接口拒绝商家/租客。
【验收标准】
1. `admin123/3816832z` 可登录并获取 token。
2. 非商家访问 `/api/v1/merchant/*` 返回 403001。
3. 非管理员访问 `/api/v1/admin/*` 返回 403001。

#### Issue 7
【Issue 标题】Django 图片上传与本地静态资源服务
【优先级】P0
【指派角色】后端开发
【详细描述】实现 `/api/v1/uploads/image` 单图上传接口，限制 5MB、jpg/png/webp，本地存储并返回可访问 URL；配置静态文件服务 `/uploads`。
【验收标准】
1. 上传成功后可通过 URL 访问图片。
2. 大文件/非法格式返回 400001。
3. 重启服务后历史图片仍可访问。

#### Issue 8
【Issue 标题】Django DRF 房源发布接口（含房型与租金方案）
【优先级】P0
【指派角色】后端开发
【详细描述】实现商家发布房源接口：校验公寓基础信息、至少 1 组房型、房型图片 ≤5 张、租期租金方案 ≥1 组；保存公寓状态为 `pending_first_review` 并创建 `first_review` 审核记录。
【验收标准】
1. 合法请求返回 apartment_id 与 audit_id。
2. 缺房型或字段不合法返回 400002。
3. 非商家调用返回 403001。

#### Issue 9
【Issue 标题】Django DRF 公共房源列表与详情接口
【优先级】P0
【指派角色】后端开发
【详细描述】实现公共房源列表（仅 `published`）、组合筛选、分页；房源详情与户型详情接口；列表卡片字段包含最低月租金。
【验收标准】
1. 筛选条件可叠加，结果按审核通过时间倒序。
2. 未上架房源不在列表出现。
3. 详情接口返回完整公寓、房型、租金方案及当前用户收藏状态（已登录时）。

#### Issue 10
【Issue 标题】Django DRF 收藏接口
【优先级】P0
【指派角色】后端开发
【详细描述】实现收藏/取消收藏、我的收藏列表；收藏按公寓维度，使用逻辑删除，支持幂等。
【验收标准】
1. 同一用户重复收藏同一公寓不报错，返回已存在标识。
2. 取消收藏后列表不再显示。
3. 列表按收藏时间倒序。

#### Issue 11
【Issue 标题】Django DRF 商家已上架房源管理与编辑（含变更审核）
【优先级】P0
【指派角色】后端开发
【详细描述】实现商家已上架列表、自有房源详情、编辑接口；编辑时若 `name`、`district_id`、`street_id`、`detail_address` 任一变化则生成 `change_review` 审核单并保留原房源；否则直接更新。
【验收标准】
1. 商家只能编辑/删除自己的房源。
2. 变更公寓名称或位置时生成待审核的 `audit_record`，原房源仍 `published`。
3. 删除房源时同步逻辑删除关联未批准审核单。

#### Issue 12
【Issue 标题】Django DRF 管理员审核通过/驳回接口
【优先级】P0
【指派角色】后端开发
【详细描述】实现管理员审核列表、审核详情、通过、驳回；首次审核通过将公寓置为 `published`，驳回置为 `first_rejected`；变更审核通过后将快照数据覆盖原房源，驳回收据作废并保留原房源。
【验收标准】
1. 通过/驳回后公寓与审核单状态正确。
2. 变更审核详情返回 `original_data`、`submitted_data`、`changed_fields`。
3. 非管理员无法操作。

#### Issue 13
【Issue 标题】Django 站内信与短信通知触发
【优先级】P0
【指派角色】后端开发
【详细描述】审核驳回时向商家发送站内信（messages 表）并记录短信发送日志（sms_logs 表，V1.0 mock 发送）；站内信包含驳回原因与跳转编辑页所需 ID。
【验收标准】
1. 首次/变更审核驳回后商家收到 1 条未读站内信。
2. 站内信包含 `related_apartment_id` 与 `related_audit_id`。
3. sms_logs 表有对应 mock 记录。

### 阶段二：前端开发

#### Issue 14
【Issue 标题】前端工程初始化与公共依赖配置
【优先级】P0
【指派角色】前端开发
【详细描述】依据「二、技术选型与整体架构」创建 Vue3 + Vite + TypeScript 工程，集成 Vant 4、Tailwind CSS、Pinia、Vue Router、Axios；配置 H5 响应式基准、请求拦截、路由守卫。
【验收标准】
1. `npm run dev` 可启动，375px 基准下页面正常。
2. 路由守卫在 token 失效时跳转登录。
3. 全局 loading 与 toast 可调用。

#### Issue 15
【Issue 标题】登录/注册/忘记密码/身份选择页面
【优先级】P0
【指派角色】前端开发
【详细描述】实现登录页（密码/验证码切换）、注册页、忘记密码页、身份选择页；表单校验、短信验证码倒计时、登录成功后根据 role 判断是否跳转身份选择。
【验收标准】
1. 注册/登录/重置/选择身份流程可闭环。
2. 首次登录强制进入身份选择，完成后进入房源列表。
3. 表单错误有明确提示。

#### Issue 16
【Issue 标题】房源列表与组合筛选页面
【优先级】P0
【指派角色】前端开发
【详细描述】实现房源列表页（默认按时间倒序）、搜索栏、筛选抽屉（行政区街道联动、户型、租期、价格区间）；卡片展示封面、名称、位置、最低租金；商家登录显示悬浮发布按钮。
【验收标准】
1. 多条件筛选结果正确。
2. 列表分页/下拉加载正常。
3. 租客看不到发布按钮，商家可见。

#### Issue 17
【Issue 标题】房源详情与户型详情页面
【优先级】P0
【指派角色】前端开发
【详细描述】实现房源详情页（只读，收藏按钮）、户型详情页（图片轮播、设施标签、租期租金方案、返回按钮）。
【验收标准】
1. 从列表/收藏进入详情数据正确。
2. 收藏/取消收藏状态实时更新。
3. 户型详情返回上一级公寓详情。

#### Issue 18
【Issue 标题】个人中心首页与收藏/消息/改密页面
【优先级】P0
【指派角色】前端开发
【详细描述】按角色展示个人中心菜单；实现我的收藏、我的消息（已读/未读、点击标记已读）、修改密码页面。
【验收标准】
1. 租客/商家/管理员菜单差异正确。
2. 消息列表按时间倒序，点击消息后状态变已读。
3. 修改密码必须短信验证码。

#### Issue 19
【Issue 标题】商家房源发布页面
【优先级】P0
【指派角色】前端开发
【详细描述】实现房源发布页：公寓基础信息表单、单张总览图上传、行政区街道联动、房型弹窗（图片最多 5 张、设施多选、租金方案多组）、提交审核。
【验收标准】
1. 至少添加 1 组房型才可提交。
2. 房型弹窗新增/编辑/删除正常。
3. 提交成功后跳转「已上架房源」页。

#### Issue 20
【Issue 标题】商家已上架房源与编辑页面
【优先级】P0
【指派角色】前端开发
【详细描述】实现「已上架房源」页的两个 Tab（已上架、审核中），展示两类审核单据；支持房源编辑、删除；变更审核中房源原信息不变。
【验收标准】
1. Tab 分类与数据展示正确。
2. 编辑页数据回显完整。
3. 删除房源后列表刷新，关联审核单同步处理。

#### Issue 21
【Issue 标题】管理员审核列表与详情页面
【优先级】P0
【指派角色】前端开发
【详细描述】实现管理员审核列表（提交审核/变更审核两个 Tab）、审核详情页、通过/驳回操作；变更审核详情中高亮显示发生变更的字段。
【验收标准】
1. 列表按提交时间倒序，Tab 切换正常。
2. 驳回必须填写原因。
3. 变更字段根据后端 `changed_fields` 标红显示。

### 阶段三：测试

#### Issue 22
【Issue 标题】Django 后端接口集成测试
【优先级】P0
【指派角色】测试
【详细描述】使用 pytest-django / Django Test Client 编写核心接口集成测试，覆盖注册登录、房源发布-审核-上架-收藏-驳回通知主流程、权限隔离、验证码频控。
【验收标准】
1. 核心流程测试用例全部通过。
2. 403/404/429 等异常场景有断言。
3. 测试可在 CI/本地通过 Docker Compose 运行。

#### Issue 23
【Issue 标题】前端联调与端到端测试
【优先级】P0
【指派角色】测试
【详细描述】以前端页面为主，联调后端接口，验证租客浏览-收藏、商家发布-编辑-审核、管理员审核-驳回的完整用户旅程；检查 H5 响应式与主要异常提示。
【验收标准】
1. 租客、商家、管理员三端核心流程手工走通。
2. 在 iOS/Android 常见浏览器宽度下无样式错乱。
3. 异常场景（网络错误、权限不足）有明确提示。

### 阶段四：P1 迭代

#### Issue 24
【Issue 标题】阿里云 OSS 图片存储切换
【优先级】P1
【指派角色】后端开发
【详细描述】在 `storage_service` 中新增 OSS 适配器，通过环境变量切换本地/OSS；前端图片 URL 保持向后兼容。
【验收标准】
1. 切换环境变量后上传图片保存到 OSS 并返回可访问 URL。
2. 本地模式与 OSS 模式可一键切换。
3. 原有本地图片仍可访问。

#### Issue 25
【Issue 标题】真实阿里云短信服务对接
【优先级】P1
【指派角色】后端开发
【详细描述】接入阿里云短信 SDK，替换 mock 发送；配置项（AccessKey、签名、模板 CODE）通过环境变量注入。
【验收标准】
1. 验证码真实发送到测试手机号。
2. 驳回短信包含驳回原因简要信息。
3. 配置缺失时服务可降级为 mock 并记录日志。
