# FROM python:3.10-slim

# # Set working directory
# WORKDIR /app

# # Copy application files
# COPY . /app

# # Install system dependencies
# RUN apt-get update && \
#     apt-get install -y --no-install-recommends \
#         gcc \
#         python3-dev \
#         libpq-dev \
#         libgl1 \
#         libsm6 \
#         libxrender1 \
#         libxext6 \
#         ffmpeg && \
#     rm -rf /var/lib/apt/lists/*

# # Upgrade pip and install Python dependencies
# RUN pip install --upgrade pip setuptools wheel && \
#     pip install --no-cache-dir -r requirements.txt

# # Expose the application port
# EXPOSE 8080

# # Command to run the application
# CMD ["uvicorn", "generation:app", "--host", "0.0.0.0", "--port", "8080"]
FROM python:3.10-slim

WORKDIR /app

COPY . /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
        python3-dev \
        libpq-dev \
        libgl1 \
        libsm6 \
        libxrender1 \
        libxext6 \
        ffmpeg \
        curl && \
    rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

EXPOSE 8080 7860

COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

CMD ["/app/entrypoint.sh"]
