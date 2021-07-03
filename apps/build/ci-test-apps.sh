echo "============="
echo "CI TEST: APPS"
echo "============="
code=0

echo "apps/simple-example"
export PYTHONPATH=engine/src/:plugins/auth/basic-auth/src:plugins/storage/fs/src:apps/examples/simple-example/src/ && python3 -m pytest -v --cov-fail-under=90 --cov-report=term --cov=apps/examples/simple-example/src/ apps/examples/simple-example/test/unit/ apps/examples/simple-example/test/integration/
code+=$?

echo "apps/client-example"
export PYTHONPATH=engine/src/:apps/examples/client-example/src/ && python3 -m pytest -v --cov-fail-under=90 --cov-report=term --cov=apps/examples/client-example/src/ apps/examples/client-example/test/unit/ apps/examples/client-example/test/integration/
code+=$?

if [ $code -gt 0 ]
then
  echo "[FAILED] CI TEST: APPS"
fi
echo "========================================================================================================"
exit $code
