FROM python:3.11-slim

RUN apt-get update && \
    apt-get install -y python3-pip
EXPOSE 8080
# Cleanup
RUN apt-get remove -y g++ make curl && \
    apt-get -y autoremove && \
    apt-get clean
RUN rm -rf \
    /root/.cache \
    /tmp/* \
    /var/lib/apt/lists/* \
    /var/tmp/*
ENV PYTHONUNBUFFERED True
WORKDIR /app
COPY *.txt .
RUN pip install --no-cache-dir --upgrade pip -r requirements.txt
COPY . ./

CMD ["gunicorn", "fastapi_main:app",  " --bind", "0.0.0.0:8080", "-k", "uvicorn.workers.UvicornWorker"]