# Panduan Kontribusi SCOR-Py

Terima kasih atas minat Anda untuk berkontribusi pada **SCOR-Py**! Kami menyambut kontribusi dari komunitas, baik berupa perbaikan bug, penambahan metrik SCOR Level 2/3, peningkatan performa, maupun dokumentasi.

---

## 🛠️ Alur Pengembangan Lokal

1. **Fork & Clone**
   ```bash
   git clone https://github.com/<username>/Scor-py.git
   cd Scor-py
   ```

2. **Buat Virtual Environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   pip install --upgrade pip
   pip install -e ".[dev,dashboard]"
   ```

3. **Buat Feature Branch**
   ```bash
   git checkout -b feat/nama-fitur-baru
   ```

---

## 🧪 Standar Pengujian & Kualitas Kode

Sebelum mengajukan Pull Request (PR), pastikan semua langkah berikut lulus tanpa peringatan atau error:

1. **Format & Linting:**
   ```bash
   ruff check .
   ruff format --check .
   ```

2. **Pengecekan Tipe Statis:**
   ```bash
   mypy scorpy
   ```

3. **Menjalankan Pengujian (Unit & Hypothesis):**
   ```bash
   pytest -q --cov=scorpy
   ```

---

## 📝 Konvensi Pesan Commit

Kami mengikuti konvensi **Conventional Commits**:
* `feat:` untuk penambahan fitur baru
* `fix:` untuk perbaikan bug
* `docs:` untuk perubahan dokumentasi
* `style:` untuk pemformatan kode tanpa perubahan logika
* `refactor:` untuk refaktorisasi kode
* `perf:` untuk peningkatan performa
* `test:` untuk penambahan atau perbaikan pengujian
* `ci:` untuk konfigurasi alur kerja CI/CD
* `chore:` untuk tugas pemeliharaan dependensi atau build
