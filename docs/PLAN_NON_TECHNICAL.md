# Rencana Kerja AI Meeting Agent — Versi Non-Teknis

Dokumen pendamping `PLAN.md`, ditulis untuk pembaca non-teknis.
Isinya: apa yang akan dibuat, dalam urutan apa, dan apa yang perlu kamu putuskan.
Dokumen ini tidak menggantikan `PLAN.md`. Kalau ada perbedaan, `PLAN.md` yang berlaku.

## 1. Produk ini apa

Aplikasi internet untuk rapat tatap muka. Tugasnya merekam suara rapat, mengubah
rekaman itu jadi catatan, lalu menyusun dua dokumen notulen dalam tiga bahasa
(Inggris, Mandarin, dan Indonesia):

- Notulen internal, untuk kalangan sendiri. Boleh memuat catatan, risiko, dan kekhawatiran internal.
- Notulen eksternal, untuk klien atau mitra. Tidak boleh memuat hal-hal yang hanya untuk internal.

Setiap notulen memuat tiga bahasa dalam satu dokumen. Ketiganya dibuat otomatis.
Saat meninjau hasilnya, kamu bisa memilih bahasa mana saja yang ingin dipakai. Bahasa
yang tidak dipakai hanya disembunyikan, bukan dihapus, jadi bisa dipakai lagi nanti.

Notulen ditulis dalam bahasa rapatnya, lalu dua bahasa lain diterjemahkan dari tulisan
itu. Tujuannya agar isi ketiganya tidak berbeda. Bahasa yang dipakai sebagai sumber
adalah bahasa yang terdeteksi dari rekaman, bukan bahasa yang dicentang saat membuat
rapat.

## 2. Kenapa dibuat

- Peserta rapat harus mendengarkan, ikut bicara, dan mencatat sekaligus. Detail penting terlewat.
- Peserta bisa bicara Inggris, Mandarin, Indonesia, atau berpindah bahasa di tengah rapat.
- Menyusun notulen tiga bahasa dalam dua versi adalah pekerjaan berulang yang melelahkan.
- Menyalin catatan internal ke dokumen klien adalah risiko kebocoran yang serius.

## 3. Aturan main saya selama membangun

- Satu langkah kecil per giliran. Setelah itu saya berhenti dan menunggu kamu.
- Setiap langkah punya syarat selesai yang jelas dan harus diuji lebih dulu.
- Kalau belum diuji, belum dianggap selesai.
- Saya catat setiap langkah sebelum melapor. Yang tidak tercatat, dianggap tidak terjadi.
- Saya tidak menambah fitur di luar yang diminta. Ide yang muncul masuk daftar tunggu.
- Kalau ada keputusan yang belum jelas, saya bertanya. Saya tidak menebak.

## 4. Bagaimana pekerjaan dibagi

### Tahap 0 — Persiapan (sudah selesai)
Menyepakati hal-hal dasar sebelum menulis kode apa pun: dokumen aturan kerja,
pilihan teknologi, dan kerangka proyek kosong yang bisa dijalankan. Pilihan
penyedia layanan internet dan layanan AI juga dibahas di sini, tapi hasilnya
ditunda.

Tahap ini sudah selesai. Kerangka aplikasinya sudah bisa dijalankan, tapi belum ada
layar yang bisa dipakai.

### Tahap 1 — Inti produk: dari rekaman jadi notulen
Ini tahap yang menghasilkan nilai utama.

Bisa membuat rapat baru dan mengisi judul, tanggal, dan bahasa rapat: Inggris, Mandarin, atau Indonesia.
Bisa merekam suara dari mikrofon, berhenti, dan memutar ulang hasilnya.
Rekaman tersimpan dengan aman dan punya batas waktu penyimpanan.
Rekaman diubah jadi teks, termasuk saat peserta berpindah antara Inggris dan Mandarin.
Transkripsi bahasa Indonesia memakai mesin yang sama. Kualitasnya belum diuji dengan rekaman asli.
Catatan rapat diringkas: topik, keputusan, tugas, penanggung jawab, tenggat, dan hal yang belum selesai.
Tersusun dua notulen tiga bahasa: internal dan eksternal.
Ada pemeriksaan yang menandai isi internal yang tidak boleh masuk ke notulen eksternal.
Ada pemeriksaan yang menandai bagian Inggris, Mandarin, dan Indonesia yang saling bertentangan.
Kamu bisa mengubah, menyetujui, dan menyimpan riwayat versi notulen.
Notulen bisa diunduh sebagai DOCX dan PDF.
Ada kendali akses dasar. Setiap rapat terikat ke akun pemiliknya, dan datanya tersimpan.

