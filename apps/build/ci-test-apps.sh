echo "============="
echo "CI TEST: APPS"
echo "============="
code=0
# test/simple-example
export PYTHONPATH=engine/src/:plugins/auth/basic-auth/src:plugins/storage/fs/src:apps/examples/simple-example/src/ && python3 -m pytest -v --cov-fail-under=90 --cov-report=term --cov=apps/examples/simple-example/src/ apps/examples/simple-example/test/unit/ apps/examples/simple-example/test/integration/
code+=$?

if [ $code -gt 0 ]
then
  echo "[FAILED] CI TEST: APPS"
fi
echo "========================================================================================================"
exit $code
