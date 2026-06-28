FROM python:3.11-slim

WORKDIR /app

# Copy the requirements file
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Ensure the database directory can be written to by creating it and setting permissions
# (This is useful in containerized environments where SQLite is used)
RUN mkdir -p /app/pizzaflow.db && chmod -R 777 /app/pizzaflow.db || true
RUN chmod 777 /app || true

# Hugging Face Spaces expose port 7860 by default
ENV PORT=7860

# Run the app
CMD ["python", "app.py"]
