FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir aiohttp

COPY webservice/signaling_server.py /app/signaling_server.py

ENV PYTHONUNBUFFERED=1

CMD ["python", "webservice/signaling_server.py"]