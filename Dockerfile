FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /workspace

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        libasound2 \
        libatk1.0-0 \
        libcups2 \
        libdbus-1-3 \
        libgbm1 \
        libgl1 \
        libglib2.0-0 \
        libgtk-3-0 \
        libnss3 \
        libvulkan1 \
        libx11-6 \
        libxcursor1 \
        libxdamage1 \
        libxext6 \
        libxfixes3 \
        libxi6 \
        libxinerama1 \
        libxrandr2 \
        libxrender1 \
        libxtst6 \
        libxxf86vm1 \
        mesa-vulkan-drivers \
        procps \
        xauth \
        xvfb \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN python -m pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "scripts/run_ai2thor_minimal.py", "--platform", "cloudrendering"]
