#!/usr/bin/env bash
# Diem vao cua Pod — che do PHUC VU (Phase E), khong con che do do mot lan.
#
# Ban truoc ket thuc bang `sleep 120` roi thoat. Container het entrypoint thi
# RunPod khoi dong lai pod => vong lap hai phut. Do la HANH VI DUNG cua mot
# script do mot lan, nhung sai voi mot dich vu. Nay ket thuc bang `wait` tren
# tien trinh dich vu: pod song chung nhip voi dich vu, khong dai hon.
set -u
export DEBIAN_FRONTEND=noninteractive
GOC=/data

# ═══ Moi truong lay TU `entrypoint.sh` CHINH CHU cua WanGP ═══════════════════
#
# 🔴 Ban dau toi tu viet diem vao nay va chi dat `HF_HOME`. WanGP CO
#    `entrypoint.sh` rieng, va no dat chin bien nua — trong do hai bien bat
#    TF32 tren Ampere, tuc thang vao toc do matmul cua A100 (SM 8.0).
#    Phep do 79,8 giay/buoc ngay 06/09 chay THIEU chung.
#
# ⭐ Khac biet duy nhat co chu y: `HF_HOME` tro vao volume thay vi
#    `/home/user/.cache`, vi o container bien mat moi lan khoi dong lai.
export PYTHONUNBUFFERED=1
export HF_HOME=$GOC/hf

export OMP_NUM_THREADS=$(nproc)
export MKL_NUM_THREADS=$(nproc)
export OPENBLAS_NUM_THREADS=$(nproc)
export NUMEXPR_NUM_THREADS=$(nproc)

export TORCH_ALLOW_TF32_CUBLAS=1
export TORCH_ALLOW_TF32_CUDNN=1

# Tat canh bao am thanh trong container — y het WanGP
export SDL_AUDIODRIVER=dummy
export PULSE_RUNTIME_PATH=/tmp/pulse-runtime
# ════════════════════════════════════════════════════════════════════════════
LOG=$GOC/ket_qua/khoi_dong.log
mkdir -p "$GOC/ket_qua" "$GOC/hf" "$GOC/config"

echo "### KHOI DONG $(date -Is)  pod=${RUNPOD_POD_ID:-?}" | tee -a "$LOG"

# --- 1. Tu lanh. Cong ben trong kiem THU THAT nen goi moi lan la an toan ---
bash "$GOC/lttv/cai_dat.sh" 2>&1 | tee -a "$LOG"

PY=$GOC/env311/bin/python
if [ ! -x "$PY" ]; then
  echo "### ⛔ KHONG CO PYTHON SAU KHI CAI — dung, khong phuc vu" | tee -a "$LOG"
  echo "khong-co-python $(date -Is)" > "$GOC/ket_qua/_LOI_KHOI_DONG"
  sleep 900          # giu pod song du lau de doc log ve, roi tu tat
  exit 1
fi

# --- 2. Thu vien cho lop HTTP. WanGP keo fastapi theo, uvicorn thi khong chac ---
if ! "$PY" -c "import uvicorn, fastapi" >/dev/null 2>&1; then
  echo "### cai uvicorn+fastapi $(date -Is)" | tee -a "$LOG"
  "$PY" -m pip install -q uvicorn fastapi >>"$LOG" 2>&1
fi

# --- 3. Khoa chia se. KHONG nam trong ma nguon, KHONG nam trong bien pod ---
#     Bien moi truong cua pod hien ra trong `GET /pods/{id}` cua REST API;
#     tep tren volume thi khong. Day la khoa truy cap job/media ngan han —
#     dung loai ma C-CLOUD DUOC PHEP giu (`Phan 7` cua ban khoa security).
if [ -f "$GOC/config/lttv_key.txt" ]; then
  LTTV_WANGP_KEY=$(tr -d '[:space:]' < "$GOC/config/lttv_key.txt")
  export LTTV_WANGP_KEY
else
  echo "### ⛔ THIEU /data/config/lttv_key.txt — dich vu se tu choi moi lenh" \
    | tee -a "$LOG"
fi

export LTTV_WANGP_ROOT=$GOC/Wan2GP
export LTTV_PROFILE=${LTTV_PROFILE:-1}
export LTTV_ATTENTION=${LTTV_ATTENTION:-sage2}

#: `--compile` — bat theo dung `run-docker-cuda-deb.sh` chinh chu cua WanGP, va
#: dung theo vi du "Best Performance" cua `docs/CLI.md:225`
#: (`--compile --attention sage2 --profile 3`). Can Triton, thu theo torch tren
#: Linux. Doi lai: lan sinh DAU TIEN sau moi lan khoi dong phai bien dich.
#: ⚠️ De TAT o lan do dau tien de tach bach hai thay doi; bat len o `E2` roi
#:    do A/B. Mot phep do doi HAI thu cung luc khong tra loi duoc thu nao.
export LTTV_COMPILE=${LTTV_COMPILE:-0}

#: ⛔ `--perc-reserved-mem-max` CHUA dat, co chu y: hai nguon cua chinh WanGP
#:    mau thuan nhau — `docs/CLI.md:156` ghi "< 0.5", con
#:    `run-docker-cuda-deb.sh` truyen `1`. Khong sao chep mu ben nao; do roi
#:    moi chot.

# --- 4. Phuc vu. 8888 vi do la cong DUY NHAT pod nay mo ra ngoai ---
cd "$GOC/lttv" || exit 1
echo "### PHUC VU tren 8888  profile=$LTTV_PROFILE $(date -Is)" | tee -a "$LOG"
date -Is > "$GOC/ket_qua/_DICH_VU_BAT_DAU"
"$PY" -m uvicorn dich_vu_ccloud:app --host 0.0.0.0 --port 8888 \
  >>"$GOC/ket_qua/dich_vu.log" 2>&1 &
DV=$!
echo "pid=$DV" | tee -a "$LOG"

# `wait` chu khong `sleep`: dich vu chet thi entrypoint ket thuc va ta THAY,
# thay vi mot pod con song ma khong con phuc vu gi.
wait $DV
ma=$?
echo "### DICH VU DUNG ma_thoat=$ma $(date -Is)" | tee -a "$LOG"
exit $ma
