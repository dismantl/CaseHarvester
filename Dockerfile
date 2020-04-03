FROM python:3-buster

WORKDIR /usr/src/app

RUN mkdir -p /root/.aws && echo "[default]\nregion=us-east-1" > /root/.aws/config

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/mjcs ./mjcs
COPY src/case_harvester.py .

CMD ["python", "case_harvester.py", "--help"]
