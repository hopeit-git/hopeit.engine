echo "================"
echo "CI TEST: PLUGINS"
echo "================"
code=0
# auth/basic-auth
export PYTHONPATH=engine/src/:plugins/auth/basic-auth/src/ && python3 -m pytest --cov-fail-under=90 --cov-report=term --cov=plugins/auth/basic-auth/src/ plugins/auth/basic-auth/test/unit/ plugins/auth/basic-auth/test/integration/
code+=$?

# streams/redis
export PYTHONPATH=engine/src/:plugins/streams/redis/src/ && python3 -m pytest --cov-fail-under=90 --cov-report=term --cov=plugins/streams/redis/src/ plugins/streams/redis/test/unit/
code+=$?

if [ $code -gt 0 ]
then
  echo "[FAILED] CI TEST: PLUGINS"
fi
echo "========================================================================================================"
exit $code
