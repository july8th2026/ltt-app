# PROMPT AI — giao thức điều hướng agent

Chốt 26/09/2026. Vai của điều phối, model cho từng làn, khuôn lời nhắc, và danh
sách soát trước khi gửi. ⛔ Chưa thi hành — chờ chủ dự án chốt plan.

Nguồn: [`../superpowers/plans/2026-09-26-prompt-ai-TONG.md`](../superpowers/plans/2026-09-26-prompt-ai-TONG.md) ·
luật agent + khoá máy: `CLAUDE.md` toàn cục mục ⭐ *Chạy agent + tiết kiệm quota*.

---

## 1. Vai của điều phối — bốn việc, không việc nào uỷ được

| # | Việc | Nghĩa là |
|---|---|---|
| Đ-1 | **Phân việc** | Một agent **một làn**, không một agent nhiều pha. Một tệp **một chủ** |
| Đ-2 | **Chọn model** | Theo §2. Sai chiều nào cũng đắt: Opus cho việc cơ học là đốt quota; Sonnet cho việc sổ sách là đốt tiền khách |
| Đ-3 | **Soát lời nhắc** | Theo §4, **trước khi gửi**. Lời nhắc là thứ duy nhất agent có — thiếu một dòng là nó tự đoán |
| Đ-4 | **Nắn khi lệch** | Theo §5. Agent im lặng không có nghĩa là đang làm việc |

### 1.1 ⛔ Việc điều phối KHÔNG uỷ cho agent

| Việc | Vì sao |
|---|---|
| **Chạy gate** | Gate là phán quyết, không phải phép dò lỗi. Một gate mỗi nhánh, và lượt gate bị ngắt để lại khoá sống |
| **Đổi biến môi trường production** (`LTT_PROMPT_AI_OMMI_ROLLOUT`) | Máy này là production, và `nssm get` **lộ bí mật**. Chỉ chủ dự án |
| **Deploy** | Xuất HEAD cây chính ⇒ mang theo commit của **mọi phiên** |
| **Giải xung đột merge trên tệp dùng chung** | 5 tệp test liên-app là lưới của phiên khác |
| **Quyết định spec hở** | Agent báo về, điều phối phán quyết và vá spec. Agent tự quyết ⇒ 5 tác giả 5 hướng |
| **Hạ mốc bánh cóc** (`check_so_test.py --accept`) | Chỉ giảm, và không khi còn sửa dở của người khác |

---

## 2. Model cho từng làn — và lý do

**Luật chốt:** `sonnet` khi **plan đã có mã** và **test quyết định đúng/sai**;
`opus` khi sai **khó đảo** hoặc chạm **tiền / bảo mật / app đang sống / tệp dùng chung**.

| Làn | Pha | Model | Vì sao |
|---|---|---|---|
| **M₁** | 1 | `sonnet` | Tách package + migration + khai cạnh. Cơ học, plan có mã, `alembic heads` và lint quyết định |
| **A** | 1 | `sonnet` | `services/bindings.py` — plan có mã đủ, 3 tệp test quyết định luật đánh số |
| **B₁** | 1 | **`opus`** | Vá **N-1** + bất biến 5 điều kiện. Đây là con bọ trung tâm; sửa nửa vời thì **vứt trường im lặng lần hai** |
| **B₂** | 2 | **`opus`** | Chạm `apps/taovideo` — app **`lifecycle="released"`** đang phục vụ. Cộng enum đóng + `idempotency.key_fields` |
| **M₃** | 3 | `sonnet` | Migration 7 bảng + `canh_id`. Cơ học, test schema quyết định |
| **C** | 3 | `sonnet` | `placeholders`/`bundle`/`briefs` — plan có mã, 6 tệp test quyết định |
| **D** | 3 | **`opus`** | **Sổ tiền.** Lượt miễn phí, giữ chỗ/quyết toán, `rejected` không hoàn. Sai một nhánh là mất tiền khách hoặc LLM miễn phí vô hạn |
| **E** | 3 | **`opus`** | **Xoá một app** + mổ **10 tệp test, 26 chỗ**, trong đó 5 tệp liên-app dùng chung. Thao tác khó đảo |
| **M₄** | 4 | `sonnet` | `share_level` × 10 bảng + 6 bảng mới. Cơ học |
| **F** | 4 | `sonnet` | Chia sẻ bằng mã. Plan có mã; test quyết định (`revoked`, `catalog` chỉ admin) |
| **G** | 4 | `sonnet` | Xuất dữ liệu từ kho **CHỈ ĐỌC** + nhập idempotent. Cơ học, nhưng lời nhắc phải có rào cứng §4.2 |
| **M₅** | 5 | `sonnet` | Migration pha 5. ⛔ **Task GATE cuối cùng là của điều phối**, không của agent |
| **H** | 5 | **`opus`** | **Bảo mật**: zip-slip, zip-bomb, dedupe theo `(owner_id, file_hash)`. Sai là lỗ thật |
| **I** | 5 | `sonnet` | `composite`/`breakdown`. Plan có mã; test số cảnh quyết định |
| **J** | 3–5 | **`opus`** | Frontend + **nghiệm thu bằng trình duyệt thật** trên `app.lttstudios.com`. Phán đoán giao diện, không có test nào thay được |

