echo "==========================="
echo "CI STATIC ANALYSIS: PLUGINS"
echo "==========================="
code=0
# auth/basic-auth
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

# streams/redis
export MYPYPATH=engine/src/:plugins/streams/redis/src/ && python3 -m mypy --namespace-packages -p hopeit.redis_streams
code+=$?
export MYPYPATH=engine/src/:plugins/streams/redis/src/ && python3 -m mypy --namespace-packages plugins/streams/redis/test/unit/
code+=$?
python3 -m flake8 --max-line-length=120 plugins/streams/redis/src/hopeit/ plugins/streams/redis/test/unit/
code+=$?
python3 -m pylint plugins/streams/redis/src/hopeit/redis_streams/
code+=$?

# storage/redis
export MYPYPATH=engine/src/:plugins/storage/redis/src/ && python3 -m mypy --namespace-packages -p hopeit.redis_storage
code+=$?
export MYPYPATH=engine/src/:plugins/storage/redis/src/ && python3 -m mypy --namespace-packages plugins/storage/redis/test/unit/
code+=$?
python3 -m flake8 --max-line-length=120 plugins/storage/redis/src/hopeit/ plugins/storage/redis/test/unit/
code+=$?
python3 -m pylint plugins/storage/redis/src/hopeit/redis_storage/
code+=$?

# storage/fs
export MYPYPATH=engine/src/:plugins/storage/fs/src/ && python3 -m mypy --namespace-packages -p hopeit.fs_storage
code+=$?
export MYPYPATH=engine/src/:plugins/storage/fs/src/ && python3 -m mypy --namespace-packages plugins/storage/fs/test/unit/
code+=$?
python3 -m flake8 --max-line-length=120 plugins/storage/fs/src/hopeit/ plugins/storage/fs/test/unit/
code+=$?
python3 -m pylint plugins/storage/fs/src/hopeit/fs_storage/
code+=$?

if [ $code -gt 0 ]
then
  echo "[FAILED] CI STATIC ANALYSIS: PLUGINS"
fi
echo "========================================================================================================"
exit $code
