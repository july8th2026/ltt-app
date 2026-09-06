#!/usr/bin/env bash
# Cai WanGP len network volume, theo DUNG cac buoc trong Dockerfile chinh chu
# cua WanGP tai SHA ghim. Khac biet duy nhat: cai vao /data (volume) thay vi
# vao anh, de no song qua moi lan xoa pod.
#
# Moi lenh deu ghi thoi gian + ma thoat => log nay CHINH LA ban nhap Dockerfile.
#
# ############################################################################
# HAI NUA, HAI TUOI THO — va do la ca goc cua su co 06/09.
#
#   NUA TAM  (o container, /usr):  python3, ffmpeg, git, cmake...  <- apt
#            MAT SACH moi lan pod khoi dong lai.
#   NUA BEN  (o volume,   /data):  venv, torch, WanGP, ckpts
#            song qua moi lan xoa pod.
#
# Nua ben PHU THUOC nua tam: `$VENV/bin/python3` la symlink TUYET DOI toi
# `/usr/bin/python3`, va venv khong bao gio chua stdlib cua chinh no.
#
# Ban dau chi co MOT cong, kiem MOT moc `_CAI_DAT_XONG` nam o nua BEN. Pod
# khoi dong lai => nua tam bay hoi, moc van con, cong bo qua cai dat, va
# `/data/venv/bin/python` thanh symlink treo. Bash bao dung cau
# "No such file or directory" cho mot symlink treo, nen loi trong nhu la
# venv da bi xoa — trong khi venv con nguyen ven tren volume.
#
# ⇒ Moi nua co cong RIENG, va ca hai cong deu kiem THU THAT (chay duoc khong)
#   chu khong kiem MOT MOC (ai do tung noi la xong).
# ############################################################################

set -u
SHA=1e1dd2757f24923f008593d9d4ec09062234be20
GOC=/data
KHO=$GOC/Wan2GP
VENV=$GOC/venv
LOG=$GOC/ket_qua/install.log

mkdir -p "$GOC/ket_qua" "$GOC/ckpts" "$GOC/hf" "$GOC/config"

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
  return 0   # khong dung ca script vi mot buoc hong — con thu thap duoc gi thi thu
}

#: Nua TAM da du chua? Kiem bang `command -v` — tuc thu chay duoc that.
co_goi_he_thong() {
  command -v python3 >/dev/null 2>&1 || return 1
  command -v ffmpeg  >/dev/null 2>&1 || return 1
  command -v git     >/dev/null 2>&1 || return 1
  return 0
}

#: Nua BEN da du chua? Ba muc, tang dan do chat:
#:   1. `-x` tren venv/bin/python  -> bat luon symlink treo (`-x` theo dich)
#:   2. kho ma nguon co .git
#:   3. NAP THAT torch + mmgp      -> bat venv cai do dang
co_moi_truong_ben() {
  [ -x "$VENV/bin/python" ] || return 1
  [ -d "$KHO/.git" ] || return 1
  "$VENV/bin/python" -c "import torch, mmgp" >/dev/null 2>&1 || return 1
  return 0
}

echo "###### CAI DAT WanGP $(date -Is)" | tee -a "$LOG"
nvidia-smi >>"$LOG" 2>&1 || echo "khong co nvidia-smi" >>"$LOG"

# --- 1. Goi he thong: y het dong `apt install` trong Dockerfile cua WanGP ---
#     Chay lai MOI lan khoi dong vi no nam o o container (tuoi tho mot phien).
if co_goi_he_thong; then
  echo "###### goi he thong da du — bo qua apt $(date -Is)" | tee -a "$LOG"
else
  echo "###### nua TAM trong — cai lai goi he thong $(date -Is)" | tee -a "$LOG"
  buoc apt_update apt-get update -qq
  buoc apt_install env DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
       python3 python3-pip python3-venv git wget curl cmake ninja-build \
       libgl1 libglib2.0-0 ffmpeg