**Đếm:** 9 làn `sonnet`, 6 làn `opus`. Và **1 Task** (gate) do điều phối tự chạy.

⚠️ Đây là **mức khởi đầu**, không phải khoán cứng. Một làn `sonnet` báo về ba lần
liên tiếp *"spec mâu thuẫn"* ⇒ nâng lên `opus` và soát lại lời nhắc: nguyên nhân
thường ở **lời nhắc thiếu**, không ở model yếu.

---

## 3. Thứ tự dispatch — bao nhiêu làn cùng lúc

Số làn = số việc **độc lập**, không trần cố định. Nhưng **một lượt nặng một lúc trên
toàn máy** (`cpu_nhieu`) ⇒ mọi agent đi qua
`python "C:\Users\Thang Tuong\.claude\ltt\chay_nang.py" --phien <làn> -- <lệnh>`, `-n ≤ 7`.

### 3.1 🔴 ⛔ KHÔNG bọc `pytest` trong `chay_nang.py` — đó là tự khoá chính mình

Đã xảy ra thật 26/09 và mất một buổi để khoanh.

`tests/conftest.py` **tự xin `cpu_nhieu`** khi lượt có **≥ 20 tệp** test
(`_NGUONG_TEP_NANG = 20`), và nó làm đúng hơn lớp bọc: xin **sau khi thu thập**, vì
chỉ lúc đó mới biết lượt to hay nhỏ. Nó bỏ qua nếu **tổ tiên** đã xin hộ — danh sách
ở `tools/test_nhanh.py::to_tien_da_giu_khoa`.

```
chay_nang.py giu cpu_nhieu
  └─ pytest (>= 20 tep)
       └─ conftest xin cpu_nhieu  ->  CHO MAI mot khoa TO TIEN dang giu
```

Khoá là tệp `O_EXCL`, ⛔ không tái nhập, nên nó **không bao giờ tự thoát**.

⚠️ **Vì sao rất dễ đuổi sai:** nó CHỈ nổ khi ≥ 20 tệp. Đo cùng ngày: **12 tệp XANH ·
18 tệp XANH · 26 tệp CHẾT**. Nên mọi lượt nhỏ đều "chứng minh" mã đúng. Và triệu chứng
giống mọi thứ khác: treo vô hạn, **CPU bằng 0**, tái hiện được với giây CPU gần y hệt
mỗi lần — vì luôn dừng ở **cùng một điểm chặn**, ⛔ không phải vì cùng một con bọ.

| Lệnh | Bọc `chay_nang`? |
|---|---|
| `pytest` (mọi số tệp) | ⛔ **KHÔNG** — nó tự lấy khoá |
| `pre-commit run --all-files` | ✅ có |
| `npm run build`, cargo, tauri | ✅ có |
| script đo của riêng mình | ✅ có |

⭐ **Cách bắt trong một lệnh:** lúc "treo", chạy `python tools/cua_so_yen.py trang-thai`
từ **shell khác**. Nếu người giữ khoá **chính là lượt của mình** ⇒ tự khoá, ⛔ không
phải con bọ.

⛔ **Và đừng chuyển hướng/nối đầu ra khi đang chẩn đoán treo.** `cua_so_yen` IN ra
`xep hang N phut - cpu_nhieu: <ai>` — đúng những dòng nói ra nguyên nhân. Điều phối mất
chúng **hai lần**: một lần vì `| grep | tail` (`tail` giữ tới khi tiến trình chết), một
lần vì `> tệp` (Python đệm stdout). Dùng `PYTHONUNBUFFERED=1` + `-u`.

