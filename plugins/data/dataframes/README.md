# hopeit.engine dataframes plugin


This library is part of hopeit.engine:

> check: https://github.com/hopeit-git/hopeit.engine


### Install using extras when installing hopeit.engine:

```
pip install hopeit.engine[dataframes]
```

### hopeit.dataframes

This plugin introduces dataclasses annotations to work with `pandas` dataframes
as other dataobjects:

`@dataframe` annotation allows a dataclass to become the schema and container for a dataframe
`@dataframeobject` annotation, acts as @dataobject with support to have dataframe annotated fields
`DataFrames` class, provides an api to create, serialize, and access pandas dataframe

Features:
-Type coercion for @dataframe fields
-Transparent access to series in @dataframe objects using dot notation
-Serialization for @dataframe and @dataframeobjects allowing them to be transferred through streams (using file system storage to store the actual data, and transferring only metadata for deserialization in the stream)
-Support to handle @dataframeobject as payload for web requests
