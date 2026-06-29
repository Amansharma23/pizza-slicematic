FROM python:3.12-slim

WORKDIR /app

# Hugging Face Docker Spaces run as UID 1000. Create the same user and make
# runtime storage writable for uploaded menus and order logs.
RUN useradd -m -u 1000 user \
    && mkdir -p /data /app \
    && chown -R user:user /data /app

# Copy the requirements file
COPY --chown=user:user requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY --chown=user:user . .

# Hugging Face Spaces expose port 7860 by default
ENV PORT=7860
ENV DATABASE_DIR=/data

USER user

# Run the app
CMD ["python", "app.py"]
