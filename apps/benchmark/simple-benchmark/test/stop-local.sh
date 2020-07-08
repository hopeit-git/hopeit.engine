#!/usr/bin/env bash
if [ -f ./local.pid ]
then
  echo Stopping hopeit.engine...
  kill -9 `cat local.pid`
  rm local.pid
  echo Done.
else
  echo ...local.pid file not found, the service could be stopped.
fi