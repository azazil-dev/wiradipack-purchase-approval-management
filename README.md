# Purchase Approval Management (`purchase_approval_management`)

Modul custom Odoo 17 Community Edition untuk **PT Wiradi Utama Packindo** yang menambahkan alur **Purchase Request (PR)**, **multi-level approval bertingkat berbasis nominal transaksi**, **riwayat persetujuan terstruktur**, **audit trail immutable**, serta **hak akses berdasarkan struktur organisasi/jabatan**.

---

## 🌟 Fitur Utama

1. **Purchase Request (PR) Workflow**:
   - Pembuatan PR lengkap dengan penomoran sequence otomatis `PR/YYYY/NNNNN`.
   - Baris item mencakup produk, deskripsi, qty, satuan (UoM), estimasi harga, subtotal, dan saran vendor.
   - Statusbar dokumen: `Draft` → `To Approve` → `Approved` / `Rejected` → `Done` / `Cancelled`.
   - Field bisnis terkunci saat PR non-draft untuk menjaga integritas data.

2. **Multi-level Approval Berbasis Nominal**:
   - Ambang batas nominal terkonfigurasi dinamis di menu *Approval Rules* (tanpa hardcode):
     - **Di bawah Rp5.000.000**: Supervisor Approval
     - **Rp5.000.000 s/d Rp50.000.000**: Manager Approval
     - **Di atas Rp50.000.000**: Director Approval
   - Dukungan 2 mode di Pengaturan Perusahaan:
     - `Highest Only` (Default): Hanya approver tingkat tertinggi yang menyetujui.
     - `Cumulative`: Rantai persetujuan berjenjang dari Supervisor → Manager → Director.

3. **Pemisahan Tugas & Keamanan (Separation of Duties)**:
   - Pembuat permintaan (*Requester*) tidak dapat menyetujui dokumen PR miliknya sendiri.
   - Satu approver tidak dapat menyetujui lebih dari satu level pada dokumen PR yang sama.
   - Record rules departemen: Supervisor dan Manager hanya dapat melihat dan menyetujui PR dari departemennya sendiri, sedangkan Director berlaku lintas departemen.

4. **Integrasi Purchase Order (PO) & Enforcement**:
   - Pembuatan PO dari PR berstatus *Approved* via wizard yang mengelompokkan baris per vendor secara otomatis.
   - Validasi toleransi selisih nominal PO vs PR (default: 5.0%).
   - Kebijakan penegakan (*Enforcement*): Konfirmasi PO diblokir jika tidak terhubung ke PR yang telah disetujui.

5. **Approval History & Immutable Audit Trail**:
   - Setiap tindakan (*submitted, approved, rejected, revised, cancelled, reminded, escalated, po_created*) dicatat secara append-only.
   - Perubahan data (create, write, unlink) dipantau secara otomatis melalui abstract mixin audit log.
   - Catatan riwayat dan audit log tidak dapat dimodifikasi atau dihapus oleh siapapun (termasuk admin).

6. **Notifikasi & Scheduler SLA**:
   - Notifikasi email dan penjadwalan to-do activity ke approver yang sedang aktif.
   - Notifikasi email ke pemohon saat disetujui atau ditolak (wajib menyertakan alasan).
   - Pengingat harian (SLA reminder) dan eskalasi otomatis (SLA escalation) ke manajemen.

7. **Pelaporan & Cetak Dokumen**:
   - Cetak laporan formal Purchase Request dalam format QWeb PDF.
   - Analisis riwayat persetujuan berbasis tampilan Pivot dan Grafik.

---

## 👥 Pengguna & Hak Akses

Modul menyediakan 7 kelompok hak akses berjenjang:
- `group_pr_user`: Requester (Staf Pemohon)
- `group_pr_supervisor`: Supervisor
- `group_pr_manager`: Manager
- `group_pr_director`: Director
- `group_pr_purchasing`: Purchasing Officer
- `group_pr_auditor`: Internal Auditor (Read-only akses)
- `group_pr_admin`: Administrator Modul

---

## 🧪 Pengujian Otomatis

Modul ini telah dilengkapi dengan unit test otomatis berbasis `TransactionCase` yang menguji skenario alur kerja dan skenario UAT PRD:

```bash
odoo -d <database_name> -i purchase_approval_management --test-enable --test-tags /purchase_approval_management --stop-after-init
```

Cakupan pengujian:
- `test_approval_flow.py`: Pengujian skenario alur PR kecil, menengah, besar, nilai batas, penolakan, revisi, pemisahan tugas, penguncian edit, toleransi PO, dan rantai kumulatif.
- `test_approval_rules.py`: Pengujian constraint overlap dan validitas aturan nominal.
- `test_security.py`: Pengujian record rule visibilitas antar-departemen dan hak akses read-only aturan.
- `test_audit.py`: Pengujian pembentukan log audit otomatis dan sifat immutable riwayat/audit log.

---

## 📄 Lisensi

OPL-1 (Odoo Proprietary License v1.0) - PT Wiradi Utama Packindo

