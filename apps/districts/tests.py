"""
行政区划模块单元测试
"""
import json

import pytest
from django.test import Client

from apps.districts.models import District


@pytest.fixture
def api_client():
    return Client()


@pytest.fixture
def seed_districts():
    """创建测试用行政区划数据"""
    district = District.objects.create(name='测试区', level=1, sort=1)
    street1 = District.objects.create(name='测试街道一', level=2, parent=district, sort=1)
    street2 = District.objects.create(name='测试街道二', level=2, parent=district, sort=2)
    return district, street1, street2


@pytest.mark.django_db
def test_district_list_level_1(api_client, seed_districts):
    """测试 GET /api/v1/districts/?level=1 返回一级行政区"""
    response = api_client.get('/api/v1/districts/?level=1')
    assert response.status_code == 200
    data = json.loads(response.content)
    assert data['code'] == 0
    assert data['message'] == 'success'
    assert len(data['data']) == 1
    assert data['data'][0]['name'] == '测试区'
    assert data['data'][0]['level'] == 1


@pytest.mark.django_db
def test_district_list_level_2(api_client, seed_districts):
    """测试 GET /api/v1/districts/?level=2 返回街道/镇"""
    response = api_client.get('/api/v1/districts/?level=2')
    assert response.status_code == 200
    data = json.loads(response.content)
    assert data['code'] == 0
    assert len(data['data']) == 2
    names = [item['name'] for item in data['data']]
    assert '测试街道一' in names
    assert '测试街道二' in names


@pytest.mark.django_db
def test_district_list_by_parent_id(api_client, seed_districts):
    """测试 GET /api/v1/districts/?parent_id={id} 返回下级区划"""
    district, _, _ = seed_districts
    response = api_client.get(f'/api/v1/districts/?parent_id={district.id}')
    assert response.status_code == 200
    data = json.loads(response.content)
    assert data['code'] == 0
    assert len(data['data']) == 2
    assert all(item['parent'] == district.id for item in data['data'])


@pytest.mark.django_db
def test_district_list_no_params(api_client, seed_districts):
    """测试无参数时返回全部区划"""
    response = api_client.get('/api/v1/districts/')
    assert response.status_code == 200
    data = json.loads(response.content)
    assert data['code'] == 0
    assert len(data['data']) == 3


@pytest.mark.django_db
def test_district_list_invalid_level(api_client):
    """测试非法 level 参数返回 400"""
    response = api_client.get('/api/v1/districts/?level=3')
    assert response.status_code == 400
    data = json.loads(response.content)
    assert data['code'] == 400001


@pytest.mark.django_db
def test_district_list_invalid_level_type(api_client):
    """测试非整数 level 参数返回 400"""
    response = api_client.get('/api/v1/districts/?level=abc')
    assert response.status_code == 400
    data = json.loads(response.content)
    assert data['code'] == 400001


@pytest.mark.django_db
def test_district_list_invalid_parent_id_type(api_client):
    """测试非整数 parent_id 参数返回 400"""
    response = api_client.get('/api/v1/districts/?parent_id=abc')
    assert response.status_code == 400
    data = json.loads(response.content)
    assert data['code'] == 400001


@pytest.mark.django_db
def test_district_list_empty_result(api_client):
    """测试无数据时返回空数组"""
    response = api_client.get('/api/v1/districts/?level=1')
    assert response.status_code == 200
    data = json.loads(response.content)
    assert data['code'] == 0
    assert data['data'] == []
