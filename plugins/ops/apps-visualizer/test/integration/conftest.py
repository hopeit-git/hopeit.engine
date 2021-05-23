import json

import pytest

from hopeit.app.config import AppConfig


TEST_EVENTS_GRAPH_DATA = """
[
  {
    "data": {
      "group": "REQUEST",
      "id": "simple_example.0x4.list_somethings.GET",
      "content": "GET"
    },
    "classes": "REQUEST"
  },
  {
    "data": {
      "group": "EVENT",
      "id": "simple_example.0x4.list_somethings",
      "content": "simple_example\\n0x4\\nlist_somethings"
    },
    "classes": "EVENT"
  },
  {
    "data": {
      "group": "REQUEST",
      "id": "simple_example.0x4.query_something.GET",
      "content": "GET"
    },
    "classes": "REQUEST"
  },
  {
    "data": {
      "group": "EVENT",
      "id": "simple_example.0x4.query_something",
      "content": "simple_example\\n0x4\\nquery_something"
    },
    "classes": "EVENT"
  },
  {
    "data": {
      "group": "REQUEST",
      "id": "simple_example.0x4.query_something_extended.POST",
      "content": "POST"
    },
    "classes": "REQUEST"
  },
  {
    "data": {
      "group": "EVENT",
      "id": "simple_example.0x4.query_something_extended",
      "content": "simple_example\\n0x4\\nquery_something_extended"
    },
    "classes": "EVENT"
  },
  {
    "data": {
      "group": "REQUEST",
      "id": "simple_example.0x4.save_something.POST",
      "content": "POST"
    },
    "classes": "REQUEST"
  },
  {
    "data": {
      "group": "EVENT",
      "id": "simple_example.0x4.save_something",
      "content": "simple_example\\n0x4\\nsave_something"
    },
    "classes": "EVENT"
  },
  {
    "data": {
      "group": "REQUEST",
      "id": "simple_example.0x4.download_something.GET",
      "content": "GET"
    },
    "classes": "REQUEST"
  },
  {
    "data": {
      "group": "EVENT",
      "id": "simple_example.0x4.download_something",
      "content": "simple_example\\n0x4\\ndownload_something"
    },
    "classes": "EVENT"
  },
  {
    "data": {
      "group": "REQUEST",
      "id": "simple_example.0x4.upload_something.MULTIPART",
      "content": "MULTIPART"
    },
    "classes": "REQUEST"
  },
  {
    "data": {
      "group": "EVENT",
      "id": "simple_example.0x4.upload_something",
      "content": "simple_example\\n0x4\\nupload_something"
    },
    "classes": "EVENT"
  },
  {
    "data": {
      "group": "STREAM",
      "id": "simple_example.0x4.streams.something_event.*",
      "content": "simple_example\\n0x4\\nstreams\\nsomething_event"
    },
    "classes": "STREAM"
  },
  {
    "data": {
      "group": "EVENT",
      "id": "simple_example.0x4.service.something_generator",
      "content": "simple_example\\n0x4\\nservice\\nsomething_generator"
    },
    "classes": "EVENT"
  },
  {
    "data": {
      "group": "REQUEST",
      "id": "simple_example.0x4.streams.something_event.POST",
      "content": "POST"
    },
    "classes": "REQUEST"
  },
  {
    "data": {
      "group": "EVENT",
      "id": "simple_example.0x4.streams.something_event",
      "content": "simple_example\\n0x4\\nstreams\\nsomething_event"
    },
    "classes": "EVENT"
  },
  {
    "data": {
      "group": "EVENT",
      "id": "simple_example.0x4.streams.process_events",
      "content": "simple_example\\n0x4\\nstreams\\nprocess_events"
    },
    "classes": "EVENT"
  },
  {
    "data": {
      "group": "REQUEST",
      "id": "simple_example.0x4.collector.query_concurrently.POST",
      "content": "POST"
    },
    "classes": "REQUEST"
  },
  {
    "data": {
      "group": "EVENT",
      "id": "simple_example.0x4.collector.query_concurrently",
      "content": "simple_example\\n0x4\\ncollector\\nquery_concurrently"
    },
    "classes": "EVENT"
  },
  {
    "data": {
      "group": "REQUEST",
      "id": "simple_example.0x4.collector.collect_spawn.POST",
      "content": "POST"
    },
    "classes": "REQUEST"
  },
  {
    "data": {
      "group": "STREAM",
      "id": "simple_example.0x4.collector.collect_spawn.collector@load_first.*",
      "content": "simple_example\\n0x4\\ncollector\\ncollect_spawn\\ncollector@load_first"
    },
    "classes": "STREAM"
  },
  {
    "data": {
      "group": "EVENT",
      "id": "simple_example.0x4.collector.collect_spawn",
      "content": "simple_example\\n0x4\\ncollector\\ncollect_spawn"
    },
    "classes": "EVENT"
  },
  {
    "data": {
      "group": "EVENT",
      "id": "simple_example.0x4.collector.collect_spawn$spawn",
      "content": "simple_example\\n0x4\\ncollector\\ncollect_spawn$spawn"
    },
    "classes": "EVENT"
  },
  {
    "data": {
      "group": "REQUEST",
      "id": "simple_example.0x4.shuffle.spawn_event.POST",
      "content": "POST"
    },
    "classes": "REQUEST"
  },
  {
    "data": {
      "group": "STREAM",
      "id": "simple_example.0x4.shuffle.spawn_event.spawn_many_events.*",
      "content": "simple_example\\n0x4\\nshuffle\\nspawn_event\\nspawn_many_events"
    },
    "classes": "STREAM"
  },
  {
    "data": {
      "group": "EVENT",
      "id": "simple_example.0x4.shuffle.spawn_event",
      "content": "simple_example\\n0x4\\nshuffle\\nspawn_event"
    },
    "classes": "EVENT"
  },
  {
    "data": {
      "group": "EVENT",
      "id": "simple_example.0x4.shuffle.spawn_event$update_status",
      "content": "simple_example\\n0x4\\nshuffle\\nspawn_event$update_status"
    },
    "classes": "EVENT"
  },
  {
    "data": {
      "group": "REQUEST",
      "id": "simple_example.0x4.shuffle.parallelize_event.POST",
      "content": "POST"
    },
    "classes": "REQUEST"
  },
  {
    "data": {
      "group": "STREAM",
      "id": "simple_example.0x4.shuffle.parallelize_event.fork_something.*",
      "content": "simple_example\\n0x4\\nshuffle\\nparallelize_event\\nfork_something"
    },
    "classes": "STREAM"
  },
  {
    "data": {
      "group": "EVENT",
      "id": "simple_example.0x4.shuffle.parallelize_event",
      "content": "simple_example\\n0x4\\nshuffle\\nparallelize_event"
    },
    "classes": "EVENT"
  },
  {
    "data": {
      "group": "STREAM",
      "id": "simple_example.0x4.shuffle.parallelize_event.process_first_part.*",
      "content": "simple_example\\n0x4\\nshuffle\\nparallelize_event\\nprocess_first_part"
    },
    "classes": "STREAM"
  },
  {
    "data": {
      "group": "EVENT",
      "id": "simple_example.0x4.shuffle.parallelize_event$process_first_part",
      "content": "simple_example\\n0x4\\nshuffle\\nparallelize_event$process_first_part"
    },
    "classes": "EVENT"
  },
  {
    "data": {
      "group": "EVENT",
      "id": "simple_example.0x4.shuffle.parallelize_event$update_status",
      "content": "simple_example\\n0x4\\nshuffle\\nparallelize_event$update_status"
    },
    "classes": "EVENT"
  },
  {
    "data": {
      "id": "edge_simple_example.0x4.list_somethings.GET",
      "source": "simple_example.0x4.list_somethings.GET",
      "target": "simple_example.0x4.list_somethings",
      "label": ""
    }
  },
  {
    "data": {
      "id": "edge_simple_example.0x4.query_something.GET",
      "source": "simple_example.0x4.query_something.GET",
      "target": "simple_example.0x4.query_something",
      "label": ""
    }
  },
  {
    "data": {
      "id": "edge_simple_example.0x4.query_something_extended.POST",
      "source": "simple_example.0x4.query_something_extended.POST",
      "target": "simple_example.0x4.query_something_extended",
      "label": ""
    }
  },
  {
    "data": {
      "id": "edge_simple_example.0x4.save_something.POST",
      "source": "simple_example.0x4.save_something.POST",
      "target": "simple_example.0x4.save_something",
      "label": ""
    }
  },
  {
    "data": {
      "id": "edge_simple_example.0x4.download_something.GET",
      "source": "simple_example.0x4.download_something.GET",
      "target": "simple_example.0x4.download_something",
      "label": ""
    }
  },
  {
    "data": {
      "id": "edge_simple_example.0x4.upload_something.MULTIPART",
      "source": "simple_example.0x4.upload_something.MULTIPART",
      "target": "simple_example.0x4.upload_something",
      "label": ""
    }
  },
  {
    "data": {
      "id": "edge_simple_example.0x4.streams.process_events.simple_example.0x4.streams.something_event.high-prio",
      "source": "simple_example.0x4.streams.something_event.*",
      "target": "simple_example.0x4.streams.process_events",
      "label": "high-prio"
    }
  },
  {
    "data": {
      "id": "edge_simple_example.0x4.streams.process_events.simple_example.0x4.streams.something_event.AUTO",
      "source": "simple_example.0x4.streams.something_event.*",
      "target": "simple_example.0x4.streams.process_events",
      "label": ""
    }
  },
  {
    "data": {
      "id": "edge_simple_example.0x4.service.something_generator.simple_example.0x4.streams.something_event.AUTO",
      "source": "simple_example.0x4.service.something_generator",
      "target": "simple_example.0x4.streams.something_event.*",
      "label": ""
    }
  },
  {
    "data": {
      "id": "edge_simple_example.0x4.streams.something_event.POST",
      "source": "simple_example.0x4.streams.something_event.POST",
      "target": "simple_example.0x4.streams.something_event",
      "label": ""
    }
  },
  {
    "data": {
      "id": "edge_simple_example.0x4.streams.something_event.simple_example.0x4.streams.something_event.high-prio",
      "source": "simple_example.0x4.streams.something_event",
      "target": "simple_example.0x4.streams.something_event.*",
      "label": "high-prio"
    }
  },
  {
    "data": {
      "id": "edge_simple_example.0x4.collector.query_concurrently.POST",
      "source": "simple_example.0x4.collector.query_concurrently.POST",
      "target": "simple_example.0x4.collector.query_concurrently",
      "label": ""
    }
  },
  {
    "data": {
      "id": "edge_simple_example.0x4.collector.collect_spawn.POST",
      "source": "simple_example.0x4.collector.collect_spawn.POST",
      "target": "simple_example.0x4.collector.collect_spawn",
      "label": ""
    }
  },
  {
    "data": {
      "id": "edge_simple_example.0x4.collector.collect_spawn$spawn.simple_example.0x4.collector.collect_spawn.collector@load_first.AUTO",
      "source": "simple_example.0x4.collector.collect_spawn.collector@load_first.*",
      "target": "simple_example.0x4.collector.collect_spawn$spawn",
      "label": ""
    }
  },
  {
    "data": {
      "id": "edge_simple_example.0x4.collector.collect_spawn.simple_example.0x4.collector.collect_spawn.collector@load_first.AUTO",
      "source": "simple_example.0x4.collector.collect_spawn",
      "target": "simple_example.0x4.collector.collect_spawn.collector@load_first.*",
      "label": ""
    }
  },
  {
    "data": {
      "id": "edge_simple_example.0x4.collector.collect_spawn$spawn.simple_example.0x4.streams.something_event.AUTO",
      "source": "simple_example.0x4.collector.collect_spawn$spawn",
      "target": "simple_example.0x4.streams.something_event.*",
      "label": ""
    }
  },
  {
    "data": {
      "id": "edge_simple_example.0x4.shuffle.spawn_event.POST",
      "source": "simple_example.0x4.shuffle.spawn_event.POST",
      "target": "simple_example.0x4.shuffle.spawn_event",
      "label": ""
    }
  },
  {
    "data": {
      "id": "edge_simple_example.0x4.shuffle.spawn_event$update_status.simple_example.0x4.shuffle.spawn_event.spawn_many_events.AUTO",
      "source": "simple_example.0x4.shuffle.spawn_event.spawn_many_events.*",
      "target": "simple_example.0x4.shuffle.spawn_event$update_status",
      "label": ""
    }
  },
  {
    "data": {
      "id": "edge_simple_example.0x4.shuffle.spawn_event.simple_example.0x4.shuffle.spawn_event.spawn_many_events.AUTO",
      "source": "simple_example.0x4.shuffle.spawn_event",
      "target": "simple_example.0x4.shuffle.spawn_event.spawn_many_events.*",
      "label": ""
    }
  },
  {
    "data": {
      "id": "edge_simple_example.0x4.shuffle.spawn_event$update_status.simple_example.0x4.streams.something_event.AUTO",
      "source": "simple_example.0x4.shuffle.spawn_event$update_status",
      "target": "simple_example.0x4.streams.something_event.*",
      "label": ""
    }
  },
  {
    "data": {
      "id": "edge_simple_example.0x4.shuffle.parallelize_event.POST",
      "source": "simple_example.0x4.shuffle.parallelize_event.POST",
      "target": "simple_example.0x4.shuffle.parallelize_event",
      "label": ""
    }
  },
  {
    "data": {
      "id": "edge_simple_example.0x4.shuffle.parallelize_event$process_first_part.simple_example.0x4.shuffle.parallelize_event.fork_something.AUTO",
      "source": "simple_example.0x4.shuffle.parallelize_event.fork_something.*",
      "target": "simple_example.0x4.shuffle.parallelize_event$process_first_part",
      "label": ""
    }
  },
  {
    "data": {
      "id": "edge_simple_example.0x4.shuffle.parallelize_event.simple_example.0x4.shuffle.parallelize_event.fork_something.AUTO",
      "source": "simple_example.0x4.shuffle.parallelize_event",
      "target": "simple_example.0x4.shuffle.parallelize_event.fork_something.*",
      "label": ""
    }
  },
  {
    "data": {
      "id": "edge_simple_example.0x4.shuffle.parallelize_event$update_status.simple_example.0x4.shuffle.parallelize_event.process_first_part.AUTO",
      "source": "simple_example.0x4.shuffle.parallelize_event.process_first_part.*",
      "target": "simple_example.0x4.shuffle.parallelize_event$update_status",
      "label": ""
    }
  },
  {
    "data": {
      "id": "edge_simple_example.0x4.shuffle.parallelize_event$process_first_part.simple_example.0x4.shuffle.parallelize_event.process_first_part.AUTO",
      "source": "simple_example.0x4.shuffle.parallelize_event$process_first_part",
      "target": "simple_example.0x4.shuffle.parallelize_event.process_first_part.*",
      "label": ""
    }
  },
  {
    "data": {
      "id": "edge_simple_example.0x4.shuffle.parallelize_event$update_status.simple_example.0x4.streams.something_event.AUTO",
      "source": "simple_example.0x4.shuffle.parallelize_event$update_status",
      "target": "simple_example.0x4.streams.something_event.*",
      "label": ""
    }
  }
]
"""


@pytest.fixture
def events_graph_data():
    return json.loads(TEST_EVENTS_GRAPH_DATA)
