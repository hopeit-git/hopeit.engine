"""
Test app api
"""

from typing import Optional

from hopeit.app.logger import app_extra_logger
from hopeit.app.context import EventContext
from mock_app import MockData

logger, extra = app_extra_logger()

__steps__ = ["entry_point"]

__api__ = {
    "summary": "Test app api",
    "description": "Test app api",
    "parameters": [
        {
            "name": "arg1",
            "in": "query",
            "required": False,
            "description": "Argument 1",
            "schema": {"type": "integer"},
        },
        {
            "description": "Track " "information: " "Request-Id",
            "in": "header",
            "name": "X-Track-Request-Id",
            "required": False,
            "schema": {"type": "string"},
        },
        {
            "description": "Track " "information: " "Request-Ts",
            "in": "header",
            "name": "X-Track-Request-Ts",
            "required": False,
            "schema": {"format": "date-time", "type": "string"},
        },
        {
            "description": "Track " "information: " "track.session_id",
            "in": "header",
            "name": "X-Track-Session-Id",
            "required": True,
            "schema": {"default": "test.session_id", "type": "string"},
        },
    ],
    "responses": {
        "200": {
            "description": "MockData result",
            "content": {"application/json": {"schema": {"$ref": "#/components/schemas/MockData"}}},
        }
    },
    "tags": ["mock_app_api.test", "my_tags"],
    "security": [{"auth.basic": []}],
}


def entry_point(payload: None, context: EventContext, arg1: Optional[int] = None) -> MockData:
    logger.info(context, "mock_app_api_get.entry_point")
    return MockData(f"get-{arg1}")
