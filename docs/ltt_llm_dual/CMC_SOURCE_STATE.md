# CMC_SOURCE_STATE — trạng thái hai nguồn LLM tại thời điểm bàn giao

> Tệp này do chiến dịch LTT-CMC yêu cầu (§4.6). Nó ghi **sự thật đo được**, không
> ghi ý định. Mọi con số dưới đây lấy bằng lệnh, và lệnh ghi kèm để chạy lại.

## 0. Drift so với ba ảnh chụp — và vì sao vẫn đi tiếp

Có **ba** ảnh chụp khác nhau của Source B, cả ba đều là **tổ tiên** của HEAD hiện
tại, nên nhánh chỉ **đi tiếp**, không rẽ hướng:

| Nguồn ảnh chụp | HEAD | Cách HEAD |
|---|---|---|
| `HANDOFF_LLM_DUAL.md` | `91e42b28` + 18 tệp dirty | +59 commit |
| Prompt chiến dịch | `5e33348d` + 4 tệp dirty | +25 commit |
| **Thật khi viết tệp này** | `54cac32d` — **cây sạch** | — |

Toàn bộ tệp dirty trong hai ảnh chụp nay **đã commit**. Delta thuộc đúng công
việc của phiên này (dual-model), nên theo §1 của prompt: tiếp tục từ trạng thái
thật, ghi lại delta. Đây là chỗ ghi.

⚠️ Một drift nữa: prompt ghi `Canonical main HEAD = 072d6d97`; đo được `3b5adcb7`
   (`072d6d97` là tổ tiên — main tiến một commit tài liệu).

## 1. Hình học hai dòng — thứ quyết định mọi bước sau

```
            34b4626e  "Close Scheduler V1"
             /                         56 commit                     111 commit
           /                          09b219a3  cmc-base-20260911        phien/ltt-llm-dual
      |  3
  3b5adcb7  main
```

`merge-base(phien/ltt-llm-dual, cmc-base-20260911)` = **`34b4626e`**, KHÔNG phải
tag. Tag **không** nằm trên dòng lịch sử của nhánh này.

⇒ Dựng `cmc/llm-dual-reconcile` từ tag là **port chủ ý**, không phải rebase hay
  cherry-pick. Hồ sơ handoff viết đúng điều đó từ đầu.

⚠️ Kho có **cả `main` lẫn `master`**, và `master` (`9e73bf1f`) **không** phải tổ
   tiên của `main`. `master` là nhánh cũ; mọi phép `merge-base ... master` trả
   lời sai câu hỏi. Canonical là `main`.

## 2. Source A — đã bị Source B thay thế hoàn toàn

Worktree `ltt-llm-api-http-guide-a3e123`, branch `claude/ltt-llm-multijob-audit-43efd3`,
HEAD `b3b11dbc`, 5 tệp dirty, patch-id **`2d985f9c29d7921c2085f02a5c27aaac6be991f1`**
— **trùng khít** giá trị trong `HANDOFF_LLM_DUAL.md` ⇒ cây A không đổi một byte
kể từ ảnh chụp.

| Tệp dirty của A | So với Source B | Phán quyết |
|---|---|---|
| `llm/tham_so_da_luot.py` | **0 dòng khác** | y hệt |
| `runtime_noi_bo/luong.py` | B gọi `luat_cho` ở 3 chỗ | hunk của A đã có trong B |
| `job_runner.py` | B đi xa hơn (trọng tài residency) | superseded |
| `server/api/chat.py` | A: `phong_cho` **0** lần · B: **14** | xem dưới |
| `server/api/streaming.py` | như trên | xem dưới |

Chỗ quyết định là `chat.py`. A viết thẳng trong chú thích rằng cửa này **không
chờ** vì `idempotency.begin` giữ `pg_advisory_xact_lock` suốt giao dịch. B giải
đúng bài toán ấy theo D04:

```python
db.commit()                      # chốt idempotency TRƯỚC, không giữ giao dịch
suat = cua_luong.cho_suat_dong_bo(..., han_s=cua_luong.han_cho_dong_bo(...))
```

và `cho_suat_dong_bo` (`runtime_noi_bo/luong.py:474`) gọi
`luat_cho(token_pool, lop=luat_nhan.TUONG_TAC, …)` — lease **vẫn mang lớp + phần
đặt chỗ**, đúng thứ A lo thiếu, **cộng** phần chờ mà A phải bỏ.

⇒ **Không hạng mục nào của A cần port.** A cần *seal* (commit cho cây sạch, làm
  bản ghi), không cần đưa sang.

⛔ Cũng **không có** hunk "trả busy ngay" hay "chạm provider/GPU trước admission"
   nào để loại: các dòng `execution_busy` là **ngữ cảnh đã commit**, không phải
   phần dirty.

