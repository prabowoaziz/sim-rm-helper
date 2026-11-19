# 📘 FASE 4 - PART 3: Laporan Akreditasi (KLPCM)

**Tujuan:** Membuat form input untuk Audit Kelengkapan Rekam Medis (KLPCM) dan menghitung persentasenya.

---

## 🤖 PERINTAH UNTUK CODEX (Backend/Logic)

Copy-paste teks di bawah ini ke Codex:

```text
Halo Codex. Kita masuk ke Laporan Akreditasi (KLPCM). Karena data kelengkapan RM tidak ada di file Excel mentah, kita akan membuat form input manual di Tab Laporan.

Tugas 1: Update `app.py` di Tab 4 (Laporan).
- Di bawah section RL 4a, tambahkan `st.subheader("📝 Audit KLPCM (Kelengkapan Rekam Medis)")`.
- Buat form menggunakan `st.form("form_klpcm")`:
  - Input `st.number_input("Jumlah RM yang diaudit", min_value=1, value=20)`
  - Input `st.number_input("RM Lengkap (Identitas, Diagnosa, TTD Dokter, dll)", min_value=0, value=15)`
  - Tombol submit: `st.form_submit_button("Hitung KLPCM")`
- Jika tombol diklik:
  - Hitung persentase: `(RM Lengkap / Jumlah Diaudit) * 100`
  - Tampilkan `st.metric("Persentase KLPCM", f"{persentase}%")`
  - Jika persentase >= 80: Tampilkan `st.success("✅ Memenuhi standar akreditasi (≥ 80%)")`
  - Jika < 80: Tampilkan `st.error("❌ Belum memenuhi standar akreditasi (< 80%)")`

Tugas 2: Pastikan form ini rapi dan tidak mengganggu section Laporan RL di atasnya.

Aturan:
- Jangan ubah CSS/tema.
- Setelah selesai, update ke GitHub.