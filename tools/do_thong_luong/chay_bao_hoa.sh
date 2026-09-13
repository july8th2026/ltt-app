#!/usr/bin/env bash
# chay_bao_hoa.sh — cau hoi trung tam cua VAN HANH THAT, hoi bang GuideLLM.
#
#   "He co SAU suat (3 moi model). Sau nguoi dau chay — con NGUOI THU BAY?"
#
# ## ⛔ Tep nay KHONG phai mot bo do. No la mot LOI GOI.
#
# Ngay 13-14/09 toi da hai lan tu viet bo do cho dung cau hoi nay. Ca hai lan
# deu sai, va lan hai sinh BON loi trong MOT luot chay — ca bon la loi cua
# chinh bo do. Xem VAN_HANH_THAT.md Sec.2b va BO_DO_CHUAN.md Sec.1/Sec.7.
#
# Ba thu toi tu nghi ra, GuideLLM DA CO, co tai lieu va co nguong cong bo:
#
# | toi tu viet            | GuideLLM da co                                    |
# |------------------------|---------------------------------------------------|
# | ma tran 16 kich ban    | `--profile kind=concurrent` + `--override streams` |
# | do "hang doi dang len" | `--constraint kind=over_saturation` — hoi quy      |
# |                        |   tuyen tinh tren (dong thoi, TTFT), co MOE        |
# | ham `_cham` tu viet    | `--metrics slo` -> SLO attainment + goodput       |
#
# Nguon: docs/guides/over_saturation_stopping.md va
#        docs/guides/service_level_objectives.md (vllm-project/guidellm)
#
# ## Vi sao `mode=monitor` chu KHONG `enforce`
#
# `enforce` DUNG phep do khi hang doi dang len — dung cho nguoi di tim "trần
# an toan". Ta thi NGUOC LAI: hang doi dang len o muc 9 la HANH VI DUNG cua he
# (3 suat/card, nguoi thu bay phai xep hang). Ta muon DO no, khong muon dung.
#
# ## Muc dong thoi — bam vao ranh gioi that, khong phai mot day so dep
#
#   1 -> mot minh, moc doi chung
#   3 -> DAY mot card
#   6 -> DAY ca hai card (het suat)
#   9 -> ba nguoi phai XEP HANG  <- cau hoi that nam o day
#
# ## Cham DAT/TRUOT — doc PHAN VI cua cong cu, khong viet ham cham
#
# BANG_DOI_SOAT.md Sec.7b chot cong D: >= 78 tok/s qua may A (do 13/09: 90,3).
# Voi `output_tokens=700`:  700 / 78 = 8,97 s  => nguong e2e 9,0 s.
#
# ⛔ `--metrics ...,slo=...` KHONG co trong GuideLLM **0.7.3 dang cai** — do
#    duoc: no tra `Extra inputs are not permitted (at 'metrics.generative.slo')`.
#    Tai lieu `service_level_objectives.md` nam o nhanh `main`, di TRUOC ban cai.
#    ⇒ Doc `request_latency` p95 trong JSON ra va so voi 9,0 s. Con so van do
#      bang cong cu; chi phep so sanh la cua ta.
#
# ⚠️ Va dung doi TTFT o cua nay: `/api/v1/chat/completions` TU CHOI `stream:true`
#    (BO_DO_CHUAN.md Sec.9.2). Khong stream thi khong co TTFT de do — muon TTFT
#    cua khach streaming thi do `/api/v1/responses`, do la mot cau hoi khac.
#
#    ⇒ Vi vay backend PHAI khai `stream=false` (`guidellm/backends/openai/http.py`
#      dong 134). Thieu no: GuideLLM mac dinh stream, cua tra 400, va bang ket
#      qua in ra TOAN SO 0 — mot bang **trong** trong y het mot bang da do. Do
#      duoc: 1/1 request errored, "Server Throughput 0.0 tok/s", ma van ket thuc
#      bang dong "✔ Benchmarking complete".
set -u
cd "$HOME/ltt_do"

MODEL="${1:-ltt-3.8}"
RA="${2:-700}"
VAO="${3:-256}"
MUC="${4:-1,3,6,9}"
SO="${5:-36}"
TEN="${MODEL//./}"
CONG_CAU=18099

K="$(cat .khoa)"

# ── cau noi: chen `Idempotency-Key` MOI moi luot ─────────────────────────────
# ⛔ Dung theo CONG, khong theo ten tien trinh: `pkill -f cau_idem.py` khop vao
#    chinh dong lenh `bash -c` dang chay no va tu giet minh truoc khi kip khoi
#    dong lai. BO_DO_CHUAN.md Sec.8.
fuser -k "${CONG_CAU}/tcp" 2>/dev/null || true
# Cau noi TU doc khoa tu tep va TU dat `Authorization` (cau_idem.py dong 87),
# nen khoa KHONG di qua dong lenh — no khong lot vao `ps`, vao log, hay vao
# transcript. Phien 12/09 da in nham hai bi mat vao transcript vi loi nguoc lai.
setsid .venv/bin/python cau_idem.py \
  --dich "https://app.lttstudios.com/api/v1" --cong "${CONG_CAU}" \
  --khoa-tep "$HOME/ltt_do/.khoa" \
  >cau.log 2>&1 &
echo $! >cau.pid
for _ in $(seq 1 30); do
  curl -sf "http://127.0.0.1:${CONG_CAU}/_cau/tre" >/dev/null && break
  sleep 1
done

# ⛔ `Qwen/Qwen3-8B` chi de DEM token cho prompt tong hop; no khong phai model
#    duoc goi. Model that do `--backend model=` quyet dinh.
TOK="${TOK:-Qwen/Qwen3-8B}"

.venv/bin/guidellm run \
  --backend "kind=openai_http,target=http://127.0.0.1:${CONG_CAU},model=${MODEL},api_key=${K},validate_backend=false,max_tokens=${RA},stream=false" \
  --profile kind=concurrent,streams=1 \
  --override "profile.streams" "${MUC}" \
  --data "kind=synthetic_text,prompt_tokens=${VAO},output_tokens=${RA}" \
  --tokenizer "kind=huggingface_auto,model=${TOK}" \
  --constraint "kind=max_requests,count=${SO}" \
  --constraint "kind=over_saturation,mode=monitor,min_seconds=30" \
  --output "kind=json,path=$HOME/ltt_do/baohoa_${TEN}.json" \
  --disable-progress
MA=$?

fuser -k "${CONG_CAU}/tcp" 2>/dev/null || true
exit $MA
