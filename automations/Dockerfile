FROM ubuntu:22.04

ARG TZ
ARG DEBIAN_FRONTEND=noninteractive
ENV TZ=${TZ}
ENV LC_ALL=it_IT.UTF-8
ENV LANG=en_US.UTF-8
ENV LANGUAGE=en_US.UTF-8


RUN if [ -f /etc/apt/sources.list.d/debian.sources ]; then \
        sed -i 's|http://deb.debian.org|https://deb.debian.org|g' /etc/apt/sources.list.d/debian.sources; \
    fi && \
    if [ -f /etc/apt/sources.list ]; then \
        sed -i 's|http://deb.debian.org|https://deb.debian.org|g' /etc/apt/sources.list; \
    fi && \
    apt-get update; \
    apt-get -y  upgrade; \
    apt-get install --no-install-recommends -y \
      bash \
      systemd \
      systemd-sysv \
      libsystemd-dev \
      build-essential pkgconf libssl-dev libffi-dev python3 python3-dev \
      python3-pip \
      curl \
      dbus \
      tzdata \
      locales locales-all; \
    apt-get clean && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /tmp/
RUN pip install --no-cache-dir -r /tmp/requirements.txt
RUN dpkg-reconfigure tzdata

RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone
COPY . /automations
RUN chmod +x /automations/init.sh

# Abilita cgroup e segnali corretti per systemd
#RUN  /automations/init.sh
ENTRYPOINT ["/automations/start.sh"]