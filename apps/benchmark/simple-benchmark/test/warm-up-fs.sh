#!/usr/bin/env bash
echo Warming up simple-benchmark fs data...
if [ -n "$1" ]
then
  host=${1}
else
  host=localhost
fi
for i in {1..2000}; do
  curl --silent --output /dev/null -d '{"id": "string", "user": "string"}' -H 'Content-Type: application/json' "http://$host:8021/api/simple-benchmark/0x14/save-something-fs"
done
echo Done.
