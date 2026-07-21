"""
测试 settings：使用 SQLite 替代 PostgreSQL
"""
from config.settings import *

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'test_db.sqlite3',
    }
}
