FROM ubuntu:24.04


ARG REQUIREMENTS
ENV REQUIREMENTS_SCRIPT=${REQUIREMENTS}
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive
ARG TZ


# Timezone
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Use https for apt sources
RUN sed -i 's|http://archive.ubuntu.com|https://archive.ubuntu.com|g' /etc/apt/sources.list && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
      python3.12 python3.12-venv python3.12-distutils python3-pip \
      build-essential git wget curl \
      ldap-utils libldap-dev libsasl2-dev \
      gcc g++ locales locales-all && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt /tmp/
RUN python3.12 -m pip install --no-cache-dir --break-system-packages -r /tmp/requirements.txt
RUN dpkg-reconfigure tzdata

RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone
COPY . /automations
RUN chmod +x /automations/init.sh

# Abilita cgroup e segnali corretti per systemd
#RUN  /automations/init.sh
ENTRYPOINT ["/automations/start.sh"]