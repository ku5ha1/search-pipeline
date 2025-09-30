FROM mcr.microsoft.com/azure-functions/python:4-python3.10

# Set working directory
WORKDIR /home/site/wwwroot

# Copy function app files
COPY requirements.txt .
COPY host.json .
COPY function_app.py .
COPY app/ ./app

# Install Python dependencies
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# The Azure Functions runtime auto-starts the function; no CMD needed
