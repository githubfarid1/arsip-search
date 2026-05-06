# Instalasi Arsip Search

## Prasyarat

- Ubuntu 20.04+ (atau distro Linux lain)
- Docker & Docker Compose v2
- MySQL sudah berjalan (bisa di server lain atau lokal)
- 2GB+ RAM tersedia

---

## Langkah 1 — Siapkan MySQL

Aplikasi ini butuh database MySQL. Buat database dan user:

```sql
CREATE DATABASE arsipserverdb2 CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'arsip'@'%' IDENTIFIED BY 'root123';
GRANT ALL PRIVILEGES ON arsipserverdb2.* TO 'arsip'@'%';
FLUSH PRIVILEGES;
```

Import schema dari file SQL yang ada:

```bash
mysql -h <MYSQL_HOST> -P 3307 -u arsip -proot123 arsipserverdb2 < arsipserverdb2.sql
```

---

## Langkah 2 — Clone / Copy File

```bash
cd /opt
cp -r ~/dev/vibe/bws/arsip-search .
cd arsip-search
```

Struktur:
```
arsip-search/
├── api/
│   ├── main.py
│   ├── requirements.txt
│   └── schemas/
├── frontend/
│   ├── src/
│   ├── package.json
│   └── ...
├── docker-compose.yml
└── installation.MD
```

---

## Langkah 3 — docker-compose.yml

Gunakan file ini sebagai referensi lengkap:

```yaml
version: '3.8'

services:
  meilisearch:
    image: getmeili/meilisearch:v1.6
    container_name: arsip-meilisearch
    ports:
      - "7700:7700"
    environment:
      - MEILI_MASTER_KEY=arsipsearch2024
    volumes:
      - ./meilisearch_data:/meili_data
    restart: unless-stopped

  api:
    build:
      context: ./api
      dockerfile: Dockerfile
    container_name: arsip-api
    ports:
      - "8888:8888"
    environment:
      - MEILI_URL=http://meilisearch:7700
      - MEILI_KEY=arsipsearch2024
      - MYSQL_HOST=<ISI_HOST_MYSQL>
      - MYSQL_PORT=3307
      - MYSQL_USER=arsip
      - MYSQL_PASSWORD=root123
      - MYSQL_DB=arsipserverdb2
    volumes:
      - ./api:/app
    command: uvicorn main:app --host 0.0.0.0 --port 8888 --reload
    restart: unless-stopped

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: arsip-frontend
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:8888
    volumes:
      - ./frontend:/app
      - /app/node_modules
      - /app/.next
    command: npm run dev
    restart: unless-stopped
```

Untuk MySQL host: jika MySQL di mesin yang sama, pakai `host.docker.internal`. Jika di server lain, isi IP server MySQL-nya.

---

## Langkah 4 — Buat Dockerfile API

```bash
cat > api/Dockerfile << 'EOF'
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EOF
```

---

## Langkah 5 — Jalankan

```bash
docker compose up -d --build
```

Cek status:
```bash
docker compose ps
docker compose logs -f
```

---

## Langkah 6 — Verifikasi

```
curl http://localhost:8888/docs        # API FastAPI
curl http://localhost:3000             # Frontend Next.js
```

---

## Catatan Penting

1. **Port** — Pastikan port 3000, 7700, 8888 belum dipakai service lain
2. **Meilisearch** — Data search index tersimpan di `./meilisearch_data/`, jangan dihapus
3. **Sync data** — Setelah semua jalan, data MySQL perlu di-sync ke Meilisearch via endpoint API (cek di FastAPI docs `/docs`)
4. **Produksi** — Untuk production, ganti `NEXT_PUBLIC_API_URL` dengan domain (misal `https://arsip.domain.com`) dan set `allow_origins` di FastAPI lebih ketat
