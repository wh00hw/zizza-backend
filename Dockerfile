FROM rust:alpine AS zecwallet-cli-builder

RUN apk add --no-cache \
    file \
    automake \
    libtool \
    openssl-dev \
    pkgconfig \
    build-base \
    cmake \
    ninja \
    protobuf-dev

WORKDIR /rust-app

COPY zizza/zcash/zecwallet-light-cli/ .

RUN cargo build --release

FROM python:3.10-alpine AS zizza-blockchain-intents-server

WORKDIR /app

RUN apk add --no-cache \
    pkgconfig \
    openssl-dev \
    libssl3 \
    build-base \
    libffi-dev \
    openssl-dev \
    musl-dev

RUN pip install --upgrade pip

COPY requirements.txt /app/
COPY zizza /app/zizza

RUN pip install --no-cache-dir -r requirements.txt

COPY server.py /app/server.py

COPY --from=zecwallet-cli-builder /rust-app/target/release/zecwallet-cli /app/zizza/zcash/zecwallet-light-cli/target/release/zecwallet-cli

EXPOSE 5001

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "5001"]