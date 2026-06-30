FROM ubuntu:24.04

LABEL maintainer="JLTSQL Contributors"
LABEL description="JRVLTSQL - JRA-VAN DataLab ETL with Wine/JV-Link bridge"

ENV DEBIAN_FRONTEND=noninteractive
ENV LANG=ja_JP.UTF-8
ENV LC_ALL=ja_JP.UTF-8
ENV PYTHONUNBUFFERED=1
ENV VIRTUAL_ENV=/opt/venv
ENV PATH="/opt/venv/bin:${PATH}"
ENV DISPLAY=:1
ENV WINEPREFIX=/wineprefix
ENV WINEARCH=win64
ENV JVLINK_WINEPREFIX=/wineprefix
ENV JVLINK_WINEARCH=win64
ENV JVLINK_BRIDGE_EXE=/app/tools/jvlink-bridge/bin/native/JVLinkBridge.exe

RUN dpkg --add-architecture i386 \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        cabextract \
        curl \
        7zip \
        7zip-rar \
        fluxbox \
        fonts-ipafont-gothic \
        fonts-noto-cjk \
        gcc \
        gcc-mingw-w64-i686 \
        git \
        gpg \
        language-pack-ja \
        libpq-dev \
        locales \
        make \
        novnc \
        python3 \
        python3-dev \
        python3-pip \
        python3-venv \
        unshield \
        unzip \
        wget \
        websockify \
        winbind \
        xdotool \
        x11vnc \
        xvfb \
    && mkdir -pm755 /etc/apt/keyrings \
    && wget -qO- https://dl.winehq.org/wine-builds/winehq.key | gpg --dearmor -o /etc/apt/keyrings/winehq-archive.key - \
    && wget -qNP /etc/apt/sources.list.d/ https://dl.winehq.org/wine-builds/ubuntu/dists/noble/winehq-noble.sources \
    && apt-get update \
    && apt-get install -y --install-recommends winehq-stable \
    && locale-gen ja_JP.UTF-8 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . .

RUN python3 -m venv /opt/venv \
    && pip install --upgrade pip setuptools wheel \
    && pip install --no-cache-dir ".[postgres,s3]" \
    && chmod +x scripts/docker-entrypoint.sh scripts/setup_wine_jvlink.sh scripts/build_jvlink_bridge_native.sh \
    && scripts/build_jvlink_bridge_native.sh \
    && mkdir -p /app/data /app/logs /wineprefix

EXPOSE 5900 6080

ENTRYPOINT ["scripts/docker-entrypoint.sh"]
CMD ["jltsql", "--help"]
