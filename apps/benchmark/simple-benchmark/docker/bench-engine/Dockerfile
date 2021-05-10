FROM centos:centos8

RUN \
  dnf install -y epel-release && \
  dnf update -y && \
  dnf install -y haproxy nginx inotify-tools wget tar gzip supervisor nano make gcc openssl-devel && \
  dnf clean all && rm -rf /var/cache/dnf

COPY ./apps/benchmark/simple-benchmark/docker/bench-engine/config/supervisord.conf /etc/supervisord.conf
COPY ./apps/benchmark/simple-benchmark/docker/bench-engine/config/haproxy.cfg /etc/haproxy/haproxy.cfg
RUN mkdir -p  /var/log/supervisor
RUN mkdir -p  /opt/hopeit.py

ENV MINICONDA_VERSION 3-latest
RUN echo "export PATH=/opt/conda/bin:$PATH" > /etc/profile.d/conda.sh
RUN curl -fSL https://repo.continuum.io/miniconda/Miniconda${MINICONDA_VERSION}-Linux-x86_64.sh -o ~/miniconda.sh
RUN /bin/bash ~/miniconda.sh -b -p /opt/conda
RUN rm ~/miniconda.sh
ENV PATH /opt/conda/bin:$PATH
RUN conda update -n base -c defaults conda
RUN conda install -y python=3.8

# install hopeit.engine
RUN mkdir -p  /opt/hopeit.py/engine
COPY ./engine /opt/hopeit.py/engine/
RUN mkdir -p  /opt/hopeit.py/apps
COPY ./apps /opt/hopeit.py/apps/
RUN mkdir -p  /opt/hopeit.py/plugins
COPY ./apps /opt/hopeit.py/plugins/
COPY ./Makefile /opt/hopeit.py/
WORKDIR /opt/hopeit.py
RUN ls -l /opt/hopeit.py
RUN make install
RUN mkdir -p  /opt/hopeit.py/logs
COPY ./apps/benchmark/simple-benchmark/docker/bench-engine/config/bootstrap.sh /

ENV   HAPROXY_MJR_VERSION=2.1 \
      HAPROXY_VERSION=2.1.2 \
      HAPROXY_CONFIG='/etc/haproxy/haproxy.cfg' \
      HAPROXY_ADDITIONAL_CONFIG='' \
      HAPROXY_PRE_RESTART_CMD='' \
      HAPROXY_POST_RESTART_CMD='' \
      REDIS_ADDRESS='redis://redis'

ENTRYPOINT ["/bootstrap.sh"]
