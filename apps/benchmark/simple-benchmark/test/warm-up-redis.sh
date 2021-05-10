#!/usr/bin/env bash
echo Starting redis image...
cd ../docker && docker-compose up -d redis
cd ..
echo Warming up simple-benchmark redis data...
if [ -n "$1" ]
then
  host=${1}
else
  host=localhost
fi
for i in {1..2000}; do
  curl --silent --output /dev/null -d '{"id": "string", "user": "string"}' -H 'Content-Type: application/json' "http://$host:8021/api/simple-benchmark/1x0/save-something-redis"
done
echo Done.