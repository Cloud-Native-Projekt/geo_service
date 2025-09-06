params_protected_area = {
    "lng": 11.1132376,
    "lat": 49.4916295
}

params_in_forest = {
    "lng": 11.466577,
    "lat": 48.232089
}

params_no_buildings = {
    "lng": 9.4482421875,
    "lat": 50.6524658203125
}

params_heidelberg = {
    "lat": 49.4093582,
    "lng": 8.694724,
}


def test_get_power_infrastructure_true(test_app):
    response = test_app.get("/geo/power", params=params_heidelberg)
    assert response.status_code == 200
    data = response.json()
    expected_keys = [
        "nearest_substation_distance_m",
        "nearest_powerline_distance_m",
    ]
    assert data['nearest_substation_distance_m'] == 721.5365174132744
    assert data['nearest_powerline_distance_m'] == 5721.874632493594
    for key in expected_keys:
        assert key in data


def test_get_power_infrastructure_false(test_app):
    response = test_app.get("/geo/power", params=params_heidelberg)
    assert response.status_code == 200
    data = response.json()
    expected_keys = [
        "nearest_substation_distance_m",
        "nearest_powerline_distance_m",
    ]
    for key in expected_keys:
        assert key in data


def test_get_forests_true(test_app):
    response = test_app.get("/geo/forest", params=params_in_forest)
    assert response.status_code == 200
    data = response.json()
    expected_keys = [
        "type",
        "in_forest",
    ]
    for key in expected_keys:
        assert key in data
    assert data['type'] == "broadleaved"
    assert data['in_forest']


def test_get_forests_false(test_app):
    response = test_app.get("/geo/forest", params=params_heidelberg)
    assert response.status_code == 200
    data = response.json()
    assert not data['in_forest']


def test_get_protected_areas_true(test_app):
    response = test_app.get("/geo/protection", params=params_protected_area)
    assert response.status_code == 200
    data = response.json()
    expected_keys = [
        "in_protected_area",
        "designation",
    ]
    print(data['designation'])
    for key in expected_keys:
        assert key in data
    assert data['designation'] == "Landschaftsschutzgebiet"
    assert data['in_protected_area']


def test_get_protected_areas_false(test_app):
    response = test_app.get("/geo/protection", params=params_heidelberg)
    assert response.status_code == 200
    data = response.json()
    assert not data['in_protected_area']


def test_get_buildings_in_area_true(test_app):
    response = test_app.get("/geo/builtup", params=params_heidelberg)
    assert response.status_code == 200
    data = response.json()
    assert data['in_populated_area']


def test_get_buildings_in_area_false(test_app):
    response = test_app.get("/geo/builtup", params=params_no_buildings)
    assert response.status_code == 200
    data = response.json()
    assert not data['in_populated_area']
