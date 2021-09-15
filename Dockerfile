FROM tiangolo/uvicorn-gunicorn:python3.8


ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ARG TZ
LABEL maintainer="Alessio Gerace <a.gerace@inrim.it>"

RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone


RUN apt-get update && apt-get install -y libldap-dev git
RUN apt-get install -y libsasl2-dev gcc python3-dev g++
RUN apt-get install -y locales locales-all
ENV LC_ALL it_IT.UTF-8
ENV LANG en_US.UTF-8
ENV LANGUAGE en_US.UTF-8

RUN rm -rf /root/.cache/pip

COPY requirements.txt /requirements.txt

RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r /requirements.txt


#COPY app /app

