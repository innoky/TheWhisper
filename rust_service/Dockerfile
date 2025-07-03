# ===== Стадия сборки =====
FROM rust:1.77 as builder

WORKDIR /app

# Кеш зависимостей
COPY Cargo.toml Cargo.lock ./
RUN mkdir src && echo "fn main() {}" > src/main.rs
RUN cargo build --release
RUN rm -rf src

# Копируем реальный код и пересобираем
COPY . .
RUN cargo build --release

# ===== Финальный образ =====
FROM debian:bullseye-slim

# Устанавливаем минимумы (SSL для Actix)
RUN apt-get update && apt-get install -y ca-certificates && rm -rf /var/lib/apt/lists/*

COPY --from=builder /app/target/release/tfidf_service /usr/local/bin/tfidf_service

EXPOSE 8080

CMD ["tfidf_service"]
