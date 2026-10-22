FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Static files (admin and Swagger UI assets) are served by WhiteNoise.
RUN DJANGO_SECRET_KEY=build-only python manage.py collectstatic --noinput

RUN useradd --create-home appuser && chown -R appuser /app
USER appuser

EXPOSE 8000

# Apply migrations, reset the shared demo account, then serve with Gunicorn.
# Render's free tier restarts the server after it sleeps, so the demo gets fresh data regularly.
# PORT is set by hosts like Render; defaults to 8000.
CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py seed_demo --reset && gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 2"]
