FROM python:3.11-slim

# System deps for Playwright/Chromium
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl wget gnupg \
    fonts-liberation \
    libnss3 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libxkbcommon0 \
    libxcomposite1 libxdamage1 libxrandr2 \
    libgbm1 libasound2 \
    libpangocairo-1.0-0 libgtk-3-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies (cached layer — rebuilt only if this RUN changes)
RUN pip install --no-cache-dir \
    requests \
    python-dotenv \
    plotly \
    playwright

# Install Chromium headless shell
RUN playwright install chromium --only-shell

# Copy all application files (done last so code changes don't invalidate dep cache)
COPY . .

# Ensure data directory exists (also mounted as a volume in docker-compose)
RUN mkdir -p /app/data

# Run the continuous loop.
# Override --provider at runtime: docker run ... python zonnebrand/zonnebrand.py --provider anwb
CMD ["python", "zonnebrand/zonnebrand.py", "--provider", "zonneplan"]