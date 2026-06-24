# Use a lightweight Python base image, pinned by digest for reproducibility
FROM python:3.9-slim@sha256:2d97f6910b16bd338d3060f261f53f144965f755599aab1acda1e13cf1731b1b

# Set working directory inside the container
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Run as a non-root user
RUN useradd --create-home --uid 10001 imgdude \
    && chown -R imgdude:imgdude /app
USER imgdude

# Expose the port the app runs on
EXPOSE 12312

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:12312/health')" || exit 1

# Default command to run the application
CMD ["uvicorn", "imgdude.main:app", "--host", "0.0.0.0", "--port", "12312"]
