# # Use lightweight Python base
# FROM python:3.10-slim

# # Set working directory
# WORKDIR /app

# # Copy requirements and install
# COPY requirements.txt .
# RUN pip install --upgrade pip \
#     && pip install --no-cache-dir -r requirements.txt \
#     && pip install "uvicorn[standard]"

# # Copy the app
# COPY app/ ./app

# # Expose FastAPI port
# EXPOSE 8000

# # Command to run FastAPI
# CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# Use official Python base
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Copy only necessary files
COPY requirements.txt . 
COPY app/ ./app

# Install dependencies
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Set default command to run the pipeline on container start
CMD ["python", "run_pipeline.py"]
