echo "==========================="
echo "CI STATIC ANALYSIS: PLUGINS"
echo "==========================="
code=0
# auth/basic-auth
export MYPYPATH=engine/src/:plugins/auth/basic-auth/src/ && python3 -m mypy --namespace-packages -p hopeit
code+=$?
export MYPYPATH=engine/src/:plugins/auth/basic-auth/src/ && python3 -m mypy --namespace-packages plugins/auth/basic-auth/test/unit/
code+=$?
export MYPYPATH=engine/src/:plugins/auth/basic-auth/src/ && python3 -m mypy --namespace-packages plugins/auth/basic-auth/test/integration/
code+=$?
python3 -m flake8 --max-line-length=120 plugins/auth/basic-auth/src/hopeit/ plugins/auth/basic-auth/test/unit/ plugins/auth/basic-auth/test/integration/
code+=$?
python3 -m pylint plugins/auth/basic-auth/src/hopeit/basic_auth/
code+=$?

if [ $code -gt 0 ]
then
  echo "[FAILED] CI STATIC ANALYSIS: PLUGINS"
fi
echo "========================================================================================================"
exit $code
