#!/usr/bin/env bash
# Cai WanGP len network volume theo BO CHINH CHU cua `docs/INSTALLATION.md`:
#
#     conda create -n wan2gp python=3.11.14
#     pip install torch==2.10.0 ... --index-url .../cu130
#     pip install -r requirements.txt
#
# ############################################################################
# VI SAO DOI TU BO CU (py3.10 + torch2.10 + cu128)
#
# Bo cu duoc dung theo `Dockerfile` cua WanGP, va no chay tot cho viec SINH
# VIDEO. Nhung WanGP chi phat hanh nhan GGUF llama.cpp CUDA cho DUNG HAI bo:
#
#     torch210cu130py311   <- py3.11 · torch 2.10.0 · CUDA 13.0
#     torch271cu128py310   <- py3.10 · torch 2.7.1  · CUDA 12.8
#
# Bo cu la py3.10 + torch2.10 + cu128 => khong khop bo nao, nen log ghi
# "[GGUF][llama.cpp CUDA] kernels unavailable, using fallback". Ma bo mo rong
# prompt `Qwen3.8-27B` — thu cho phep DOC ANH de viet prompt, tuc chinh co che
# Seedance — dung trong so GGUF.
#
# Driver may chu do duoc: 580.159.04 => CUDA 13.0. Nen bo `py311/cu130` chay
# duoc tren dung card nay.
# ############################################################################
#
# ⛔ HAI NUA, HAI TUOI THO — luat cu van nguyen gia tri:
#      NUA TAM  (/usr, o container): apt — MAT moi lan pod khoi dong lai
#      NUA BEN  (/data, volume):     conda env, torch, WanGP, ckpts
#    Moi nua mot cong, va ca hai cong kiem THU THAT chu khong kiem MOT MOC.

set -u
SHA=1e1dd2757f24923f008593d9d4ec09062234be20
GOC=/data
KHO=$GOC/Wan2GP
# ⛔ `forge` chu KHONG `conda`: `/data/conda` da chua mot Miniconda tu luot
#    06/09. Dung lai duong day thi cong `[ ! -x "$CONDA/bin/conda" ]` se thay
#    "da co conda" roi BO QUA — va ta van chay dung ban dinh cong ToS vua tranh.
#    Mot cong kiem thu that van sai neu no kiem NHAM thu.
CONDA=$GOC/forge
MOI_TRUONG=$GOC/env311
LOG=$GOC/ket_qua/install.log

#: Ban Python cua bo chinh chu. `INSTALLATION.md` ghi 3.11.14.
BAN_PY=3.11.14
#: Banh xe nhan GGUF cho dung bo nay. Thieu no thi Qwen3.8 chay khong nhan.
GGUF_WHL=https://github.com/deepbeepmeep/kernels/releases/download/GGUF_Kernels/llamacpp_gguf_cuda-1.0.14+torch210cu130py311-cp311-cp311-linux_x86_64.whl

mkdir -p "$GOC/ket_qua" "$GOC/hf" "$GOC/config"

buoc() {
  local ten="$1"; shift
  local t0 t1 ma
  t0=$(date +%s)
  echo "=== [$ten] bat dau $(date -Is)" | tee -a "$LOG"
  "$@" >>"$LOG" 2>&1
  ma=$?
  t1=$(date +%s)
  echo "=== [$ten] ma_thoat=$ma giay=$((t1-t0))" | tee -a "$LOG"
  echo "{\"buoc\":\"$ten\",\"ma_thoat\":$ma,\"giay\":$((t1-t0))}" >> "$GOC/ket_qua/cai_dat.jsonl"
  return 0
}

#: Nua TAM du chua? Kiem bang `command -v` — tuc thu chay duoc that.
co_goi_he_thong() {
  command -v git    >/dev/null 2>&1 || return 1
  command -v wget   >/dev/null 2>&1 || return 1
  command -v ffmpeg >/dev/null 2>&1 || return 1
  return 0
}

#: Nua BEN du chua? Ba muc, tang dan do chat.
co_moi_truong_ben() {
  [ -x "$MOI_TRUONG/bin/python" ] || return 1
  [ -d "$KHO/.git" ] || return 1
  "$MOI_TRUONG/bin/python" -c "import torch, mmgp" >/dev/null 2>&1 || return 1
  return 0
}

echo "###### CAI DAT WanGP (bo chinh chu py3.11/cu130) $(date -Is)" | tee -a "$LOG"
nvidia-smi >>"$LOG" 2>&1 || echo "khong co nvidia-smi" >>"$LOG"

