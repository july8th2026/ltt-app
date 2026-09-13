#!/usr/bin/env bash
# chay_guidellm.sh — do cong D/E bang GuideLLM, KHONG bang script tu viet.
#
# ## Vi sao doi cong cu
#
# Bo do tu viet cua phien nay noi doi ve production bon lan:
#   - lay thoi gian NAP MODEL vao mau so cua C1 -> "scaling 3,93x" cho 3 slot
#   - gioi han 2 ket noi/host cua .NET -> 3 luot "dong thoi" thanh 2+1
#   - cho chu `done` tren API trong khi API tra `succeeded`
#   - dem `hold` tren so ghi kep thanh "khoan treo"
#
# Bon loi ay deu la loi ma mot bo do CHUAN da giai xong tu lau. GuideLLM
# (vllm-project) do dung cac dai luong nganh dung: TTFT, ITL, TPOT, thong luong,
# phan vi — va no quan ly dong thoi bang mot bo lap lich dung dan.
#
# ## Rang buoc cua ta, do duoc chu khong doan
#
#   - `uvloop` KHONG chay tren Windows  => GuideLLM phai chay trong WSL
#   - WSL co Python 3.14, GuideLLM doi 3.10-3.13 => dung `uv` lay dung 3.13
#   - `Idempotency-Key` KHONG bat buoc  => cong cu chuan ban thang vao duoc
#   - Cloudflare KHONG chan httpx       => do duoc qua duong cong khai
#   - `validate_backend` mac dinh hong voi API cua ta (no dung `api_routes`
#     rong) => tat no; do la mot buoc chao hoi, khong phai phep do
#
# ## San `max_tokens` (L-02) rang buoc de bai
#
# `ltt-3.8` san 64, `ltt-3.5` san 1024 o muc `medium`. Ta dat
# `reasoning_effort=none` (san 64 cho ca hai) va `output_tokens` 700 — tren san,
# va du dai de phan decode ap dao phan prefill.

set -u
cd "$HOME/ltt_do"

MODEL="${1:-ltt-3.8}"
RA="${2:-700}"
VAO="${3:-256}"
SO="${4:-12}"
TEN="${MODEL//./}"

K="$(cat .khoa)"

# ⛔ `Qwen/Qwen3-8B` chi de DEM TOKEN khi dung prompt tong hop; no khong phai
#    model duoc goi. Model that do `--backend model=` quyet dinh. Neu bo dem cua
#    no lech voi bo dem that thi `prompt_tokens` de bai se lech — va do la ly do
#    bao cao duoi day IN CA `prompt_tokens` may chu DEM DUOC de doi chieu.
TOK="${TOK:-Qwen/Qwen3-8B}"

exec .venv/bin/guidellm run \
  --backend "kind=openai_http,target=https://app.lttstudios.com/api/v1,model=${MODEL},api_key=${K},validate_backend=false,max_tokens=${RA}" \
  --profile kind=concurrent,streams=1 \
  --override "profile.streams" 1,3 \
  --data "kind=synthetic_text,prompt_tokens=${VAO},output_tokens=${RA}" \
  --tokenizer "kind=huggingface_auto,model=${TOK}" \
  --constraint "kind=max_requests,count=${SO}" \
  --output "kind=json,path=$HOME/ltt_do/kq_${TEN}.json" \
  --disable-progress
