# 1. Base image: lightweight Python
FROM python:3.10-slim

# 2. Install Linux C++ compiler (g++) required for the core engine
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# 3. Set working directory
WORKDIR /app

# 4. Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy the rest of the application code
COPY . .

# 6. Compile the C++ module within the Linux environment
RUN pip install .

# 7. Expose the server port
EXPOSE 5000

# 8. Start the application
CMD ["python", "src/main.py"]