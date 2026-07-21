# 上海公寓租赁平台后端服务

## 技术栈
- Python 3.11+
- Django 5.2 + Django REST Framework 3.17
- PostgreSQL 15（开发/生产统一）
- JWT 认证（djangorestframework-simplejwt）
- drf-spectacular 自动生成 OpenAPI 3.0 文档

## 快速启动

### 1. 环境准备
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 本地开发需额外安装开发依赖
pip install -r requirements-dev.txt
```

### 2. 环境变量
复制 `.env.example` 为 `.env` 并修改：
```bash
cp .env.example .env
```

### 3. Docker Compose 启动（推荐）
```bash
docker-compose up -d
```

### 4. 本地开发启动
```bash
python manage.py migrate
python manage.py runserver 127.0.0.1:8000
```

## 接口文档
启动后访问：
- Swagger UI: `/api/docs/`
- Redoc: `/api/redoc/`
- OpenAPI JSON: `/api/schema/`

## 健康检查
```bash
curl http://localhost:8000/health
```

## 项目结构
```
my_multica_server/
├── config/              # Django 配置包
├── apps/                # 业务应用
│   └── core/            # 公共层（响应、异常、权限、工具）
├── seed_data/           # 初始化数据
├── manage.py
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```
