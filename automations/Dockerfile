FROM ubuntu:24.04


ARG REQUIREMENTS
ENV REQUIREMENTS_SCRIPT=${REQUIREMENTS}
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive
ARG TZ


RUN set -eux; \
    echo 'Acquire::ForceIPv4 "true";' > /etc/apt/apt.conf.d/99force-ipv4; \
    # imposta mirror solo HTTPS
    sed -i 's|http://archive.ubuntu.com|https://archive.ubuntu.com|g' /etc/apt/sources.list; \
    sed -i 's|http://security.ubuntu.com|https://security.ubuntu.com|g' /etc/apt/sources.list; \
    if [ -f /etc/apt/sources.list.d/ubuntu.sources ]; then \
        sed -i 's|http://|https://|g' /etc/apt/sources.list.d/ubuntu.sources; \
    fi; \
    echo 'Acquire::https::Verify-Peer "false";'  > /etc/apt/apt.conf.d/99insecure-temporary; \
    echo 'Acquire::https::Verify-Host "false";' >> /etc/apt/apt.conf.d/99insecure-temporary; \
    apt-get update || true; \
    apt-get install -y --no-install-recommends ca-certificates || true; \
    update-ca-certificates || true; \
    rm -f /etc/apt/apt.conf.d/99insecure-temporary; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
      bash systemd systemd-sysv libsystemd-dev \
      build-essential pkgconf libssl-dev libffi-dev \
      python3 python3-dev python3-pip curl dbus tzdata locales && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /tmp/
RUN pip3 install --no-cache-dir --break-system-packages -r /tmp/requirements.txt
RUN dpkg-reconfigure tzdata

RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone
COPY . /automations
RUN chmod +x /automations/init.sh

# Abilita cgroup e segnali corretti per systemd
#RUN  /automations/init.sh
ENTRYPOINT ["/automations/start.sh"]