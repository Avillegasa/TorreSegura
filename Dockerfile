# Use Python 3.12 slim image as base
FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3-pip \
    python3-cffi \
    python3-brotli \
    libpango1.0-0 \
    libpangoft2-1.0-0 \
    libffi-dev \
    libcairo2 \
    libcairo2-dev \
    libjpeg62-turbo-dev \
    libgdk-pixbuf2.0-0 \
    libgdk-pixbuf2.0-dev \
    libglib2.0-0 \
    libglib2.0-dev \
    build-essential \
    fontconfig \
    && apt-get clean

# Set environment variables
ENV LD_LIBRARY_PATH=/usr/lib:/usr/local/lib:/usr/lib/x86_64-linux-gnu:$LD_LIBRARY_PATH

# Set the working directory
WORKDIR /condominio_app

# Copy the application code
COPY . /condominio_app/

# Install Python dependencies
RUN pip install -r requirements.txt

# Production startup script with error checking
RUN echo '#!/bin/bash\nset -e\necho "=== Starting Django application ==="\necho "Checking Django configuration..."\npython manage.py check || (echo "Django check failed but continuing..." && true)\necho "Running migrations..."\npython manage.py migrate --noinput || echo "Migrations failed, continuing..."\necho "Collecting static files..."\npython manage.py collectstatic --noinput || echo "Collectstatic failed, continuing..."\necho "Starting Gunicorn..."\nexec gunicorn --bind 0.0.0.0:8000 --workers 2 --timeout 120 --access-logfile - --error-logfile - condominio_app.wsgi:application' > /condominio_app/start.sh
RUN chmod +x /condominio_app/start.sh

# Command to run the application
CMD ["/bin/bash", "/condominio_app/start.sh"]