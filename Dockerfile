
FROM ubuntu:bionic

WORKDIR /

#COPY ./requirements.txt /requirements.txt

RUN apt-get update \
 && apt-get install gnupg -y

RUN echo "deb [arch=amd64] http://repo.sawtooth.me/ubuntu/chime/stable bionic universe" >> /etc/apt/sources.list \
 && apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys 8AA7AF1F1091A5FD \
 && apt-get update \
 && apt-get -f -y install \
 && apt-get install -y -q \
    curl \
    python3-cbor \
    python3-zmq \
    python3-flask \
    #python3-flask-cors \
    python3-sawtooth-sdk \
    python3-sawtooth-cli \
    python3-sawtooth-poet-cli

RUN apt-get update \
 && apt-get -f -y install \
 && apt-get install -y -q \
    python3-pip

RUN pip3 install --upgrade Flask-Cors pandas

COPY . .

ENV PATH=$PATH:/

EXPOSE 5000