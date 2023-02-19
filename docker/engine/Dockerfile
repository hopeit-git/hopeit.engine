# syntax=docker/dockerfile:1
FROM python:3.10
ENV VIRTUAL_ENV=/opt/venv

# Get last stable hopeit.engien code from git
RUN git clone https://github.com/hopeit-git/hopeit.engine.git
WORKDIR /hopeit.engine

COPY config/dev-docker.json /hopeit.engine/engine/config/dev-local.json

# Install exmaples apps and create OPENAPI files according to installed libraries
RUN make update-examples-api

ENV PORT=8020
ENV APP=run-simple-example

EXPOSE $PORT
ENTRYPOINT "exec" "make" $APP
