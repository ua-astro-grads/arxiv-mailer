# syntax=docker/dockerfile:1
FROM ubuntu:22.04

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    git \
    pkg-config

RUN git clone https://github.com/ua-astro-grads/arxiv-mailer.git
WORKDIR arxiv-mailer

# setup the virtual environment
RUN pip install --upgrade pip
RUN python3 -m pip install -r requirements.txt

# setup the environment variables for the mailer
RUN cp config.py.template config.py

# run the mailer
CMD python3 mailer.py