# CA bundle used only to bootstrap apt over verified HTTPS (no plain HTTP, no TLS bypass)
FROM python:3.12.16-slim@sha256:dacd1678a25ee255c22ea5de948374f5542db3562dd365038b14349051ea156c AS cacerts

FROM ubuntu:24.04@sha256:24737cef17f4e22b1977df7d9a05e77c4e28b7da5b8911f8d8ccda136bf3573c

COPY --from=cacerts /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/ca-certificates.crt


ARG REQUIREMENTS
ENV REQUIREMENTS_SCRIPT=${REQUIREMENTS}
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive
ARG TZ


RUN set -eux; \
    echo 'Acquire::ForceIPv4 "true";' > /etc/apt/apt.conf.d/99force-ipv4; \
    # imposta mirror solo HTTPS (TLS verification stays enabled)
    sed -i 's|http://archive.ubuntu.com|https://archive.ubuntu.com|g' /etc/apt/sources.list; \
    sed -i 's|http://security.ubuntu.com|https://security.ubuntu.com|g' /etc/apt/sources.list; \
    if [ -f /etc/apt/sources.list.d/ubuntu.sources ]; then \
        sed -i 's|http://|https://|g' /etc/apt/sources.list.d/ubuntu.sources; \
    fi; \
    apt-get update; \
    apt-get install -y --no-install-recommends ca-certificates; \
    # distrust emSign roots removed from certifi 2026.10.19 (eMudhra incident)
    sed -i -E 's#^(mozilla/emSign_(Root_CA_-_C1|ECC_Root_CA_-_C3|ECC_Root_CA_-_G3)\.crt)$#!\1#' /etc/ca-certificates.conf; \
    update-ca-certificates --fresh; \
    apt-get install -y --no-install-recommends \
      bash systemd systemd-sysv libsystemd-dev \
      build-essential pkgconf libssl-dev libffi-dev \
      python3 python3-dev python3-pip curl dbus tzdata locales && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /tmp/
RUN pip3 install --no-cache-dir --break-system-packages -r /tmp/requirements.txt && \
    python3 -c "from importlib.metadata import version; v = version('certifi'); assert tuple(map(int, v.split('.')[:3])) >= (2026, 10, 19), v; print('certifi', v)"
RUN dpkg-reconfigure tzdata

RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone
COPY . /automations
RUN chmod +x /automations/init.sh

# Abilita cgroup e segnali corretti per systemd
#RUN  /automations/init.sh
ENTRYPOINT ["/automations/start.sh"]