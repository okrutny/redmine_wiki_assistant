FROM python:3.11-slim

ARG UID=1001
ARG GID=1001

RUN addgroup --gid $GID appgroup && \
    adduser --uid $UID --gid $GID --disabled-password appuser

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

RUN mkdir -p /app/chroma_store && \
    chown -R $UID:$GID /app/chroma_store

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

USER appuser

ENTRYPOINT ["/entrypoint.sh"]