#!/usr/bin/env bash
# Diem vao cua Pod. Chay khong nguoi: cai -> do -> danh dau xong.
# Moi thu ghi ra /data (network volume) nen song qua lan xoa pod.
set -u
export DEBIAN_FRONTEND=noninteractive
export HF_HOME=/data/hf
mkdir -p /data/ket_qua /data/hf /data/config
echo "### KHOI DONG $(date -Is)" | tee -a /data/ket_qua/khoi_dong.log
echo "pod=${RUNPOD_POD_ID:-khong-ro}" | tee -a /data/ket_qua/khoi_dong.log

bash /data/lttv/cai_dat.sh 2>&1 | tee -a /data/ket_qua/khoi_dong.log

if [ -x /data/venv/bin/python ]; then
  echo "### BAT DAU DO $(date -Is)" | tee -a /data/ket_qua/khoi_dong.log
  cd /data/Wan2GP && /data/venv/bin/python /data/lttv/do_luong.py 2>&1 \
    | tee -a /data/ket_qua/khoi_dong.log
else
  echo "### KHONG CO VENV — cai dat that bai, bo qua buoc do" \
    | tee -a /data/ket_qua/khoi_dong.log
fi

echo "### KET THUC $(date -Is)" | tee -a /data/ket_qua/khoi_dong.log
date -Is > /data/ket_qua/_POD_XONG
# giu tien trinh song them 10 phut de con doc log neu can, roi tu tat
sleep 600
