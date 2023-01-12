echo "==========================="
echo "CI STATIC ANALYSIS: PLUGINS"
echo "==========================="

declare -i code=0
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

echo "clients/app-client"
export MYPYPATH=engine/src/:plugins/clients/apps-client/src/ && python3 -m mypy --namespace-packages -p hopeit.apps_client
code+=$?
export MYPYPATH=engine/src/:plugins/clients/apps-client/src/ && python3 -m mypy --namespace-packages plugins/clients/apps-client/test/unit/
code+=$?
python3 -m flake8 --max-line-length=120 plugins/clients/apps-client/src/hopeit/ plugins/clients/apps-client/test/unit/
code+=$?
python3 -m pylint plugins/clients/apps-client/src/hopeit/apps_client/
code+=$?

echo "streams/redis"
export MYPYPATH=engine/src/:plugins/streams/redis/src/ && python3 -m mypy --namespace-packages -p hopeit.redis_streams
code+=$?
export MYPYPATH=engine/src/:plugins/streams/redis/src/ && python3 -m mypy --namespace-packages plugins/streams/redis/test/unit/
code+=$?
python3 -m flake8 --max-line-length=120 plugins/streams/redis/src/hopeit/ plugins/streams/redis/test/unit/
code+=$?
python3 -m pylint plugins/streams/redis/src/hopeit/redis_streams/
code+=$?

echo "storage/redis"
export MYPYPATH=engine/src/:plugins/storage/redis/src/ && python3 -m mypy --namespace-packages -p hopeit.redis_storage
code+=$?
export MYPYPATH=engine/src/:plugins/storage/redis/src/ && python3 -m mypy --namespace-packages plugins/storage/redis/test/unit/
code+=$?
python3 -m flake8 --max-line-length=120 plugins/storage/redis/src/hopeit/ plugins/storage/redis/test/unit/
code+=$?
python3 -m pylint plugins/storage/redis/src/hopeit/redis_storage/
code+=$?

echo "storage/fs"
export MYPYPATH=engine/src/:plugins/storage/fs/src/ && python3 -m mypy --namespace-packages -p hopeit.fs_storage
code+=$?
export MYPYPATH=engine/src/:plugins/storage/fs/src/ && python3 -m mypy --namespace-packages plugins/storage/fs/test/unit/ plugins/storage/fs/test/integration/
code+=$?
python3 -m flake8 --max-line-length=120 plugins/storage/fs/src/hopeit/ plugins/storage/fs/test/unit/ plugins/storage/fs/test/integration/
code+=$?
python3 -m pylint plugins/storage/fs/src/hopeit/fs_storage/
code+=$?

echo "ops/apps-visualizer"
export MYPYPATH=engine/src/:plugins/storage/fs/src/:plugins/ops/log-streamer/src/:plugins/ops/config-manager/src/:plugins/ops/apps-visualizer/src/ && python3 -m mypy --namespace-packages -p hopeit.apps_visualizer
code+=$?
export MYPYPATH=engine/src/:plugins/storage/fs/src/:plugins/ops/log-streamer/src/:plugins/ops/config-manager/src/:plugins/ops/apps-visualizer/src/ && python3 -m mypy --namespace-packages plugins/ops/apps-visualizer/test/integration/
code+=$?
python3 -m flake8 --max-line-length=120 plugins/ops/apps-visualizer/src/hopeit/ plugins/ops/apps-visualizer/test/integration/
code+=$?
python3 -m pylint plugins/ops/apps-visualizer/src/hopeit/apps_visualizer/
code+=$?

echo "ops/config-manager"
export MYPYPATH=engine/src/:plugins/ops/config-manager/src/ && python3 -m mypy --namespace-packages -p hopeit.config_manager
code+=$?
export MYPYPATH=engine/src/:plugins/ops/config-manager/src/ && python3 -m mypy --namespace-packages plugins/ops/config-manager/test/integration/
code+=$?
python3 -m flake8 --max-line-length=120 plugins/ops/config-manager/src/hopeit/ plugins/ops/config-manager/test/integration/
code+=$?
python3 -m pylint plugins/ops/config-manager/src/hopeit/config_manager/
code+=$?

echo "ops/log-streamer"
export MYPYPATH=engine/src/:plugins/storage/fs/src/:plugins/ops/log-streamer/src/ && python3 -m mypy --namespace-packages -p hopeit.log_streamer
code+=$?
export MYPYPATH=engine/src/:plugins/storage/fs/src/:plugins/ops/log-streamer/src/ && python3 -m mypy --namespace-packages plugins/ops/log-streamer/test/integration/
code+=$?
python3 -m flake8 --max-line-length=120 plugins/ops/log-streamer/src/hopeit/ plugins/ops/log-streamer/test/integration/
code+=$?
python3 -m pylint plugins/ops/log-streamer/src/hopeit/log_streamer/
code+=$?
if [ $code -gt 0 ]
then
  echo "[FAILED] CI STATIC ANALYSIS: PLUGINS"
  exit 1
fi
echo "========================================================================================================"
exit $code
