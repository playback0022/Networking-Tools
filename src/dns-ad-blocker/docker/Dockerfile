FROM python:latest

# update packages and install python dependency
RUN apt update && apt upgrade -y; pip install scapy

# create working directory
RUN mkdir -p /dns/logs

# the working directory in which commands are executed
WORKDIR /dns
COPY dns-resolver.py ./resolver.py
COPY banned.txt .