✅ Đã vá 26/09: thêm `"chay_nang.py"` vào `to_tien_da_giu_khoa`, kèm `test_5104`. Nhưng
brief **vẫn phải ghi luật này** — bản vá chỉ đỡ được khi agent chạy trong cây đã có nó.

| Lô | Gửi cùng lúc | Chờ gì |
|---|---|---|
| 1 | **M₁** | — |
| 2 | **A** | M₁ xong (cần `ommi_binding` + `tables/`) |
| 3 | **B₁** | A xong (cần `list_bindings`) |
| — | *điều phối gộp `main`, báo* | |
| 4 | **B₂** | B₁ xong (cần `bat_bien_giao_bai`) |
| — | *gộp `main` · deploy pha 2* | |
| 5 | **M₃** | — |
| 6 | **C** ∥ **E** | M₃ xong. Hai làn khác tệp hoàn toàn |
| 7 | **D** | C1–C6 xong (cần `bundle.dung_bundle`) |
| 8 | **C7** rồi **D2** | D1 xong — ⚠️ xem §6 lỗi `LUOT_MIEN_PHI` |
| 9 | **J** | C, D, E xong (cần endpoint thật) |
| — | *gộp `main` · deploy pha 3* | |
| 10 | **M₄** → **F** → **G** | tuần tự (G cần `share_level` của F) |
| 11 | **M₅** → **H** ∥ **I** | H và I khác tệp |
| — | *điều phối: gate MỘT lần · deploy · báo* | |

⛔ Không bao giờ gửi hai làn sửa **cùng một tệp**. Cần tệp của làn khác ⇒ đọc
`Interfaces` của Task đó và **chờ**.

---

## 4. Khuôn lời nhắc — 12 mục, thiếu mục nào là agent tự đoán

Mọi brief thi hành **phải** có đủ 12 mục dưới đây, theo đúng thứ tự này.

| # | Mục | Nội dung |
|---|---|---|
| 1 | **Vai + giới hạn** | *"Bạn thi hành **đúng Task N..M** của làn X. ⛔ Không chạm tệp ngoài danh sách §3."* |
| 2 | **Cây làm việc** | Đường tuyệt đối. ⛔ Không `cd` ra khỏi worktree để **GHI**. ✅ Được **ĐỌC** ngoài cây khi việc đòi: `D:\BOT GEMINI` (kho tham chiếu chỉ-đọc), `C:\LTTPlatform\app` (bản đã cài — xem §4.3), `C:\LTTPlatform\secrets\app.env` (⛔ chỉ **đếm**, ⛔ không in giá trị). Ghi ra ngoài cây ⇒ **dừng và báo** |
| 3 | **Đọc trước** | Plan pha (từ Task nào tới Task nào) + spec §nào. ⭐ **Đọc HẸP** — chỉ mục cần |
| 4 | **Tệp được sửa** | Liệt kê **tường minh**. Một tệp không có trong danh sách ⇒ ⛔ dừng và báo |
| 5 | **Dải số test** | Số cụ thể. Kèm: `python tools/check_so_test.py --list` trước khi tạo tệp |
| 6 | **Interfaces** | Chữ ký hàm **đầy đủ** của việc nó Consumes (do làn trước tạo) và Produces |
| 7 | **Nhịp TDD** | test đỏ → chạy thấy đỏ → cài đặt tối thiểu → chạy thấy xanh → commit. ⛔ Không viết mã trước test |
| 8 | **Lệnh nặng** | Qua `chay_nang.py --phien <làn>`, `-n ≤ 7`. Kiểm `cua_so_yen.py trang-thai` + `tai_may.py` trước. 🔴 **⛔ TRỪ `pytest` — xem §3.1**: bọc `pytest` là **tự khoá chính mình**. Và ⛔ nhiều bước thì viết một tệp `.py` rồi chạy tệp, ⛔ không `cmd /c "a && b"` (thoát exit 0 mà **không chạy gì**) |
| 9 | **Rào cứng của làn** | §4.2 — riêng từng làn |
| 10 | **⛔ Không được làm** | Không gate · không deploy · không đổi ENV production · không `git add .` · không sửa `tests/conftest.py` gốc · không `--accept` bánh cóc |
| 11 | **Ghi dần** | ⭐ Commit sau **mỗi Task**, ⛔ không giữ việc trong ngữ cảnh rồi commit một lần cuối |
| 12 | **Báo cáo** | ≤ 250 từ: Task đã xong, test đã xanh (kèm lệnh), và **mọi chỗ spec mâu thuẫn** — ⛔ không tự quyết, báo về |

