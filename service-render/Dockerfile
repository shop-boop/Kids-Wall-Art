# Cloud Run image for service-render (Components A + C).
# Heavy on purpose: Pillow+RAQM, HarfBuzz, FreeType, FriBiDi, IndicXlit
# weights, bundled Noto Indic fonts. Keep this OUT of service-webhook.
#
# Build from the REPO ROOT (not this folder) since it needs ../shared:
#   docker build -f service-render/Dockerfile -t service-render .

FROM python:3.11-slim AS base

# System deps for Pillow + RAQM complex text layout (spec Section 4)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    meson \
    ninja-build \
    pkg-config \
    libfreetype6-dev \
    libharfbuzz-dev \
    libfribidi-dev \
    libjpeg-dev \
    zlib1g-dev \
    liblcms2-dev \
    libwebp-dev \
    libtiff5-dev \
    libopenjp2-7-dev \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# libraqm is not always available as a distro package; build from source if
# the Pillow wheel doesn't already bundle it. UPDATE ME: verify this step is
# still needed for the python:3.11-slim base — recent Pillow wheels may
# bundle libraqm already, in which case this block can be dropped.
RUN curl -L https://github.com/HOST-Oman/libraqm/releases/download/v0.10.1/raqm-0.10.1.tar.gz -o /tmp/raqm.tar.gz \
    && mkdir -p /tmp/raqm && tar -xzf /tmp/raqm.tar.gz -C /tmp/raqm --strip-components=1 \
    && cd /tmp/raqm && meson setup build && meson compile -C build && meson install -C build \
    && ldconfig \
    && rm -rf /tmp/raqm /tmp/raqm.tar.gz

WORKDIR /srv

COPY service-render/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Local shared/ package (script_payload, transliterate_interface)
COPY shared /srv/shared
RUN pip install --no-cache-dir -e /srv/shared

COPY service-render/app /srv/app
# UPDATE ME: bundle real Noto Indic font files here before deploying —
# see fonts/README.md. Without them, /render returns 404 FileNotFoundError.
COPY service-render/fonts /srv/fonts

# Pre-download IndicXlit model weights at build time, not request time
# (spec 1.1). beam_width=4, rescore=False confirmed empirically 2026-06-19
# (matches app/backends/indicxlit.py — rescore=True needs an LM dependency
# not exercised/installed here).
RUN python -c "from ai4bharat.transliteration import XlitEngine; XlitEngine(beam_width=4, rescore=False)" || \
    echo "WARNING: IndicXlit weight prefetch failed at build time — fix before deploying"

ENV PORT=8080
EXPOSE 8080

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
