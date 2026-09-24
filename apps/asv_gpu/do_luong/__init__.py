"""Nang luc DO LUONG bang model cua Auto Scan Video (ASV final, 22/09/2026).

Moi bo do o day tra loi MOT cau hoi bang MOT model/cong cu da thanh danh, co
license code + license weights da xac minh
(`docs/auto_scan_video_final/OPEN_SOURCE_METRIC_AUDIT.md`,
`THIRD_PARTY_METRICS.md`).

## Vi sao nam o `asv_gpu` chu khong o `auto_scan_video`

Model chay tren card, trong mot venv RIENG (`C:\\LTTPlatform\\qc-venv`,
`setup/cai_qc_models.ps1`) — dung khuon `whisperx-venv`/`vieneu-venv`: worker
khong nap torch GPU, no goi mot TIEN TRINH CON qua `venv.chay`. `asv_gpu` la
executor khai `requires=("gpu",)` trung thuc cua ASV, nen day la cho card duoc
nen tang cap (`gpu_lease`) va ghim vao tien trinh con.

⛔ Khong model nao tai ve thu muc ma nguon. Weights nam o `HF_HOME`
   (`C:\\LTTPlatform\\hf-cache`), co ban ghim (revision) va checksum.

⛔ Thieu venv / thieu model ⇒ `KhongKhaDung`. Nguoi goi danh dau muc QC do la
   `khong_kha_dung`; KHONG lui ve mot cong thuc tu che de chuoi "xanh".
"""
