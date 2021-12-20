ARG base_image=ubuntu:21.04
FROM "$base_image"

ARG TZ
RUN set -eux; \
    apt-get update; \
    apt-get -y  upgrade; \
    DEBIAN_FRONTEND=noninteractive apt-get install --no-install-recommends -y \
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
    apt-get clean

RUN pip3 install python-dotenv
RUN pip3 install httpx
RUN pip3 install pymongo
RUN pip3 install pytz
RUN dpkg-reconfigure tzdata
ENV LC_ALL it_IT.UTF-8
ENV LANG en_US.UTF-8
ENV LANGUAGE en_US.UTF-8
ENV TZ ${TZ}
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone
COPY . /automations
RUN chmod +x /automations/init.sh
RUN  /automations/init.sh
ENTRYPOINT ["/lib/systemd/systemd"]