FROM postgres:18

WORKDIR /app

# Install build dependancies
RUN apt-get update && apt-get install -y \
git \
build-essential \
postgresql-server-dev-18 \
postgresql-18-postgis-3

# Install pgvector
RUN cd /tmp && \
    git clone --branch v0.8.2 https://github.com/pgvector/pgvector.git && \
    cd pgvector && \
    make && \
    make install

COPY init.sql /docker-entrypoint-initdb.d/

EXPOSE 5432
