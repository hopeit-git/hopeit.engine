# Filesystem storage plugin

This package supplies `FileStorage` for JSON dataobjects and binary files, plus
reusable storage events. Basic library usage does not require a plugin app config.

## Usage

- Read typed `FileStorageSettings` in the app event and initialize storage with
  `FileStorage.with_settings(settings)`. Follow
  [save_something.py](../../../apps/examples/simple-example/src/simple_example/save_something.py)
  and [query_something.py](../../../apps/examples/simple-example/src/simple_example/query_something.py).
- Await `store(key, value)` and `get(key, datatype=Type, partition_key=...)` for
  dataobjects. Use `store_file` / `get_file` for binary data. Handle missing reads
  as `None` in the app event.
- Object partitions use `event_ts()` or the current time, normalized to UTC.
  File partitions use `partition_dt` or the current time. Supply the matching
  partition key when reading; keep local business dates separate.
- Use distinct keys for distinct objects within a partition. Preserve serialized
  type compatibility when loading existing stored data.

## Development

Check [the implementation](src/hopeit/fs_storage/__init__.py),
[partition helpers](src/hopeit/fs_storage/partition.py), and [tests](test/).
Preserve the temporary-write/rename behavior for JSON writes and the distinction
between dataobject keys and binary filenames.

Run from the repository root:

```sh
make PLUGINFOLDER=plugins/storage/fs lint-plugin
make PLUGINFOLDER=plugins/storage/fs test-plugin
```
