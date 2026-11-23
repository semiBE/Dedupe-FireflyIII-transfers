FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && useradd --system --no-create-home app
COPY main.py .
USER app

ENTRYPOINT ["python", "-u", "main.py"]