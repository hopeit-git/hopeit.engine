export SAMSA_NODES="http://localhost:9020,http://localhost:9021,http://localhost:9022"

# Events are partitioned in 3 nodes when produced
export SAMSA_PUSH_NODES=$SAMSA_NODES
export SAMSA_CONSUME_NODES=$SAMSA_NODES

# Start a Samsa cluster
nohup hopeit_server run --port=9020 --start-streams --config-files=engine/config/dev-noauth-samsa.json,plugins/streams/samsa/config/1x0.json &
nohup hopeit_server run --port=9021 --start-streams --config-files=engine/config/dev-noauth-samsa.json,plugins/streams/samsa/config/1x0.json &
nohup hopeit_server run --port=9022 --start-streams --config-files=engine/config/dev-noauth-samsa.json,plugins/streams/samsa/config/1x0.json &

# Start 3 nodesof simple application
nohup hopeit_server run --port=8020 --start-streams --config-files=engine/config/dev-noauth-samsa.json,plugins/auth/basic-auth/config/1x0.json,apps/examples/simple-example/config/1x0.json --api-file=apps/examples/simple-example/api/openapi.json &
nohup hopeit_server run --port=8021 --start-streams --config-files=engine/config/dev-noauth-samsa.json,plugins/auth/basic-auth/config/1x0.json,apps/examples/simple-example/config/1x0.json --api-file=apps/examples/simple-example/api/openapi.json &
nohup hopeit_server run --port=8022 --start-streams --config-files=engine/config/dev-noauth-samsa.json,plugins/auth/basic-auth/config/1x0.json,apps/examples/simple-example/config/1x0.json --api-file=apps/examples/simple-example/api/openapi.json &

#Monitor cluster
watch -n 0.3 "curl localhost:9020/api/samsa/1x0/cluster-stats?nodes=$SAMSA_NODES | jq"
