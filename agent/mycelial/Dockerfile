FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY dashboard/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy core library
COPY mycelial.py .
COPY schema.sql .
COPY hook.py .

# Copy dashboard
COPY dashboard/ /app/dashboard/

# Database mounted at /data/iris.db
ENV PORT=8051

EXPOSE 8051

WORKDIR /app/dashboard
CMD ["gunicorn", "--bind", "0.0.0.0:8051", "--workers", "2", "--timeout", "120", "app:app"]
