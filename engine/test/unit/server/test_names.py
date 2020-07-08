from hopeit.server.names import route_name, module_name, auto_path, auto_path_prefixed


def test_route_name():
    assert route_name('api', 'app-name', '1.0') == '/api/app-name/1x0'
    assert route_name('api', 'app_name', '1.0') == '/api/app-name/1x0'
    assert route_name('api', 'app_name', '1x0') == '/api/app-name/1x0'
    assert route_name('api', 'app-name', '1.0', 'plugin-name', '2.0') == \
        '/api/app-name/1x0/plugin-name/2x0'


def test_module_name():
    assert module_name('simple.example', 'simple_event') == "simple.example.simple_event"
    assert module_name('simple_example', 'simple_event') == "simple_example.simple_event"
    assert module_name('root.simple_example', 'simple_event') == "root.simple_example.simple_event"
    assert module_name('default-app', 'simple_event') == "default_app.simple_event"


def test_auto_path():
    assert auto_path('simple-example', '1.0') == "simple_example.1x0"
    assert auto_path('simple.example', '1.0') == "simplexexample.1x0"


def test_auto_path_prefixed():
    assert auto_path_prefixed('simple.example', '1.0') == "simple.example.1x0"
