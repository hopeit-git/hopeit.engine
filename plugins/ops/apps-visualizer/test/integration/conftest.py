import json
import os
from pathlib import Path

import pytest


@pytest.fixture
def events_graph_data():
    with open(Path(os.path.dirname(os.path.realpath(__file__))) / 'events_graph_data.json') as f:
        return json.load(f)
