echo "========================"
echo "CI STATIC ANALYSIS: APPS"
echo "========================"
code=0
# test/simple-example
export MYPYPATH=engine/src/:plugins/auth/basic-auth/src:apps/examples/simple-example/src/ && python3 -m mypy --namespace-packages apps/examples/simple-example/src/ apps/examples/simple-example/test/unit/ apps/examples/simple-example/test/integration/
code+=$?
python3 -m flake8 --max-line-length=120 apps/examples/simple-example/src/ apps/examples/simple-example/test/unit/ apps/examples/simple-example/test/integration/
code+=$?
python3 -m pylint apps/examples/simple-example/src/
code+=$?

if [ $code -gt 0 ]
then
  echo "[FAILED] CI STATIC ANALYSIS"
fi
echo "========================================================================================================"
exit $code
