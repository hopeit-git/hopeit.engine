#!/usr/bin/env bash
unameOut="$(uname -s)"
case "${unameOut}" in
    Linux*)     machine=linux;;
    Darwin*)    machine=mac;;
    CYGWIN*)    machine=Cygwin;;
    MINGW*)     machine=MinGw;;
    *)          machine="UNKNOWN:${unameOut}"
esac

if [ -f ./wrk2/wrk ]
then
  echo "Performing tests with wrk2, a constant throughput, correct latency recording variant of wrk"
  echo "... more info in https://github.com/giltene/wrk2"
elif [ $machine == 'mac' ] || [ $machine == 'linux' ]
then 
  echo Downloading from github.com wrk2
  git clone https://github.com/giltene/wrk2.git
  cd wrk2
  make
  cd ..
  echo "Performing tests with wrk2, a constant throughput, correct latency recording variant of wrk"
  echo "... more info in https://github.com/giltene/wrk2"
else
  echo unsupported platform for autotesting
fi