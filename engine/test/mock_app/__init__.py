from dataclasses import dataclass

import pytest  # type: ignore

from hopeit.app.config import AppConfig, AppDescriptor, \
    EventDescriptor, EventType, ReadStreamDescriptor, WriteStreamDescriptor, \
    EventConfig, EventLoggingConfig, AppEngineConfig, EventStreamConfig
from hopeit.dataobjects import dataobject
from hopeit.server.config import APIConfig, AuthConfig, AuthType, LoggingConfig, ServerConfig, StreamsConfig


@dataobject(event_id='value')
@dataclass
class MockData:
    """MockData object"""
    value: str


@dataobject(event_id='value')
@dataclass
class MockResult:
    value: str
    processed: bool = True


@pytest.fixture
def mock_app_config():
    return AppConfig(
        app=AppDescriptor(
            name='mock_app',
            version='test'
        ),
        plugins=[
            AppDescriptor('mock_plugin', 'test')
        ],
        engine=AppEngineConfig(
            import_modules=['mock_app'],
            read_stream_timeout=1,
            read_stream_interval=5,
            track_headers=['session_id'],
            cors_origin='http://test'
        ),
        env={
            'app': {
                'app_value': 'test_app_value'
            },
            'plugin': {
                'custom_value': 'test_custom_value_override'
            }
        },
        events={
            "mock_event": EventDescriptor(
                type=EventType.GET,
                route='mock-app/test/mock-event-test'
            ),
            "mock_event_logging": EventDescriptor(
                type=EventType.GET
            ),
            "mock_post_event": EventDescriptor(
                type=EventType.POST,
                route='mock-app/test/mock-event-test'
            ),
            "mock_multipart_event": EventDescriptor(
                type=EventType.MULTIPART,
                route='mock-app/test/mock-multipart-event-test'
            ),
            "mock_post_nopayload": EventDescriptor(
                type=EventType.POST,
                route='mock-app/test/mock-post-nopayload'
            ),
            "mock_post_preprocess": EventDescriptor(
                type=EventType.POST,
                route='mock-app/test/mock-post-preprocess'
            ),
            "mock_stream_event": EventDescriptor(
                type=EventType.STREAM,
                read_stream=ReadStreamDescriptor(
                    name='mock_stream',
                    consumer_group='mock_consumer_group'
                ),
                config=EventConfig(
                    logging=EventLoggingConfig(
                        extra_fields=['value'],
                        stream_fields=['msg_id']
                    )
                )
            ),
            "mock_stream_timeout": EventDescriptor(
                type=EventType.STREAM,
                read_stream=ReadStreamDescriptor(
                    name='mock_stream',
                    consumer_group='mock_consumer_group'
                ),
                config=EventConfig(
                    logging=EventLoggingConfig(
                        extra_fields=['value'],
                        stream_fields=['msg_id']
                    ),
                    stream=EventStreamConfig(
                        timeout=2
                    )
                )
            ),
            "mock_write_stream_event": EventDescriptor(
                type=EventType.GET,
                write_stream=WriteStreamDescriptor(
                    name='mock_write_stream_event'
                ),
                config=EventConfig(
                    stream=EventStreamConfig(
                        target_max_len=10
                    )
                )
            ),
            "mock_service_event": EventDescriptor(
                type=EventType.SERVICE,
                write_stream=WriteStreamDescriptor(
                    name='mock_write_stream_event'
                ),
                config=EventConfig(
                    stream=EventStreamConfig(
                        target_max_len=10,
                        throttle_ms=100,
                        batch_size=2
                    )
                )
            ),
            "mock_service_timeout": EventDescriptor(
                type=EventType.SERVICE,
                write_stream=WriteStreamDescriptor(
                    name='mock_write_stream_event'
                ),
                config=EventConfig(
                    response_timeout=2.0
                )
            ),
            "mock_spawn_event": EventDescriptor(
                type=EventType.GET,
                write_stream=WriteStreamDescriptor(
                    name='mock_write_stream_event'
                ),
                config=EventConfig(
                    stream=EventStreamConfig(
                        target_max_len=10,
                        throttle_ms=100,
                        batch_size=2
                    )
                )
            ),
            "mock_shuffle_event": EventDescriptor(
                type=EventType.GET,
                write_stream=WriteStreamDescriptor(
                    name='mock_write_stream_event'
                ),
                config=EventConfig(
                    stream=EventStreamConfig(
                        target_max_len=10,
                        throttle_ms=100
                    )
                )
            ),
            "mock_parallelize_event": EventDescriptor(
                type=EventType.GET
            ),
            "mock_file_response": EventDescriptor(
                type=EventType.GET
            ),
            "mock_file_response_content_type": EventDescriptor(
                type=EventType.GET
            ),
            "mock_auth": EventDescriptor(
                type=EventType.GET,
                auth=[AuthType.BASIC]
            ),
            "mock_post_auth": EventDescriptor(
                type=EventType.POST,
                auth=[AuthType.BASIC]
            ),
            "mock_collector": EventDescriptor(
                type=EventType.POST
            ),
            'mock_timeout': EventDescriptor(
                type=EventType.GET,
                config=EventConfig(response_timeout=2.0)
            ),
            'mock_read_write_stream': EventDescriptor(
                type=EventType.STREAM,
                read_stream=ReadStreamDescriptor(
                    name='mock_read_write_stream.read',
                    consumer_group='mock_read_write_stream'
                ),
                write_stream=WriteStreamDescriptor(
                    name='mock_read_write_stream.write'
                )
            )
        },
        server=ServerConfig(
            streams=StreamsConfig(
                stream_manager='mock_engine.MockStreamManager',
                delay_auto_start_seconds=0
            ),
            logging=LoggingConfig(
                log_level="DEBUG", log_path="work/logs/test/")
        )
    )


