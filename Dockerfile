FROM python:3.12-slim

WORKDIR /app

# System deps for Playwright
RUN apt-get update && apt-get install -y \
    wget curl gnupg \
    libnss3 libatk-bridge2.0-0 libdrm2 libxkbcommon0 \
    libgbm1 libasound2 libxrandr2 libxfixes3 libxcomposite1 \
    && rm -rf /var/lib/apt/lists/*

# Copy and install ONLY requirements.txt — never pip install .
COPY requirements.txt .
RUN pip install --no-cache-dir --no-build-isolation -r requirements.txt

# Install Playwright browsers
RUN playwright install chromium --with-deps

# Copy app code AFTER pip install (better layer caching)
COPY . .

# Create empty __init__.py files so Python treats folders as modules
RUN touch app_api/__init__.py core/__init__.py services/__init__.py

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