fi

# --- 1b. Ban python cua container PHAI khop ban ma venv duoc dung ---
#     site-packages bien dich theo cp3XX. Apt doi ban minor => venv im lang
#     hong theo mot kieu KHAC, kho lan hon nhieu so voi symlink treo.
BAN_HT=$(python3 -c 'import sys; print("%d.%d" % sys.version_info[:2])' 2>/dev/null || echo "?")
BAN_VENV=$(ls -d "$VENV"/lib/python3.* 2>/dev/null | head -1 | sed 's#.*/python##')
if [ -n "${BAN_VENV:-}" ] && [ "$BAN_HT" != "$BAN_VENV" ]; then
  echo "###### ⛔ LECH BAN PYTHON: container=$BAN_HT venv=$BAN_VENV" | tee -a "$LOG"
  echo "###### venv phai dung lai tu dau — dung cai dat de khong ghi de am tham" \
    | tee -a "$LOG"
  exit 3
fi

if co_moi_truong_ben; then
  echo "###### nua BEN da du (torch+mmgp nap duoc) — bo qua $(date -Is)" | tee -a "$LOG"
  echo "###### python=$BAN_HT  HEAD=$(git -C "$KHO" rev-parse HEAD 2>/dev/null)" \
    | tee -a "$LOG"
  exit 0
fi

echo "###### nua BEN thieu — cai tiep $(date -Is)" | tee -a "$LOG"

# --- 2. Ma nguon tai SHA ghim ---
if [ ! -d "$KHO/.git" ]; then
  buoc clone git clone --quiet https://github.com/deepbeepmeep/Wan2GP.git "$KHO"
fi
buoc checkout git -C "$KHO" checkout --quiet "$SHA"
echo "HEAD=$(git -C "$KHO" rev-parse HEAD)" | tee -a "$LOG"

# --- 3. Venv tren volume => thu vien song qua moi lan xoa pod ---
if [ ! -x "$VENV/bin/python" ]; then
  buoc venv python3 -m venv "$VENV"
fi
PY="$VENV/bin/python"
buoc pip_upgrade "$PY" -m pip install -q --upgrade pip setuptools wheel

# --- 4. torch: DUNG phien ban trong Dockerfile cua WanGP (cu128) ---
buoc torch "$PY" -m pip install -q \
     torch==2.10.0+cu128 torchvision==0.25.0+cu128 torchaudio==2.10.0+cu128 \
     --index-url https://download.pytorch.org/whl/cu128

# --- 5. requirements.txt cua WanGP ---
buoc requirements "$PY" -m pip install -q -r "$KHO/requirements.txt"

# --- 6. SageAttention: y het Dockerfile, ke ca ban va phat hien GPU ---
#     8.0 = A100 theo chinh bang trong Dockerfile cua WanGP.
export TORCH_CUDA_ARCH_LIST="8.0"
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

# --- 7. Bao cao moi truong ---
"$PY" - <<'ENV' > "$GOC/ket_qua/moi_truong.json" 2>>"$LOG"
import json, platform, subprocess, sys
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
for ten, mod in (("mmgp", "mmgp"), ("sageattention", "sageattention")):
    try:
        from importlib.metadata import version
        ra[ten] = version(mod)
    except Exception as e:
        ra[ten] = "THIEU: %s" % str(e)[:60]
print(json.dumps(ra, ensure_ascii=False, indent=1))
ENV

echo "###### CAI DAT XONG $(date -Is)" | tee -a "$LOG"
du -sh "$VENV" "$KHO" >> "$LOG" 2>&1
# ⛔ KHONG con `touch _CAI_DAT_XONG`. Moc do chinh la thu da gay ra su co:
#    no khang dinh mot tinh chat cua he HAI TUOI THO ma no chi nhin thay MOT.
#    Cong o tren kiem thu that, nen khong can moc nao ca.
