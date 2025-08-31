FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
WORKDIR /app

# Install git, curl and git-lfs
RUN apt-get update && \
    apt-get install -y git curl ca-certificates gnupg && \
    curl -fsSL https://packagecloud.io/install/repositories/github/git-lfs/script.deb.sh | bash && \
    apt-get update && apt-get install -y git-lfs && \
    rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY requirements.txt /app/
RUN python -m pip install --upgrade pip
RUN pip install -r requirements.txt

# Copy project
COPY . /app

# Add start script
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

EXPOSE 8000

CMD ["/app/start.sh"]
