FROM python:3.12.3-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       gcc \
       curl \
       libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy all environment files into /app/ (equivalent to spec's COPY * /app/)
# Using COPY . /app/ instead of COPY * /app/ to also include hidden files (e.g. .env)
COPY . /app/

# Install all service dependencies in one shared Python environment
RUN pip install --upgrade pip==24.0 --no-cache-dir \
    && pip install --no-cache-dir -r /app/api-gateway/requirements.txt \
    && pip install --no-cache-dir -r /app/auth-service/requirements.txt \
    && pip install --no-cache-dir -r /app/data-service/requirements.txt \
    && pip install --no-cache-dir -r /app/worker/requirements.txt

EXPOSE 8000 5001 5002

CMD ["bash"]
