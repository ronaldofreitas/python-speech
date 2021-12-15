FROM python:3.9-slim AS develop-stage
RUN python -m venv /venv
ENV PATH="/venv/bin:$PATH"
WORKDIR /app
COPY requirements.txt /requirements.txt
RUN pip install -r /requirements.txt
#CMD ["python", "main.py"]

FROM python:3.9-slim
ENV DEBIAN_FRONTEND noninteractive
ENV TERM linux
ENV PATH="/venv/bin:$PATH"
WORKDIR /app
#RUN apt update && apt install -y ffmpeg libavcodec-extra && rm -rf /var/lib/apt/lists/*
#COPY --from=develop-stage --chown=65535:65535 /venv /venv
COPY --from=develop-stage --chown=root:root /venv /venv
COPY . .
USER root
#USER 65535

ENV PORT 8080
CMD exec gunicorn --bind 0.0.0.0:$PORT --workers 1 --threads 8 --timeout 0 app:app
