FROM python:3.8-slim-buster
RUN apt-get update && apt-get upgrade -y && \
    apt-get install build-essential -y
COPY . /app
WORKDIR /app
RUN pip install .
ARG PG_DSN="postgres://demo:demo@localhost/demo"
ENV PG_DSN=$PG_DSN
EXPOSE 5000
#CMD ["bash"]
ENTRYPOINT ["run-api"]
