echo "==============="
echo "CI TEST: ENGINE"
echo "==============="
code=0
export PYTHONPATH=engine/src/:engine/test/:engine/test/unit/:engine/test/integration/ && python3 -m pytest --cov-fail-under=90 --cov-report=term --cov=engine/src/ engine/test/unit/ engine/test/integration/
code+=$?
if [ $code -gt 0 ]
then
  echo "[FAILED] CI TEST: ENGINE"
fi
echo "========================================================================================================"
exit $code
