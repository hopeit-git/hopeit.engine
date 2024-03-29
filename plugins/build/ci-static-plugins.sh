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
python3 -m flake8 --max-line-length=120 plugins/auth/basic-auth/src/hopeit/ plugins/auth/basic-auth/test/unit/ plugins/auth/basic-auth/test/integration/
code+=$?
python3 -m pylint plugins/auth/basic-auth/src/hopeit/basic_auth/
code+=$?
fi

if [ "$1" == "" ] || [ "clients/app-client" = "$1" ] ; then
echo "clients/app-client"
export MYPYPATH=engine/src/:plugins/clients/apps-client/src/ && python3 -m mypy --namespace-packages -p hopeit.apps_client
code+=$?
export MYPYPATH=engine/src/:plugins/clients/apps-client/src/ && python3 -m mypy --namespace-packages plugins/clients/apps-client/test/unit/
code+=$?
python3 -m flake8 --max-line-length=120 plugins/clients/apps-client/src/hopeit/ plugins/clients/apps-client/test/unit/
code+=$?
python3 -m pylint plugins/clients/apps-client/src/hopeit/apps_client/
code+=$?
fi

if [ "$1" == "" ] || [ "streams/redis" = "$1" ] ; then
echo "streams/redis"
export MYPYPATH=engine/src/:plugins/streams/redis/src/ && python3 -m mypy --namespace-packages -p hopeit.redis_streams
code+=$?
export MYPYPATH=engine/src/:plugins/streams/redis/src/ && python3 -m mypy --namespace-packages plugins/streams/redis/test/unit/
code+=$?
python3 -m flake8 --max-line-length=120 plugins/streams/redis/src/hopeit/ plugins/streams/redis/test/unit/
code+=$?
python3 -m pylint plugins/streams/redis/src/hopeit/redis_streams/
code+=$?
fi

if [ "$1" == "" ] || [ "storage/redis" = "$1" ] ; then
echo "storage/redis"
export MYPYPATH=engine/src/:plugins/storage/redis/src/ && python3 -m mypy --namespace-packages -p hopeit.redis_storage
code+=$?
export MYPYPATH=engine/src/:plugins/storage/redis/src/ && python3 -m mypy --namespace-packages plugins/storage/redis/test/unit/
code+=$?
python3 -m flake8 --max-line-length=120 plugins/storage/redis/src/hopeit/ plugins/storage/redis/test/unit/
code+=$?
python3 -m pylint plugins/storage/redis/src/hopeit/redis_storage/
code+=$?
fi

if [ "$1" == "" ] || [ "storage/fs" = "$1" ] ; then
echo "storage/fs"
export MYPYPATH=engine/src/:plugins/storage/fs/src/ && python3 -m mypy --namespace-packages -p hopeit.fs_storage
code+=$?
export MYPYPATH=engine/src/:plugins/storage/fs/src/ && python3 -m mypy --namespace-packages plugins/storage/fs/test/unit/ plugins/storage/fs/test/integration/
code+=$?
python3 -m flake8 --max-line-length=120 plugins/storage/fs/src/hopeit/ plugins/storage/fs/test/unit/ plugins/storage/fs/test/integration/
code+=$?
python3 -m pylint plugins/storage/fs/src/hopeit/fs_storage/
code+=$?
fi

if [ "$1" == "" ] || [ "ops/apps-visualizer" = "$1" ] ; then
echo "ops/apps-visualizer"
export MYPYPATH=engine/src/:plugins/storage/fs/src/:plugins/ops/log-streamer/src/:plugins/ops/config-manager/src/:plugins/ops/apps-visualizer/src/ && python3 -m mypy --namespace-packages -p hopeit.apps_visualizer
code+=$?
export MYPYPATH=engine/src/:plugins/storage/fs/src/:plugins/ops/log-streamer/src/:plugins/ops/config-manager/src/:plugins/ops/apps-visualizer/src/ && python3 -m mypy --namespace-packages plugins/ops/apps-visualizer/test/integration/
code+=$?
python3 -m flake8 --max-line-length=120 plugins/ops/apps-visualizer/src/hopeit/ plugins/ops/apps-visualizer/test/integration/
code+=$?
python3 -m pylint plugins/ops/apps-visualizer/src/hopeit/apps_visualizer/
code+=$?
fi

if [ "$1" == "" ] || [ "ops/config-manager" = "$1" ] ; then
echo "ops/config-manager"
export MYPYPATH=engine/src/:plugins/ops/config-manager/src/ && python3 -m mypy --namespace-packages -p hopeit.config_manager
code+=$?
export MYPYPATH=engine/src/:plugins/ops/config-manager/src/ && python3 -m mypy --namespace-packages plugins/ops/config-manager/test/integration/
code+=$?
python3 -m flake8 --max-line-length=120 plugins/ops/config-manager/src/hopeit/ plugins/ops/config-manager/test/integration/
code+=$?
python3 -m pylint plugins/ops/config-manager/src/hopeit/config_manager/
code+=$?
fi

if [ "$1" == "" ] || [ "ops/log-streamer" = "$1" ] ; then
echo "ops/log-streamer"
export MYPYPATH=engine/src/:plugins/storage/fs/src/:plugins/ops/log-streamer/src/ && python3 -m mypy --namespace-packages -p hopeit.log_streamer
code+=$?
export MYPYPATH=engine/src/:plugins/storage/fs/src/:plugins/ops/log-streamer/src/ && python3 -m mypy --namespace-packages plugins/ops/log-streamer/test/integration/
code+=$?
python3 -m flake8 --max-line-length=120 plugins/ops/log-streamer/src/hopeit/ plugins/ops/log-streamer/test/integration/
code+=$?
python3 -m pylint plugins/ops/log-streamer/src/hopeit/log_streamer/
code+=$?
fi

if [ "$1" == "" ] || [ "data/dataframes" = "$1" ] ; then
echo "data/dataframes"
export MYPYPATH=engine/src/:plugins/storage/fs/src/:plugins/data/dataframes/src/ && python3 -m mypy --namespace-packages -p hopeit.dataframes
code+=$?
export MYPYPATH=engine/src/:plugins/storage/fs/src/:plugins/data/dataframes/src/ && python3 -m mypy --namespace-packages plugins/data/dataframes/test/integration/
code+=$?
python3 -m flake8 --max-line-length=120 plugins/data/dataframes/src/hopeit/ plugins/data/dataframes/test/integration/
code+=$?
python3 -m pylint plugins/data/dataframes/src/hopeit/dataframes/
code+=$?
fi

if [ $code -gt 0 ]
then
  echo "[FAILED] CI STATIC ANALYSIS: PLUGINS"
  exit 1
fi
echo "========================================================================================================"
exit $code
