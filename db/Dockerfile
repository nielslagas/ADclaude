FROM postgres:14

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    postgresql-server-dev-14 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Clone and build pgvector
RUN git clone --branch v0.5.1 https://github.com/pgvector/pgvector.git \
    && cd pgvector \
    && make \
    && make install \
    && cd .. \
    && rm -rf pgvector

# Copy initialization scripts
COPY ./init-scripts/ /docker-entrypoint-initdb.d/

# Expose PostgreSQL port
EXPOSE 5432

# Set environment variables
ENV POSTGRES_USER=postgres
ENV POSTGRES_PASSWORD=postgres
ENV POSTGRES_DB=postgres

# Set locale for full-text search
ENV LANG=en_US.utf8