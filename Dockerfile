FROM ubuntu:24.04@sha256:4fbb8e6a8395de5a7550b33509421a2bafbc0aab6c06ba2cef9ebffbc7092d90 AS jvlink-bridge-builder

ENV DEBIAN_FRONTEND=noninteractive

RUN dpkg --add-architecture i386 \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        binutils-mingw-w64-i686=2.41.90.20240122-1ubuntu1+11.4 \
        gcc-mingw-w64-i686=13.2.0-6ubuntu1+26.1 \
        gcc-mingw-w64-i686-posix=13.2.0-6ubuntu1+26.1 \
        gcc-mingw-w64-i686-win32=13.2.0-6ubuntu1+26.1 \
        make \
        mingw-w64-common=11.0.1-3build1 \
        mingw-w64-i686-dev=11.0.1-3build1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
COPY tools/jvlink-bridge/bridge_native.c /build/bridge_native.c
RUN i686-w64-mingw32-gcc \
        -std=c99 \
        -O2 \
        -Wall \
        -Wextra \
        -static \
        -Wl,--no-insert-timestamp \
        -o /JVLinkBridge.exe \
        /build/bridge_native.c \
        -lole32 \
        -loleaut32 \
        -luuid

FROM ubuntu:24.04@sha256:4fbb8e6a8395de5a7550b33509421a2bafbc0aab6c06ba2cef9ebffbc7092d90

LABEL maintainer="JLTSQL Contributors"
LABEL description="JLTSQL - JRA-VAN DataLab ETL with the Wine/JV-Link bridge"

ENV DEBIAN_FRONTEND=noninteractive
ENV LANG=ja_JP.UTF-8
ENV LC_ALL=ja_JP.UTF-8
ENV TZ=Asia/Tokyo
ENV PYTHONUNBUFFERED=1
ENV VIRTUAL_ENV=/opt/venv
ENV PATH="/opt/venv/bin:${PATH}"
ENV PYTHONPATH=/app
ENV DISPLAY=:1
ENV WINEPREFIX=/wineprefix
ENV WINEARCH=win64
ENV JVLINK_WINEPREFIX=/wineprefix
ENV JVLINK_WINEARCH=win64
ENV JVLINK_BRIDGE_EXE=/app/tools/jvlink-bridge/bin/native/JVLinkBridge.exe
# The bridge refuses to guess an interpreter on non-Windows hosts.
ENV JVLINK_BRIDGE_RUNNER=wine
ENV XDG_CACHE_HOME=/app/.cache
ENV HOME=/home/jrvltsql

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
        gosu \
        gpg \
        language-pack-ja \
        locales \
        novnc \
        python3 \
        python3-pip \
        python3-venv \
        unshield \
        unzip \
        websockify \
        winbind \
        x11-apps \
        x11vnc \
        xvfb \
        tini \
    && mkdir -pm755 /etc/apt/keyrings \
    && curl -fsSL https://dl.winehq.org/wine-builds/winehq.key | gpg --dearmor -o /etc/apt/keyrings/winehq-archive.key - \
    && curl -fsSL -o /etc/apt/sources.list.d/winehq-noble.sources https://dl.winehq.org/wine-builds/ubuntu/dists/noble/winehq-noble.sources \
    && apt-get update \
    && apt-get install -y --install-recommends winehq-stable \
    && locale-gen ja_JP.UTF-8 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . .
COPY --from=jvlink-bridge-builder /JVLinkBridge.exe /app/tools/jvlink-bridge/bin/native/JVLinkBridge.exe

RUN if [ ! -f config/config.yaml ] && [ -f config/config.yaml.example ]; then cp config/config.yaml.example config/config.yaml; fi \
    && python3 -m venv /opt/venv \
    && pip install --upgrade pip setuptools wheel \
    && pip install --no-cache-dir ".[postgres,s3]" \
    && chmod +x scripts/docker-entrypoint.sh scripts/build_jvlink_bridge_native.sh \
    && mkdir -p /opt/jvlink-bridge \
    && ln -sf /app/tools/jvlink-bridge/bin/native/JVLinkBridge.exe /opt/jvlink-bridge/JVLinkBridge.exe \
    && mkdir -p /app/data /app/logs /app/.cache /wineprefix /home/jrvltsql

EXPOSE 5900 6080

ENTRYPOINT ["/usr/bin/tini", "--", "scripts/docker-entrypoint.sh"]
CMD ["jltsql", "status"]
