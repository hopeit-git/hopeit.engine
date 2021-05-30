import json
import os
from pathlib import Path

import pytest

from . import APP_VERSION


@pytest.fixture
def events_graph_data():
    with open(Path(os.path.dirname(os.path.realpath(__file__))) / 'events_graph_data.json') as f:
        json_str = f.read().replace("${APP_VERSION}", APP_VERSION)
        return json.loads(json_str)