# --- 1. Goi he thong (nua TAM) — chay lai MOI lan khoi dong ---
#     KHONG cai `python3` nua: Python nay den tu conda tren volume.
if co_goi_he_thong; then
  echo "###### goi he thong da du — bo qua apt $(date -Is)" | tee -a "$LOG"
else
  echo "###### nua TAM trong — cai lai goi he thong $(date -Is)" | tee -a "$LOG"
  buoc apt_update apt-get update -qq
  buoc apt_install env DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
       git wget curl cmake ninja-build libgl1 libglib2.0-0 ffmpeg
fi

if co_moi_truong_ben; then
  echo "###### nua BEN da du (torch+mmgp nap duoc) — bo qua $(date -Is)" | tee -a "$LOG"
  "$MOI_TRUONG/bin/python" -c "import sys, torch; print('python', sys.version.split()[0], '| torch', torch.__version__, '| cuda', torch.version.cuda)" \
    | tee -a "$LOG"
  exit 0
fi

echo "###### nua BEN thieu — cai tiep $(date -Is)" | tee -a "$LOG"

# --- 2. MINIFORGE tren VOLUME => song qua moi lan xoa pod ---
#
# 🔴 VI SAO MINIFORGE CHU KHONG MINICONDA. Luot 06/09 dung Miniconda va chet o
#    buoc tao moi truong:
#
#        CondaToSNonInteractiveError: Terms of Service have not been accepted
#        for the following channels...
#
#    Kenh mac dinh cua Anaconda (`repo.anaconda.com`) nay doi chap nhan Dieu
#    khoan dich vu, va che do khong tuong tac thi tu choi thang.
#
# ⛔ KHONG tu chay `conda tos accept`. Do la nhan mot rang buoc PHAP LY thay chu
#    du an, va dieu khoan cua Anaconda con co dieu kien ve su dung THUONG MAI.
#    Miniforge mac dinh `conda-forge` — khong cong ToS, khong cau hoi giay phep,
#    va la kenh chuan cho ngan xep khoa hoc.
#
# ⭐ Hai lop phong ve, co chu y: chon Miniforge O DAY, va van truyen
#    `--override-channels -c conda-forge` o buoc sau. Lop thu hai giu dung ke ca
#    khi `$CONDA` da chua mot ban conda khac do lan cai truoc de lai.
if [ ! -x "$CONDA/bin/conda" ]; then
  buoc tai_miniforge wget -q -O /tmp/mf.sh \
       https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh
  # `-f`: ghi de thu muc san co. Can no vi luot 06/09 da kip ghi mot ban
  # Miniconda do dang vao dung duong nay truoc khi ban va toi noi. Khong co `-f`
  # thi trinh cai tu choi va ta ket o mot thu muc nua voi nua kia.
  buoc cai_miniforge bash /tmp/mf.sh -b -f -p "$CONDA"
fi

# --- 3. Moi truong Python 3.11.14, dung ban `INSTALLATION.md` ghi ---
if [ ! -x "$MOI_TRUONG/bin/python" ]; then
  # `--override-channels -c conda-forge`: noi RO kenh thay vi de conda tu chon,
  # de mot ban Miniforge cu (co con `defaults` trong cau hinh) khong keo ta tro
  # lai dung cai cong ToS vua tranh.
  buoc tao_env "$CONDA/bin/conda" create -y -p "$MOI_TRUONG"        --override-channels -c conda-forge "python=$BAN_PY"
fi
PY="$MOI_TRUONG/bin/python"
buoc pip_upgrade "$PY" -m pip install -q --upgrade pip setuptools wheel

# --- 4. torch cu130 — bo ma banh xe GGUF nham toi ---
buoc torch "$PY" -m pip install -q \
     torch==2.10.0 torchvision==0.25.0 torchaudio==2.10.0 \
     --index-url https://download.pytorch.org/whl/cu130

# --- 5. Ma nguon tai SHA ghim ---
if [ ! -d "$KHO/.git" ]; then
  buoc clone git clone --quiet https://github.com/deepbeepmeep/Wan2GP.git "$KHO"
fi
buoc checkout git -C "$KHO" checkout --quiet "$SHA"
echo "HEAD=$(git -C "$KHO" rev-parse HEAD)" | tee -a "$LOG"

buoc requirements "$PY" -m pip install -q -r "$KHO/requirements.txt"

