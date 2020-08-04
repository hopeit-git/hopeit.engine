![hopeit.engine QA](https://github.com/hopeit-git/hopeit.engine/workflows/hopeit.engine%20QA/badge.svg)

**Our QA pipeline**:
> - Engine and example application built and tested on Linux using Python 3.7 and 3.8
> - Types checked with [*mypy*](https://pypi.org/project/mypy/)
> - Code style checked with [*flake*](https://pypi.org/project/flake8/), [*pylint*](https://pypi.org/project/pylint/)
> - *hopeit.engine* unit tested using [*pytest*](https://pypi.org/project/pytest/), required coverage > 90%
> - HTTP server integration tests using [*pytest_aiohttp*](https://pypi.org/project/pytest-aiohttp/)
> - *simple-example* appplication integration tests
> - Included plugins integration tests
                                                                      


# hopeit engine

**"Microservices with Data Streams"**

*hopeit.engine* is a library that allows development and deployment of reactive, data driven microservices in Python. It provides a way to create APIs, implement business and data driven applications in Python, communicate between services using data streams, test, deploy and scale services.

### Motivation

**Small organizations**: *hopeit.engine* is intented initially to enable small organizations and companies, which don't have a huge software development infrastructure, to create new systems with the benifits of microservices: quick to develop, simple and small, easy to mantain and operate. This characteristics allow also migration of existing systems piece by piece to microservices. But that's not all: *hopeit.engine* adds a few features and good practices that all production-grades microservices must have out-of-the-box: modularity, scalability, logging, tracking/tracing, stream processing, metrics and monitoring. 

**Learning:** A second objective, but not less importat is learning: if you want to learn how to develop microservices, *hopeit.engine* is a good starting point, since it will quickly make you productive and at the same time you will learn all the necessary steps and features that a production-grade microservice should have. Only basic Python knowledge is required. *hopeit.engine* was succesfully adopted by full-stack and backend software developers, data engineers and data scientists coming from different backgrounds.

**Data driven**: *hopeit.engine* was thought keeping in mind that most business logic and decisions are and will be driven by data. Working with data is a key part of the library. We embrace [*dataclasses*](https://docs.python.org/3/library/dataclasses.html) and enforce data-types checking on input and output data. The library provides Open API validation and documentation and a way to share data between applications using streams. *hopeit.engine* is Data Science/Machine Learning friendly. We try to keep the library compatible with Python ecosystem around Machine Learning: Jupyter Notebooks and the Scientific Stack. We aim to enable Data teams creating their own services in a way people with different skills can contribute.

**Streams**: *hopeit.engine* provides the main necessary features for your system to accomplish the objectives of modern, reactive systems: responsiveness, resiliency, scalability and message driven. The architecture enforced by *hopeit.engine* will lead you to develop small stateless services, primarily running asynchronous operations, that can recover from failure, can scale up quickly and handle more load, and communicate asynchrounously with other services and process data using streams.

**Ready for production**: Even if *hopeit.engine* is in an early stage of development and many things can be improved, we aim to ease the steps needed to put microservices in production. *hopeit.engine* provides out of the box logging of app events with extra information that allows monitor, track and measure requests. It is easy configurable to run in containers and allows extensibility using plugins to add the pieces you need to integrate new microservices in your organization: i.e. plugins are available to integrate authentication and monitoring into your existing infrastructure.

Microservices architecture is proven to be an efficient way that allows company to grow and adapt, being adopted since years now by big internet and e-commerce giants. If you are small organization and want to start moderninzing and scaling, *hopeit.engine* can help you starting quickly. If you are already running microservices or you are running a bigger infrastructure, *hopeit.engine* can help you create new features that will be easily integrated with your current services. If you want to learn microservices or how to build production-grade applications in Python, check our [*docs and tutorials*](https://hopeitengine.readthedocs.io/en/latest/index.html). 


## Features

- Enables development of microservices in Python (3.7+).
- Provides web server for API endpoints. *
- Open API schema validation and docs. *
- Modular and testable application design: each microservice is an app composed of independent events
- Logging of event invocations and results.
- Metrics: event durations, events starts, success, failures. Stream processing rates.
- Tracking/tracing: keep track of request ids among applications and multiple events execution.
- Event publishing and consuming to Redis Streams. *
- Helps creating elegant and well structure code using your prefered IDE.
- Data Science / Machine Learning friendly: applications can be developed and tested using Jupyter Notebooks. *
- Testing: provides utilities to test from Notebooks or Python testing frameworks.


## Open Source

*hopeit.engine* is Open Source, and we encourage people to adopt it, improve it and contribute changes back. 
Check [*LICENSE*](LICENSE) file. The library also takes advantage of other well-known python open source libraries to deliver the features described above:

- HTTP endpoints are based on [*aiohttp*](https://pypi.org/project/aiohttp/)
- Open API / Swagger support is enables by [*aiohttp_swagger3*](https://pypi.org/project/aiohttp-swagger3/)
- Stream processing is supported using [*Redis*](https://redis.io/) and connected using [*aioredis*](https://pypi.org/project/aioredis/)
- To develop in Jupyter Notebooks we recommed using [*nbdev*](https://pypi.org/project/nbdev/)

For a full list of required libraries and licenses check [*THIRDPARTY*](THIRDPARTY) file.

## Architecture

A few examples of how microservices can be architected using *hopeit.engine*

### Concepts:

**App**: is the service we just created consisting of at least configuration file plus a python module.

**Event**: is the basic execution unit that is triggered when an endpoint is invoked, or a message is received from a stream. Events can be of GET, POST, STREAM or SERVICE types. GET and POST are triggered from HTTP calls, STREAM when a message is consumed from a data stream and SERVICE events can run continuously. 

**Steps**: each Event can define a list of Steps to be executed when the event is triggered. *hopeit.engine* ensures execution of steps and depedency based on its inputs/outputs, allowing each step to be simple and independently testable.

**Plugin**: a special type of App that can extend other Apps functionallity.

**Server**: a group of Apps and Plugins, a server configuration file plus an Open API specificacation file can run together using hopeit.server.web module.

Check [Simple Example Application](apps/examples/simple-example) for examples of supported event types, steps, configuration and Open API specification files. 


### A Simple Microservice

![Simple Microservice](docs/source/readme/hopeit.engine-simple.png)

In this schema, we can see a service or *App* created using hopeit.engine. The app orchestrates the implementation for two *Events*, each one accesible using an API endpoint. When an external client send requests to the route associated by the event, the engine will trigger the execution of the steps defined in the Event. Multiple events are served concurrently (but not necessarily in parallel) using [*asyncio*](https://docs.python.org/3/library/asyncio.html)

### Composing API

![Compose](docs/source/readme/hopeit.engine-compose.png)

Many Apps can generate a single API specification and grouped together in a service unit. This sometimes could be desired to simplify operations, specilly in small organizations where you don't want to deal with a lot of microservices to manage at the beginning. Later on, the apps can be dettached easily and run separately if required.

### Streams

![Streams](docs/source/readme/hopeit.engine-streams.png)

If an external request triggers a process that requires background tasks to be ran, the process can be splitted in many events, and even in many services using streams. In this example App 1 is receiving the request and can quickly respond to the client while submitting a message to a *stream*. This is easily configurable just adding a *write_stream* section on the App configuration file. Then a second microservice (App 2) consumes the messages in the stream and performs extra processing, in this example, finally saving the result to a database. This is a poweful tool for reactive systems to use. Streams are not only fast but they allow to design the systems in a modular way, keep evey piece small while providing resiliency specially on data processing scenarios. Check the tutorials on how to develop events that can publish and consume events from streams [here](https://hopeitengine.readthedocs.io/en/latest/tutorials/05-streams.html)

### Scalability and operations

![Scale](docs/source/readme/hopeit.engine-scale.png)

*hopeit.engine* enforces your Apps implementation to be scalable. We mentioned that events are served concurrently using asyncio, but to achieve real parallelism, many instances of an App can run in the same or different server instances. Putting a load balancer (i.e: [NGINX](https://nginx.org/en/) or [HAProxy](http://www.haproxy.org/), in front of your API Server app instances, will ensure serving high load of requests in parallel. The same scalability/load-balancing pattern applies for stream events processing. You can run many instances of Apps consuming Redis Streams. Using consumer groups, Redis will act as a load-balancer and each App instance will consume events from the stream in parallel. Apps created with *hopeit.engine* are also easy to deploy in containers, like [Docker](https://www.docker.com/). Only a Python runtime and a load-balancer is needed.

## Current status and roadmap

- **JULY 2020**: hopeit.engine version 0.1.0 is released as Open Source in github!
    
- We are mainly working in improving documentation and tutorials.

- Early adopters are implementing solutions in small organizations using hopeit.engine. We are continuosly gathering feedback and making the engine more stable and easy to use as we learn from real use case scenarios.

- Our next objective is to create more learning material to allow software professionals to learn on Microservices development using *hopeit.engine* to enable this. Tutorials are already available as part of [documentation](https://hopeitengine.readthedocs.io/en/latest/tutorials/index.html)


## More info

Please check the [docs](https://hopeitengine.readthedocs.io/en/latest/index.html).

If you are interested to become an early adopter, to learn microservices using *hopeit.engine* or to contribute and collaborate, contact the authors at ![_@_](docs/source/readme/contact.png)

Thank you!



```python

```