@dataobject
@dataclass
class TestAPIObj:
    msg: str


@pytest.fixture
def mock_api_app_config():
    return AppConfig(
        app=AppDescriptor(
            name='mock-app-api',
            version='test'
        ),
        plugins=[AppDescriptor(
            name='mock-plugin', version='test'
        )],
        engine=AppEngineConfig(
            import_modules=['mock_app'],
            read_stream_timeout=1,
            read_stream_interval=5,
            track_headers=['session_id'],
            cors_origin='http://test'
        ),
        events={
            "mock-app-api-get": EventDescriptor(
                type=EventType.GET,
                auth=[AuthType.BASIC],
                route='mock-app-api/test/mock-app-api'
            ),
            "mock-app-api-post": EventDescriptor(
                type=EventType.POST,
                route='mock-app-api/test/mock-app-api'
            ),
            "mock-app-api-multipart": EventDescriptor(
                type=EventType.MULTIPART,
                route='mock-app-api/test/mock-app-api-multipart'
            ),
            "mock-app-api-get-list": EventDescriptor(
                type=EventType.GET,
                auth=[AuthType.REFRESH]
            ),
            "mock-app-noapi": EventDescriptor(
                type=EventType.GET
            ),
            "mock_file_response_content_type": EventDescriptor(
                type=EventType.GET
            ),
        },
        server=ServerConfig(
            logging=LoggingConfig(
                log_level="DEBUG", log_path="work/logs/test/"),
            auth=AuthConfig(
                secrets_location='/tmp',
                auth_passphrase='test',
                default_auth_methods=[AuthType.BEARER]
            ),
            api=APIConfig(
                docs_path='/api/docs'
            )
        )
    )


