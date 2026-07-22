"""
行政区划模块单元测试
"""
import pytest
from rest_framework.test import APIClient

from apps.districts.models import District


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def seed_districts():
    """创建测试用行政区划数据"""
    # 创建一级行政区
    pudong = District.objects.create(name='浦东新区', level=1, sort=1)
    huangpu = District.objects.create(name='黄浦区', level=1, sort=2)

    # 创建二级街道/镇
    District.objects.create(name='陆家嘴街道', level=2, parent=pudong, sort=1)
    District.objects.create(name='张江街道', level=2, parent=pudong, sort=2)
    District.objects.create(name='南京东路街道', level=2, parent=huangpu, sort=1)

    return {'pudong': pudong, 'huangpu': huangpu}


@pytest.mark.django_db
def test_district_list_level1(api_client, seed_districts):
    """测试获取一级行政区列表"""
    response = api_client.get('/api/v1/districts/', {'level': 1})
    assert response.status_code == 200
    data = response.json()
    assert data['code'] == 0
    assert data['message'] == 'success'
    assert len(data['data']) == 2
    names = [item['name'] for item in data['data']]
    assert '浦东新区' in names
    assert '黄浦区' in names


@pytest.mark.django_db
def test_district_list_level2(api_client, seed_districts):
    """测试获取二级街道/镇列表"""
    pudong = seed_districts['pudong']
    response = api_client.get('/api/v1/districts/', {'level': 2, 'parent_id': pudong.id})
    assert response.status_code == 200
    data = response.json()
    assert data['code'] == 0
    assert len(data['data']) == 2
    names = [item['name'] for item in data['data']]
    assert '陆家嘴街道' in names
    assert '张江街道' in names


@pytest.mark.django_db
def test_district_list_level2_missing_parent_id(api_client):
    """测试 level=2 但未传 parent_id 返回参数错误"""
    response = api_client.get('/api/v1/districts/', {'level': 2})
    assert response.status_code == 200
    data = response.json()
    assert data['code'] == 400001


@pytest.mark.django_db
def test_district_list_missing_level(api_client):
    """测试未传 level 返回参数错误"""
    response = api_client.get('/api/v1/districts/')
    assert response.status_code == 200
    data = response.json()
    assert data['code'] == 400001


@pytest.mark.django_db
def test_district_list_invalid_level(api_client):
    """测试 level 不是 1 或 2 返回参数错误"""
    response = api_client.get('/api/v1/districts/', {'level': 3})
    assert response.status_code == 200
    data = response.json()
    assert data['code'] == 400001


@pytest.mark.django_db
def test_district_list_invalid_parent_id(api_client):
    """测试 parent_id 对应的行政区不存在返回参数错误"""
    response = api_client.get('/api/v1/districts/', {'level': 2, 'parent_id': 99999})
    assert response.status_code == 200
    data = response.json()
    assert data['code'] == 400001


@pytest.mark.django_db
def test_district_list_level2_with_level1_parent_id(api_client, seed_districts):
    """测试用 level=1 的 parent_id 去查 level=2（理论上不会查到，但验证行为）"""
    # 用黄浦区的 id 查，应该能查到其下属的街道
    huangpu = seed_districts['huangpu']
    response = api_client.get('/api/v1/districts/', {'level': 2, 'parent_id': huangpu.id})
    assert response.status_code == 200
    data = response.json()
    assert data['code'] == 0
    assert len(data['data']) == 1
    assert data['data'][0]['name'] == '南京东路街道'


@pytest.mark.django_db
def test_district_list_no_parent_field(api_client, seed_districts):
    """测试返回结果中不包含 parent 字段"""
    response = api_client.get('/api/v1/districts/', {'level': 1})
    assert response.status_code == 200
    data = response.json()
    assert data['code'] == 0
    for item in data['data']:
        assert 'parent' not in item
        assert 'id' in item
        assert 'name' in item
        assert 'level' in item
        assert 'code' in item
        assert 'sort' in item
