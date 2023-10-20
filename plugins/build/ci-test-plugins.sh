echo "================"
echo "CI TEST: PLUGINS"
echo "================"


code=0
if [ "$1" == "" ] || [ "auth/basic-auth" = "$1" ] ; then
# auth/basic-auth
export PYTHONPATH=engine/src/:plugins/auth/basic-auth/src/ && python3 -m pytest -v --cov-fail-under=90 --cov-report=term --cov=plugins/auth/basic-auth/src/ plugins/auth/basic-auth/test/unit/ plugins/auth/basic-auth/test/integration/
code+=$?
fi

if [ "$1" == "" ] || [ "clients/apps-client" = "$1" ] ; then
# clients/apps-client
export PYTHONPATH=engine/src/:plugins/clients/apps-client/src/:plugins/clients/apps-client/test/ && python3 -m pytest -v --cov-fail-under=90 --cov-report=term --cov=plugins/clients/apps-client/src/ plugins/clients/apps-client/test/unit/
code+=$?
fi

if [ "$1" == "" ] || [ "streams/redis" = "$1" ] ; then
# streams/redis
export PYTHONPATH=engine/src/:plugins/streams/redis/src/ && python3 -m pytest -v --cov-fail-under=90 --cov-report=term --cov=plugins/streams/redis/src/ plugins/streams/redis/test/unit/
code+=$?
fi

if [ "$1" == "" ] || [ "storage/redis" = "$1" ] ; then
# storage/redis
export PYTHONPATH=engine/src/:plugins/storage/redis/src/ && python3 -m pytest -v --cov-fail-under=90 --cov-report=term --cov=plugins/storage/redis/src plugins/storage/redis/test/unit/
code+=$?
fi

if [ "$1" == "" ] || [ "storage/fs" = "$1" ] ; then
# storage/fs
export PYTHONPATH=engine/src/:plugins/storage/fs/src/ && python3 -m pytest -v --cov-fail-under=90 --cov-report=term --cov=plugins/storage/fs/src/ plugins/storage/fs/test/unit/ plugins/storage/fs/test/integration/
code+=$?
fi

if [ "$1" == "" ] || [ "ops/apps-visualizer" = "$1" ] ; then
# ops/apps-visualizer
export PYTHONPATH=engine/src/:plugins/auth/basic-auth/src:plugins/storage/fs/src/:apps/examples/simple-example/src/:apps/examples/client-example/src/:plugins/ops/log-streamer/src/:plugins/ops/config-manager/src/:plugins/ops/apps-visualizer/src/ && python3 -m pytest -v --cov-fail-under=90 --cov-report=term --cov=plugins/ops/apps-visualizer/src/ plugins/ops/apps-visualizer/test/integration/
code+=$?
fi

if [ "$1" == "" ] || [ "ops/config-manager" = "$1" ] ; then
# ops/config-manager
export PYTHONPATH=engine/src/:plugins/auth/basic-auth/src:plugins/storage/fs/src/:apps/examples/simple-example/src/:apps/examples/client-example/src/:plugins/ops/config-manager/src/ && python3 -m pytest -v --cov-fail-under=90 --cov-report=term --cov=plugins/ops/config-manager/src/ plugins/ops/config-manager/test/integration/
code+=$?
fi

if [ "$1" == "" ] || [ "ops/log-streamer" = "$1" ] ; then
# ops/log-streamer
export PYTHONPATH=engine/src/:plugins/storage/fs/src/:plugins/ops/log-streamer/src/ && python3 -m pytest -v --cov-fail-under=90 --cov-report=term --cov=plugins/ops/log-streamer/src/ plugins/ops/log-streamer/test/integration/
code+=$?
fi

if [ "$1" == "" ] || [ "data/dataframes" = "$1" ] ; then
# data/dataframes
export PYTHONPATH=engine/src/:plugins/data/dataframes/src/ && python3 -m pytest -v --cov-fail-under=90 --cov-report=term --cov=plugins/data/dataframes/src/ plugins/data/dataframes/test/integration/
code+=$?
fi

if [ $code -gt 0 ]
then
  echo "[FAILED] CI TEST: PLUGINS"
  exit 1
fi
echo "========================================================================================================"
exit $code
