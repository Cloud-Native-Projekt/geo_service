params_protected_area = {
    "lat": 49.4916295,
    "lng": 11.1132376
}

params_in_forest = {
    "lng": 11.466577,
    "lat": 48.232089
}


def test_get_power_infrastructure(test_app):
    response = test_app.get("/geo/power", params=params_protected_area)
    assert response.status_code == 200
    data = response.json()
    expected_keys = [
        "nearest_substation_distance_m",
        "nearest_powerline_distance_m",
    ]
    for key in expected_keys:
        assert key in data


def test_get_forests(test_app):
    response = test_app.get("/geo/forest", params=params_in_forest)
    assert response.status_code == 200
    data = response.json()
    expected_keys = [
        "type",
        "in_forest",
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
    assert data['in_forest'] is True


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
    assert data['in_protected_area'] is True


def test_get_protected_areas(test_app):
    response = test_app.get("/geo/protection", params=params_protected_area)
    assert response.status_code == 200
    data = response.json()
    expected_keys = [
        "in_protected_area",
        "designation",
    ]
    for key in expected_keys:
        assert key in data


def test_get_buildings_in_area(test_app):
    response = test_app.get("/geo/builtup", params=params_protected_area)
    assert response.status_code == 200
    data = response.json()
    expected_keys = [
        "in_populated_area",
    ]
    for key in expected_keys:
        assert key in data