@pytest.fixture
def mock_api_spec():
    return {
        "openapi": "3.0.3",
        "info": {
            "version": "1.0.1",
            "title": "Test API",
            "description": "Test API OpenAPI Spec"
        },
        "paths": {
            "/api/mock-app-api/test/mock-app-api": {
                "get": {
                    "summary": "Test app api",
                    "description": "Test app api",
                    "parameters": [
                        {
                            "name": "arg1",
                            "in": "query",
                            "required": False,
                            "description": "Argument 1",
                            "schema": {
                                "type": "integer"
                            }
                        },
                        {'description': 'Track '
                                        'information: '
                                        'Request-Id',
                         'in': 'header',
                         'name': 'X-Track-Request-Id',
                         'required': False,
                         'schema': {'type': 'string'}},
                        {'description': 'Track '
                                        'information: '
                                        'Request-Ts',
                         'in': 'header',
                         'name': 'X-Track-Request-Ts',
                         'required': False,
                         'schema': {'format': 'date-time',
                                    'type': 'string'}},
                        {'description': 'Track '
                                        'information: '
                                        'track.session_id',
                         'in': 'header',
                         'name': 'X-Track-Session-Id',
                         'required': True,
                         'schema': {'default': 'test.session_id',
                                    'type': 'string'}}
                    ],
                    "responses": {
                        "200": {
                            "description": "MockData result",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/MockData"
                                    }
                                }
                            }
                        }
                    },
                    "tags": [
                        "mock_app_api.test"
                    ],
                    "security": [
                        {
                            "auth.basic": []
                        }
                    ]
                },
                "post": {
                    "summary": "Test app api part 2",
                    "description": "Description Test app api part 2",
                    "parameters": [
                        {
                            "name": "arg1",
                            "in": "query",
                            "required": True,
                            "description": "Argument 1",
                            "schema": {
                                "type": "string"
                            }
                        },
                        {'description': 'Track '
                                        'information: '
                                        'Request-Id',
                         'in': 'header',
                         'name': 'X-Track-Request-Id',
                         'required': False,
                         'schema': {'type': 'string'}},
                        {'description': 'Track '
                                        'information: '
                                        'Request-Ts',
                         'in': 'header',
                         'name': 'X-Track-Request-Ts',
                         'required': False,
                         'schema': {'format': 'date-time',
                                    'type': 'string'}},
                        {'description': 'Track '
                                        'information: '
                                        'track.session_id',
                         'in': 'header',
                         'name': 'X-Track-Session-Id',
                         'required': True,
                         'schema': {'default': 'test.session_id',
                                    'type': 'string'}}
                    ],
                    "requestBody": {
                        "description": "MockData payload",
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/MockData"
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {
                            "description": "int",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "required": [
                                            "mock-app-api-post"
                                        ],
                                        "properties": {
                                            "mock-app-api-post": {
                                                "type": "integer"
                                            }
                                        },
                                        "description": "mock-app-api-post integer payload"
                                    }
                                }
                            }
                        }
                    },
                    "tags": [
                        "mock_app_api.test"
                    ],
                    "security": [
                        {
                            "auth.bearer": []
                        }
                    ]
                }
            }, "/api/mock-app-api/test/mock-app-api-multipart": {
                "post": {
                    "summary": "Test app api multipart post form",
                    "description": "Description Test app api part 2",
                    "parameters": [{
                        "name": "arg1",
                        "in": "query",
                        "required": True,
                        "description": "Argument 1",
                        "schema": {
                            "type": "string"
                        }
                    },
                        {
                        "name": "X-Track-Request-Id",
                        "in": "header",
                        "required": False,
                        "description": "Track information: Request-Id",
                        "schema": {
                            "type": "string"
                        }
                    },
                        {
                        "name": "X-Track-Request-Ts",
                        "in": "header",
                        "required": False,
                        "description": "Track information: Request-Ts",
                        "schema": {
                            "type": "string",
                            "format": "date-time"
                        }
                    },
                        {
                        "name": "X-Track-Session-Id",
                        "in": "header",
                        "required": True,
                        "description": "Track information: track.session_id",
                        "schema": {
                            "type": "string",
                            "default": "test.session_id"
                        }
                    }],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "multipart/form-data": {
                                "schema": {
                                    "type": "object",
                                    "required": [
                                        "field1",
                                        "field2",
                                        "file"
                                    ],
                                    "properties": {
                                        "field1": {
                                            "type": "string",
                                            "description": "Field 1"
                                        },
                                        "field2": {
                                            "$ref": "#/components/schemas/MockData",
                                            "description": "Field 2 json"
                                        },
                                        "file": {
                                            "type": "string",
                                            "format": "binary",
                                            "description": "Upload file"
                                        }
                                    }
                                },
                                "encoding": {
                                    "field1": {"contentType": "text/plain"},
                                    "field2": {"contentType": "application/json"},
                                    "file": {"contentType": "application/octect-stream"}
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {
                            "description": "int",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "required": [
                                            "mock-app-api-multipart"
                                        ],
                                        "properties": {
                                            "mock-app-api-multipart": {
                                                "type": "integer"
                                            }
                                        },
                                        "description": "mock-app-api-multipart integer payload"
                                    }
                                }
                            }
                        }
                    },
                    "tags": [
                        "mock_app_api.test"
                    ],
                    "security": [
                        {
                            "auth.bearer": []
                        }
                    ]
                }
            }, '/api/mock-app-api/test/mock-app-api-get-list': {
                'get': {
                    'summary': 'Test app api list',
                    'description': 'Description of Test app api list',
                    'parameters': [{
                        'description': 'Argument 1',
                        'in': 'query',
                        'name': 'arg1',
                        'required': False,
                        'schema': {'type': 'integer'}
                    }, {
                        'description': 'Track information: Request-Id',
                        'in': 'header',
                        'name': 'X-Track-Request-Id',
                        'required': False,
                        'schema': {'type': 'string'}
                    }, {'description': 'Track information: Request-Ts',
                        'in': 'header',
                        'name': 'X-Track-Request-Ts',
                        'required': False,
                        'schema': {
                            'format': 'date-time',
                            'type': 'string'}
                        }, {
                        'description': 'Track information: track.session_id',
                        'in': 'header',
                        'name': 'X-Track-Session-Id',
                        'required': True,
                        'schema': {
                            'default': 'test.session_id',
                            'type': 'string'}
                    }], 'responses': {
                        '200': {
                            'content': {
                                'application/json': {
                                    'schema': {
                                        'items': {'$ref': '#/components/schemas/MockData'},
                                        'type': 'array'}}
                            }, 'description': 'MockData result'
                        }
                    },
                    'security': [{'mock_app_api.test.refresh': []}],
                    'tags': ['mock_app_api.test']
                }
            },
            "/api/mock-app-api/test/mock-file-response-content-type": {
                "get": {
                    "description": "Test app file response",
                    "parameters": [
                        {
                            "description": "File Name",
                            "in": "query",
                            "name": "file_name",
                            "required": True,
                            "schema": {
                                "type": "string"
                            }
                        },
                        {
                            "description": "Track information: Request-Id",
                            "in": "header",
                            "name": "X-Track-Request-Id",
                            "required": False,
                            "schema": {
                                "type": "string"
                            }
                        },
                        {
                            "description": "Track information: Request-Ts",
                            "in": "header",
                            "name": "X-Track-Request-Ts",
                            "required": False,
                            "schema": {
                                "format": "date-time",
                                "type": "string"
                            }
                        },
                        {
                            "description": "Track information: track.session_id",
                            "in": "header",
                            "name": "X-Track-Session-Id",
                            "required": True,
                            "schema": {
                                "default": "test.session_id",
                                "type": "string"
                            }
                        }
                    ],
                    "responses": {
                        "200": {
                            "content": {
                                "image/png": {
                                    "schema": {
                                        "format": "binary",
                                        "type": "string"
                                    }
                                }
                            },
                            "description": ""
                        }
                    },
                    "security": [
                        {
                            "auth.bearer": []
                        }
                    ],
                    "summary": "Test app file response",
                    "tags": [
                        "mock_app_api.test"
                    ]
                }
            }
        }, "components": {
            "schemas": {
                "MockData": {
                    "type": "object",
                    "required": [
                        "value"
                    ],
                    "properties": {
                        "value": {
                            "type": "string"
                        }
                    },
                    "description": "MockData object",
                    "x-module-name": "mock_app"
                }
            }, "securitySchemes": {
                "auth.basic": {
                    "type": "http",
                    "scheme": "basic"
                }, "auth.bearer": {
                    "type": "http",
                    "scheme": "bearer"
                }, "mock_app_api.test.refresh": {
                    "in": "cookie",
                    "name": "mock_app_api.test.refresh",
                    "type": "apiKey"
                }
            }
        },
        "security": [
            {
                "auth.bearer": []
            }

        ]
    }