### 4.1 Điều phối soát gì trước khi bấm gửi

| # | Phép soát | Đỏ thì làm gì |
|---|---|---|
| S-1 | Mọi chữ ký hàm trong mục 6 **có thật** trong plan của làn trước? | Tra lại plan; sai thì sửa brief, ⛔ không để agent tự khớp |
| S-2 | Dải số test **không chồng** làn nào đang chạy? | Cấp dải khác |
| S-3 | Danh sách tệp ở mục 4 **không giao** với làn đang chạy? | Đổi thứ tự lô |
| S-4 | Model ở §2 khớp mức rủi ro của Task? | Nâng/hạ, ghi lý do |
| S-5 | Rào cứng của làn (§4.2) đã có đủ? | Bổ sung |
| S-6 | Brief có nhắc **cái giá nếu sai** của Task này? | Thêm — agent cần biết chỗ nào không được đoán |
| S-7 | Brief có mục 11 (ghi dần)? | Thêm. Bỏ mục này là ca treo 26/09 lặp lại |

### 4.3 🔴 Kênh nghiệm thu phải ĐO ĐƯỢC mã của mình

Bổ sung 27/09 sau khi điều phối đưa một làn **đúng một kênh không thể trả lời câu nó
cần hỏi**. Đây là mục quan trọng nhất của §4, vì sai ở đây cho ra một báo cáo **xanh
mà vô nghĩa**.

**Sự thật đo được:** hai dịch vụ production chạy `AppDirectory = C:\LTTPlatform\app`
— **bản ĐÃ CÀI**, ⛔ không phải cây làm việc. `Test-Path` trên bốn tệp của pha 1/2
(`services/bat_bien.py`, `bindings.py`, `handoff_stage.py`, `tables/binding.py`) đều
**KHÔNG CÓ**.

⇒ Mở `https://app.lttstudios.com` là đo **đường ống cũ**:
- "thành công" ⇒ vừa xác nhận mã **không phải của mình**;
- "thất bại" ⇒ có thể **chẳng liên quan** mã của mình.

Cả hai kết luận **vô giá trị**. Bài học `doc-thu-dai-dien-thay-vi-doc-thu-that`:
⭐ *"thứ tôi đang hỏi có SẴN ở chỗ tôi đang đứng không?"*

| Muốn kiểm | Kênh đúng |
|---|---|
| Logic, service, route của **mã mình vừa viết** | `TestClient` của FastAPI — dựng app từ **cây này** |
| **Giao diện** của mã mình vừa viết | ⭐ uvicorn **cục bộ dựng từ cây này** (`sys.path[0]`=worktree, `chdir` worktree, `server.app.create_app()`), rồi lái bằng Playwright. Vừa đo đúng mã, vừa có render |
| Cấu hình / biến môi trường / hành vi **đã deploy** | `https://app.lttstudios.com` — và ⭐ nói rõ phạm vi là **bản đã cài** |
| Mã mình trên production | ⛔ **Không kiểm được cho tới khi deploy.** Ghi **món nợ có tên** |

**Món nợ phải ghi đủ bốn phần** — ⛔ không ghi "chưa kiểm được" chung chung:
> *"Nghiệm thu trình duyệt cho <việc>: **CHƯA LÀM**. Lý do: dịch vụ chạy
> `C:\LTTPlatform\app`, mã pha N chưa deploy. **Đo bằng `Test-Path`, ngày 27/09.**
> Trả được **sau một lượt deploy**."*

⛔ Và khi báo cáo một phép đo trên uvicorn cục bộ, **ghi rõ đó là cục bộ** — kể cả
trong commit message. Một ảnh chụp không nói phạm vi sẽ được đọc như bằng chứng
production ở phiên sau.

### 4.2 Rào cứng riêng từng làn — ⛔ thiếu là mất dữ liệu hoặc gate đỏ