# --- 6. SageAttention ---
# 🔴 Ban truoc gan cung `8.0` (A100). Ngay 07/09 `US-KS-2` HET A100 va ta roi
#    xuong H100 — SM **9.0**. Mot arch gan cung se bien dich cho sai card, va
#    loi do khong no luc build ma no luc CHAY.
#
# ⭐ Do tu card THAT moi la ban goc cua SageAttention: `setup.py` thuong nguon
#    VON phat hien capability tu torch. `Dockerfile` cua WanGP thay no bang mot
#    danh sach co dinh chi vi luc BUILD DOCKER khong co GPU. Tren pod thi co.
# ⛔ Do bang `nvidia-smi` chu KHONG bang torch: buoc nay chay TRUOC khi torch
#    chac chan co, va luot 06/09 da cho thay hau qua — python chua ton tai nen
#    phep do roi ve mac dinh `8.0`, trong khi card that la H100 (9.0). Mot gia
#    tri du phong IM LANG bien mot phep do thanh mot lo^i doan.
ARCH=$(nvidia-smi --query-gpu=compute_cap --format=csv,noheader 2>/dev/null | head -1 | tr -d "[:space:]")
if [ -z "${ARCH:-}" ]; then
  echo "###### ⛔ KHONG DO DUOC compute_cap — dung, khong doan" | tee -a "$LOG"
  exit 4
fi
echo "###### TORCH_CUDA_ARCH_LIST do duoc tu card: $ARCH" | tee -a "$LOG"
export TORCH_CUDA_ARCH_LIST="$ARCH"
export FORCE_CUDA=1
export MAX_JOBS=8
if [ ! -d /tmp/sageattention ]; then
  buoc sage_clone git clone --quiet https://github.com/thu-ml/SageAttention.git /tmp/sageattention
fi
cat > /tmp/patch_setup.py <<'PATCH'
import os
with open('setup.py', 'r') as f:
    content = f.read()
arch_list = os.environ.get('TORCH_CUDA_ARCH_LIST')
arch_set = '{' + ', '.join([f'"{a}"' for a in arch_list.split(';')]) + '}'
old = '''compute_capabilities = set()
device_count = torch.cuda.device_count()
for i in range(device_count):
    major, minor = torch.cuda.get_device_capability(i)
    if major < 8:
        warnings.warn(f"skipping GPU {i} with compute capability {major}.{minor}")
        continue
    compute_capabilities.add(f"{major}.{minor}")'''
new = 'compute_capabilities = ' + arch_set + '''
print(f"Manually set compute capabilities: {compute_capabilities}")'''
if old in content:
    content = content.replace(old, new)
    print("da va setup.py")
else:
    print("CANH BAO: khong tim thay doan can va — setup.py thuong nguon da doi")
with open('setup.py', 'w') as f:
    f.write(content)
PATCH
buoc sage_patch bash -c "cd /tmp/sageattention && $PY /tmp/patch_setup.py"
buoc sage_build bash -c "cd /tmp/sageattention && $PY -m pip install -q --no-build-isolation ."

# --- 7. Nhan GGUF llama.cpp CUDA — LY DO CHINH cua ca lan nang bo nay ---
buoc gguf_kernels "$PY" -m pip install -q "$GGUF_WHL"

# --- 8. Bao cao moi truong ---
"$PY" - <<'ENV' > "$GOC/ket_qua/moi_truong.json" 2>>"$LOG"
import json, platform, sys
ra = {"python": sys.version, "platform": platform.platform()}
try:
    import torch
    ra.update(torch=torch.__version__, cuda=torch.version.cuda,
              cuda_available=torch.cuda.is_available(),
              gpu=[torch.cuda.get_device_name(i) for i in range(torch.cuda.device_count())],
              sm=[list(torch.cuda.get_device_capability(i)) for i in range(torch.cuda.device_count())],
              vram_gb=[round(torch.cuda.get_device_properties(i).total_memory/1e9, 2)
                       for i in range(torch.cuda.device_count())])
except Exception as e:
    ra["torch_loi"] = str(e)
for ten, mod in (("mmgp", "mmgp"), ("sageattention", "sageattention"),
                 ("llamacpp_gguf_cuda", "llamacpp_gguf_cuda")):
    try:
        from importlib.metadata import version
        ra[ten] = version(mod)
    except Exception as e:
        ra[ten] = "THIEU: %s" % str(e)[:60]
print(json.dumps(ra, ensure_ascii=False, indent=1))
ENV

echo "###### CAI DAT XONG $(date -Is)" | tee -a "$LOG"
du -sh "$MOI_TRUONG" "$CONDA" "$KHO" >> "$LOG" 2>&1
# ⛔ KHONG co moc `_CAI_DAT_XONG`. Cong o tren kiem thu that.
