FROM python:3.10-slim

RUN apt-get update && \
    apt-get install -y python3-pip \
EXPOSE 80
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

CMD ["uvicorn", "app.fastapi_main:app", "--host", "0.0.0.0", "--port", "80"]