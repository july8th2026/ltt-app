# BÀN GIAO PHIÊN — LTT LLM dual-model

> Viết 12/09/2026 cuối phiên. Phiên sau **đọc tệp này**, không đọc transcript:
> transcript dài, lẫn nhiều đường cụt đã bị bác bỏ, và **có hai bí mật bị in
> nhầm vào đó**.
>
> ⛔ Mọi con số dưới đây **đo được**. Chỗ nào chưa đo thì nói rõ là chưa đo.

---

## 1. Đang đứng ở đâu

| | |
|---|---|
| Worktree | `D:\LTTSTUDIOSAPP\.claude\worktrees\ltt-video-architecture-recovery-746b24` |
| Nhánh | `cmc/llm-dual-reconcile` |
| Dựng từ | tag `cmc-base-20260911` (`09b219a3`) + trộn `phien/ltt-llm-dual` |
| Gate | **PASS** 30 PASS / 3 BOQUA / 0 FAIL tại `4bc3ea48`, `cay_da_doi_giua_chung=False` |
| Bản ghi gate | `test-results/gates/20260912T125202Z-8004.json` |
| Đã deploy | **máy B** (hai model) **và máy A** (năm migration đã apply) |

`phien/ltt-llm-dual` giữ nguyên làm **Source B đã niêm phong** — đừng sửa nó.

⚠️ **Việc gộp vào `main` là phiên riêng của chủ sản phẩm.** Không merge, không
push `main`.

---

## 2. Tài nguyên

### Máy A — chính là máy đang chạy phiên này
- Production: `C:\LTTPlatform` · công khai `https://app.lttstudios.com` · loopback `http://127.0.0.1:8100`
- Dịch vụ: `LTTStudioWeb` (uvicorn **1 tiến trình, không `--workers`**), `LTTStudioWorker`, `LTTStudioVoice`
- Rollback deploy gần nhất: `C:\LTTPlatform\app.previous`

### Máy B — `192.168.2.66`
- Vào bằng `ssh -i %USERPROFILE%\.ssh\nexus_b lengo@192.168.2.66` (đo 12/09: chạy được)
- Cổng LLM `:8299` · cổng render `:8199` · llama-swap `:8280` (**chỉ loopback trên B** — `000` từ máy A là **đúng**)
- `nssm` ở `E:\AI\ltt_render\scripts\nssm.exe`
- Rollback: `H:/LTT_LLM/releases/auto-20260912-184817`

### Hai model
| | `ltt-3.8` | `ltt-3.5` |
|---|---|---|
| id nội bộ | `qwen38-api` | `qwen35-api` |
| card | 3090 (`…b03e78`) | 5060 Ti (`…6dc1df`) |
| suất | 3 | 3 |
| `token_pool` | 221.184 | 262.144 |
| `residency_group` | **`rtx3090`** | *(không)* |
| công bố / nén / trần vào | 171.458 / 138.690 / 186.368 | 209.141 / 176.373 / 227.328 |
| giá (credit/1M) | vào 50 · ra **400** | vào 13 · ra **20** |

⇒ Chỉ `ltt-3.8` bị trọng tài cư trú 3090 chi phối. Job ảnh chặn 3.8, **không**
chặn 3.5.

---

## 3. Tài khoản thử — PHẢI XOÁ SAU

| Email | Credit | Bút toán |
|---|---|---|
| `do.haimodel@lttstudios.local` | 1000 | id 6230 |
| `canary.api@lttstudios.local` | +200 | id 6653 |

🔴 **Mật khẩu của `do.haimodel` đã bị in vào transcript phiên 12/09.** Tài khoản
này **phải xoá**, không chỉ vì dọn dẹp.

⚠️ Sổ credit là **append-only**: xoá được tài khoản và khoá, **không** xoá được
bút toán. Hai dòng nạp ở lại vĩnh viễn, đuôi `.local` để truy được.

Khoá API nằm ở thư mục scratchpad của phiên cũ ⇒ **đã mất**. Phiên mới phát lại:

```
powershell -ExecutionPolicy Bypass -File setup\khoa_thu_api.ps1 -Repo <repo> -Email <mail>
```

⛔ `-Email` là **bắt buộc**; thiếu nó PowerShell hỏi tương tác và **treo vĩnh
viễn** trong cửa sổ ẩn. `nap_credit` giới hạn `--so` trong `(0, 1000]`.

### Bí mật sống ở đâu (KHÔNG BAO GIỜ in ra)
| | |
|---|---|
| `LTT_LLM_TOKEN` | `C:\ProgramData\LTTLlm\gateway.env` (máy B) |
| `LTT_RENDER_TOKEN` | `C:\ProgramData\LTTRender\gateway.env` (máy B) — **đã xoay 12/09** vì bị lộ |
| `LTT_DATABASE_URL`, khoá mã hoá | `C:\LTTPlatform\secrets\app.env` (**chỉ Admin đọc**) |

