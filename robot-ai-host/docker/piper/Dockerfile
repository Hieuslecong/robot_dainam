FROM python:3.12-slim
ARG PIPER_VERSION=1.5.0
RUN pip install --no-cache-dir "piper-tts[http]==${PIPER_VERSION}"
WORKDIR /srv/piper
COPY docker/piper/start.sh /usr/local/bin/start-piper
RUN chmod +x /usr/local/bin/start-piper
EXPOSE 5000
ENTRYPOINT ["/usr/local/bin/start-piper"]
