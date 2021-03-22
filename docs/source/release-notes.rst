Release Notes
============

Version 0.2.0
_____________
- MULTIPART uploads http endpoints support: post form-data with file attachments in request (with Json response)
- Support for `__preprocess__` web requests in GET, POST and MULTIPART endpoints


Version 0.1.5
_____________
- Automatic publishing to PyPi
- Open API: added summary and description parameters to Open API specification. Deprecation warning for title param.
- FIX: Improved dependency handling
- FIX: fix object listing in FileStorage toolkit

Version 0.1.0
_____________

Initial __hopeit.engine__ version support for:
- Enables development of microservices in Python (3.7+)
- Provides aiohttp web server for API endpoints.
- Open API schema validation and docs site.
- Modular and testable application design: each microservice is an app composed of independent events
- Logging of event invocations and results.
- Metrics: event durations, events starts, success, failures. Stream processing rates.
- Tracking/tracing: keep track of request ids among applications and multiple events execution.
- Event publishing and consuming to Redis Streams.
- Engine core support for functional Events with Steps
- Multiple microservices definition as Apps
- GET, POST http endpoints with JSON responses
- STREAM events to asynchroously consume and process messages
- SERVICE events for continuously running processes
- read_stream / write_stream support for Redis streams
- OpenAPI specification support for HTTP endpoints
- Dataobjects with Json Schema validation
- JSON configuration files with Json Schema validation
- Collector steps pattern support for concurrent execution of steps using asyncio
- hopeit_server command line interface
- hopeit_openapi command line interface
- Helps to create elegant and well structure code using your preferred IDE.
- Data Science / Machine Learning friendly: applications can be developed and tested using Jupyter Notebooks.
- Testing: provides utilities to test from Notebooks or Python testing frameworks.