Yang kamu lihat setelah tahap ini: satu rapat bisa berjalan dari rekaman sampai notulen siap dibagikan.

### Tahap 2 — Teks langsung saat rapat (opsional)
Teks hasil pengenalan suara muncul di layar saat rapat berjalan. Bisa dinyalakan
dan dimatikan kapan saja. Mematikannya tidak menghentikan rekaman.

### Tahap 3 — Terjemahan langsung saat rapat (opsional)
Terjemahan teks Inggris ke Mandarin dan sebaliknya, muncul di layar sambil rapat
berjalan. Terjemahan butuh fitur teks langsung dari tahap 2, jadi tidak bisa
menyala sendiri. Mematikannya tidak mematikan teks langsung.

### Tahap 4 — Pengembangan lanjutan
Kamus istilah khusus perusahaan, pemetaan nama pembicara yang dikonfirmasi
pengguna, template notulen, opsi ekspor tambahan, pencarian riwayat rapat,
sambungan ke kalender/CRM/email, dan bahasa tambahan.

Catatan: urutan tahap 2, 3, dan 4 bisa berubah. Yang tidak berubah adalah tahap 1
dulu, karena notulen adalah nilai utama produk ini.

## 5. Rincian tahap 1, langkah per langkah

Satu baris di bawah ini adalah satu giliran kerja saya. Nomor PRD untuk tiap
langkah ada di `PLAN.md`.

| Langkah | Yang dikerjakan | Cara kita tahu sudah beres |
| --- | --- | --- |
| P1-01 | Menentukan data apa saja yang disimpan: rapat, rekaman, transkrip, notulen, versi | Rancangan disetujui, penyimpanan bisa disiapkan |
| P1-02 | Membuat rapat baru lewat form: judul, tanggal, bahasa | Rapat bisa dibuat lalu dibuka lagi |
| P1-03 | Tombol mulai, jeda, lanjut, dan berhenti merekam dari mikrofon | Rekaman lokal bisa diputar ulang |
| P1-04 | Mengunggah rekaman dengan aman, plus aturan berapa lama disimpan | Rekaman tersimpan dan menempel ke rapat yang benar |
| P1-05 | Mengubah rekaman jadi teks, bahasa Inggris dulu | Ada transkrip dari contoh rekaman |
| P1-06 | Menambah Mandarin dan percakapan campur dua bahasa | Contoh rekaman campuran berhasil jadi transkrip |
| P1-06c | Menambah bahasa Indonesia sebagai bahasa rapat | Rapat berbahasa Indonesia diterima, dan transkripsi memakai petunjuk bahasa Indonesia |
| P1-07 | Menarik inti rapat: topik, keputusan, tugas, penanggung jawab, tenggat | Ada hasil terstruktur dari satu contoh rapat |
| P1-08 | Menyusun notulen internal tiga bahasa | Draf notulen internal jadi dengan tiga bahasa |
| P1-09 | Menyusun notulen eksternal tiga bahasa | Draf notulen eksternal jadi dengan tiga bahasa |
| P1-10 | Memeriksa apakah notulen eksternal bocor isi internal | Teks internal yang sengaja disisipkan terdeteksi |
| P1-11 | Memeriksa bagian Inggris, Mandarin, dan Indonesia tidak bertentangan | Perbedaan tanggal, angka, atau nama terdeteksi |
| P1-12 | Layar tinjau: ubah, pilih bahasa, setujui, riwayat versi | Setelah disetujui, notulen terkunci dan versinya tersimpan |
| P1-13 | Ekspor ke DOCX dan PDF | Kedua file bisa dibuka dengan benar |
| P1-14 | Kendali akses dasar | Yang tidak berhak tidak bisa membuka data |
| P1-15 | Uji terima tahap 1 sesuai daftar di PRD bagian 18 | Daftar uji lulus dan tercatat |

