echo "========================"
echo "CI STATIC ANALYSIS: APPS"
echo "========================"

declare -i code=0
echo "apps/simple-example"
export MYPYPATH=engine/src/:plugins/storage/fs/src:engine/src/:plugins/auth/basic-auth/src:apps/examples/simple-example/src/ && python3 -m mypy --check-untyped-defs --namespace-packages -p common -p model -p simple_example
code+=$?
export MYPYPATH=engine/src/:plugins/storage/fs/src:engine/src/:plugins/auth/basic-auth/src:apps/examples/simple-example/src/ && python3 -m mypy --namespace-packages apps/examples/simple-example/test/unit/
code+=$?
export MYPYPATH=engine/src/:plugins/storage/fs/src:engine/src/:plugins/auth/basic-auth/src:apps/examples/simple-example/src/ && python3 -m mypy --namespace-packages apps/examples/simple-example/test/integration/
code+=$?
python3 -m flake8 --max-line-length=120 apps/examples/simple-example/src/ apps/examples/simple-example/test/unit/ apps/examples/simple-example/test/integration/
code+=$?
python3 -m pylint apps/examples/simple-example/src/
code+=$?

echo "apps/client-example"
export MYPYPATH=engine/src/:plugins/auth/basic-auth/src:apps/examples/simple-example/src/:apps/examples/client-example/src/ && python3 -m mypy --check-untyped-defs --namespace-packages -p client_example
code+=$?
export MYPYPATH=engine/src/:plugins/auth/basic-auth/src:apps/examples/simple-example/src/:apps/examples/client-example/src/ && python3 -m mypy --namespace-packages apps/examples/client-example/test/unit/
code+=$?
export MYPYPATH=engine/src/:plugins/auth/basic-auth/src:apps/examples/simple-example/src/:apps/examples/client-example/src/ && python3 -m mypy --namespace-packages apps/examples/client-example/test/integration/
code+=$?
python3 -m flake8 --max-line-length=120 apps/examples/client-example/src/ apps/examples/client-example/test/unit/ apps/examples/client-example/test/integration/
code+=$?
python3 -m pylint apps/examples/client-example/src/client_example/
code+=$?

if [ $code -gt 0 ]
then
  echo "[FAILED] CI STATIC ANALYSIS"
fi
echo "========================================================================================================"
exit $code
