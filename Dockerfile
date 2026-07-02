FROM python:3.12-bookworm

ARG DEBIAN_FRONTEND=noninteractive
ARG APP_UID=1000
ARG APP_GID=1000

LABEL org.opencontainers.image.title="jrvltsql"
LABEL org.opencontainers.image.description="jrvltsql Wine/noVNC JRA-VAN collector with JVLinkBridge"

ENV PYTHONUNBUFFERED=1 \
    LANG=ja_JP.UTF-8 \
    LC_ALL=ja_JP.UTF-8 \
    TZ=Asia/Tokyo \
    PATH="/opt/venv/bin:${PATH}" \
    HOME=/home/jra \
    DISPLAY=:1 \
    WINEPREFIX=/wineprefix \
    WINEARCH=win64 \
    WINEDEBUG=-all \
    JVLINK_WINE=wine \
    JVLINK_WINEPREFIX=/wineprefix \
    JVLINK_WINEARCH=win64 \
    JVLINK_INSTALLERS_DIR=/installers \
    JVLINK_BRIDGE_EXE=/opt/jvlink-bridge/JVLinkBridge.exe \
    JRA_COLLECTOR_SERVICE_PORT=8081

RUN dpkg --add-architecture i386 \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        cabextract \
        curl \
        fluxbox \
        fonts-ipafont-gothic \
        fonts-noto-cjk \
        gcc-mingw-w64-i686 \
        gosu \
        locales \
        p7zip-full \
        procps \
        unshield \
        unzip \
        websockify \
        wine \
        wine32 \
        wine64 \
        winbind \
        x11-utils \
        xdotool \
        x11vnc \
        xvfb \
        novnc \
    && sed -i 's/# ja_JP.UTF-8 UTF-8/ja_JP.UTF-8 UTF-8/' /etc/locale.gen \
    && locale-gen \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd --gid "${APP_GID}" jra \
    && useradd --uid "${APP_UID}" --gid "${APP_GID}" --create-home --shell /bin/bash jra \
    && mkdir -p /app /installers /wineprefix /opt/jvlink-bridge /app/data/cache /app/logs \
    && chown -R jra:jra /app /installers /wineprefix /opt/jvlink-bridge

WORKDIR /app

COPY pyproject.toml README.md ./
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir --upgrade pip setuptools wheel \
    && mkdir -p src \
    && touch src/__init__.py \
    && /opt/venv/bin/pip install --no-cache-dir ".[postgres]" \
    && rm -rf src build *.egg-info

COPY . .
RUN /opt/venv/bin/pip install --no-cache-dir --force-reinstall --no-deps . \
    && chmod +x /app/scripts/docker-entrypoint.sh /app/scripts/setup_wine_jvlink.sh /app/scripts/build_jvlink_bridge_native.sh /app/scripts/collector_service.py \
    && JVLINK_BRIDGE_EXE=/opt/jvlink-bridge/JVLinkBridge.exe /app/scripts/setup_wine_jvlink.sh --bridge-only \
    && chown -R jra:jra /app /opt/venv /opt/jvlink-bridge

EXPOSE 8081 6080 5900

ENTRYPOINT ["/app/scripts/docker-entrypoint.sh"]
CMD ["python", "/app/scripts/collector_service.py", "--kind", "jra", "--host", "0.0.0.0", "--port", "8081"]