| Làn | Rào cứng bắt buộc ghi trong brief |
|---|---|
| **M₁·M₃·M₄·M₅** | `python -m alembic heads` phải in **đúng MỘT** head trước **và** sau. Nhiều hơn ⇒ **DỪNG**, báo — phiên khác vừa thêm migration. `downgrade` phải chạy được thật |
| **M₁** | Khai cạnh app→app là việc **HAI ĐẦU**: `APP_DUOC_DUNG_APP` **và** `BE_MAT_CONG_KHAI` trong `apps/taovideo/__init__.py` (đang **RỖNG**). Bản khai là **tuple literal**, ⛔ không bọc `frozenset(...)` |
| **A·B₁·B₂** | Variant **mất bản ghi** ⇒ ⛔ **không** tiêu số thứ tự. Variant **còn bản ghi mà mất tệp** ⇒ **có** tiêu số, và vào `skipped`. Lẫn hai ca là đánh số vỡ |
| **B₁·B₂** | Chỉ được import **đúng 5 tên** của `apps.taovideo.refs`. ⛔ Không `routes`/`jobs`/`cost`/`manifest`. Chi tiết `camera` chữ tự do vào **`prompt`**, enum chỉ gợi ý thô, không khớp ⇒ `""` |
| **C** | `ommi_canh.id` **PHẢI** tái dùng id truyền vào. Sinh id mới ⇒ mọi binding pha 1 thành hư không |
| **D** | Bộ đếm lượt miễn phí **trong CSDL**, tăng **cùng transaction** với `OmmiIteration`. ⛔ `verdict="rejected"` **không** hoàn credit. Handler **phải ném exception** khi lỗi |
| **E** | ⛔ **Không xoá `apps/prompt_canh`** trước khi E3 xanh **và** E4 có bản đối chứng kết luận đạt. Đo lại `grep -rc "prompt_canh" tests/` **trước khi xoá** — số có thể đã đổi. 5 tệp liên-app sửa **tối thiểu** |
| **G** | `D:\BOT GEMINI` là kho production **CHỈ ĐỌC**. ⛔ Không ghi/sửa/xoá gì, ⛔ không mở `.db` tại chỗ — copy sang scratchpad rồi `mode=ro`. Viết **tệp `.py`**, ⛔ không `python -c`. stdout Windows là cp1252 ⇒ ghi kết quả ra **tệp UTF-8**, ⛔ đừng `print` tiếng Việt |
| **H** | Dedupe theo **`(owner_id, file_hash)`**, ⛔ không theo `file_hash` toàn cục. Zip-slip + zip-bomb có **số cụ thể**. Giải nén đi qua **hàng đợi job** — Cloudflare cắt 100 MB / 100 giây |
| **J** | Nghiệm thu trên **`https://app.lttstudios.com`**, ⛔ không loopback (bỏ qua Cloudflare). Đăng nhập `khach1.thu` **bằng cookie**, ⛔ không gõ mật khẩu. Đổi CSS/JS ⇒ cache-bust `ASSET_VER` + **khởi động lại** service. Kiểm console errors **và** failed network requests |

---

### 4.4 🔴 Đổi một TRẦN ⇒ đếm hết chỗ khai, và chỗ ở **worker** là chỗ hay thiếu

Giao một làn đổi một giới hạn (trần số lượng, trần dung lượng, trần lượt) thì
⛔ **đừng liệt kê chỗ khai cho nó** — hãy bắt nó **tự đếm và báo lại số chỗ tìm
được**, rồi đối chiếu với con số mình nghĩ. Tôi liệt kê 5 chỗ; làn T đếm ra **6**.

⭐ Chỗ thứ sáu là chỗ đắt nhất: **trần kiểm ở worker**, chạy SAU khi credit đã giữ
(`apps/taovideo/jobs.py:111`, gọi từ dòng 165). Nâng trần ở cửa mà quên worker ⇒
khách nộp đúng trần cửa, **bị trừ tiền**, rồi job chết. **Xấu hơn hiện trạng.**
Đây là bất biến **B-6** trong spec.

| Cửa | Hỏi gì |
|---|---|
| Cửa vào HTTP (`routes.py`) | trần này chặn TRƯỚC khi tính tiền chứ? |
| Worker (`jobs.py`) | trần này có ≥ trần ở cửa không? |
| `manifest.py` (`params_schema`) | kiểu `x[]` còn bị `TRAN_MEDIA_MOT_THAM_SO` kẹp |
| Template / JS | con số hiển thị cho khách có khớp không? |
| Test | phép kiểm đo **hành vi** hay chỉ đo *chuỗi có trong HTML*? |

⛔ **Không sửa sáu chỗ cho khớp số** — bắt làn gom về **một hằng số**, mọi chỗ
import. Sáu chỗ khai cùng một điều thì sớm muộn lệch nhau.

