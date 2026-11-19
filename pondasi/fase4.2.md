# 📘 FASE 4 - PART 2: Laporan RL 3.1 & RL 4a Kemenkes

**Tujuan:** Membuat rekap angka untuk diinput ke portal SIRS Kemenkes (RL 3.1 & RL 4a).

---

## 🤖 PERINTAH UNTUK CODEX (Backend/Logic)

Copy-paste teks di bawah ini ke Codex:

```text
Halo Codex. Kita masuk ke pembuatan Laporan Kemenkes (RL 3.1 dan RL 4a). Tolong kerjakan instruksi ini.

Tugas 1: Update `modules/reporter.py` (Tambahkan fungsi baru, jangan hapus yang lama).

Fungsi A: `hitung_rl_31(df_long)`
- Logika: Mengambil baris terakhir per pasien (groupby no_rm, tail(1)) untuk melihat status akhirnya.
- Return DataFrame dengan format:
  - Pasien Awal Bulan: (Asumsi 0 dulu, atau hitung dari tgl_masuk < awal bulan)
  - Pasien Masuk (Total baris unik no_rm): ...
  - Pasien Keluar Hidup (Status selain Meninggal): ...
  - Pasien Keluar Mati (Status = Meninggal): ...
  - Pasien Pindah (Status = Pindah Kamar/Rujuk): ...
  - Pasien Sisa: (Asumsi 0 dulu)
  Bentuk tabelnya: kolom 'Indikator' dan 'Jumlah'.

Fungsi B: `hitung_rl_4a(df_long)`
- Logika: 
  - Ambil baris terakhir per pasien.
  - Groupby kolom 'diagnosa' (atau bisa pakai kolom 'no_rm' jika diagnosa kosong).
  - Hitung jumlah pasien Laki-laki (jenis_kelamin == 'L') dan Perempuan (jenis_kelamin == 'P').
  - Total = L + P.
  - Urutkan berdasarkan Total terbanyak (descending).
  - Ambil Top 10.
- Return DataFrame dengan kolom: ['No', 'Diagnosa', 'L', 'P', 'Total'].

Tugas 2: Update `app.py` di Tab 4 (Laporan).
- Di bawah section Mortalitas, tambahkan:
  - `st.subheader("📋 RL 3.1 — Kegiatan Pelayanan Ranap")`
  - Tampilkan tabel `hitung_rl_31`.
  - Tambahkan tombol download Excel untuk RL 3.1.
  
  - `st.subheader("📋 RL 4a — Morbiditas Rawat Inap (Top 10)")`
  - Tampilkan tabel `hitung_rl_4a`.
  - Tambahkan tombol download Excel untuk RL 4a.

Aturan:
- Jangan ubah CSS/tema.
- Pastikan tidak error jika kolom diagnosa ada yang kosong (isi dengan "Diagnosa Tidak Terisi").
- Setelah selesai, update ke GitHub.