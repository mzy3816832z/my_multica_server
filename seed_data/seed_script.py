#!/usr/bin/env python
"""
Django 预置数据种子脚本
初始化内容：
1. 上海 16 个行政区及下属街道/镇
2. 系统字典（户型、设施、租期、支付方式、内外窗、朝向）
3. 管理员账号 admin123 / 3816832z

用法：
    python manage.py shell < seed_data/seed_script.py
或作为独立脚本：
    python seed_data/seed_script.py
"""

import os
import sys
import django

# 设置 Django 环境
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

import bcrypt
from apps.districts.models import District
from apps.dicts.models import SystemDict
from apps.users.models import User


# ============================
# 1. 上海行政区划数据
# ============================
SHANGHAI_DISTRICTS = {
    '黄浦区': [
        '南京东路街道', '外滩街道', '半淞园路街道', '小东门街道', '豫园街道',
        '老西门街道', '五里桥街道', '打浦桥街道', '淮海中路街道', '瑞金二路街道',
    ],
    '徐汇区': [
        '天平路街道', '湖南路街道', '斜土路街道', '枫林路街道', '长桥街道',
        '田林街道', '虹梅路街道', '康健新村街道', '徐家汇街道', '凌云路街道',
        '龙华街道', '漕河泾街道', '华泾镇',
    ],
    '长宁区': [
        '华阳路街道', '新华路街道', '江苏路街道', '天山路街道', '周家桥街道',
        '虹桥街道', '仙霞新村街道', '程家桥街道', '北新泾街道', '新泾镇',
    ],
    '静安区': [
        '江宁路街道', '石门二路街道', '南京西路街道', '静安寺街道', '曹家渡街道',
        '天目西路街道', '北站街道', '宝山路街道', '共和新路街道', '大宁路街道',
        '彭浦新村街道', '临汾路街道', '芷江西路街道', '彭浦镇',
    ],
    '普陀区': [
        '曹杨新村街道', '长风新村街道', '长寿路街道', '甘泉路街道', '石泉路街道',
        '宜川路街道', '真如镇街道', '万里街道', '长征镇', '桃浦镇',
    ],
    '虹口区': [
        '欧阳路街道', '曲阳路街道', '广中路街道', '嘉兴路街道', '凉城新村街道',
        '四川北路街道', '江湾镇街道', '北外滩街道',
    ],
    '杨浦区': [
        '定海路街道', '平凉路街道', '江浦路街道', '四平路街道', '控江路街道',
        '长白新村街道', '延吉新村街道', '殷行街道', '大桥街道', '五角场街道',
        '新江湾城街道', '长海路街道', '江浦路街道', '四平路街道',
    ],
    '闵行区': [
        '江川路街道', '古美路街道', '新虹街道', '浦锦街道', '申莘街道',
        '莘庄镇', '七宝镇', '浦江镇', '梅陇镇', '虹桥镇',
        '马桥镇', '吴泾镇', '华漕镇', '颛桥镇',
    ],
    '宝山区': [
        '吴淞街道', '张庙街道', '大场镇', '杨行镇', '月浦镇',
        '罗店镇', '顾村镇', '高境镇', '庙行镇', '淞南镇',
        '宝山城市工业园区', '罗泾镇',
    ],
    '嘉定区': [
        '新成路街道', '真新街道', '菊园新区街道', '嘉定镇街道', '南翔镇',
        '安亭镇', '马陆镇', '徐行镇', '华亭镇', '外冈镇', '江桥镇',
    ],
    '浦东新区': [
        '潍坊新村街道', '陆家嘴街道', '周家渡街道', '塘桥街道', '上钢新村街道',
        '南码头路街道', '沪东新村街道', '金杨新村街道', '洋泾街道', '浦兴路街道',
        '东明路街道', '花木街道', '申港街道', '陆家嘴街道', '张江镇',
        '金桥镇的', '高桥镇', '高行镇', '高东镇', '曹路镇',
        '唐镇', '北蔡镇', '合庆镇', '蔡路镇', '川沙新镇',
        '南汇新城镇', '大团镇', '周浦镇', '航头镇', '新场镇',
        '宣桥镇', '六灶镇', '惠南镇', '老港镇', '万祥镇',
        '书院镇', '泥城镇', '芦潮港镇',
    ],
    '金山区': [
        '石化街道', '朱泾镇', '枫泾镇', '张堰镇', '亭林镇',
        '吕巷镇', '廊下镇', '金山卫镇', '漕泾镇', '山阳镇',
    ],
    '松江区': [
        '岳阳街道', '永丰街道', '方松街道', '中山街道', '广富林街道',
        '九里亭街道', '泗泾镇', '佘山镇', '车墩镇', '新桥镇',
        '洞泾镇', '九亭镇', '泖港镇', '石湖荡镇', '新浜镇',
        '叶榭镇', '小昆山镇', '莘庄镇',
    ],
    '青浦区': [
        '夏阳街道', '盈浦街道', '香花桥街道', '赵巷镇', '徐泾镇',
        '华新镇', '重固镇', '白鹤镇', '朱家角镇', '练塘镇',
        '金泽镇', '夏阳街道',
    ],
    '奉贤区': [
        '南桥街道', '奉浦街道', '庄行镇', '金汇镇', '青村镇',
        '柘林镇', '四团镇', '海湾镇', '奉城镇', '南桥镇',
        '西渡街道', '海湾旅游区', '上海海港综合经济开发区',
    ],
    '崇明区': [
        '城桥镇', '堡镇', '新河镇', '庙镇', '竖新镇',
        '向化镇', '三星镇', '港西镇', '建设镇', '中兴镇',
        '陈家镇', '绿华镇', '新村乡', '长兴镇', '横沙乡',
        '新海镇', '东平镇', '光明农场', '跃进农场', '新海农场',
        '红星农场', '红旗农场', '前进农场', '前哨农场', '前进农场',
    ],
}


