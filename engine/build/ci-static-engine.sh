echo "=========================="
echo "CI STATIC ANALYSIS: ENGINE"
echo "=========================="
code=0
export MYPYPATH=engine/src/ && python3 -m mypy --namespace-packages engine/src/hopeit/ engine/test/
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
