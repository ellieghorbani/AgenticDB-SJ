ARG PGVECTOR_VERSION=0.8.7

FROM postgis/postgis:16-3.5

ARG PGVECTOR_VERSION

# PostgreSQL 16 + PostGIS 3.5 currently uses Debian Bullseye.
# Bullseye and PGDG packages have moved to archive repositories.
RUN set -eux; \
    find /etc/apt -type f \( -name '*.list' -o -name '*.sources' \) -print0 \
      | xargs -0 sed -ri \
          -e 's#https?://deb\.debian\.org/debian-security#https://archive.debian.org/debian-security#g' \
          -e 's#https?://security\.debian\.org/debian-security#https://archive.debian.org/debian-security#g' \
          -e 's#https?://deb\.debian\.org/debian#https://archive.debian.org/debian#g' \
          -e 's#https?://apt\.postgresql\.org/pub/repos/apt#https://apt-archive.postgresql.org/pub/repos/apt#g'; \
    printf 'Acquire::Check-Valid-Until "false";\n' \
      > /etc/apt/apt.conf.d/99archive; \
    apt-get -o Acquire::Check-Valid-Until=false update; \
    apt-get install -y --no-install-recommends \
        build-essential \
        ca-certificates \
        git \
        postgresql-server-dev-16; \
    git clone \
        --branch "v${PGVECTOR_VERSION}" \
        --depth 1 \
        https://github.com/pgvector/pgvector.git \
        /tmp/pgvector; \
    make -C /tmp/pgvector clean; \
    make -C /tmp/pgvector OPTFLAGS=""; \
    make -C /tmp/pgvector install; \
    rm -rf /tmp/pgvector; \
    apt-get purge -y --auto-remove \
        build-essential \
        git \
        postgresql-server-dev-16; \
    rm -rf /var/lib/apt/lists/*