# ============================
# 2. 系统字典数据
# ============================
SYSTEM_DICTS = [
    # 户型
    {'category': 'layout_type', 'code': 'studio', 'label': '一室', 'sort': 1},
    {'category': 'layout_type', 'code': 'one_bedroom', 'label': '一室一厅', 'sort': 2},
    {'category': 'layout_type', 'code': 'two_bedroom', 'label': '两室一厅', 'sort': 3},
    {'category': 'layout_type', 'code': 'two_bedroom_2', 'label': '两室两厅', 'sort': 4},
    {'category': 'layout_type', 'code': 'three_bedroom', 'label': '三室一厅', 'sort': 5},
    {'category': 'layout_type', 'code': 'three_bedroom_2', 'label': '三室两厅', 'sort': 6},
    {'category': 'layout_type', 'code': 'loft', 'label': 'LOFT', 'sort': 7},
    {'category': 'layout_type', 'code': 'duplex', 'label': '复式', 'sort': 8},

    # 设施
    {'category': 'facility', 'code': 'air_conditioner', 'label': '空调', 'sort': 1},
    {'category': 'facility', 'code': 'washing_machine', 'label': '洗衣机', 'sort': 2},
    {'category': 'facility', 'code': 'refrigerator', 'label': '冰箱', 'sort': 3},
    {'category': 'facility', 'code': 'water_heater', 'label': '热水器', 'sort': 4},
    {'category': 'facility', 'code': 'wifi', 'label': 'WiFi', 'sort': 5},
    {'category': 'facility', 'code': 'tv', 'label': '电视', 'sort': 6},
    {'category': 'facility', 'code': 'sofa', 'label': '沙发', 'sort': 7},
    {'category': 'facility', 'code': 'bed', 'label': '床', 'sort': 8},
    {'category': 'facility', 'code': 'wardrobe', 'label': '衣柜', 'sort': 9},
    {'category': 'facility', 'code': 'desk', 'label': '书桌', 'sort': 10},
    {'category': 'facility', 'code': 'kitchen', 'label': '厨房', 'sort': 11},
    {'category': 'facility', 'code': 'balcony', 'label': '阳台', 'sort': 12},
    {'category': 'facility', 'code': 'elevator', 'label': '电梯', 'sort': 13},
    {'category': 'facility', 'code': 'parking', 'label': '停车位', 'sort': 14},
    {'category': 'facility', 'code': 'gym', 'label': '健身房', 'sort': 15},

    # 租期
    {'category': 'lease_term', 'code': '1_month', 'label': '1个月', 'sort': 1},
    {'category': 'lease_term', 'code': '3_months', 'label': '3个月', 'sort': 2},
    {'category': 'lease_term', 'code': '6_months', 'label': '半年', 'sort': 3},
    {'category': 'lease_term', 'code': '1_year', 'label': '1年', 'sort': 4},
    {'category': 'lease_term', 'code': '18_months', 'label': '18个月', 'sort': 5},
    {'category': 'lease_term', 'code': '2_years', 'label': '2年', 'sort': 6},

    # 支付方式
    {'category': 'payment_method', 'code': 'pay_1_deposit_1', 'label': '押一付一', 'sort': 1},
    {'category': 'payment_method', 'code': 'pay_1_deposit_3', 'label': '押一付三', 'sort': 2},
    {'category': 'payment_method', 'code': 'pay_1_deposit_6', 'label': '押一付六', 'sort': 3},
    {'category': 'payment_method', 'code': 'pay_1_deposit_12', 'label': '押一付年', 'sort': 4},
    {'category': 'payment_method', 'code': 'no_deposit', 'label': '免押金', 'sort': 5},

    # 内外窗
    {'category': 'window_type', 'code': 'inner', 'label': '内窗', 'sort': 1},
    {'category': 'window_type', 'code': 'outer', 'label': '外窗', 'sort': 2},

    # 朝向
    {'category': 'orientation', 'code': 'east', 'label': '东', 'sort': 1},
    {'category': 'orientation', 'code': 'south', 'label': '南', 'sort': 2},
    {'category': 'orientation', 'code': 'west', 'label': '西', 'sort': 3},
    {'category': 'orientation', 'code': 'north', 'label': '北', 'sort': 4},
    {'category': 'orientation', 'code': 'southeast', 'label': '东南', 'sort': 5},
    {'category': 'orientation', 'code': 'southwest', 'label': '西南', 'sort': 6},
    {'category': 'orientation', 'code': 'northeast', 'label': '东北', 'sort': 7},
    {'category': 'orientation', 'code': 'northwest', 'label': '西北', 'sort': 8},
]


