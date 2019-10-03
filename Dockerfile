FROM python:3-buster

RUN apt-get update && apt-get install -y \
    jq

WORKDIR /usr/src/app

RUN mkdir -p /root/.aws && echo "[default]\nregion=us-east-1" > /root/.aws/config

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/mjcs ./mjcs
COPY src/case_harvester.py .
COPY src/spider/scheduled_spider.py .

CMD ["python", "case_harvester.py", "--help"]
