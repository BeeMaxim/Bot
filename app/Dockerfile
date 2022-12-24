FROM ubuntu:latest

RUN apt-get update && apt-get install -y python3.9 python3.11-distutils

RUN apt-get install -y python3.pip

RUN pip install -U aiogram

RUN pip install redis

CMD ["python3", "/data/app.py"]