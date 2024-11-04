FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN apt-get update
RUN apt-get install -y sqlite3 

COPY . .

ARG SERVER_HOST=0.0.0.0
ARG SERVER_PORT=5000

ENV SERVER_HOST=$SERVER_HOST
ENV SERVER_PORT=$SERVER_PORT

EXPOSE 5000

CMD ["python", "server.py"]