## 6. Keputusan yang sudah diambil

### Sudah diputuskan (15 Oktober 2026)

1. Penyedia layanan cloud dan wilayah server: pakai penanda sementara dulu. Pilihan sebenarnya ditunda, dan harus selesai sebelum pekerjaan menyimpan rekaman dengan aman dan mengubah suara jadi teks.
2. Fitur teks langsung dan terjemahan langsung: tidak ikut di rilis pertama. Keduanya menyusul di tahap 2 dan 3.
3. Rekaman suara mentah: tetap disimpan setelah notulen jadi, dan pengguna boleh menghapus rekamannya sendiri.
4. Bentuk ekspor notulen: per bagian berurutan, bukan dua kolom berdampingan.
5. Ambang batas angka untuk uji pilot: ditunda ke tahap 2. Di tahap 1 ukurannya sederhana saja — fiturnya ada dan terbukti bekerja.
6. Aturan persetujuan perekaman per negara: tidak dianalisis. Yang tetap ada di produk adalah penanda sedang merekam dan pemberitahuan bahwa AI memproses suara rapat, karena keduanya sudah diwajibkan.
7. Lokasi file PRD: tetap di folder utama proyek. Selisih nomor versi 2.0 di dalam dokumen dan v2.1 di nama file: salah ketik, tidak perlu diurus.

### Retensi: sudah diputuskan

Rilis pertama hanya mode berakun. Mode tanpa akun dibuang, jadi setiap rapat punya pemilik berupa akun dan datanya disimpan. Benturannya hilang sendiri: aturan privasi di PRD mengatur rapat tanpa akun, dan rapat tanpa akun tidak dibuat lagi.

Dua akibatnya. Langkah P1-14 tinggal kendali akses saja, dan daftar uji terima tidak lagi memuat butir data rapat tamu.

Angka itu sudah dipatok: rekaman disimpan 90 hari sejak diunggah, dan pemiliknya boleh menghapus lebih cepat.

### Penyimpanan dan pengenalan suara (19 Oktober 2026)

Penyimpanan rekaman memakai AWS S3, wilayah Singapura. Wilayah ini paling dekat, jadi unggah dan unduh terasa cepat, dan biayanya murah untuk ukuran rekaman rapat.

Pengubah suara jadi teks memakai Amazon Transcribe, karena satu keluarga dengan S3 sehingga rekaman tidak perlu dikirim ke pihak lain.

Pemilihan S3 dan Transcribe baru berlaku sebagai rencana. Pembuatannya menunggu kunci akses AWS. Sampai itu siap, rekaman disimpan di folder lokal komputer pengembang dan suara diubah jadi teks oleh mesin Whisper yang berjalan di komputer yang sama. Folder rekaman tidak ikut masuk ke penyimpanan kode. Penggantian ke layanan AWS nanti hanya menyentuh satu berkas untuk tiap layanan, jadi pekerjaan sekarang tidak terbuang.

## 7. Kalau tahap 1 selesai, kamu bisa apa

- Menjalankan rapat tatap muka dan mendapat rekaman yang bisa diputar ulang.
- Mendapat transkrip yang menangani Inggris, Mandarin, dan percakapan campuran.
- Membuat rapat dengan bahasa Indonesia.
- Mendapat dua notulen tiga bahasa: satu internal, satu eksternal. Kamu bisa memilih bahasa mana saja yang dipakai.
- Melihat tanda peringatan kalau notulen eksternal mengandung isi internal, atau kalau ketiga bahasa tidak sejalan.
- Mengubah dan menyetujui notulen, lalu mengunduhnya sebagai DOCX atau PDF.
- Mengakses rapat lamanya kapan saja, karena semua rapat tersimpan di akunnya.

Tahap 1 belum mencakup: mode tanpa akun (rapat tanpa login), sambungan ke Zoom,
Teams, atau Google Meet, suara terjemahan, pengiriman email otomatis, dan
analisis lintas rapat.
