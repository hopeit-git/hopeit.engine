echo "=========================="
echo "CI STATIC ANALYSIS: ENGINE"
echo "=========================="
export MYPYPATH=engine/src/ && python3 -m mypy --install-types --non-interactive --namespace-packages -p hopeit
export MYPYPATH=engine/src:engine/test/ && python3 -m mypy --install-types --non-interactive --namespace-packages engine/test/unit/
export MYPYPATH=engine/src:engine/test/ && python3 -m mypy --install-types --non-interactive --namespace-packages engine/test/integration/
declare -i code=0
export MYPYPATH=engine/src/ && python3 -m mypy --namespace-packages -p hopeit
code+=$?
export MYPYPATH=engine/src:engine/test/ && python3 -m mypy --namespace-packages engine/test/unit/
code+=$?
export MYPYPATH=engine/src:engine/test/ && python3 -m mypy --namespace-packages engine/test/integration/
code+=$?
python3 -m flake8 --max-line-length=120 engine/src/hopeit/ engine/test/
code+=$?
python3 -m pylint engine/src/hopeit/*
code+=$?
if [ $code -gt 0 ]
then
  echo "[FAILED] CI STATIC ANALYSIS: ENGINE"
fi
echo "========================================================================================================"
exit $code
