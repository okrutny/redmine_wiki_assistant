FROM python:3.11-slim

ARG ENV=dev
ENV ENV=${ENV}

ARG UID=1001
ARG GID=1001

RUN addgroup --gid $GID appgroup && \
    adduser --uid $UID --gid $GID --disabled-password appuser

WORKDIR /app

# Kopiuj oba requirements
COPY requirements.txt requirements.prod.txt ./

# Warunkowa instalacja zależnie od ENV
RUN pip install --upgrade pip && \
    pip install -r requirements.txt && \
    if [ "$ENV" = "prod" ]; then pip install -r requirements.prod.txt; fi

COPY . .

RUN mkdir -p /app/chroma_store && \
    chown -R $UID:$GID /app/chroma_store

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

USER appuser

ENTRYPOINT ["/entrypoint.sh"]