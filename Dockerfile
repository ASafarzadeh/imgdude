# Use a lightweight Python base image
FROM python:3.9-slim

# Set working directory inside the container
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Expose the port the app runs on
EXPOSE 12312

# Default command to run the application
CMD ["uvicorn", "imgdude.main:app", "--host", "0.0.0.0", "--port", "12312"]