FROM python:3.12-slim

WORKDIR /app

# System deps for Playwright Chromium (manual — avoids broken --with-deps on slim)
RUN apt-get update && apt-get install -y \
    wget curl gnupg ca-certificates \
    libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 \
    libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 \
    libgbm1 libasound2 libpango-1.0-0 libpangocairo-1.0-0 \
    libgtk-3-0 libx11-xcb1 libxcb-dri3-0 \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps directly — bypasses requirements.txt entirely
RUN pip install --no-cache-dir \
    fastapi==0.115.0 \
    "uvicorn[standard]==0.30.6" \
    pydantic==2.9.2 \
    pydantic-settings==2.5.2 \
    openai==1.51.0 \
    anthropic==0.37.1 \
    "supabase>=2.0.0" \
    playwright==1.48.0 \
    beautifulsoup4==4.12.3 \
    python-dotenv==1.0.1 \
    httpx==0.27.2

# Install Playwright Chromium only (no --with-deps — deps installed above manually)
RUN playwright install chromium

# Copy app code
COPY . .

# Create empty __init__.py files so Python treats folders as modules
RUN touch app_api/__init__.py core/__init__.py services/__init__.py

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
