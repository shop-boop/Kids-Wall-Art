# Cloud Run image for service-webhook (Component D).
# Deliberately tiny: no Pillow/RAQM/fonts/IndicXlit. Fast cold starts so
# Shopify's webhook ack window is never at risk (see docs/spec-v2.md
# "Repo layout decision").
#
# Build from the REPO ROOT (not this folder) since it needs ../shared:
#   docker build -f service-webhook/Dockerfile -t service-webhook .

FROM python:3.11-slim

WORKDIR /srv

COPY service-webhook/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY shared /srv/shared
RUN pip install --no-cache-dir -e /srv/shared

COPY service-webhook/app /srv/app

ENV PORT=8080
EXPOSE 8080

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
