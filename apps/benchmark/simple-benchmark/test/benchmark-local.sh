#!/usr/bin/env bash
echo ./wrk2/wrk -t8 -c40 -d60s -R4000 --u_latency "http://localhost:8021/api/simple-benchmark/1x0/give-me-something?item_id=string"
./wrk2/wrk -t8 -c40 -d60s -R4000 --u_latency "http://localhost:8021/api/simple-benchmark/1x0/give-me-something?item_id=string"
sleep 5
echo ./wrk2/wrk -t6 -c32 -d60s -R4000 --u_latency "http://localhost:8021/api/simple-benchmark/1x0/query-something-redis?item_id=string"
./wrk2/wrk -t6 -c32 -d60s -R4000 --u_latency "http://localhost:8021/api/simple-benchmark/1x0/query-something-redis?item_id=string"
sleep 5
echo ./wrk2/wrk -t4 -c18 -d60s -R4000 --u_latency "http://localhost:8021/api/simple-benchmark/1x0/query-something-fs?item_id=string"
./wrk2/wrk -t4 -c18 -d60s -R4000 --u_latency "http://localhost:8021/api/simple-benchmark/1x0/query-something-fs?item_id=string"