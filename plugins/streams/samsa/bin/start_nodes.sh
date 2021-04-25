export SAMSA_NODES="http://localhost:8020,http://localhost:8021,http://localhost:8022"

# Events are partitioned in 3 nodes when produced
export SAMSA_PUSH_NODES=$SAMSA_NODES

# Optimal setup: 1 local consumer per partition
export SAMSA_CONSUME_NODES="in-process"

# Uncomment to distribute consumption between cluster nodes
# export SAMSA_CONSUME_NODES=$SAMSA_NODES

# Start 3 nodes with embedded Samsa stream manager
nohup hopeit_server run --port=8020 --start-streams --config-files=engine/config/dev-noauth-samsa.json,plugins/streams/samsa/config/1x0.json,plugins/auth/basic-auth/config/1x0.json,apps/examples/simple-example/config/1x0.json --api-file=apps/examples/simple-example/api/openapi.json &
nohup hopeit_server run --port=8021 --start-streams --config-files=engine/config/dev-noauth-samsa.json,plugins/streams/samsa/config/1x0.json,plugins/auth/basic-auth/config/1x0.json,apps/examples/simple-example/config/1x0.json --api-file=apps/examples/simple-example/api/openapi.json &
nohup hopeit_server run --port=8022 --start-streams --config-files=engine/config/dev-noauth-samsa.json,plugins/streams/samsa/config/1x0.json,plugins/auth/basic-auth/config/1x0.json,apps/examples/simple-example/config/1x0.json --api-file=apps/examples/simple-example/api/openapi.json &

#Monitor cluster
watch -n 0.3 "curl localhost:8020/api/samsa/1x0/cluster-stats?nodes=$SAMSA_NODES | jq"
