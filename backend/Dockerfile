# Multi-stage Dockerfile for AdventureTogether Django API Backend
FROM python:3.12-slim-bookworm AS base

# Prevent Python from writing .pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system geospatial libraries (GDAL, GEOS, PROJ, SpatiaLite, PostgreSQL client)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gdal-bin \
    libgdal-dev \
    libgeos-dev \
    libproj-dev \
    libspatialite-dev \
    spatialite-bin \
    libpq-dev \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy dependency definition
COPY requirements.txt /app/

# Install Python packages
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy backend source code
COPY . /app/

# Expose port
EXPOSE 8000

# Default entrypoint runs Django server (or Q worker via entrypoint override)
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
