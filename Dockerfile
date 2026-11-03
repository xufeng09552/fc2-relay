FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000

WORKDIR /app
COPY app.py /app/app.py

RUN useradd -m -u 1000 relay && chown -R relay:relay /app
USER relay

EXPOSE 8000
CMD ["python", "-u", "/app/app.py"]
