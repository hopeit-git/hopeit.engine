echo "==========================="
echo "CI STATIC ANALYSIS: PLUGINS"
echo "==========================="

declare -i code=0


if [ "$1" == "" ] || [ "auth/basic-auth" = "$1" ] ; then
echo "auth/basic-auth"
export MYPYPATH=engine/src/:plugins/auth/basic-auth/src/ && python3 -m mypy --namespace-packages -p hopeit.basic_auth
code+=$?
export MYPYPATH=engine/src/:plugins/auth/basic-auth/src/ && python3 -m mypy --namespace-packages plugins/auth/basic-auth/test/unit/
code+=$?
export MYPYPATH=engine/src/:plugins/auth/basic-auth/src/ && python3 -m mypy --namespace-packages plugins/auth/basic-auth/test/integration/
code+=$?
fi

if [ "$1" == "" ] || [ "clients/app-client" = "$1" ] ; then
echo "clients/app-client"
export MYPYPATH=engine/src/:plugins/clients/apps-client/src/ && python3 -m mypy --namespace-packages -p hopeit.apps_client
code+=$?
export MYPYPATH=engine/src/:plugins/clients/apps-client/src/ && python3 -m mypy --namespace-packages plugins/clients/apps-client/test/unit/
code+=$?
fi

if [ "$1" == "" ] || [ "streams/redis" = "$1" ] ; then
echo "streams/redis"
export MYPYPATH=engine/src/:plugins/streams/redis/src/ && python3 -m mypy --namespace-packages -p hopeit.redis_streams
code+=$?
export MYPYPATH=engine/src/:plugins/streams/redis/src/ && python3 -m mypy --namespace-packages plugins/streams/redis/test/unit/
code+=$?
fi

if [ "$1" == "" ] || [ "storage/redis" = "$1" ] ; then
echo "storage/redis"
export MYPYPATH=engine/src/:plugins/storage/redis/src/ && python3 -m mypy --namespace-packages -p hopeit.redis_storage
code+=$?
export MYPYPATH=engine/src/:plugins/storage/redis/src/ && python3 -m mypy --namespace-packages plugins/storage/redis/test/unit/
code+=$?
fi

if [ "$1" == "" ] || [ "storage/fs" = "$1" ] ; then
echo "storage/fs"
export MYPYPATH=engine/src/:plugins/storage/fs/src/ && python3 -m mypy --namespace-packages -p hopeit.fs_storage
code+=$?
export MYPYPATH=engine/src/:plugins/storage/fs/src/ && python3 -m mypy --namespace-packages plugins/storage/fs/test/unit/ plugins/storage/fs/test/integration/
code+=$?
fi

if [ "$1" == "" ] || [ "ops/apps-visualizer" = "$1" ] ; then
echo "ops/apps-visualizer"
export MYPYPATH=engine/src/:plugins/storage/fs/src/:plugins/ops/log-streamer/src/:plugins/ops/config-manager/src/:plugins/ops/apps-visualizer/src/ && python3 -m mypy --namespace-packages -p hopeit.apps_visualizer
code+=$?
export MYPYPATH=engine/src/:plugins/storage/fs/src/:plugins/ops/log-streamer/src/:plugins/ops/config-manager/src/:plugins/ops/apps-visualizer/src/ && python3 -m mypy --namespace-packages plugins/ops/apps-visualizer/test/integration/
code+=$?
fi

if [ "$1" == "" ] || [ "ops/config-manager" = "$1" ] ; then
echo "ops/config-manager"
export MYPYPATH=engine/src/:plugins/ops/config-manager/src/ && python3 -m mypy --namespace-packages -p hopeit.config_manager
code+=$?
export MYPYPATH=engine/src/:plugins/ops/config-manager/src/ && python3 -m mypy --namespace-packages plugins/ops/config-manager/test/integration/
code+=$?
fi

if [ "$1" == "" ] || [ "ops/log-streamer" = "$1" ] ; then
echo "ops/log-streamer"
export MYPYPATH=engine/src/:plugins/storage/fs/src/:plugins/ops/log-streamer/src/ && python3 -m mypy --namespace-packages -p hopeit.log_streamer
code+=$?
export MYPYPATH=engine/src/:plugins/storage/fs/src/:plugins/ops/log-streamer/src/ && python3 -m mypy --namespace-packages plugins/ops/log-streamer/test/integration/
code+=$?
fi

if [ "$1" == "" ] || [ "data/dataframes" = "$1" ] ; then
echo "data/dataframes"
export MYPYPATH=engine/src/:plugins/storage/fs/src/:plugins/data/dataframes/src/ && python3 -m mypy --namespace-packages -p hopeit.dataframes
code+=$?
export MYPYPATH=engine/src/:plugins/storage/fs/src/:plugins/data/dataframes/src/ && python3 -m mypy --namespace-packages plugins/data/dataframes/test/integration/
code+=$?
fi

if [ $code -gt 0 ]
then
  echo "[FAILED] CI STATIC ANALYSIS: PLUGINS"
  exit 1
fi
echo "========================================================================================================"
exit $code
