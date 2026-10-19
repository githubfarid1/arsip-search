# SIDAGI

**Sistem Dokumentasi Arsip Digital BWS Maluku Utara**

Dokumen ini menjelaskan cara memakai aplikasi SIDAGI untuk mencari, melihat, dan mengelola arsip digital.

---

## Daftar Isi

1. [Tentang SIDAGI](#tentang-sidagi)
2. [Teknologi yang Digunakan](#teknologi-yang-digunakan)
3. [Mengakses Aplikasi](#mengakses-aplikasi)
4. [Antarmuka Utama](#antarmuka-utama)
5. [Cara Mencari Arsip](#cara-mencari-arsip)
6. [Melihat PDF & Watermark](#melihat-pdf--watermark)
7. [Statistik Arsip](#statistik-arsip)
8. [Sinkronisasi (Reindex)](#sinkronisasi-reindex)
9. [Mode Terang / Gelap](#mode-terang--gelap)
10. [Struktur Berkas PDF](#struktur-berkas-pdf)
11. [Tanya Jawab (FAQ)](#tanya-jawab-faq)
12. [Lampiran Screenshot](#lampiran-screenshot)

---

## Tentang SIDAGI

SIDAGI adalah sistem dokumentasi arsip digital untuk mendukung pencarian arsip di lingkungan **BWS Maluku Utara**. Aplikasi ini mengindeks metadata arsip dari database ke mesin pencari full-text, lalu menyajikan hasil pencarian beserta file PDF yang tersimpan di penyimpanan (NAS).

Jenis arsip yang diindeks:

| Jenis | Keterangan |
|-------|------------|
| **Tahun** | Arsip tingkat tahun |
| **Box** | Kotak arsip |
| **Bundle** | Berkas/bundle dalam box |
| **Item** | Item/lembar arsip (detail terendah) |

---

## Teknologi yang Digunakan

### Frontend
| Teknologi | Versi / Keterangan |
|-----------|-------------------|
| Next.js | 14.2.5 (App Router, standalone) |
| React | 18.3 |
| TypeScript | 5.5.3 |
| Tailwind CSS | 3.4 |
| Recharts | Grafik statistik |
| Plus Jakarta Sans | Font display (via `next/font`) |

### Backend (API)
| Teknologi | Versi / Keterangan |
|-----------|-------------------|
| Python | 3.11 |
| FastAPI | 0.110 |
| Uvicorn | 0.27 (ASGI server) |
| Meilisearch | 1.6 (mesin pencari full-text) |
| MySQL | Database sumber arsip (`arsip_tata_*`) |
| PyMuPDF (fitz) | Watermark & thumbnail PDF |
| PyMySQL | Koneksi MySQL |

### Infrastruktur
| Teknologi | Keterangan |
|-----------|------------|
| Docker & Docker Compose | Containerisasi & orkestrasi |
| Dokploy | Platform deploy |
| NFS / NAS | Penyimpanan file PDF (`/home/arsip/nas-media`) |

---

## Mengakses Aplikasi

1. Buka browser (Chrome / Firefox / Edge terbaru).
2. Akses URL aplikasi, contoh:

   ```
   http://<alamat-server>:8007
   ```

3. Halaman utama akan menampilkan kotak pencarian dan navigasi SIDAGI.

> **Catatan:** Port default frontend adalah **8007**. Sesuaikan dengan alamat server Anda.

---

## Antarmuka Utama

Bagian-bagian penting pada halaman utama:

| Area | Fungsi |
|------|--------|
| Header **SIDAGI** | Identitas aplikasi |
| Kotak pencarian | Mengetik kata kunci arsip |
| Tombol reindex | Menyinkronkan data MySQL → Meilisearch |
| Tombol statistik | Membuka panel statistik arsip |
| Tombol tema | Beralih mode terang / gelap |
| Daftar hasil | Hasil pencarian arsip |

**Screenshot — Halaman utama**

```markdown
![Halaman utama SIDAGI](docs/screenshots/01-home.png)
```

> Tempel screenshot di folder `docs/screenshots/` lalu tautan di atas akan menampilkan gambar.  
> Sementara ini, ganti blok di atas dengan gambar hasil paste, misalnya:
>
> `![Halaman utama SIDAGI](docs/screenshots/01-home.png)`

<!-- PASTE SCREENSHOT: Halaman utama / landing SIDAGI di sini -->

---

## Cara Mencari Arsip

1. Klik kotak **“Cari arsip...”** di tengah halaman.
2. Ketik kata kunci, contoh:
   - `irigasi`
   - `AMDAL`
   - `pembangunan bendung`
   - nama kegiatan / kode arsip
3. Tekan **Enter** atau tunggu hasil muncul.
4. Hasil ditampilkan sebagai kartu yang memuat:
   - Jenis arsip (Tahun / Box / Bundle / Item)
   - Kode arsip
   - Tahun (`yeardate`)
   - Nomor box, bundle, item
   - Judul / deskripsi
   - Indikator **PDF** jika file tersedia

### Tips pencarian
- Gunakan **kata kunci pendek** yang spesifik (nama proyek, lokasi, tahun).
- Kombinasi kata akan dicari secara full-text oleh Meilisearch.
- Jika hasil terlalu banyak, perkecil dengan kata yang lebih khas.

**Screenshot — Hasil pencarian**

```markdown
![Hasil pencarian](docs/screenshots/02-search-results.png)
```

<!-- PASTE SCREENSHOT: Hasil pencarian di sini -->

---

## Melihat PDF & Watermark

1. Pada kartu hasil yang memiliki tombol/indikator **PDF**, klik untuk membuka.
2. PDF ditampilkan pada modal **PDF Viewer**.
3. Pada modal:
   - **Download** — unduh file PDF
   - **Toggle watermark** — tampilkan versi dengan watermark **COPY** atau tanpa watermark
   - **Tutup** — kembali ke hasil pencarian

### Keterangan watermark
- Watermark menggunakan teks **COPY** yang ditimpa pada halaman PDF (via PyMuPDF).
- Digunakan untuk salinan kontrol; file asli tetap utuh di NAS.

**Screenshot — Modal PDF**

```markdown
![Viewer PDF dengan watermark](docs/screenshots/03-pdf-viewer.png)
```

<!-- PASTE SCREENSHOT: Modal PDF viewer di sini -->

**Screenshot — PDF dengan watermark COPY**

```markdown
![PDF watermark COPY](docs/screenshots/04-pdf-watermark.png)
```

<!-- PASTE SCREENSHOT: Contoh PDF ber-watermark di sini -->

---

## Statistik Arsip

1. Klik ikon **Statistik dokumen** (di header).
2. Panel statistik menampilkan:
   - Total dokumen
   - Jumlah yang **ada PDF** vs **belum ada PDF**
   - Grafik komposisi per jenis arsip
   - Grafik **Jumlah Dokumen per Tahun** (Ada PDF / Belum)

Gunakan panel ini untuk memantau cakupan digitalisasi arsip.

**Screenshot — Panel statistik**

```markdown
![Statistik arsip](docs/screenshots/05-statistics.png)
```

<!-- PASTE SCREENSHOT: Panel statistik di sini -->

---

## Sinkronisasi (Reindex)

Setelah data arsip di **MySQL** bertambah/diubah, indeks pencarian perlu diperbarui.

1. Klik tombol **Reindex dari MySQL ke Meilisearch** (ikon refresh/sync).
2. Tunggu proses selesai.
3. Lakukan pencarian ulang untuk memastikan data terbaru sudah muncul.

Kapan perlu reindex?
- Setelah import / update data arsip di database
- Jika hasil pencarian terasa tidak lengkap
- Setelah pemeliharaan database

**Screenshot — Proses sinkronisasi**

```markdown
![Sinkronisasi reindex](docs/screenshots/06-reindex.png)
```

<!-- PASTE SCREENSHOT: Status reindex/sync di sini -->

> **Catatan teknis:** Saat API pertama kali start, sistem juga menjalankan *auto-reindex* di latar belakang.

---

## Mode Terang / Gelap

- Klik ikon **toggle theme** pada header untuk berpindah mode.
- Preferensi tersimpan di browser (`localStorage`).
- Default mengikuti preferensi sistem operasi (terang/gelap).

**Screenshot — Mode gelap**

```markdown
![Mode gelap](docs/screenshots/07-dark-mode.png)
```

<!-- PASTE SCREENSHOT: Tampilan dark mode di sini -->

---

## Struktur Berkas PDF

File PDF disimpan di NAS mengikuti pola:

```text
{PDF_HOST_PATH}/arsip_tata/{tahun}/{kode}.pdf
```

Contoh pada server:

```text
/home/arsip/nas-media/arsip_tata/2023/ABC-123.pdf
```

Di dalam container Docker, path tersebut dipetakan ke:

```text
/pdfs/arsip_tata/{tahun}/{kode}.pdf
```

Jika file tidak ditemukan, aplikasi menampilkan status **tanpa PDF** / HTTP 404 — bukan error aplikasi.

---

## Tanya Jawab (FAQ)

**Q: Hasil pencarian tidak muncul?**  
A: Pastikan sudah klik **Reindex**, atau cek koneksi ke Meilisearch dan MySQL di sisi admin.

**Q: PDF tidak bisa dibuka / 404?**  
A: File mungkin belum diunggah ke NAS, atau nama file tidak sesuai pola `{tahun}/{kode}.pdf`. Cek folder di NAS.

**Q: Aplikasi terasa lambat saat NAS mati?**  
A: Pastikan mount NFS memakai opsi `soft,timeo=10,retrans=3` (lihat `installation.MD`) agar tidak hang.

**Q: Berapa lama data baru muncul di pencarian?**  
A: Setelah **Reindex** (atau auto-reindex saat API start) selesai.

---

## Lampiran Screenshot

Gunakan bagian ini untuk menempel gambar dokumentasi final.

| No | Gambar | Keterangan |
|----|--------|------------|
| 1 | `docs/screenshots/01-home.png` | Halaman utama |
| 2 | `docs/screenshots/02-search-results.png` | Hasil pencarian |
| 3 | `docs/screenshots/03-pdf-viewer.png` | Modal PDF viewer |
| 4 | `docs/screenshots/04-pdf-watermark.png` | PDF dengan watermark |
| 5 | `docs/screenshots/05-statistics.png` | Statistik arsip |
| 6 | `docs/screenshots/06-reindex.png` | Sinkronisasi |
| 7 | `docs/screenshots/07-dark-mode.png` | Mode gelap |

### Cara menempel screenshot

1. Buat folder `docs/screenshots/` di root project.
2. Simpan / paste screenshot dengan nama di atas (PNG direkomendasikan).
3. Tempel di Markdown dengan format:

   ```markdown
   ![Judul gambar](docs/screenshots/01-home.png)
   ```

<!-- PASTE SCREENSHOT TAMBAHAN DI SINI -->

---

## Dokumen Terkait

- [installation.MD](installation.MD) — instalasi & konfigurasi server
- `.env.dokploy.example` — contoh environment variable deploy

---

**SIDAGI** — Sistem Dokumentasi Arsip Digital BWS Maluku Utara