@pytest.fixture
def mock_app_api_generated():
    return {'/api/mock-app-api/test/mock-app-noapi': {
        'get': {
            'description': '<<<mock-app-noapi>>>',
            'parameters': [
                {
                    'description': 'Track information: Request-Id',
                    'in': 'header',
                    'name': 'X-Track-Request-Id',
                    'required': False,
                    'schema': {'type': 'string'}
                }, {
                    'description': 'Track information: Request-Ts',
                    'in': 'header',
                    'name': 'X-Track-Request-Ts',
                    'required': False,
                    'schema': {'format': 'date-time',
                               'type': 'string'}
                }, {
                    'description': 'Track information: track.session_id',
                    'in': 'header',
                    'name': 'X-Track-Session-Id',
                    'required': True,
                    'schema': {'default': 'test.session_id',
                               'type': 'string'}}],
            'responses': {},
            'security': [{'auth.bearer': []}],
            'tags': ['mock_app_api.test']}
    }, '/api/mock-app-api/test/mock-plugin/test/plugin-event': {
        'get': {
            'description': '<<<plugin_event>>>',
            'parameters': [
                {
                    'description': 'Track information: Request-Id',
                    'in': 'header',
                    'name': 'X-Track-Request-Id',
                    'required': False,
                    'schema': {'type': 'string'}
                }, {
                    'description': 'Track information: Request-Ts',
                    'in': 'header',
                    'name': 'X-Track-Request-Ts',
                    'required': False,
                    'schema': {
                        'format': 'date-time',
                        'type': 'string'}
                }, {
                    'description': 'Track information: track.session_id',
                    'in': 'header',
                    'name': 'X-Track-Session-Id',
                    'required': True,
                    'schema': {
                        'default': 'test.session_id',
                        'type': 'string'}
                }
            ],
            'responses': {},
            'security': [{'auth.bearer': []}],
            'tags': ['mock_app_api.test']}}
    }
