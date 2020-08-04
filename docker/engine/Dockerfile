FROM centos:centos8

# ------------------------
# HAProxy from source
# ------------------------

ENV   HAPROXY_MJR_VERSION=2.1 \
      HAPROXY_VERSION=2.1.2 \
      HAPROXY_CONFIG='/etc/haproxy/haproxy.cfg' \
      HAPROXY_ADDITIONAL_CONFIG='' \
      HAPROXY_PRE_RESTART_CMD='' \
      HAPROXY_POST_RESTART_CMD='' \
      REDIS_ADDRESS='redis://redis'

RUN \
  dnf install -y epel-release && \
  dnf update -y && \
  dnf install -y haproxy inotify-tools wget tar gzip supervisor nano && \
  dnf clean all && rm -rf /var/cache/dnf

# ------------------------
# INSTALL Instance handling
# supervisor
# ------------------------
#COPY /etc/supervisord.conf /etc/supervisord.conf.origin
COPY config/supervisord.conf /etc/supervisord.conf
COPY config/haproxy.cfg /etc/haproxy/hapoxy.conf
RUN mkdir -p  /var/log/supervisor
RUN mkdir -p  /opt/hopeit.engine/logs


# ------------------------
# DATA SCIENCE STACK
# miniconda et al.
# ------------------------
# Install miniconda to /miniconda
ENV MINICONDA_VERSION 3-latest
RUN echo "export PATH=/opt/conda/bin:$PATH" > /etc/profile.d/conda.sh
RUN curl -fSL https://repo.continuum.io/miniconda/Miniconda${MINICONDA_VERSION}-Linux-x86_64.sh -o ~/miniconda.sh
RUN /bin/bash ~/miniconda.sh -b -p /opt/conda
RUN rm ~/miniconda.sh
ENV PATH /opt/conda/bin:$PATH
RUN conda update -n base -c defaults conda
RUN conda install -y python=3.8

# ---------------------------
# INSTALL HOPEIT APP DEPS
# requierements, supervisor
# ---------------------------
# install python deps
COPY config/requirements.txt /opt/hopeit.engine/requirements.txt
RUN /bin/bash -c "pip install -r /opt/hopeit.engine/requirements.txt"
COPY config/bootstrap.sh /

ENTRYPOINT ["/bootstrap.sh"]
