FROM python:3.11.3

LABEL maintainer="Alessio Gerace <a.gerace@inrim.it>"
ARG REQUIREMENTS
ENV REQUIREMENTS_SCRIPT=${REQUIREMENTS}
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV DEBIAN_FRONTEND noninteractive
ARG TZ

RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone


RUN apt-get update;  \
    apt-get install -y \
            build-essential python3-dev git wget \
            ldap-utils libldap-dev libsasl2-dev python3-dev python3-pip \
            gcc g++ locales locales-all; \
    apt-get clean

ENV LC_ALL it_IT.UTF-8
ENV LANG en_US.UTF-8
ENV LANGUAGE en_US.UTF-8

RUN mkdir -p /root/.docker/cli-plugins/
RUN wget -O /root/.docker/cli-plugins/docker-compose https://github.com/docker/compose/releases/download/v2.9.0/docker-compose-linux-aarch64
RUN chmod a+x /root/.docker/cli-plugins/docker-compose


COPY ./start.sh /start.sh
COPY ./gunicorn_conf.py /gunicorn_conf.py
COPY . /apps

RUN $REQUIREMENTS_SCRIPT

# RUN python-on-whales download-cli

ENV PYTHONPATH=/app

ENTRYPOINT ["/start.sh"]