`git cherry phien/ltt-llm-dual claude/ltt-llm-multijob-audit-43efd3` ⇒ vẫn
**8/9 patch-equivalent**, chỉ `fd9b41b3` (T3 schema) khác — con số trong hồ sơ
**vẫn đúng** sau 59 commit nữa ở B.

## 3. Vì sao máy A KHÔNG deploy được từ nhánh này — đo được, không suy

```
CSDL production : d9a1f6c2b3e5     (head của baseline CMC — Voice RC1)
alembic của ta  : a3f7c214e8b9     (rẽ TRƯỚC revision đó)
=> CommandError: Can't locate revision identified by 'd9a1f6c2b3e5'
```

Nhưng alembic chỉ là **triệu chứng**. Bản chất:

```
git rev-list --count 54cac32d..main                     ->  59 commit
git diff --name-only 54cac32d main | grep -v '^(docs|tests)/' | wc -l  ->  191 tệp
```

Trong 191 tệp có **ba migration Voice RC1** (`voice_license_va_curate`,
`voice_ngon_ngu_nguon`, `voice_lich_su`). ⇒ Deploy nhánh này lên máy A sẽ **gỡ
Voice RC1 khỏi production** cùng 56 commit khác.

⛔ Đây là lý do thứ tự của chiến dịch tồn tại. Thử đi vòng qua nó ngày 12/09 đã
   làm production **tắt ~4 phút** (19:05–19:09). Bản hỏng giữ ở
   `C:\LTTPlatform\app.that-bai-20260912-190903`; CSDL **không** bị chạm
   (alembic đổ ở bước lập kế hoạch, chưa apply gì); lăn lại bằng `app.previous`.

## 4. Đã deploy những gì — MÁY B, và chỉ máy B

| | Trước | Sau |
|---|---|---|
| `llama-swap.yaml` | 1 hồ sơ + `qwen38-vision` | `qwen38-api` + `qwen35-api` |
| `LTT_LLM_MODELS` | `qwen38-api,qwen38-vision` | `qwen38-api,qwen35-api` |
| `LTT_LLM_MAX_DONG_THOI=1` | còn (bóp 1/3 năng lực) | đã xoá |
| `LTT_HO_DUNG_CARD` / `LTT_TRA_CARD_GIAY` | còn (nhả **cả** LTT-3.5) | đã gỡ |
| `DependOnService: LTTComfyUI` | còn (R28 tự chặn) | rỗng |
| `gpu_may_b.json` trong bản cài render | **THIẾU** | có |
| mã hai cổng | cũ | mới, **hash khớp 39 tệp** |

Nghiệm thu: `GET /v1/models` → `['qwen35-api','qwen38-api']`; `/health` →
`models_mo` đúng hai, `models_la: []`, trọng tài `bat=true`.
**Rollback máy B:** `H:/LTT_LLM/releases/auto-20260912-184817`.

## 5. Sổ khoá production

| provider | trước | sau |
|---|---|---|
| `ltt_llm` | `['qwen38-api','qwen38-vision']` | `['qwen38-api','qwen35-api']` |
| `ltt_image` | — | credential **mới** (xoay token, 12/09) |

Bản rollback đầy đủ (ngoài kho): `%TEMP%\claude
ollback_so_khoa.json`.

⚠️ `ltt_llm` thiếu `qwen35-api` chính là **chặn deploy** đã nêu ở RUNBOOK §2.2
   mục 2 — nay đã gỡ.

## 6. Còn mở

1. Máy A chờ `cmc/llm-dual-reconcile` (mục 3).
2. Bí danh `ltt_llm_vision` đã cắt (D02) và hồ sơ `qwen38-vision` không còn ở máy
   B. Đọc ảnh nay là **năng lực của cả hai model** (`catalog.HO_SO`,
   `co_vision=True`, cùng nạp `mmproj`), nên đây là việc cắt **có chủ ý**, không
   phải hồi quy.
3. `LTT_RENDER_TOKEN` đã xoay ngày 12/09 vì nó **bị in ra một transcript phiên**.
   Giá trị mới sống ở `C:\ProgramData\LTTRender\gateway.env` và sổ khoá
   `ltt_image` — **không** ghi ở đây, và không ghi vào bất kỳ tệp nào trong kho.
   ⚠️ Đổi tệp ấy thôi là **chưa đủ**: `nssm` nướng cả bộ env lúc cài, và
   `render_gateway/nap_env` **cố ý không ghi đè** biến đã có ⇒ phải nướng lại
   `AppEnvironmentExtra` rồi restart. Đã làm và đã đo (token cũ → 401, mới → 200).
4. Cây chính `D:\LTTSTUDIOSAPP` có **index git hỏng** (hai lần tắt máy đột ngột).
   Đã dựng lại từ HEAD; bản hỏng giữ ở `.git/index.hong-20260912`. Cây chính hiện
   mang **6 tệp sửa dở của một phiên khác** — không đụng tới.
