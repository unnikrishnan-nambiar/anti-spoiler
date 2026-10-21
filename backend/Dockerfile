FROM python:3.12-slim
RUN --mount=type=secret,id=platform_ca if [ -f /run/secrets/platform_ca ]; then cp /run/secrets/platform_ca /usr/local/share/ca-certificates/environment-proxy.crt; update-ca-certificates; fi
RUN sed -i 's|http://deb.debian.org|https://deb.debian.org|g' /etc/apt/sources.list.d/debian.sources && apt-get update && apt-get install -y --no-install-recommends ffmpeg libglib2.0-0 libgl1 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN PIP_CERT=/etc/ssl/certs/ca-certificates.crt pip install --no-cache-dir -r requirements.txt
RUN useradd --uid 10001 --create-home appuser
COPY --chown=appuser:appuser app app
COPY --chown=appuser:appuser tests tests
USER appuser
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
