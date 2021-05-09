echo "================"
echo "CI TEST: PLUGINS"
echo "================"
code=0
# auth/basic-auth
export PYTHONPATH=engine/src/:plugins/auth/basic-auth/src/ && python3 -m pytest -v --cov-fail-under=90 --cov-report=term --cov=plugins/auth/basic-auth/src/ plugins/auth/basic-auth/test/unit/ plugins/auth/basic-auth/test/integration/
code+=$?

# streams/redis
export PYTHONPATH=engine/src/:plugins/streams/redis/src/ && python3 -m pytest -v --cov-fail-under=90 --cov-report=term --cov=plugins/streams/redis/src/ plugins/streams/redis/test/unit/
code+=$?

# storage/redis
export PYTHONPATH=engine/src/:plugins/storage/redis/src/ && python3 -m pytest -v --cov-fail-under=90 --cov-report=term --cov=plugins/storage/redis/src plugins/storage/redis/test/unit/
code+=$?

# storage/fs
export PYTHONPATH=engine/src/:plugins/storage/fs/src/ && python3 -m pytest -v --cov-fail-under=90 --cov-report=term --cov=plugins/storage/fs/src/ plugins/storage/fs/test/unit/
code+=$?

if [ $code -gt 0 ]
then
  echo "[FAILED] CI TEST: PLUGINS"
fi
echo "========================================================================================================"
exit $code
