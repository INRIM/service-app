FROM ubuntu:24.04


ARG REQUIREMENTS
ENV REQUIREMENTS_SCRIPT=${REQUIREMENTS}
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive
ARG TZ


RUN echo 'Acquire::ForceIPv4 "true";' > /etc/apt/apt.conf.d/99force-ipv4 && \
    if [ -f /etc/apt/sources.list.d/debian.sources ]; then \
        sed -i 's|http://deb.debian.org|https://deb.debian.org|g' /etc/apt/sources.list.d/debian.sources; \
    fi && \
    if [ -f /etc/apt/sources.list ]; then \
        sed -i 's|http://deb.debian.org|https://deb.debian.org|g' /etc/apt/sources.list; \
    fi && \
    apt-get update && \
    apt-get -y upgrade && \
    apt-get install -y \
      bash \
      systemd systemd-sysv libsystemd-dev \
      build-essential pkgconf libssl-dev libffi-dev python3 python3-dev \
      python3-pip curl dbus tzdata \
      locales locales-all && \
    apt-get clean && rm -rf /var/lib/apt/lists/

COPY requirements.txt /tmp/
RUN pip3 install --no-cache-dir -r /tmp/requirements.txt
RUN dpkg-reconfigure tzdata

RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone
COPY . /automations
RUN chmod +x /automations/init.sh

# Abilita cgroup e segnali corretti per systemd
#RUN  /automations/init.sh
ENTRYPOINT ["/automations/start.sh"]