⚠️ Lọc cấu hình phải theo **danh sách trắng từng khoá**. `findstr /B "LTT_RENDER"`
quét trúng `LTT_RENDER_TOKEN` và làm lộ nó — lọc theo tiền tố là lọc theo thứ
mình đoán.

---

## 4. Quyền

```
python tools\nang_quyen.py <script.py> [--log <tệp>]
python tools\nang_quyen.py --lenh "<dòng cmd>"
```

Máy này đặt `ConsentPromptBehaviorAdmin = 0` ⇒ nâng quyền **im lặng, không có
hộp thoại**. Đừng bảo chủ dự án "bấm Yes" — sẽ không có gì hiện lên.

⛔ **Đừng nới UAC, đừng `icacls`.** ACL ở `secrets\` và `D:\LTTBackups` là **cố
ý** (W1.5). Công cụ trên đủ để **làm việc cần quyền**; nó không dùng để **hạ mức
an toàn**.

Việc **bắt buộc** nâng quyền: đọc `app.env` · ba bước gate (`bat bien da tien
trinh`, `migration tren postgres`, `M-1 tren postgres` — thiếu quyền thì chúng
**tự bỏ qua** và gate tự khai *"KHÔNG PHẢI BẰNG CHỨNG"*) · đọc trạng thái tiến
trình dịch vụ (phiên thường trả `cpu 0%` — một **phép đo sai im lặng**) · ghi sổ
khoá · `setup\2-cai-dat.ps1`.

---

## 5. Sổ lỗi — đọc `SO_LOI_DO_TAI.md` trước khi làm gì

| mã | triệu chứng | loại | trạng thái |
|---|---|---|---|
| **L-01** | máy A gây chậm chéo **2,1–8,1×** giữa hai model | **CHẶN** | đang truy, đã loại 6 nghi can |
| L-02 | `ltt-3.5` với `max_tokens ≤ 300` → **rỗng, vẫn tính tiền** | ĐỘC LẬP | chờ |
| L-03 | `ltt-3.8` khai *"Text only"* dù engine **đã nạp `mmproj`** | ĐỘC LẬP | chờ |
| L-04 | bộ chấm `bia-01` cấm chuỗi tiếng Việt, model trả lời tiếng Anh → **điểm đúng giả** | ĐỘC LẬP | chờ |

### L-01 — đã loại trừ được gì (đừng đo lại)
```
qua máy A (Cloudflare)     1,93× / 6,20×
qua máy A (loopback 8100)  2,09× / 8,11×   ⇒ KHÔNG phải Cloudflare
THẲNG máy B                0,85× / 1,05×   ⇒ hai GPU ĐỘC LẬP — kiến trúc ĐÚNG
nén bằng tài khoản khác    7,15× / 2,36×   ⇒ KHÔNG phải khoá advisory theo tài khoản
máy B /health              phục vụ 170 · từ chối 0, mọi bộ đếm chặn = 0
máy B GPU                  đúng card sáng, VRAM ổn định, CPU-B 9–27%
máy A pid nghe 8100        cpu 6–14%, luồng 8→15, kết nối 8→12 ⇒ luồng đang CHỜ
```
**Còn lại để truy:** pool kết nối CSDL (`platform_core/db.py` **không đặt
`pool_size`** ⇒ mặc định 5 + 10 tràn), khoá advisory theo *tài nguyên*, hoặc một
chỗ tuần tự hoá khác trong `server/api/chat.py`.

---

## 6. Quy trình chủ sản phẩm đã chốt

1. Thấy lỗi → **nghiên cứu** (tài liệu model, cộng đồng, mã nguồn mở) → sửa →
   deploy → **test lại** → pass mới sang hạng mục sau.
2. Phân loại **CHẶN** (làm các phép đo sau mất giá trị ⇒ sửa ngay) và **ĐỘC LẬP**
   (ghi sổ, chạy tiếp, sửa theo lô). Giữ "không bỏ qua lỗi" mà không phải deploy
   25 lần.
3. Deploy theo lô, **máy B đi trước** (rẻ gấp mười lần máy A).
4. **Điều kiện dừng:** hai vòng liên tiếp cho kết quả trùng khớp. Khác nhau ⇒ có
   thứ không tất định, và *thứ đó* mới là lỗi cần truy.
5. **Mỗi bản sửa phải có ĐỐI CHỨNG** mới được gọi là đã sửa: mã cũ đỏ, mã mới
   xanh. Không có đối chứng thì "đã sửa" chỉ là một lời tuyên bố.
6. Nghiên cứu tài liệu **sau khi khoanh vùng bằng phép đo**, không trước.

---

## 7. Bộ đo

`tools/do_tai_hai_model.py --khoa <tệp khoá> --pha {1,2}`

Ba nguyên tắc: đáp án là **sự kiện** · **đối chứng ở đầu** (trượt ⇒ *bộ đo hỏng*,
không phải model kém) · **rỗng ≠ sai** (tách ba trạng thái).

### Đã chạy
| | Kết quả |
|---|---|
| Pha 1 — 7 câu × 2 model | **14/14 đúng** (trừ L-04 là điểm đúng giả ⇒ thực chất **13/14**) |
| Trung vị lúc rảnh | `ltt-3.8` **3,2 s** · `ltt-3.5` **7,2 s** |
| Pha 2 — 6 lượt cùng lúc (3/model) | **6/6 đúng**, 21,2 s |

### Chưa chạy
S2.1–2.2 (lấp suất, lượt thứ 4 chờ) · S3.1–3.3 (hàng đợi 9 và 12 job, 429 +
`Retry-After`) · S4.1–4.5 (text dài ~150K, **hai lượt dài bị chặn bởi
`token_pool` chứ không phải suất**, vượt trần → 413) · S5.1–5.3 (job ảnh chiếm
3090 → 3.8 chờ, **3.5 không ảnh hưởng**) · S6.1–6.7 (huỷ, ngắt, tên đã cắt →
`model_not_found`, idempotency, tuyến Desktop, đọc ảnh cả hai model).

---

## 8. Mười cái bẫy đã cắn thật trong phiên 12/09

1. **Cloudflare trả `403` mã `1010`** cho User-Agent mặc định của `urllib`. Phải đặt UA.
2. **`/api/v1` đòi `Idempotency-Key`** — thiếu là `400`. Mỗi lượt đồng thời phải có khoá **riêng**, nếu không sáu lượt bị gộp thành một.
3. **`ltt-3.5` cần `max_tokens ≳ 600`** — `--reasoning-budget 512` ăn hết trước khi có chữ nào.
4. **Gate là phán quyết, không phải chẩn đoán.** Vòng lặp: hẹp → cụm → `--doi` → full gate **một lần**. Phiên 12/09 tốn 3–4 tiếng vì dùng full gate (12–16 ph/lượt) làm dụng cụ chẩn đoán.
5. **Deploy chỉ từ cây chính**, hoặc từ **bản chép thuần không có `.git`** (`git archive` — đường script tự mở). Deploy từ cây riêng bị chặn.
6. **Máy A không deploy được từ `phien/ltt-llm-dual`**: nhánh đó thiếu 59 commit gồm **ba migration Voice RC1** ⇒ sẽ gỡ Voice khỏi production. Đã thử và production **tắt 4 phút**.
7. **Bash nuốt backslash** trong heredoc và cả dòng lệnh thường. Dùng gạch xuôi, `chr(92)`, hoặc công cụ Write.
8. **cp1252 giết công cụ** ở một emoji. Luôn đặt `PYTHONIOENCODING=utf-8`.
9. **`nssm` nướng cả bộ env lúc CÀI**, và `render_gateway/nap_env` **cố ý không ghi đè** (ngược hẳn cổng LLM nơi *tệp thắng*). Đổi `gateway.env` rồi restart là **không đủ** — phải nướng lại `AppEnvironmentExtra`.
10. **Hỏi sai tiến trình.** Phiên thường tìm ra `pid 32`; tiến trình thật nghe 8100 là `pid 7696`, và chỉ đọc được khi nâng quyền. Một phép đo sai im lặng.

---

## 9. Hai bài học quy trình đắt nhất của phiên

**Một ghi chú tự khai là "đã đo" vẫn có thể sai, và khi sai thì nó đắt hơn không
có ghi chú** — nó làm người sau tin câu hỏi đã được trả lời rồi đi tìm chỗ khác.
Phép đo rẻ nhất để bác bỏ: dựng cây tạm ở điểm rẽ nhánh (`git worktree add
--detach <tmp> $(git merge-base HEAD main)`) rồi chạy đúng ca đó — **4 giây**.

**Một giả thuyết khớp quá vừa là lúc phải nghi nhất.** L-01: "khoá advisory theo
tài khoản" có cả dòng mã đúng hình dạng; đối chứng bằng tài khoản thứ hai bác bỏ
nó. Nếu sửa theo giả thuyết ấy thì đã **sửa nhầm chỗ và tin là xong**.
