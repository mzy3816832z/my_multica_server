"""
字典模块单元测试
"""
import pytest
from rest_framework.test import APIClient

from apps.dicts.models import SystemDict


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def seed_dicts():
    """创建测试用字典数据"""
    SystemDict.objects.create(category='layout_type', code='studio', label='一室', sort=1)
    SystemDict.objects.create(category='layout_type', code='one_bedroom', label='一室一厅', sort=2)
    SystemDict.objects.create(category='lease_term', code='1_month', label='1个月', sort=1)
    SystemDict.objects.create(category='facility', code='wifi', label='WiFi', sort=1)
    SystemDict.objects.create(category='payment_method', code='pay_1_deposit_1', label='押一付一', sort=1)
    SystemDict.objects.create(category='window_type', code='inner', label='内窗', sort=1)
    SystemDict.objects.create(category='window_orientation', code='east', label='东', sort=1)

    # 创建一个未启用的字典项，用于验证过滤
    SystemDict.objects.create(
        category='layout_type', code='inactive', label='未启用', sort=99, is_active=False
    )

    # 创建一个已软删除的字典项，用于验证过滤
    deleted = SystemDict.objects.create(
        category='layout_type', code='deleted', label='已删除', sort=100
    )
    deleted.delete()


@pytest.mark.django_db
def test_dict_list_layout_type(api_client, seed_dicts):
    """测试获取户型字典列表"""
    response = api_client.get('/api/v1/dicts/', {'category': 'layout_type'})
    assert response.status_code == 200
    data = response.json()
    assert data['code'] == 0
    assert data['message'] == 'success'
    assert len(data['data']) == 2
    codes = [item['code'] for item in data['data']]
    assert 'studio' in codes
    assert 'one_bedroom' in codes


@pytest.mark.django_db
def test_dict_list_lease_term(api_client, seed_dicts):
    """测试获取租期字典列表"""
    response = api_client.get('/api/v1/dicts/', {'category': 'lease_term'})
    assert response.status_code == 200
    data = response.json()
    assert data['code'] == 0
    assert len(data['data']) == 1
    assert data['data'][0]['code'] == '1_month'


@pytest.mark.django_db
def test_dict_list_facility(api_client, seed_dicts):
    """测试获取设施字典列表"""
    response = api_client.get('/api/v1/dicts/', {'category': 'facility'})
    assert response.status_code == 200
    data = response.json()
    assert data['code'] == 0
    assert len(data['data']) == 1
    assert data['data'][0]['code'] == 'wifi'


@pytest.mark.django_db
def test_dict_list_payment_method(api_client, seed_dicts):
    """测试获取支付方式字典列表"""
    response = api_client.get('/api/v1/dicts/', {'category': 'payment_method'})
    assert response.status_code == 200
    data = response.json()
    assert data['code'] == 0
    assert len(data['data']) == 1
    assert data['data'][0]['code'] == 'pay_1_deposit_1'


@pytest.mark.django_db
def test_dict_list_window_type(api_client, seed_dicts):
    """测试获取窗户类型字典列表"""
    response = api_client.get('/api/v1/dicts/', {'category': 'window_type'})
    assert response.status_code == 200
    data = response.json()
    assert data['code'] == 0
    assert len(data['data']) == 1
    assert data['data'][0]['code'] == 'inner'


@pytest.mark.django_db
def test_dict_list_window_orientation(api_client, seed_dicts):
    """测试获取窗户朝向字典列表"""
    response = api_client.get('/api/v1/dicts/', {'category': 'window_orientation'})
    assert response.status_code == 200
    data = response.json()
    assert data['code'] == 0
    assert len(data['data']) == 1
    assert data['data'][0]['code'] == 'east'


@pytest.mark.django_db
def test_dict_list_missing_category(api_client):
    """测试未传 category 返回参数错误"""
    response = api_client.get('/api/v1/dicts/')
    assert response.status_code == 400
    data = response.json()
    assert data['code'] == 400001


@pytest.mark.django_db
def test_dict_list_empty_category(api_client):
    """测试空 category 返回参数错误"""
    response = api_client.get('/api/v1/dicts/', {'category': ''})
    assert response.status_code == 400
    data = response.json()
    assert data['code'] == 400001


@pytest.mark.django_db
def test_dict_list_inactive_filtered(api_client, seed_dicts):
    """测试未启用的字典项被过滤"""
    response = api_client.get('/api/v1/dicts/', {'category': 'layout_type'})
    assert response.status_code == 200
    data = response.json()
    codes = [item['code'] for item in data['data']]
    assert 'inactive' not in codes


@pytest.mark.django_db
def test_dict_list_deleted_filtered(api_client, seed_dicts):
    """测试已软删除的字典项被过滤"""
    response = api_client.get('/api/v1/dicts/', {'category': 'layout_type'})
    assert response.status_code == 200
    data = response.json()
    codes = [item['code'] for item in data['data']]
    assert 'deleted' not in codes


@pytest.mark.django_db
def test_dict_list_nonexistent_category(api_client):
    """测试查询不存在的 category 返回空数组"""
    response = api_client.get('/api/v1/dicts/', {'category': 'nonexistent'})
    assert response.status_code == 200
    data = response.json()
    assert data['code'] == 0
    assert data['data'] == []
