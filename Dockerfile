FROM ubuntu:16.04

RUN apt-get update && apt-get install -y apt-transport-https ca-certificates

RUN echo "deb https://mirrors.tuna.tsinghua.edu.cn/ubuntu/ xenial main restricted universe multiverse" > /etc/apt/sources.list && \
    echo "deb https://mirrors.tuna.tsinghua.edu.cn/ubuntu/ xenial-updates main restricted universe multiverse" >> /etc/apt/sources.list && \
    echo "deb https://mirrors.tuna.tsinghua.edu.cn/ubuntu/ xenial-backports main restricted universe multiverse" >> /etc/apt/sources.list && \
    echo "deb https://mirrors.tuna.tsinghua.edu.cn/ubuntu/ xenial-security main restricted universe multiverse" >> /etc/apt/sources.list

RUN apt-get update
RUN apt-get install -y wget python3.5 python3-pip git

RUN python3.5 -m pip install kubernetes tornado aiohttp pymongo --ignore-installed -i https://pypi.tuna.tsinghua.edu.cn/simple

ADD . /ktqueue
WORKDIR /ktqueue

RUN python3.5 -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
CMD python3 /ktqueue/server.py

EXPOSE 8080
