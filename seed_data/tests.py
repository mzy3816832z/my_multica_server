"""
种子数据单元测试
"""
import pytest
import bcrypt

from apps.districts.models import District
from apps.dicts.models import SystemDict
from apps.users.models import User


@pytest.fixture
def seeded_db(db):
    """每次测试前执行种子脚本"""
    from seed_data.seed_script import run_seed
    run_seed()
    return db


@pytest.mark.django_db
def test_seed_districts_count(seeded_db):
    """验证行政区划数量：16个行政区 + 下属街道/镇"""
    level1 = District.objects.filter(level=1)
    level2 = District.objects.filter(level=2)
    assert level1.count() == 16, f'Expected 16 districts, got {level1.count()}'
    assert level2.count() > 0, 'Expected some streets/towns'
    assert level1.count() + level2.count() > 16


@pytest.mark.django_db
def test_seed_districts_names(seeded_db):
    """验证16个行政区名称完整"""
    expected_names = {
        '黄浦区', '徐汇区', '长宁区', '静安区', '普陀区',
        '虹口区', '杨浦区', '闵行区', '宝山区', '嘉定区',
        '浦东新区', '金山区', '松江区', '青浦区', '奉贤区', '崇明区',
    }
    actual_names = set(District.objects.filter(level=1).values_list('name', flat=True))
    assert expected_names == actual_names


@pytest.mark.django_db
def test_seed_districts_hierarchy(seeded_db):
    """验证街道/镇都有父级行政区"""
    for street in District.objects.filter(level=2):
        assert street.parent is not None
        assert street.parent.level == 1


@pytest.mark.django_db
def test_seed_system_dict_categories(seeded_db):
    """验证6个字典分类都存在"""
    expected_categories = {'layout_type', 'facility', 'lease_term', 'payment_method', 'window_type', 'window_orientation'}
    actual_categories = set(
        SystemDict.objects.values_list('category', flat=True).distinct()
    )
    assert expected_categories == actual_categories


@pytest.mark.django_db
def test_seed_system_dict_layout_type(seeded_db):
    """验证户型字典完整"""
    codes = list(
        SystemDict.objects.filter(category='layout_type').order_by('sort').values_list('code', flat=True)
    )
    expected = ['studio', 'one_bedroom', 'two_bedroom', 'two_bedroom_2',
                'three_bedroom', 'three_bedroom_2', 'loft', 'duplex']
    assert codes == expected


@pytest.mark.django_db
def test_seed_system_dict_facility(seeded_db):
    """验证设施字典完整"""
    count = SystemDict.objects.filter(category='facility').count()
    assert count == 15


@pytest.mark.django_db
def test_seed_system_dict_lease_term(seeded_db):
    """验证租期字典完整"""
    codes = list(
        SystemDict.objects.filter(category='lease_term').order_by('sort').values_list('code', flat=True)
    )
    expected = ['1_month', '3_months', '6_months', '1_year', '18_months', '2_years']
    assert codes == expected


@pytest.mark.django_db
def test_seed_system_dict_payment_method(seeded_db):
    """验证支付方式字典完整"""
    codes = list(
        SystemDict.objects.filter(category='payment_method').order_by('sort').values_list('code', flat=True)
    )
    expected = ['pay_1_deposit_1', 'pay_1_deposit_3', 'pay_1_deposit_6', 'pay_1_deposit_12', 'no_deposit']
    assert codes == expected


@pytest.mark.django_db
def test_seed_system_dict_window_type(seeded_db):
    """验证内外窗字典完整"""
    codes = list(
        SystemDict.objects.filter(category='window_type').order_by('sort').values_list('code', flat=True)
    )
    expected = ['inner', 'outer']
    assert codes == expected


@pytest.mark.django_db
def test_seed_system_dict_window_orientation(seeded_db):
    """验证朝向字典完整"""
    codes = list(
        SystemDict.objects.filter(category='window_orientation').order_by('sort').values_list('code', flat=True)
    )
    expected = ['east', 'south', 'west', 'north', 'southeast', 'southwest', 'northeast', 'northwest']
    assert codes == expected


@pytest.mark.django_db
def test_seed_admin_user_exists(seeded_db):
    """验证管理员账号存在"""
    admin = User.objects.filter(username='admin123').first()
    assert admin is not None
    assert admin.role == 'admin'
    assert admin.is_active is True
    assert admin.phone is None


@pytest.mark.django_db
def test_seed_admin_user_password(seeded_db):
    """验证管理员密码可校验"""
    admin = User.objects.get(username='admin123')
    assert admin.check_password('3816832z')


@pytest.mark.django_db
def test_seed_admin_user_unique(seeded_db):
    """验证管理员账号唯一"""
    count = User.objects.filter(username='admin123').count()
    assert count == 1


@pytest.mark.django_db
def test_seed_idempotent(seeded_db):
    """验证种子脚本幂等：重复执行不会重复创建"""
    from seed_data.seed_script import run_seed
    # 第一次已在 fixture 中执行，再次执行应无新增
    before_district = District.objects.count()
    before_dict = SystemDict.objects.count()
    before_user = User.objects.count()

    run_seed()

    assert District.objects.count() == before_district
    assert SystemDict.objects.count() == before_dict
    assert User.objects.count() == before_user