# ============================
# 3. 管理员账号
# ============================
ADMIN_USERNAME = 'admin123'
ADMIN_PASSWORD = '3816832z'
ADMIN_ROLE = 'admin'


def seed_districts():
    """初始化上海行政区划"""
    created_count = 0
    for district_name, streets in SHANGHAI_DISTRICTS.items():
        district, created = District.objects.get_or_create(
            name=district_name,
            defaults={
                'parent': None,
                'level': 1,
                'code': None,
                'sort': 0,
            }
        )
        if created:
            created_count += 1

        for street_name in streets:
            _, created = District.objects.get_or_create(
                name=street_name,
                parent=district,
                defaults={
                    'level': 2,
                    'code': None,
                    'sort': 0,
                }
            )
            if created:
                created_count += 1

    print(f'[Districts] Created {created_count} records.')
    return created_count


def seed_system_dicts():
    """初始化系统字典"""
    created_count = 0
    for item in SYSTEM_DICTS:
        _, created = SystemDict.objects.get_or_create(
            category=item['category'],
            code=item['code'],
            defaults={
                'label': item['label'],
                'sort': item['sort'],
                'is_active': True,
            }
        )
        if created:
            created_count += 1

    print(f'[SystemDicts] Created {created_count} records.')
    return created_count


def seed_admin_user():
    """初始化管理员账号"""
    existing = User.objects.filter(username=ADMIN_USERNAME).first()
    if existing:
        print(f'[AdminUser] User "{ADMIN_USERNAME}" already exists (id={existing.id}).')
        return existing

    hashed = bcrypt.hashpw(ADMIN_PASSWORD.encode(), bcrypt.gensalt()).decode()
    admin = User.objects.create(
        username=ADMIN_USERNAME,
        phone=None,
        hashed_password=hashed,
        role=ADMIN_ROLE,
        is_active=True,
    )
    print(f'[AdminUser] Created admin user "{ADMIN_USERNAME}" (id={admin.id}).')
    return admin


def run_seed():
    """执行全部种子数据初始化"""
    print('=' * 50)
    print('Starting seed data initialization...')
    print('=' * 50)

    d_count = seed_districts()
    dict_count = seed_system_dicts()
    admin = seed_admin_user()

    print('=' * 50)
    print('Seed data initialization completed!')
    print(f'  - Districts: {d_count} created')
    print(f'  - SystemDicts: {dict_count} created')
    print(f'  - AdminUser: {admin.username} (id={admin.id})')
    print('=' * 50)

    # 验证数据
    district_level1 = District.objects.filter(level=1).count()
    district_level2 = District.objects.filter(level=2).count()
    dict_categories = SystemDict.objects.values('category').distinct().count()
    print(f'[Verification] Level-1 districts: {district_level1}')
    print(f'[Verification] Level-2 districts: {district_level2}')
    print(f'[Verification] Dict categories: {dict_categories}')
    print(f'[Verification] Total dict items: {SystemDict.objects.count()}')


if __name__ == '__main__':
    run_seed()
