params_protected_area = {
    "lng":  9.8482,
    "lat": 52.9340,
    "radius": 10000
}

# Forest in bavaria
params_in_forest = {
    "lng": 11.466577,
    "lat": 48.232089,
    "radius": 5000
}

# Point in Sahara
params_sahara = {
    "lat": 23.4162,
    "lng": 25.6628,
    "radius": 2000
}

params_heidelberg = {
    "lat": 49.4093582,
    "lng": 8.694724,
    "radius": 10000
}

# Point in Pfälzer Wald
params_no_infra = {
    "lng": 7.7583,
    "lat": 49.2872,
    "radius": 2000
}


def test_get_power_infrastructure_true(test_app):
    response = test_app.get("/geo/power", params=params_heidelberg)
    assert response.status_code == 200
    data = response.json()
    nearest_substation_distance_m = data['nearest_substation_distance_m']
    nearest_powerline_distance_m = data['nearest_powerline_distance_m']
    assert nearest_substation_distance_m < 10000
    assert nearest_powerline_distance_m < 10000
    assert nearest_substation_distance_m > 0
    assert nearest_powerline_distance_m > 0


def test_get_power_infrastructure_false(test_app):
    response = test_app.get("/geo/power", params=params_no_infra)
    assert response.status_code == 200
    data = response.json()
    assert data['nearest_substation_distance_m'] == 0
    assert data['nearest_powerline_distance_m'] == 0


def test_get_forests_true(test_app):
    response = test_app.get("/geo/forest", params=params_in_forest)
    assert response.status_code == 200
    data = response.json()
    assert data['type'] == "broadleaved"
    assert data['in_forest']


def test_get_forests_false(test_app):
    response = test_app.get("/geo/forest", params=params_sahara)
    assert response.status_code == 200
    data = response.json()
    assert not data['in_forest']


def test_get_protected_areas_true(test_app):
    response = test_app.get("/geo/protection", params=params_protected_area)
    assert response.status_code == 200
    data = response.json()
    assert data['designation'] == "Naturschutzgebiet"
    assert data['in_protected_area']


def test_get_protected_areas_false(test_app):
    response = test_app.get("/geo/protection", params=params_sahara)
    assert response.status_code == 200
    data = response.json()
    assert not data['in_protected_area']


def test_get_buildings_in_area_true(test_app):
    response = test_app.get("/geo/builtup", params=params_heidelberg)
    assert response.status_code == 200
    data = response.json()
    assert data['in_populated_area']


def test_get_buildings_in_area_false(test_app):
    response = test_app.get("/geo/builtup", params=params_sahara)
    assert response.status_code == 200
    data = response.json()
    assert not data['in_populated_area']
