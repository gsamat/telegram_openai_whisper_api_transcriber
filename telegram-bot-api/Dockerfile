ARG DEBIAN_VERSION=trixie-20250908-slim

FROM debian:${DEBIAN_VERSION} AS build

ENV CXXFLAGS=""
ARG BUILD_CPU_COUNT=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    linux-headers-amd64 \
    git \
    zlib1g-dev \
    libssl-dev \
    gperf \
    cmake \
    zstd \
    ca-certificates

RUN git clone --recursive https://github.com/tdlib/telegram-bot-api.git \
 && cd telegram-bot-api \
 && mkdir -p build \
 && cd build \
 && cmake -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX:PATH=.. .. \
 && cmake --build . --target install -j ${BUILD_CPU_COUNT} \
 && strip /telegram-bot-api/bin/telegram-bot-api


FROM debian:${DEBIAN_VERSION}

ENV TELEGRAM_WORK_DIR="/var/lib/telegram-bot-api" \
    TELEGRAM_TEMP_DIR="/tmp/telegram-bot-api"

RUN apt-get update && apt-get install -y --no-install-recommends \
    openssl \
    libstdc++6 \
    adduser \
 && rm -rf /var/lib/apt/lists/*


COPY --from=build /telegram-bot-api/bin/telegram-bot-api /usr/local/bin/telegram-bot-api


COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh \
&& addgroup --system --gid 101 telegram-bot-api \
&& adduser --system --disabled-password --no-create-home --uid 101 --home ${TELEGRAM_WORK_DIR} --shell /bin/false --ingroup telegram-bot-api telegram-bot-api \
&& mkdir -p ${TELEGRAM_WORK_DIR} ${TELEGRAM_TEMP_DIR} \
&& chown telegram-bot-api:telegram-bot-api ${TELEGRAM_WORK_DIR} ${TELEGRAM_TEMP_DIR}

EXPOSE 8081/tcp 8082/tcp
ENTRYPOINT ["/docker-entrypoint.sh"]
