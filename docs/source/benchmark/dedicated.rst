hopeit.engine on dedicated hardware
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
This section shows how to measure the performance of hopeit.engine being run as a python process in a linux operating
system, as well as in a docker container for 1 hopeit.engine instance and 4 hopeit.engine instances behind a reverse
proxy.

The tool used for the measurement is `wrk2 <https://github.com/giltene/wrk2>`_. wrk2 is wrk modified to produce a
constant throughput load, and accurate latency details to the high 9s.

The measurement strategy proposes a scenario where each tested endpoint responds with a latency close to 30ms ("near
real time") for every request in the 99th percentile. The result is a rate (request/s) for the p99.

Three endpoints are evaluated in each test scenario

* http://hostname:port/api/simple-benchmark/1x0/give-me-something retrieves information from objects randomly created

* http://hostname:port/api/simple-benchmark/1x0/query-something-redis returns information from objects stored on a Redis server (memory store)

* http://hostname:port/api/simple-benchmark/1x0/query-something-fs retrieves information from objects stored on a file system (SSD drive)

Scenarios:
__________

:ref:`1 . Local single instance of hopeit.engine`

:ref:`2 . Docker, single/multiple instances of hopeit.engine`

Hardware Used:

* CPU:  Intel(R) Core(TM) i7-8550U CPU @ 1.80GHz 4 real (or 8 HT) cores
* Network:  Intel(R) PRO/1000 Network Connection
* HDD: Western Digital PC SN720 NVMe SSD
* Memory: 16 GB DDR4

Software environment:

The tests were performed on Fedora Workstation 32 with python3 and Redis stock packages.

* Fedora 32 (stock Linux Kernel 5.6.18-300.fc32.x86_64)
* Python 3.8.3
* Redis 5.0.8

1 . Local single instance of hopeit.engine
__________________________________________

Retrieve the hopeit.engine from the git repository, make the dist package, and install it

.. code-block:: bash

    git clone https://github.com/hopeit-git/hopeit.engine.git
    cd hopeit.engine
    python -m venv venv
    source venv/bin/activate    
    make install
    make PLUGINFOLDER=plugins/storage/redis install-plugin
    cd apps/benchmark/simple-benchmark/test

Now we are ready to start the simple-benchmark app to run the tests

.. code-block:: bash

    ./start-local.sh # starts an instance of simple-benchmark app running on hopeit.engine
    ./get-wrk2.sh # gets wrk2 sources from git and make the binary (you'll need git, openssl-devel, gcc, and make on your OS)
    ./warm-up-fs.sh # initializes resources for benchmarking fs endpoint
    ./warm-up-redis.sh # initializes resources for benchmarking redis endpoint
    ./benchmark-local.sh # performs benchmarks for random, fs, and redis endpoints
    ./stop-local.sh # stops the instance of hopeit.engine

Latency (HdrHistogram - Uncorrected Latency, measured without taking delayed starts into account) results:

./wrk2/wrk -t8 -c34 -d60s -R4000 --u_latency "http://localhost:8021/api/simple-benchmark/1x0/give-me-something?item_id=string"
 p99 30.38ms @ 1794.29 req/s

./wrk2/wrk -t6 -c32 -d60s -R4000 --u_latency "http://localhost:8021/api/simple-benchmark/1x0/query-something-redis?item_id=string"
 p99 27.18ms @ 1226.51 req/s

./wrk2/wrk -t4 -c18 -d60s -R4000 --u_latency "http://localhost:8021/api/simple-benchmark/1x0/query-something-fs?item_id=string"
 p99 31.12ms @ 803.38 req/s

2 . Docker, single/multiple instances of hopeit.engine
______________________________________________________

Running docker in the same hardware as dedicated tests, with a custom made docker image to run the hopeit.engine and
reverse proxy, and a stock redis:6 docker image.

The test will be performed on two modalities:

* 1 instance of hopeit.engine on port 8021
* 4 instances of hopeit.engine on ports 8021/8022/8023/8024 running behind a reverse proxy (HAProxy) attending on port 8025

Run the benchmarks

.. code-block:: bash

    ./start-docker.sh # starts a docker with instances of simple-benchmark app running on hopeit.engine
    ./get-wrk2.sh # gets wrk2 sources from git and make the binary (you'l need git, openssl-devel, gcc, and make on your OS fur success build of wrk2)
    ./warm-up-fs.sh # initializes resources for benchmarking fs endpoint
    ./warm-up-redis.sh # initializes resources for benchmarking redis endpoint
    ./benchmark-docker.sh # perform benchmark for random, fs and redis endpoints
    ./stop-docker.sh # stops the instance of hopeit.engine

Latency (HdrHistogram - Uncorrected Latency, measured without taking delayed starts into account) results:

4 hopeit.engine instances behind a reverse proxy

./wrk2/wrk -t8 -c40 -d60s -R4000 --u_latency "http://localhost:8025/api/simple-benchmark/1x0/give-me-something?item_id=string"
 p99 27.77ms @ 2587.95 req/s

./wrk2/wrk -t6 -c32 -d60s -R4000 --u_latency "http://localhost:8025/api/simple-benchmark/1x0/query-something-redis?item_id=string"
 p99 28.67ms @ 1810.14 req/s

./wrk2/wrk -t4 -c20 -d60s -R4000 --u_latency "http://localhost:8025/api/simple-benchmark/1x0/query-something-fs?item_id=string"
 p99 30.29ms @ 1241.39 req/s

1 hopeit.engine instance

./wrk2/wrk -t8 -c34 -d60s -R4000 --u_latency "http://localhost:8021/api/simple-benchmark/1x0/give-me-something?item_id=string"
 p99 26.48ms @ 1336.18 req/s

./wrk2/wrk -t6 -c24 -d60s -R4000 --u_latency "http://localhost:8021/api/simple-benchmark/1x0/query-something-redis?item_id=string"
 p99 29.14ms @ 908.93 req/s

./wrk2/wrk -t4 -c14 -d60s -R4000 --u_latency "http://localhost:8021/api/simple-benchmark/1x0/query-something-fs?item_id=string"
 p99 24.77ms @ 624.77 req/s