⚠️ **Trần khác cửa thì ĐƯỢC khác số.** `TRAN_MEDIA_MOT_THAM_SO = 8` tồn tại vì
một chi phí KHÁC (mỗi phần tử `image[]` là một lượt tra CSDL trước khi có tiền),
không phải vì engine. Bắt làn **ghi rõ cửa nào chịu số nào**; không ghi thì người
sau thấy 8 cạnh 9 và "sửa cho khớp".

🔴 **Và phép kiểm của trần phải đo HÀNH VI.** `assert "total>4" in page` xanh với
bất kỳ con số nào và ⛔ không chứng minh trần có hiệu lực — nộp quá trần phải bị
**từ chối** mới là phép kiểm.

---

## 5. Nắn agent — đo bằng gì, can thiệp lúc nào

⛔ **"Agent chưa báo xong" không phải phép đo.** Agent im lặng trông giống agent
đang làm việc.

| Tín hiệu | Cách đo | Ngưỡng | Làm gì |
|---|---|---|---|
| **Treo khi sinh văn bản** | `date -r <tệp>` + `wc -l` tệp đích | **> 30 phút** không tăng dòng | `TaskStop`, **giữ** phần đã ghi, tự viết nốt hoặc chia nhỏ giao lại |
| **Treo khi thi hành mã** | `git log --oneline` của làn đó | > 30 phút không commit | Hỏi bằng `SendMessage`; không trả lời ⇒ `TaskStop` |
| **Lệch hướng** | Báo cáo nhắc tệp **ngoài** danh sách mục 4 | ngay lần đầu | `SendMessage` nắn lại, ⛔ đừng để nó "xong rồi sửa sau" |
| **Spec hở** | Agent báo *"spec mâu thuẫn"* | ngay | **Điều phối phán quyết**, vá spec, rồi `SendMessage` cho **mọi** làn bị ảnh hưởng — kể cả làn đã xong |
| **Giữ khoá lâu** | `tools\cua_so_yen.py trang-thai` | > 30 phút giữ `cpu_nhieu` | Kiểm CPU: giữ lâu + CPU một chữ số = **đang CHỜ**, không phải đang tính ⇒ nhả |
| **Tiến trình mồ côi** | `Desktop\HOP DEN\KHAM.bat`, đọc `so_tien_trinh` cạnh `cpu` | máy vừa treo | ⛔ **Từ chối mọi pid có cha là `services.exe`** — một cú giết cây làm PostgreSQL production sập 4 phút |

### 5.1 Sau khi làn nào cũng xong: ba phép soát liên làn

⭐ Đây là phép đã bắt được **4 xung đột thật** ở bước viết plan. Chạy lại ở bước thi hành.

| # | Phép | Lệnh |
|---|---|---|
| 1 | **Trùng số test** | `python tools/check_so_test.py --list` |
| 2 | **Tên hàm gọi mà không ai định nghĩa** | `grep` chữ ký trong `Interfaces` của mọi plan, đối chiếu mã thật |
| 3 | **Hai chỗ khai một điều** | Bánh cóc đọc AST/nguồn: enum `taovideo`, `LUOT_MIEN_PHI`, `_cost` ⟷ `jobs.handle` |

---

## 6. Ba chỗ điều phối đã biết là sẽ va — nắn trước, đừng chờ nó xảy ra

| # | Chỗ | Nắn thế nào |
|---|---|---|
| 1 | `routes/briefs.py::quote` (làn C) **gõ lại số `2`**, còn `LUOT_MIEN_PHI = 2` khai ở làn D | **Đổi thứ tự: D1 trước C7.** Brief của C phải ghi rõ `quote` dùng `con_mien_phi()`, ⛔ không gõ số |
| 2 | Bộ enum `taovideo` **chép literal** sang `prompt_ai_ommi` (G-3b cấm import `manifest`) | Brief làn B₂ **bắt buộc** kèm bánh cóc `test_5156` đặt **ngoài cả hai app**, so literal với `params_schema` |
| 3 | Làn I (pha 5) dùng bảng `ommi_image_template`/`ommi_storyboard_framework` của **pha 4** | Brief làn I phải khai chúng trong `Consumes` kèm **tên cột cụ thể**, và ghi: pha 4 chưa gộp ⇒ **DỪNG và báo**, ⛔ không tự dựng bảng giả |
