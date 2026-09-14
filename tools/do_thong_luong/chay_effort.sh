#!/usr/bin/env bash
# chay_effort.sh — `reasoning_effort` dat them bao nhieu? Do bang GuideLLM.
#
# ## Cau hoi, va NUA nao cua no tep nay tra loi duoc
#
# Chu du an hoi 14/09: *"nen de medium hay xhigh"*. Cau ay co HAI nua:
#
#   chi phi  (token, do tre, thong luong)  -> GuideLLM tra loi duoc  <- TEP NAY
#   chat luong (tra loi co tot hon khong)  -> GuideLLM KHONG tra loi duoc
#
# ⛔ GuideLLM khong cham diem cau tra loi. Thu gan nhat no co la SLO attainment,
#    va do cung chi la mot nguong THOI GIAN. Dung no de ket luan ve chat luong
#    la do lech chieu — so tay du an goi do la phep do phai BO, khong phai sua.
#
# ⇒ Nua chat luong di bang `tools/danh_gia_llm.py`, la thu DUY NHAT trong kho
#   cham diem, va la thu da sinh ra bang 12/09 trong `llama-swap.yaml` ma ta
#   dang dua vao. Hai nua, hai cong cu, moi cai tra loi dung cau cua no.
#
# ## Vi sao khong sua `chay_bao_hoa.sh`
#
# Cai kia tra loi cau "he co xep hang dung khong". Cai nay tra loi "mot muc
# effort dat them bao nhieu". Tron hai cau vao mot tep la lam ca hai kho doc.
#
# ## Ket qua doc thang o dau
#
# `output_tokens` trung binh noi model NGHI + TRA bao nhieu; `request_latency`
# noi khach cho bao lau. So hai lan chay chi khac MOT bien.
set -u
cd "$HOME/ltt_do"

MODEL="${1:-ltt-3.8}"
MUC="${2:-medium}"
SO="${3:-8}"
VAO="${4:-256}"
RA="${5:-1400}"
TEN="${MODEL//./}"
CONG_CAU=18099

K="$(cat .khoa)"

fuser -k "${CONG_CAU}/tcp" 2>/dev/null || true
setsid .venv/bin/python cau_idem.py \
  --dich "https://app.lttstudios.com/api/v1" --cong "${CONG_CAU}" \
  --khoa-tep "$HOME/ltt_do/.khoa" >cau.log 2>&1 &
echo $! >cau.pid
for _ in $(seq 1 30); do
  curl -sf "http://127.0.0.1:${CONG_CAU}/_cau/tre" >/dev/null && break
  sleep 1
done

TOK="${TOK:-Qwen/Qwen3-8B}"

# ⭐ `extras.body` la cho GuideLLM chen truong RIENG cua ta vao than request
#    (`guidellm/schemas/request.py`). Khong co no thi khong dat duoc
#    `reasoning_effort`, va hai lan chay se khac KHONG bien nao.
.venv/bin/guidellm run \
  --backend "{\"kind\":\"openai_http\",\"target\":\"http://127.0.0.1:${CONG_CAU}\",\"model\":\"${MODEL}\",\"api_key\":\"${K}\",\"validate_backend\":false,\"max_tokens\":${RA},\"stream\":false,\"extras\":{\"body\":{\"reasoning_effort\":\"${MUC}\"}}}" \
  --profile kind=concurrent,streams=1 \
  --override "profile.streams" 3 \
  --data "kind=synthetic_text,prompt_tokens=${VAO},output_tokens=${RA}" \
  --tokenizer "kind=huggingface_auto,model=${TOK}" \
  --constraint "kind=max_requests,count=${SO}" \
  --output "kind=json,path=$HOME/ltt_do/effort_${TEN}_${MUC}.json" \
  --disable-progress
MA=$?

fuser -k "${CONG_CAU}/tcp" 2>/dev/null || true
exit $MA
