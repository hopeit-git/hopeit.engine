![hopeit.engine QA](https://github.com/hopeit-git/hopeit.engine/workflows/hopeit.engine%20QA/badge.svg)

Our QA pipeline:
> - Engine and example application built and tested on Linux using Python 3.7 and 3.8
> - Types checked with [*mypy*](https://pypi.org/project/mypy/)
> - Code style checked with [*flake*](https://pypi.org/project/flake8/), [*pylint*](https://pypi.org/project/pylint/)
> - *hopeit.engine* unit tested using [*pytest*](https://pypi.org/project/pytest/), coverage > 90%
> - HTTP server integration tests using [*pytest_aiohttp*](https://pypi.org/project/pytest-aiohttp/)
> - *simple-example* appplication integration tests
> - Included plugins integration tests
                                                                      


# hopeit engine

*hopeit.engine* is a library that allows development and deployment of reactive microservices.

### Motivation

**Small organizations**: *hopeit.engine* is intented initially to enable small organizations and companies, which don't have a huge software development infrastructure, to create new systems with the benifits of microservices: small, fast to develop, easy to mantain and operate. This characteristics allow also migration of existing systems piece by piece to microservices. But that's not all: *hopeit.engine* facilitates a few features and good practices that all production-grades microservices must have: modularity, scalability, logging, tracking/tracing and monitoring. 

**Learning:** A second objective, but not less importat is learning: if you want to learn how to develop microservices, *hopeit.engine* is a good starting point, since it will quickly make you productive and at the same time you will learn all the necessary steps and features that a production-grade microservice should have. Only basic Python knowledge is required.

**Data driven**: *hopeit.engine* was thought keeping in mind that most business logic and decisions are and will be driven by data. Working with data is a key part of the library. We embrace [*dataclasses*](https://docs.python.org/3/library/dataclasses.html) and enforce data-types checking on input and output data. It provides Open API validation and documentation and a way to share data between applications using data streams. *hopeit.engine* is Data Science/Machine Learning friendly. We try to keep the library compatible with Python ecosystem around Machine Learning: Jupyter Notebooks and the Scientific Stack.

**Reactive**: *hopeit.engine* provides the main necessary features for your system to accomplish the objectives of modern, reactive systems: responsiveness, resiliency, scalability and message driven. The architecture enforced by *hopeit.engine* will lead you to develop small stateless services, primarily runnign asynchronous operations, that can recover from failure, can scale up quickly and handle more load, and communicate asynchrounously with each other using streams.

**Ready for production**: Event *hopeit.engine* is in an earyly stage of development and many things can be improved, we aim to ease the steps needed to put microservices in productions. *hopeit.engine* provides out of the box logging of app events with extra information that allows monitor, track and measure requests. It is easy configurable to run in containers and allows extensibility using plugins to add the pieces you need to integrate new microservices in your organization: i.e. plugins can be easily created to integrate authentication and monitoring into your existing infrastructure.

So, if you are running a new company or a small organization, *hopeit.engine* will help you to quickly start moving to a modern and scalable architecture of microservices. Microservices architecture is proven to be an efficient way that allows company to grow and adapt, being adopted since years now by big internet and e-commerce giants. If you are already running microservices or you are running a bigger infrastructure, *hopeit.engine* can help you create new features that will be quicly integrated in your current infrastructure. If you want to learn microservices or how to build production-grade applications in Python, check our [*docs and tutorials*](https://hopeitengine.readthedocs.io/en/latest/index.html). 


## Features

- Enables develop microservices in Python (3.7+)
- Provides web server for API endpoints *
- Open API schema validation and docs *
- Modular application design: each microservice is an app composed of independent events
- Logging of event invokations and results
- Metrics: event durations, events starts, success, failures.
- Tracking/tracing: keep track of request ids among applications
- Event publishing and consuming to Redis Streams *
- Data Science / Machine Learning friendly: applications can be developed and tested using Jupyter Notebooks *
- Testing: provides utilities to test from Notebooks or Python testing frameworks


## Open Source

*hopeit.engine* is Open Source, and we encourage people to adopt it, improve it and contribute tha changes back. 
Check [*LICENSE*](https://github.com/hopeit-git/hopeit.engine/blob/master/LICENSE) file. The library also takes advantage of other well-known python open source libraries to deliver the features described above:

- HTTP endpoints are based on [*aiohttp*](https://pypi.org/project/aiohttp/)
- Open API / Swagger support is enables by [*aiohttp_swagger3*](https://pypi.org/project/aiohttp-swagger3/)
- Stream processing is supported using [*Redis*](https://redis.io/) and connected though [*aioredis*](https://pypi.org/project/aioredis/)
- To develop in Jupyter Notebooks we recommed using [*nbdev*](https://pypi.org/project/nbdev/)

For a full list of required libraries and licenses check [*THIRDPARTY*](https://github.com/hopeit-git/hopeit.engine/blob/master/THIRDPARTY) file.

## Architecture



```python

```
