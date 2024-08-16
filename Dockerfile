FROM python:3.11-slim

WORKDIR /app
COPY . /app/


RUN pip install -r /app/src/requirements.txt

EXPOSE 8000

CMD python -u src/server.py