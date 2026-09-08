# 31 — NHẬT KÝ TRIỂN KHAI

> Ghi **việc đã làm và bằng chứng đo được**, theo từng đợt của
> `27_29 §28`. Không ghi ý định; chỉ ghi thứ đã chạy.
>
> Quy tắc: một đợt chỉ được đánh ✅ khi có **cổng chất lượng xanh trên một cây
> đứng yên**. Cụm test hẹp xanh là *tiến độ*, không phải *bằng chứng*.

---

## ĐỢT 1 — Sửa thứ đang chảy máu hôm nay

**Bắt đầu:** 2026-09-07 · **Chạm:** `platform_core/jobs.py`, `platform_core/models.py`
⚠️ Đây là lớp **đang phục vụ thật** (868 job/28 ngày) — rủi ro `R1`, cao nhất lộ trình.

### 1.1 · `claim()` biết sức chứa trước khi nhặt — `G11` / `WF-202`

**Thay đổi:** `platform_core/jobs.py` — thêm `_con_cho_tai_nguyen(now)`, một mệnh
đề SQL loại job của tài nguyên đã đầy ra khỏi câu truy vấn `claim()`.

```
Job.admission_resource == ''       →  không dùng tài nguyên chia sẻ, luôn qua
Job.admission_slots <= 0           →  app chưa khai sức chứa, giữ hành vi cũ
count(lease còn sống) < slots      →  còn chỗ
```

Lease "còn sống" = `heartbeat_at >= now - ORPHAN_TIMEOUT`, cùng ngưỡng
`admission.acquire()` dùng để thu hồi lease mồ côi.

⭐ **Ghi rõ trong docstring rằng nó KHÔNG phải khoá.** Hai worker vẫn có thể cùng
thấy một suất trống rồi cùng nhặt hai job của cùng tài nguyên; lớp giành thật vẫn
là `ExecutionLease` với `UNIQUE(resource, slot)`, và `job_runner` vẫn
`defer_resource` khi hụt. Bộ lọc chỉ làm chuyện đó **hiếm** thay vì **thường trực**.

### 1.2 · Khử trùng bằng ràng buộc — `G24` / `WF-302`

**Thay đổi:** `platform_core/models.py` + migration `c9d4e1a77b02`.

```sql
UNIQUE INDEX ux_jobs_dedupe_active (user_id, dedupe_key)
  WHERE dedupe_key <> '' AND status IN ('queued', 'running')
```

Hai vế của mệnh đề `WHERE` đều bắt buộc — bỏ vế nào cũng hỏng:
- `dedupe_key <> ''` : mặc định là chuỗi rỗng, phần lớn job không dùng ⇒ UNIQUE
  đầy đủ sẽ chặn **mọi job thứ hai** của một người dùng.
- `status IN (...)` : xong rồi thì gửi lại cùng yêu cầu là hợp lệ (bấm "Tạo lại"),
  và job cũ vẫn phải nằm đó làm **bằng chứng cho sổ tiền**.

⛔ **Migration từ chối tự dọn.** Nếu CSDL đã có cặp trùng, nó **dừng và liệt kê**
thay vì huỷ bớt job — huỷ một job chạm giữ chỗ credit và hoàn tiền, và một
migration không phải chỗ quyết định điều đó trong im lặng. Operator quyết, rồi
chạy lại. Không dữ liệu nào bị mất.

### 1.3 · Đo

```
                       lượt claim TRẢ VỀ job   job xong   tỉ lệ
KHÔNG bộ lọc (cũ)                         24         12    2,00
CÓ bộ lọc  (mới)                          12         12    1,00
```

**1,00 = mọi lượt claim trả về job đều giành được lease.**

⚠️ **Giới hạn của phép đo này, nói trước khi ai hỏi.** Mô phỏng cho bản cũ ra
**2,00**, không phải **13,74** của production. Mô hình một-tick-một-lượt **đánh
giá thấp** mức lãng phí thật, nơi job giữ suất ~5 giây trong khi worker khác quay
lại hỏi qua cửa sổ 20 giây. ⇒ Ngưỡng `M3` **chưa đạt**; chỉ đo được sau deploy,
trên log worker thật.

### Kỷ luật đã theo

| | |
|---|---|
| **RED trước** | 7 phép kiểm viết trước mã, **xem đỏ đúng lý do** (`assert <Job …> is None`, `DID NOT RAISE IntegrityError`) |
| **Đối chứng** | tiêm 2 bản sai vào mã sản phẩm → cả hai làm **đỏ đúng phép kiểm**, rồi khôi phục nguyên trạng |
| **Viết lại test cũ, không hạ chuẩn** | xem dưới |

#### Một phép kiểm cũ bị đỏ — và cách xử lý

`test_worker_hoan_job_khi_execution_slot_ban_khong_tinh_attempt` đỏ sau thay đổi.

**Mệnh đề của nó vẫn đúng và vẫn phải giữ:** thua cuộc đua giành suất thì hoàn
job về hàng đợi, **không tiêu một lượt thử**. Thứ hỏng là *bối cảnh dựng* — nó
giữ sẵn suất **trước** khi worker nhặt, và bối cảnh đó nay bị `claim()` chặn từ
trước nên không còn tới được nhánh cần kiểm.

⇒ Viết lại **bối cảnh**, giữ nguyên **khẳng định**: cướp suất **đúng sau khi
`claim()` trả về**, tái hiện chính cuộc đua thật. Bản mới **khó xanh hơn** — nó
đòi cả `claim()` cho qua **lẫn** `defer_resource` xử lý đúng, thay vì chỉ vế sau.

⛔ Đây là ranh giới dễ vượt nhất trong cả đợt: sửa test cho khớp mã. Phép thử để
tự bắt: *bản viết lại có KHÓ xanh hơn bản cũ không?* Nếu dễ hơn ⇒ đang hạ chuẩn.

### Bằng chứng

| Phép đo | Kết quả |
|---|---|
| Cụm hẹp: admission · queue · worker · policy · runtime · content · events · UI | **130 passed** |
| `alembic upgrade head` trên CSDL trống | `rc = 0` |
| Chuỗi migration | **một head**; `c9d4e1a77b02` trong chuỗi |
| `ruff --select F401` trên 4 tệp đã sửa | **All checks passed** |
| Cổng đầy đủ trên cây **đứng yên** | ❌ **chưa đạt được** — xem §"Hai lượt gate" |

### 🔴 Hai lượt gate, cả hai đều KHÔNG dùng làm bằng chứng được

| Lượt | Kết quả | Bước đỏ | Cây đổi giữa chừng |
|---|---|---|---|
| `20260907T143450Z` *(trước khi tôi bắt đầu)* | **PASS** | — | — |
| `20260907T152315Z-26824` | FAIL 5/29 | `kieu xuong dong` · `ruff` · `dich thieu ban EN` · `frontend chatltt` · `bo test` | 14 tệp `ltt_voice` |
| `20260907T170926Z-9180` | FAIL 4/29 | `kieu xuong dong` · `chuoi chua dich` · `frontend chatltt` · `bo test` | `locale/en/…messages.{po,mo}` |

⭐ Lượt `14:34` **PASS sạch** là mốc quan trọng: nó chứng minh cây **đã** xanh
ngay trước khi ba phiên bắt đầu ghi song song.

#### Quy trách nhiệm — 4 bước đỏ, **0 của tôi**, mỗi cái có bằng chứng riêng

| Bước đỏ | Của ai | Cách xác định |
|---|---|---|
| `kieu xuong dong` | phiên **LTT Voice** | `check_xuong_dong.py` chỉ đúng một tệp: `apps/ltt_voice/jobs.py` — `HEAD=CRLF -> hien tai=LF (25 dong)`. Tệp của tôi: **0 CRLF** trên cả 4 tệp mã + migration + 17 tệp docs |
| `chuoi chua dich` | phiên **LTT Voice** | 8 chuỗi mới đều về giọng (*"Giới tính giọng"*, *"Ngôn ngữ của clip"*…); họ đã sửa **giữa lượt chạy** nên gate thấy bản cũ |
| `frontend chatltt` | phiên **ChatLTT** | `tests/a11y.test.tsx` → `Failed to resolve import "axe-core"`; **có** khai trong `package.json`, chỉ thiếu `npm install` |
| `bo test (song song)` | phiên **ASV** | 7 lỗi `test_448`, nguyên nhân gốc `khong provider nao phuc vu duoc: ltt_llm: ban` — bản ghi bằng chứng chụp lúc **ba phiên tranh một suất `llm_remote`** |

**Đối chứng cho mục cuối** — gỡ hẳn thay đổi của tôi rồi chạy lại:

```
KHONG co thay doi cua toi ->  7 failed, 14 passed, 2 skipped
CO  thay doi cua toi     ->  7 failed, 14 passed, 2 skipped
```

Giống hệt ⇒ độc lập với `claim()`. Và lỗi phát từ **tầng định tuyến provider bên
trong handler**, nghĩa là job **đã** được nhặt và **đã** chạy — bộ lọc không chặn nó.

#### ⛔ Kết luận thẳng: tôi KHÔNG tự làm gate xanh được

Gate là **phán quyết trên toàn cây**, và cây đang chứa việc dở của **ba phiên**.
Không phiên nào một mình làm nó xanh. Đây không phải lý do để hạ chuẩn — nó là
lý do để **nói rõ trạng thái thật** thay vì gọi cụm test hẹp là bằng chứng.

⇒ **Đợt 1 chưa được đánh ✅.** Điều kiện còn thiếu **không nằm trong tầm tôi**.

#### ⭐ Một luật rút ra về "cây đứng yên"

Tôi đo cây trước khi bấm (0 tệp sửa/5 phút) và vẫn dính `CAY DA DOI GIUA CHUNG`.
Vì lượt chạy dài **12,7 phút**, và phiên Voice sửa `locale/*.po` **ở giữa**.

> **"Cây đứng yên" phải tính từ lúc BẤM tới lúc XONG, không phải chỉ lúc bấm.**
> Với gate ~13 phút trên máy nhiều phiên, điều đó cần **hẹn trước**, không phải
> đo trước.

### Lượt gate đầu tiên — chi tiết

Lượt 15:07–15:23 UTC ra `RESULT: FAIL`, nhưng gate **tự** gắn cờ
`CAY DA DOI GIUA CHUNG - KHONG DUNG LAM BANG CHUNG`: phiên *LTT Voice* ghi 14 tệp
giữa lượt chạy 14,7 phút.

Ba test đỏ, và đã **đo để tách trách nhiệm** thay vì đoán:

```
ruff --select F401  trên 4 tệp tôi sửa    →  All checks passed
ruff --select F401  trên apps/ltt_voice/  →  Found 77 errors
```
`F401 416 → 418` (2 import thừa mới) và 8 chuỗi chưa dịch (*"Giới tính giọng"*,
*"Ngôn ngữ của clip"*, …) đều thuộc `apps/ltt_voice`. Đã nhắn phiên đó kèm số đo;
**không đụng một tệp nào bên họ**.

---

## 🔴 HAI CÁI BẪY GẶP TRONG ĐỢT 1

### B1 — Mã thoát đọc qua một **ỐNG** là mã của lệnh cuối ống

> ⚠️ **BẢN ĐẦU CỦA MỤC NÀY SAI, VÀ ĐÃ ĐƯỢC SỬA.** Tôi viết *"`gate.py` thoát với
> mã 0 trong khi `RESULT: FAIL`"* và ghi nó như một khuyết tật của `gate.py`.
> Phiên *LTT Voice* bác lại bằng mã nguồn; tôi kiểm và **họ đúng**.
> Giữ lại nguyên văn cái sai vì lý do nó nguy hiểm nằm ở §B1.3.

**Quan sát ban đầu (đúng):** lượt gate đầu báo `[exited with code 0]` trong khi
dòng cuối ghi `RESULT: FAIL (5/29)`.

**Chẩn đoán ban đầu (SAI):** *"`gate.py` trả 0 khi FAIL."*

#### B1.1 · Mã nguồn nói ngược

```
tools/gate.py:1565   failed = [s for s in steps if not s.ok]
tools/gate.py:1595   ket = "PASS" if not failed else f"FAIL ({len(failed)}/{len(steps)})"
tools/gate.py:1652   return 0 if not failed else 1
```

`ket` và mã thoát rút ra từ **cùng một biến** `failed`, cùng một hàm, **không
nhánh nào chen giữa**. `RESULT: FAIL` ⇒ mã 1, luôn luôn. Đã đọc lại `1560-1570`
và `1648-1655` để chắc không có nhánh ẩn. `CONFIRMED`

#### B1.2 · Nguyên nhân thật — đo được, không suy luận

Lệnh gốc tôi gõ: `python tools/gate.py 2>&1 | tail -30`. **Có ống.**

```
python -c "sys.exit(1)"                    ->  $? = 1
python -c "sys.exit(1)" | tail -1          ->  $? = 0
python -c "sys.exit(1)" 2>&1 | tail -1     ->  $? = 0     ← đúng dạng lệnh gốc
```

Mã 0 là của **`tail`**, không phải của `gate.py`. Bash trả mã lệnh **cuối ống**
trừ khi bật `set -o pipefail`; PowerShell đặt `$LASTEXITCODE` theo lệnh cuối
pipeline; và dòng *"Background command completed (exit code 0)"* của harness là
mã của **shell bọc**, không phải của python.

#### B1.3 · 🔴 Vì sao cái sai này nguy hiểm hơn một lỗi thường

Lời khuyên thực hành **giống hệt nhau** ở cả bản sai lẫn bản đúng: *đọc dòng
`RESULT`*. Nên cái sai **không gây hại ngay** — nó nằm im, đúng về hành vi, sai
về nguyên nhân.

⛔ Nhưng một phiên sau đọc *"gate trả 0 khi FAIL"* sẽ đi **sửa `gate.py`** — sửa
một khuyết tật không tồn tại, ở đúng tệp mà **mọi phiên** dựa vào để ra phán
quyết. Một dấu `|` của tôi biến thành một thay đổi chạm tất cả mọi người.

⭐ Đây là lớp lỗi *"giả thuyết khớp quá vừa"*: chẩn đoán sai **khớp hoàn hảo** với
quan sát (mã 0 + FAIL), nên nó **kết thúc cuộc điều tra** trước khi ai hỏi *"lệnh
đó có ống không?"*.

#### B1.4 · Luật rút ra

> **Đừng đọc mã thoát qua một ống.** Chạy `gate.py` **không ống** rồi đọc `$?`,
> hoặc đọc dòng `RESULT` từ đầu ra. `gate.py` trả 0/1 **đúng** theo `failed`.
> Và trước khi kết luận một công cụ có khuyết tật: **đọc mã của nó, và đọc lại
> lệnh của chính mình.**

#### B1.5 · 🔴 Tôi lặp lại đúng cái bẫy này **sau khi** đã viết mục trên

Vài phút sau khi sửa §B1, tôi gõ:

```
python tools/check_xuong_dong.py 2>&1 | head -20 ; echo "rc=$?"
   →  rc=0        trong khi công cụ in  RESULT: FAIL
```

⭐ **Đây mới là bằng chứng thật cho luật.** Cái bẫy không nằm ở `gate.py` — nó
nằm ở **thói quen gõ ống** của tôi, và viết luật ra **không** đủ để bỏ thói quen.

⇒ Luật phải ở dạng **kiểm được bằng mắt trước khi bấm Enter**, không phải dạng
ghi nhớ:

> Thấy `| head`, `| tail`, `| grep` **và** định đọc `$?` trong cùng một lệnh
> ⇒ **bỏ một trong hai**. Đọc `$?` thì bỏ ống; giữ ống thì đọc dòng `RESULT`.

### B2 — `cua_so_yen` báo `RANH` khi gate của chính mình đang chạy

Lượt trước tôi kết luận đây là **lỗ của giao ước**. **Sai, hai lần:**

1. `gate.py` **có** xin khoá — lượt sau kiểm lại thấy đúng
   `[cpu_nhieu] … chay 'gate --ho-so day-du' duoc 0.2 phut`. Lần đầu tôi kiểm
   **quá sớm**, trước khi gate kịp xin.
2. Và cái lỗ thật thì **đã được ghi sẵn trong `tools/gate.py`**, kèm hai ca đo
   được:

   > *"Cả hai đều **vô hình với khoá** — khoá chỉ thấy ai XIN khoá. Cả hai đều
   > **hiện ra ở CPU**."*
   > — `tools/gate.py:199`

   Và ca thứ ba từ hộp đen 03/09: **12 tiến trình `demucs`, mỗi cái 460–984 %
   CPU**, chạy ngoài mọi khoá.

⇒ **Luật đúng, và nó đã tồn tại:** `cua_so_yen` là điều kiện **CẦN**;
**CPU là vế quyết định**. `gate.py` đã vá bằng `_ap_ngan_sach_thuc` (đo CPU thật
rồi mới đặt ngân sách worker).

⭐ Bài học cho tôi: **trước khi báo một công cụ có lỗ, đọc docstring của nó.**
Hai lượt tôi trình bày như phát hiện mới một thứ dự án đã đo, đã ghi, đã vá.

---

## Nhịp kiểm CPU đã thi hành trong đợt này

| Thời điểm | `cua_so_yen` | CPU | RAM trống |
|---|---|---|---|
| trước cụm test agent | RANH | 22 % | — |
| trước gate lượt 1 | RANH | 12 % | — |
| giữa gate lượt 1 | RANH *(kiểm sớm)* | 40 % | 13,1 GiB |
| trước cụm hẹp | RANH | 13 % | — |
| trước gate lượt 2 | RANH | **2 %** | 17,1 GiB |
| giữa gate lượt 2 | **[cpu_nhieu] pid 9180** | 17 % | 17,2 GiB |

Ngưỡng sự cố tham chiếu (03/09): **CPU 100 %, RAM trống 14 GiB, 12 `demucs`**.
Không lượt nào tới gần.

---

## VIỆC GỠ CHẶN — không thuộc đợt nào, nhưng chặn cả ba phiên

### `frontend chatltt` — `npm install`

Bước gate `frontend chatltt` đỏ vì `tests/a11y.test.tsx` → `Failed to resolve
import "axe-core"`. Phụ thuộc **đã khai** trong `package.json` **đã commit**;
chỉ thiếu ở `node_modules`. Phiên sở hữu (ChatLTT) đã đóng.

```
npm install --no-audit --no-fund   ->  added 1 package in 2s
npm test                           ->  15 tep / 186 test  XANH   (truoc: 14 + 1 khong nap duoc)
git status --porcelain frontend/chatltt  ->  (rong)
```

**Kiểm an toàn TRƯỚC khi chạy** — hai câu, hai nguồn:

```
gate.py:1275  _BO_QUA_THU_MUC = frozenset({"__pycache__", "node_modules"})
gate.py:1296  con[:] = [d for d in con if d not in _BO_QUA_THU_MUC]
git check-ignore -v frontend/chatltt/node_modules  ->  .gitignore:76
```

⇒ Ảnh chụp cây **không** đi xuống `node_modules`, và git bỏ qua nó. Không phá
dấu vân tay, không thêm dòng `??`.

⭐ Đây **không** phải sửa mã của ai. Nó là *dựng lại môi trường* — hiện thực hoá
một phụ thuộc đã có trong hợp đồng đã commit.

---

## 🔴 B3 — TÔI SUÝT SỬA MỘT LỖI KHÔNG TỒN TẠI, LẦN THỨ TƯ TRONG NGÀY

Rủi ro `R4` nói: *"`M1`/`M3` đo trên SQLite, Postgres có thể khác."* Nên tôi
biên dịch mệnh đề `_con_cho_tai_nguyen` cho cả hai dialect.

**Kết quả làm tôi hoảng:**

```sql
-- bien dich MENH DE ROI
(SELECT count(execution_leases.id) FROM execution_leases, jobs
 WHERE execution_leases.resource = jobs.admission_resource AND ...)
                            ^^^^ `jobs` trong FROM => tich Descartes, MAT tuong quan
```

Đọc như một lỗi nặng: subquery đếm lease khớp `admission_resource` của **bất kỳ**
job nào, không phải của hàng đang xét. Và nó **giải thích được** vì sao test vẫn
xanh (bộ dữ liệu nhỏ cho ra cùng kết quả).

**Nhưng tôi đã biên dịch sai thứ.** Biên dịch **câu truy vấn thật** của `claim()`:

```sql
-- trong CAU THAT: select(Job).where(...).where(_con_cho_tai_nguyen(now))
(SELECT count(execution_leases.id) FROM execution_leases
 WHERE execution_leases.resource = jobs.admission_resource AND ...)
                            ^^ chi mot bang => TUONG QUAN DUNG
```

`.correlate(Job)` cần `jobs` có mặt ở `FROM` của câu **bao ngoài**. Biên dịch
mệnh đề **rời** thì không có câu bao ngoài, nên SQLAlchemy tự thêm `jobs` vào —
một sản phẩm phụ của phép đo, **không** phải của mã.

### Vì sao ca này đáng ghi riêng

Đây là lần thứ **tư** trong một ngày của cùng một lớp lỗi, và là lần **nguy hiểm
nhất** vì nó suýt dẫn tới một *"bản sửa"* làm hỏng mã đang đúng:

| # | Tôi đo thứ đại diện | Thay vì |
|---|---|---|
| 1 | mã thoát của `tail` | mã thoát của `gate.py` |
| 2 | thông điệp lỗi trong log gate | tệp bằng chứng của ASV |
| 3 | **tên bước** gate (`chuoi chua dich`) | **công cụ** chạy sau tên đó |
| 4 | **mệnh đề SQL rời** | **câu truy vấn thật** |

⭐ Cả bốn đều **khớp hoàn hảo** với quan sát. Đó là dấu hiệu nhận dạng của lớp
lỗi này — không phải sự mơ hồ, mà là **sự vừa vặn**.

> **Luật:** biên dịch/đo một **mảnh** chỉ nói về mảnh đó. Muốn kết luận về hành
> vi thật thì phải dựng lại **đúng ngữ cảnh nó chạy**. Với SQLAlchemy: luôn
> compile cả `select(...)`, không bao giờ compile một `whereclause` rời.

✅ **Kết luận thật của `R4`: mệnh đề đúng trên CẢ HAI dialect.** Cấu trúc SQL
sinh ra giống hệt nhau; chỉ khác kiểu tham số (`%(name)s` vs `?`).

---

## Quan sát nhận từ phiên ASV — thuộc `WF-302`

> **Cái rào chặn theo BẢN GHI, không theo CÂU HỎI mà từng bài đặt ra.**

`_chan_tai_nguyen_ban` của họ chặn cả 19 bài khi bản ghi đến từ máy bận. Nhưng
ba bài trong đó (*"máy chạy có được ghi lại không"*, *"báo cáo có nói rõ thứ
được thay thế không"*, *"cửa gọi model có trả đúng kiểu không"*) **vẫn trả lời
đúng được** trên một bản ghi hỏng.

⇒ Cùng thiếu sót của `WF-302` ở tầng khác: **một phép kiểm cũng cần khai nó phụ
thuộc điều kiện nào để có nghĩa.** Ba bài kia phụ thuộc *"có một bản ghi"*; mười
sáu bài còn lại phụ thuộc *"có một lần chạy ĐI HẾT chuỗi"*. Hai tiền đề khác
nhau, một cái rào — nên cái rào phải chọn tiền đề chặt hơn, và **nói ra** rằng
nó đang chặn thứ lẽ ra trả lời được.

⭐ Và cách họ xử lý đáng học hơn cả bản vá: ghi tension ra **có tên**, rồi
**không** tái cấu trúc nhân tiện —
*"tôi không đổi thiết kế, tôi chỉ làm cái rào nổ đúng lúc nó đã luôn phải nổ."*

---

---

## Bốn lớp kiểm máy — và lớp thứ năm mà chính phép đo tạo ra

Bảng bốn lớp đã dùng cả phiên:

| | đo gì | trả lời câu hỏi |
|---|---|---|
| LỚP 1 | `cua_so_yen trang-thai` | có ai giữ khoá tài nguyên không |
| LỚP 2 | `CPU` + `ProcessorQueueLength` | máy có đang quá tải không (>10 trên 10 lõi vật lý) |
| LỚP 3 | tập tiến trình lọc `CommandLine` | ai đang chạy gate/test |
| LỚP 4 | tiến trình deploy | có an toàn để **GHI TỆP** không |

### Khuyết tật đã bắt được ở chính bảng này (2026-09-08)

**① Bộ lọc tự khớp vào chính nó.** Lượt đo đầu báo `LỚP 4 = 1 TIẾN TRÌNH`. Tiến
trình ấy là **chính lệnh đo** — chuỗi lọc `deploy_nang_quyen` nằm trong dòng
lệnh của nó. Memory dự án có mục riêng cho lỗi này (*"đã giết shell BỐN lần"*),
và nó vẫn tái diễn vì bảng bốn lớp không ghi kèm cách chống.

⇒ Luật: **lớp 3 và lớp 4 phải loại `$PID` cùng toàn bộ tiến trình con của nó.**
Nếu không, công cụ đo **tự sinh ra dữ liệu nó đo được** — một dạng dương tính
giả không bao giờ tự hết, vì nó có mặt ở *mọi* lượt đo.

**② Tên thư mục worktree không nói ai đang chạy.** Muốn biết một tiến trình
`gate.py` là của phiên nào thì **truy cây cha tới `claude.exe`** rồi so với tổ
tiên của chính mình:

```
pid=124  gate.py  ->  ppid 26100 bash  ->  28508  ->  21900  ->  claude.exe 10604
phien nay:              pwsh 3768   ->  claude.exe 23624
```

Khác `claude.exe` ⇒ khác phiên. Đây là **sự thật độc lập**, không phải suy luận
từ tuổi tiến trình hay từ thư mục.

### Vế mà bốn lớp KHÔNG nhìn thấy — ASV nêu

> *"Lớp 1–3 đo **trạng thái hiện tại**. Cơn tải này do **chính lệnh sắp bấm**
> sinh ra. Không lớp nào nhìn thấy tải mà mình sắp tạo."*

Đúng, và nó áp cho mọi lệnh nặng chứ không riêng deploy. Bốn lớp trả lời *"bây
giờ có ai không"*; chúng **không** trả lời *"thứ tôi sắp chạy tốn bao nhiêu"*.
Hai câu hỏi khác nhau, và câu thứ hai chỉ đọc được từ **mã của chính lệnh đó**.

⭐ Và lớp 4 có một tính chất riêng ASV chỉ ra: nó là lớp duy nhất **không đo
được hoàn toàn từ máy**. Ba lớp đầu là số; lớp 4 là *"có ai sắp bấm một nút
không"*. Cách duy nhất biến nó thành phép đo là **bên deploy tự đọc tiến trình
ngay trước khi bấm** — gộp chờ + kiểm + bấm vào một mạch, thay vì tin một giao
ước ba bên. Giao ước hỏng ở lần thứ tư; phép đo thì không.

---

## `setup/2-cai-dat.ps1` — HAI khuyết tật, không phải một

Phiên trước ghi đây là *"một dòng có hai vấn đề"*. ASV chỉ ra cách đọc đó làm
mất phần nguy hiểm: **hai khuyết tật NHÂN nhau**, và chỉ một trong hai có thể
làm treo máy.

| | khuyết tật | hệ quả một mình | sửa |
|---|---|---|---|
| ① | thông điệp `Error compiling` nói sai nghĩa khi tệp nằm trong `.claude` | đọc sai một dòng log | đổi thông điệp cho đúng nguyên nhân |
| ② | `compileall -j 0` (worker = số lõi ≈ 20) × phạm vi gồm cả `.claude` (sáu checkout) | **20 worker biên dịch sáu cây** | giới hạn worker, hoặc thu phạm vi về đúng thứ sắp giao |

Hai điều làm ② nặng hơn tổng hai phần:

- `-j 0` một mình = 20 worker trên **một** cây. `.claude` một mình = quét thừa
  nhưng tuần tự. Cộng lại = 20 worker trên **sáu** cây.
- Nó chạy ở **đúng bước ngay trước `Stop-Service`** — lúc production sắp dừng,
  không phải lúc máy rảnh.

⇒ Phương án *"giữ nguyên phạm vi, chỉ đổi thông điệp"* sửa ①, **không chạm** ②.
Đó là hai việc rời nhau và ② mới là cái liên quan tới lần treo máy 03/09.

⛔ **Ngoài phạm vi Workflow V2 — ghi nợ, không tự sửa.** `setup/` là đường
deploy của cả nền tảng; sửa nó giữa lúc hai phiên khác đang deploy là đúng thứ
`§0` cấm. Đã báo cho phiên đang giữ `setup/`.

---

## Đợt 1 · việc 3 — `co_job_dang_cho_tai_nguyen()` (WF-403)

**Vì sao có việc này.** Bộ lọc suất ở việc 1 làm `claim()` trả `None` với **hai**
nguyên nhân khác nhau: hết việc thật, và có việc nhưng tài nguyên đầy. Giá trị
trả về không phân biệt được — nên bên gọi phải **đoán**.

Vòng worker thật (`job_runner.py:1644`) may mắn đúng ở cả hai vì nó ngủ
`POLL_INTERVAL_S` rồi thử lại. Nhưng ba nhóm bên gọi khác thì không:

```
tools/h26_queue_soak.py:58        if job is None: break
tools/bench_llm_admission.py:70   if job is None: break
tests/test_448_...:196            if job is None: break
```

⛔ **Bản vá hiển nhiên là bản sai.** *"Thấy `None` thì ngủ rồi thử lại"* phạt cả
những lượt hàng đợi rỗng thật bằng đúng số giây ấy — trong một bộ đo hiệu năng
thì đó là làm hỏng chính thứ đang đo. Phiên ASV chỉ ra vế này.

⇒ Cái phải sửa không phải **phản ứng**, mà là **câu hỏi**: bên gọi cần hỏi được
theo *ý nghĩa* thay vì suy từ *hình dạng* của giá trị trả về.

### TDD

```
RED    6 failed  AttributeError: module 'platform_core.jobs' has no attribute
                 'co_job_dang_cho_tai_nguyen'
GREEN  6 passed  ->  ca tep test_313: 33 passed
CUM    110 passed  (7 tep job/lease/admission, -n 6, 6,55 giay)
```

Sáu bài phủ hai chiều nên không có bản cài đặt hằng số nào lọt: ba bài đòi
`False` (hàng đợi rỗng · job không cần tài nguyên · vừa nhả suất), ba bài đòi
`True` hoặc phân biệt (suất đã hết · lease hết hạn KHÔNG tính là đang giữ ·
`capabilities` được tôn trọng).

Kèm theo: **sửa docstring `claim()`**. Câu *"Trả None nếu hàng đợi trống"* trở
thành sai kể từ việc 1, và phiên ASV **đã tin câu đó** rồi suýt viết một bản vá
dựa trên nó. Một chú thích sai nguy hiểm hơn không có chú thích, vì nó trả lời
tự tin — cùng lý do `ho_so_he_thong.txt` bị gỡ.

---

## Lỗi lần thứ SÁU: kết luận nhân quả không có đối chứng

Tôi đã ghi vào nhật ký này rằng thay đổi `claim()` làm 7 bài `test_448` đỏ. Cơ
sở: 7 bài đỏ **sau** khi tôi sửa, và tôi có một cơ chế hợp lý để giải thích
(claim trả `None` ⇒ vòng lặp `break` trước khi kịp ghi `HOAN`).

Đối chứng thật — thay `platform_core/jobs.py` bằng bản `HEAD` nguyên gốc, chạy
lại **cùng một lệnh**:

| bản `jobs.py` | kết quả |
|---|---|
| của tôi | `7 failed, 14 passed, 2 skipped` |
| `HEAD` gốc | `7 failed, 14 passed, 2 skipped` |

**Giống hệt.** Nguyên nhân thật nằm ở môi trường:

```
('giu_hinh', 'content_process', 'khong provider nao phuc vu duoc: ltt_llm: ban')
```

Máy B bận — máy B chỉ có **một** suất đồng thời.

⭐ Điều đáng ghi không phải "tôi đoán sai", mà là **vì sao lời đoán sống được**:
tôi có một cơ chế **đúng về mặt kỹ thuật** (claim *thật sự* trả `None` khi tài
nguyên đầy) khớp hoàn hảo với triệu chứng. Đây đúng là mục
`gia-thuyet-khop-qua-vua-ket-thuc-dieu-tra` trong memory — một giải thích **sai**
mà khớp **hoàn hảo** thì kết thúc điều tra sớm hơn cả một giải thích dở.

⇒ Luật rút ra, và nó nghiêm hơn luật cũ: **một cơ chế hợp lý không phải bằng
chứng nhân quả.** Bằng chứng duy nhất là *gỡ nguyên nhân bị nghi ra và đo lại*.
Với thay đổi mã, phép đó rẻ: `git show HEAD:<tệp> > <tệp>`, chạy, chép lại.
Mất 90 giây — bằng thời gian gõ một câu suy luận sai vào tài liệu.

⛔ Và nó tốn của phiên khác: ASV nhận một lời buộc tội sai về bộ kiểm của họ, và
suýt đi sửa một thứ không hỏng.

---

## Đo thật: bao nhiêu bên gọi đọc `None` của `claim()`

Không chép lại con số của phiên trước — đếm lại từ mã:

```
grep -rn "claim(" -A 3 tests/ tools/ platform_core/ | grep "is None"
```

| | |
|---|---|
| tệp có đọc `None` | **19** |
| vị trí đọc `None` | **28** |
| trong đó của ASV (`test_4xx`) | **11 tệp** |
| công cụ vòng lặp (`h26_queue_soak`, `bench_llm_admission`, `autosub_gpu_smoke`) | **3** |
| chính nền tảng (`jobs.py`, `job_runner.py`) | **2** |

⭐ Nhưng **hình dạng mới là thứ quyết định**, không phải số đếm. Hai hình dạng
khác hẳn nhau:

- `assert claim(...) is None` — phép kiểm khẳng định một tiền đề *đã dựng sẵn*
  (worker sai năng lực · job hẹn tương lai · job đã huỷ). Ở đó không có
  `ExecutionLease` sống nào, nên nghĩa thứ hai của `None` **không xuất hiện**.
  Đây là 14/19 tệp, và cụm 110 bài xanh xác nhận chúng không bị chạm.
- `if job is None: break` — vòng lặp **suy ra trạng thái hệ thống** từ `None`.
  Chỉ có ở **3 công cụ** và một bộ chạy trong `test_448`.

⇒ Bài học nhỏ nhưng lặp lại cả phiên: **đếm cách dùng, đừng đếm lần xuất hiện.**
28 vị trí trông như 28 chỗ phải sửa; đo theo hình dạng thì còn **4**.

### Rồi đo tiếp cả 4 chỗ đó — và không chỗ nào đang hỏng

Tôi sắp viết bốn bản vá. Trước khi viết, đo xem chúng có **thật sự** rơi vào
nghĩa thứ hai của `None` không — tức job của chúng có khai tài nguyên chia sẻ,
và có `ExecutionLease` nào sống không:

| công cụ | khai `admission_resource` | có giữ lease | đang hỏng |
|---|---|---|---|
| `tools/h26_queue_soak.py` | **không** | không | **không** |
| `tools/autosub_gpu_smoke.py` | **không** | không | **không** |
| `tools/bench_llm_admission.py` | `llm_remote`, 1 suất | **không** | **không** |
| `tests/test_448` (bộ chạy) | có | không (máy B ở ngoài CSDL) | **không** |

Không khai tài nguyên ⇒ `Job.admission_resource == ""` ⇒ nhánh đầu của
`_con_cho_tai_nguyen` cho qua ⇒ bộ lọc **trơ**. Bốn bản vá là **không cần thiết**.

⚠️ Nhưng `bench_llm_admission.py` là một **khuyết tật tiềm ẩn thật**, và nó
thuộc họ *"phép đo lệch chiều"*: nó có khai `llm_remote`. Ngày nào có một lease
`llm_remote` sống song song — lưu lượng thật, hay máy B — vòng `drain` của nó
thoát sớm và báo một `drain_s` **nhanh giả**. Sai số đẩy về phía đẹp, nên không
ai nghi.

⇒ Ghi nợ `N3`, **không sửa bây giờ**: chưa có phép kiểm nào bắt được nó, và sửa
một công cụ đo mà không có cách chứng minh bản sửa đúng thì chỉ đổi một sai số
này lấy một sai số khác.

⭐ Và đây là lần thứ **hai trong một giờ** tôi chặn được cùng một lỗi trước khi
nó vào tài liệu — lần đầu là `test_448`, lần này là bốn bản vá. Cả hai lần thứ
cứu tôi là cùng một câu hỏi: *"tôi đã đo cái gì, hay tôi chỉ có một cơ chế nghe
hợp lý?"*

---

## ĐÍNH CHÍNH lần hai của cùng một chẩn đoán — và ranh giới của một đối chứng

Tôi viết ở trên: *"Nguyên nhân thật nằm ở môi trường — máy B bận."* **Cũng sai.**
Phiên ASV bác bỏ, và tôi đã kiểm lại độc lập:

```
7/7 bai nhan fixture `bc`  ->  _bao_cao()  ->  doc mot TEP TINH
docs/auto_scan_video_v4/evidence/nghiem_thu_hien_hanh.json
    mtime  2026-09-07 20:25
    chua chuoi "khong provider nao phuc vu duoc"  x12
```

Chuỗi `ltt_llm: ban` tôi thấy trong đầu ra **không phải một lỗi vừa xảy ra**. Nó
là **nội dung của một tệp** đã ghi từ hôm trước. Máy B rảnh hay bận thì bảy bài
ấy vẫn đỏ y hệt, cho tới khi ai đó ghi lại bản bằng chứng.

### Điều đáng ghi: một đối chứng chỉ trả lời ĐÚNG MỘT câu hỏi

Phép đối chứng của tôi (`git show HEAD:jobs.py`, chạy lại, cùng kết quả) **đúng
và đủ** — cho câu hỏi *"có phải do thay đổi của tôi không?"*. Nó không nói gì về
*"vậy do cái gì?"*, và tôi đã dùng nó như thể nó nói.

⇒ Luật: **loại trừ một nguyên nhân không xác định được nguyên nhân còn lại.**
Sau một đối chứng âm tính, câu tiếp theo phải là một phép đo MỚI, không phải một
suy đoán được đối chứng kia bảo trợ. Ở đây phép đo mới rẻ hơn cả lần trước: đọc
fixture, `grep` tệp bằng chứng — 30 giây.

### Vì sao nó bắt được BỐN phiên — ASV chỉ ra, và đây mới là phần có giá trị

Không phải bốn lần bốn người cẩu thả. Tệp bằng chứng **chứa nguyên văn một thông
điệp lỗi runtime**, nên đầu ra test trông y hệt một sự cố **đang xảy ra** — và
mọi thứ khác trong ngữ cảnh đều khớp (máy B thật sự chỉ có một suất; hôm trước
thật sự có tranh chấp ba phiên).

⭐ Đây là một **cái bẫy đặt sẵn trong dữ liệu**, không phải một sai lầm cá nhân.
Bản vá đúng cũng không phải "cẩn thận hơn" mà là **đổi thông điệp cho nó thôi
giả dạng một lỗi runtime** — đúng thứ `_chan_tai_nguyen_ban` của ASV làm:

```
LUOT NGHIEM THU NAY KHONG CHAY DUOC - tai nguyen dung chung BAN,
khong phai san pham hong.
```

Một câu, thay vì bảy dòng `AssertionError` trông như sản phẩm hỏng.

⚠️ Và nó là lập luận mạnh cho việc **hoà bản vá của ASV sớm**: chừng nào chưa
hoà, cái bẫy còn nguyên và sẽ bắt phiên thứ năm.


---

## ĐỢT 2.1 — bảng định nghĩa workflow ✅ mã xong, chờ gate

Dải test **950–999** cấp cho LTT WORKFLOW V2. Quyết bằng **đo kho**, không bằng
đọc bảng cấp phát:

```
400-454 ASV · 500-504 (5 tep) · 600-637 CHATLTT · 800-849 (50 tep) · 900-906 Mobile
700-799 de trong (dang cap cho LTT VIDEO AI) · 907+ TRONG
```

⚠️ Bảng cấp phát trong memory ghi *"800–899 CHATLTT"*; đo kho ra **600–637**.
Bảng chép tay lại trôi — đúng lý do `CLAUDE.md` đã bỏ bảng "cái gì đang sống".

### TDD, và lần này có ĐỐI CHỨNG chứ không chỉ có RED

```
RED     12 failed   ModuleNotFoundError: platform_core.workflow
GREEN   12 passed
```

RED chứng minh phép kiểm chạy được. Nó **không** chứng minh phép kiểm bắt được
gì — một hàm trả hằng số cũng làm nó xanh. Nên tiêm hai bản hỏng vào bản GREEN:

| tiêm | kết quả | bài nào bắt |
|---|---|---|
| bỏ `"position"` khỏi `LOAI_TRU_KHOI_HASH` | **3 đỏ** | khai tường minh · bỏ qua trình bày · xuất bản trùng |
| bỏ `sorted(...)` cho `nodes`/`edges` | **1 đỏ** | không phụ thuộc thứ tự node |

Rồi khôi phục ⇒ 12 xanh. Mất 90 giây, và nó là thứ phân biệt *"phép kiểm chạy"*
với *"phép kiểm canh"*.

### Hai chuẩn hoá của `bam_do_thi`, và vì sao cần cả hai

⭐ `json.dumps(sort_keys=True)` **chỉ sắp khoá của dict**, không sắp phần tử của
list. Canvas trả `nodes` theo thứ tự dựng, nên thiếu `sorted(...)` thì kéo–thả
đổi thứ tự mảng ⇒ hash đổi ⇒ version giả. Đây là nửa mà `sort_keys` **trông
như** đã lo hộ.

Nửa kia là `LOAI_TRU_KHOI_HASH`. Không khai thì `position` vào hash, và
`UNIQUE(workflow_id, graph_hash)` mất tác dụng vì **không lần xuất bản nào trùng
lần nào** — ràng buộc vẫn đứng đó, chỉ là không bao giờ chạm tới.

### Migration `a4f81c2d6b95` — đã áp thử trên chuỗi đầy đủ

```
e7b2c94a1d38 -> a4f81c2d6b95
BANG TAO RA: workflow · workflow_draft · workflow_version
             workflow_version_edge · workflow_version_node
workflow_version UNIQUE: uq_workflow_version_seq · uq_workflow_version_hash
```

Chạy từ `base` tới `head` trên một sqlite tạm — không phải chỉ `ast.parse`, mà
**thi hành thật cả 90 bước** rồi soi lược đồ ra bằng `inspect()`.

⛔ Chỉ `CREATE TABLE` mới. Không đổi cột nào đang có, không chạm dữ liệu nào
đang có, chưa nối vào đường chạy nào.

### Không dùng lại `agent_workflows` — và đây là lý do đo được

Bảng cũ trộn **ba vòng đời** vào một hàng: bản đang soạn (sửa được), bản đang
chạy (phải bất biến), phóng chiếu thi hành. Hệ quả trực tiếp: sửa workflow lúc
10:00 thì lượt chạy bắt đầu 09:58 **đổi theo** — không ghim được một lượt chạy
vào đúng nội dung nó khởi động cùng.

`workflow_version` bất biến + `workflow_run.version_id` ghim là cách tách ba
vòng đời ấy ra ba bảng, mỗi bảng một luật ghi.


---

## ĐỢT 2.2 — bảng thi hành, mô hình C ✅ mã xong

```
RED    13 do   (5 failed + 8 error tu fixture)  ModuleNotFoundError
GREEN  13 xanh -> ca cum 950+951+313: 59 passed
```

### Phép kiểm bắt được một câu SAI trong docstring của chính tôi

Bài `test_idempotency_key_trung_bi_CSDL_tu_choi` đỏ dù ràng buộc hoạt động
đúng. Nguyên nhân: tôi bọc `pytest.raises` quanh `db.commit()`, nhưng
`IntegrityError` nổi lên ở **`flush()` bên trong `tao_run`** — hàm phải `flush()`
để có `id`, và `flush()` chính là lúc `INSERT` chạm CSDL.

Docstring tôi viết *"Bên gọi bắt `IntegrityError` ở `commit()`"* — **sai**, và
nó sẽ dạy sai mọi người gọi sau. Đã sửa cả hai, và ghim vế ấy trong phép kiểm.

⇒ Một phép kiểm viết theo *chỗ tôi NGHĨ lỗi xuất hiện* thất bại theo cách chỉ
đúng một nửa: nó đỏ, nhưng lý do đỏ không phải lý do tôi tưởng.

### Đối chứng: ba phép tiêm, ba lần đỏ

| tiêm | đỏ |
|---|---|
| lần chuyển bị từ chối **vẫn** đổi con trỏ | 1 bài |
| **sửa** ảnh chụp cũ thay vì thêm hàng mới | 4 bài |
| bỏ chỉ mục `ux_workflow_run_idem` | 1 bài |

Phép tiêm thứ hai là phép quan trọng nhất: nó biến mô hình **C** thành mô hình
**A** (một khối sửa tại chỗ) — đúng thứ cả đợt này sinh ra để thay. Bốn bài đỏ
nghĩa là ranh giới ấy có người canh, không chỉ có người mô tả.

### ⛔ Và bước HOÀN TÁC của phép tiêm suýt xoá cả hai đợt

Sau phép tiêm thứ ba tôi gõ `git checkout -- platform_core/models.py`. Tệp ấy
**đang giữ 255 dòng chưa commit** của Đợt 1 và Đợt 2. Một lệnh, mất sạch, không
cảnh báo — và `git status` sau đó **sạch**, tức dấu hiệu duy nhất là tệp bỗng
khớp `HEAD`.

Dựng lại được nguyên vẹn vì có **hai** bản sao ngoài kho (`backup_dot1/` và hai
tệp mảnh), xác minh bằng 9 dấu hiệu nội dung rồi 59 phép kiểm.

⭐ Bài học đã ghi vào memory: **phép tiêm nhắm vào một mệnh đề, lệnh hoàn tác
nhắm vào cả tệp.** Hai phạm vi khác nhau, và ta chỉ nghĩ về phạm vi thứ nhất
trong lúc làm. Hoàn tác bằng `cp` từ bản chép trước khi tiêm, không bằng
`git checkout` — `git checkout` hoàn tác về `HEAD`, không về *trước lúc tiêm*.

### Migration `b5c92e3f7a41`

```
a4f81c2d6b95 -> b5c92e3f7a41
BANG: node_run · node_run_snapshot · workflow_run  (+5 bang cua 2.1 = 8)
workflow_run INDEX: ux_workflow_run_idem (BO PHAN, WHERE idempotency_key <> '')
                    + 4 chi muc doc
```

Thi hành thật từ `base` tới `head` trên sqlite tạm, soi lược đồ bằng `inspect()`.


---

## ĐỢT 2.3 + 2.4 — waitpoint và bảng đánh thức ✅

```
RED    23 do   ImportError: platform_core.workflow.cho_doi / danh_thuc
GREEN  23 xanh -> ca cum WF V2 + Dot 1: 82 passed
```

### Ba quyết định của 2.3, ba khiếm khuyết đo được ở kho khác

| | vì sao có | thiếu nó thì |
|---|---|---|
| nhiều-nhiều | `WF-204`: 20 node ForEach cùng chờ **một** job GPU | Activepieces không biểu đạt nổi — và đây là hình dạng **mặc định** của ForEach có tài nguyên chung, không phải ca hiếm |
| `sealed` | `ALL` cần một mẫu số | *"đủ tất cả"* là câu hỏi **không có mẫu số** khi số nhánh động |
| `NOT_DISPATCHED` | một nhánh chết | nhánh ấy không SUCCEEDED cũng không FAILED — nó **vắng mặt**, và barrier treo **vĩnh viễn** |

⭐ Điểm tinh tế ở `da_mo()`: khi `required_successes == 0` và chưa `sealed`,
trả `False` **không** có nghĩa *"chưa đủ"* — nó có nghĩa **"chưa biết"**. Gộp
hai thứ ấy chính là khiếm khuyết mà `sealed` sinh ra để đóng.

### 2.4 — vì sao bảng chứ không phải `NOTIFY`, bằng một con số

```
worker restart 13,6 lan/ngay   (01 §A.6)
```

Một `NOTIFY` phát đúng lúc worker khởi động lại **biến mất không dấu vết**. Bảng
thì không. Đây là *"polling như dự phòng, không phải cơ chế chính"* của
`WF-402` — quét mỗi **5 giây**, vì `NOTIFY` lo phần tức thì.

🔴 **`M2` được đo, không được mô tả.** `test_953` dựng 200 run cùng tới hạn rồi
đếm **câu SQL thật** qua `before_cursor_execute`:

```
assert len(dem) == 1   # 200 run  ->  MOT truy van cho toan he thong
```

Một vòng lặp ẩn trong `den_han()` sẽ hiện ra thành **con số**, không thành một
nhận xét. Phép tiêm T4 xác nhận: viết lại `den_han` thành vòng `db.get()` từng
hàng ⇒ bài này đỏ ngay.

### Đối chứng: bốn phép tiêm, bốn lần đỏ đúng bài

| tiêm | đỏ |
|---|---|
| bỏ qua `sealed` (ALL kết luận luôn) | 1 |
| `NOT_DISPATCHED` coi là **chưa** xong | 1 |
| `chan_node` không luỹ đẳng | 1 |
| `den_han` lặp theo từng run (phá `M2`) | 1 |

⭐ Lần này **hoàn tác bằng `cp`** từ bản chép trước khi tiêm, không bằng
`git checkout` — đúng bài học vừa trả giá ở Đợt 2.2.

### Migration `c6d13a8e4b72`

```
b5c92e3f7a41 -> c6d13a8e4b72
12 BANG (2.1: 5 · 2.2: 3 · 2.3: 3 · 2.4: 1)
waitpoint  ix_waitpoint_due (BO PHAN: status='PENDING' AND due_at IS NOT NULL)
           ux_waitpoint_idem (BO PHAN: idempotency_key <> '')
wakeup     uq_wakeup_khu_trung (run, node_run, kind, due_at)
           ix_wakeup_due (BO PHAN: claimed_at IS NULL)
```

Cả ba chỉ số bộ phận cùng một lý do: **hàng đã chết không được nằm trong chỉ số
mà bộ quét đi qua mỗi 5 giây.**

---

## ĐỢT 2 ĐÓNG — trạng thái

| hạng mục | bảng | test | migration |
|---|---|---|---|
| 2.1 định nghĩa | 5 | 13 | `a4f81c2d6b95` |
| 2.2 thi hành | 3 | 13 | `b5c92e3f7a41` |
| 2.3 waitpoint | 3 | 13 | `c6d13a8e4b72` |
| 2.4 đánh thức | 1 | 10 | *(cùng trên)* |
| **tổng** | **12** | **49** | **3** |

Cộng Đợt 1 (`test_313`, 33 bài) = **82 bài xanh**.

Kiểm tĩnh: `ruff` sạch · `i18n` không tăng · `test_147_layering` 8 xanh ·
`lint_app_contract` 21 app ERROR 0 · `check_bo_qua` PASS.

⛔ **Chưa nối vào đường chạy nào.** Đợt 2 chỉ là lược đồ + service + test, đúng
`27_29 §28`. Scheduler là Đợt 3.


---

## ĐỢT 3A + 3B — máy trạng thái và hệ con `finally` ✅

```
RED    21 do    (bang chuyen + ket so chua ton tai)
GREEN  21 xanh  -> ca cum Workflow V2 + Dot 1: 121 passed
```

### 3A — ba trạng thái, ba khiếm khuyết của chính BẢN NHÁP CỦA TA

Khác Đợt 2 (vá khiếm khuyết của kho khác), ba thứ này vá bản nháp `WF-207`:

| trạng thái | thiếu nó thì |
|---|---|
| `RUNNING_WITH_WAITPOINTS` | ForEach có vài vòng xong + vài vòng đang chờ là một run **có thật mà không có tên**. `RUNNING ⇄ WAITING` tách rời không biểu đạt nổi |
| `SYSTEM_FAILURE` tách `FAILED` | hai chuyện khác nhau về **tiền** và **cảnh báo** bị gộp vào `AGENT_ERROR` (`G21`) |
| `ABANDONED` | provider **có thể đã nhận** — `AmbiguousProviderError` 10 lần/28 ngày là có thật, và thử lại có thể tính tiền hai lần |

⭐ **Lần chuyển bị TỪ CHỐI vẫn ghi một ảnh chụp** (`is_valid=False`), kèm lý do
dạng `PENDING -> SUCCEEDED khong nam trong bang`. Không ghi thì thứ duy nhất
còn lại là trạng thái cuối — thứ **không nói ai đã thử gì**.

### 3B — `M10`: 145 → 0, và nguyên nhân là HÌNH DẠNG

```
145 dong "GIU CHO TREO: <n> khoan, <n> credit cua khach dang bi giu"  / 28 ngay
```

Khoản giữ chỗ treo là **tiền của khách bị giam**: số dư hiển thị thấp hơn thực
tế, không lệnh nào của khách gỡ được, và nó **không gây lỗi, không gây cảnh
báo** — chỉ im lặng cho tới khi ai đó đọc log.

⭐ Nguyên nhân không phải sự cẩu thả: `_terminal_status` ghi trạng thái ở một
chỗ, `budget.settle` kết sổ ở chỗ khác, và **giữa hai chỗ là một cửa sổ**.
Worker restart 13,6 lần/ngày ⇒ cửa sổ ấy được **thử 13,6 lần mỗi ngày**.

⇒ Bản vá không phải *"nhớ gọi settle"* mà là **gộp hai thao tác vào một
  transaction**: `chuyen_run()` gọi thẳng `ket_so()`.

🔑 Và `test_955` kiểm điều đó bằng **rollback**, không bằng đọc mã: nếu hai
thao tác ở hai transaction thì một trong hai **sống sót** qua rollback. Cả hai
cùng biến mất mới là bằng chứng chúng cùng một transaction.

### Vì sao cần một CỘT `ket_so_luc`, không phải một suy luận

Suy từ `hold_id == ""` sai ở đúng cách nguy hiểm:

```
hold_id rong  ->  co the la "da ket so"
              ->  cung co the la "run nay CHUA BAO GIO co giu cho"
```

Hai chuyện khác hẳn, một giá trị. `ket_so_luc IS NULL` nói về **hành động**,
không nói về **hậu quả** của hành động.

### Đối chứng: năm phép tiêm, năm lần đỏ

| tiêm | đỏ |
|---|---|
| không ghi ảnh chụp khi bị từ chối | 2 |
| kết sổ **ngoài** transaction chuyển | **6** |
| `SYSTEM_FAILURE` vẫn thu tiền | 1 |
| tính cả hàng `is_valid=False` | 1 |
| kết sổ không luỹ đẳng | 1 |

Phép tiêm thứ hai đỏ **6 bài** — đúng như mong đợi: gỡ hệ con `finally` ra khỏi
transaction là gỡ toàn bộ `M10`.

### Và một phép kiểm XANH-RỖNG tôi tự bắt được

`test_goi_ket_so_LAN_HAI` ban đầu chỉ đếm `CreditEntry`. Mã hiện tại **chưa ghi
`CreditEntry` nào**, nên "không tăng" đúng **cả khi** kết sổ chạy lại từ đầu —
bài ấy xanh mà không đo gì. Đã siết: `lan_hai is False` **và** `ket_so_luc`
không bị ghi đè.

⭐ Đây là dạng lỗi mà đối chứng-bằng-tiêm **không bắt được**: tiêm một lỗi vào
`ket_so` vẫn để bài ấy xanh. Thứ bắt được nó là câu hỏi *"bài này sẽ đỏ khi
nào?"* — và câu trả lời hoá ra là **không bao giờ**.

### Migration `d7e24b9f1c53`

```
c6d13a8e4b72 -> d7e24b9f1c53
workflow_run + ket_so_luc (nullable) + ly_do_ket_so
```

Hai cột mới trên một bảng chưa ai dùng. Thi hành thật từ `base` tới `head`.

### Còn lại của Đợt 3

`3.3` middleware trên cạnh (3 hook, `G45` — quyền tool kiểm **lúc thi hành**) ·
`3.4` bộ chaos giết tiến trình ở 10 điểm (`M6`: 10/10 cùng kết quả).


---

## ĐỢT 3C + 3D — middleware cạnh và bộ chaos ✅ · ĐỢT 3 ĐÓNG

```
3C middleware  11 xanh      3D chaos M6  5 xanh
ca cum Workflow V2 + Dot 1: 139 passed  (98 xanh ca khi NGAU NHIEN HOA thu tu)
```

### 3C — vì sao middleware chứ không phải một `if` trong scheduler

`WF-903` là một lỗ **có thật**, và nó sinh ra từ một tính chất ta **muốn**:

> `validate_plan` lọc theo `app_access` (đúng), nhưng một `WorkflowVersion`
> **đã publish** có thể chạy **sau khi quyền bị thu hồi**.

Version **bất biến** — nó giữ nguyên nội dung đã duyệt kể cả khi quyền của chủ
nó đã đổi. Bất biến là thứ khiến tái dựng được, và **chính nó** tạo ra lỗ này.
Nên bản vá không thể nằm ở `validate`; nó phải nằm ở **thời điểm truyền**.

⛔ **Fail-CLOSED khi hook ném lỗi.** Đây là chỗ cắm của kiểm quyền, nên một hook
   lỗi mà cho đi tiếp là **mở cổng khi bộ gác ngã**.

⛔ **Tên điểm cắm sai bị từ chối NGAY.** Một hook gắn vào điểm không tồn tại là
   một hook **không bao giờ chạy** — nếu nó là hook quyền thì đó là một cổng mở
   mà không ai thấy.

### 3D — `M6` và ba lần phép kiểm xanh vì lý do SAI

Bộ chaos đầu tiên **4/4 xanh ngay lượt đầu**. Đối chứng cho thấy nó yếu hơn tên
gọi của nó: trong ba phép tiêm, **chỉ một** làm nó đỏ.

| tiêm | lượt đầu | sau khi sửa bộ kiểm |
|---|---|---|
| node: chuyển từ trạng thái kết thúc được chấp nhận | **2 đỏ** ✅ | 2 đỏ |
| run: gỡ rào `hien in RUN_KET_THUC` | **0 đỏ** ❌ | **1 đỏ** ✅ |
| `ket_so` mất tính luỹ đẳng | **0 đỏ** ❌ | **1 đỏ** ✅ |

**Nguyên nhân, và cả hai đều đáng ghi:**

⭐ **Rào `hien in RUN_KET_THUC` là MÃ CHẾT.** Không trạng thái kết thúc nào là
*khoá* của `RUN_CHUYEN`, nên mệnh đề `sang not in RUN_CHUYEN.get(hien, ...)` đã
đủ — rào kia **không bao giờ chạy**. Bài `test_run_da_ket_thuc_thi_khong_chuyen_nua`
xanh vì một lý do **khác lý do nó khai**.

⇒ Vá bằng cách làm cái rào **sống**: `monkeypatch` mở một đường ra khỏi `FAILED`
  trong bảng rồi đòi rào vẫn chặn. Đó là cách duy nhất nó có nghĩa — nó phòng
  đúng một chuyện: **một lần sửa bảng trong tương lai**. Cộng một bất biến cấu
  trúc `set(RUN_CHUYEN) & RUN_KET_THUC == set()`.

⭐ **Đường phát lại không bao giờ gọi `ket_so` lần hai** — `chuyen_run` tới
trạng thái kết thúc đã bị từ chối trước đó. Nhưng **bộ dọn nền thì có gọi**, và
đó chính là kiến trúc cũ mà `M10` sinh ra để thay. Thêm bài đo đúng đường ấy.

⚠️ Và bài mới ấy **vẫn** xanh ở lượt đầu, vì `_anh_chup_ket_qua` chỉ giữ
`da_ket_so` là một **bool** — một lần kết sổ chạy lại từ đầu cho ra ảnh chụp y
hệt. Phải so cả `ket_so_luc` mới thấy. **Ba tầng, ba lần xanh sai.**

🔑 Bài học tổng quát của cả ngày, ở dạng chặt nhất: **đối chứng-bằng-tiêm chỉ
mạnh bằng độ mịn của thứ phép kiểm SO SÁNH.** Tiêm đúng chỗ mà so bằng một
bool thì vẫn xanh.

### `M6` — thứ ngưỡng này thật sự hỏi

Không phải *"có khôi phục được không"* mà **"khôi phục có ra CÙNG một kết quả
không"**. Câu thứ hai khó hơn hẳn: một hệ có thể khôi phục được mà vẫn **thu
tiền hai lần**. 10 điểm giết + 1 lượt không giết ⇒ 11 lượt, cùng một ảnh chụp
(trạng thái · chi phí · giữ chỗ · trạng thái từng node).

⭐ Và mô hình C trả công ở đây: sau một lần giết, ta đọc được **cả đường đi thật
lẫn những bước bị từ chối lúc phát lại**. Một khối JSON sửa tại chỗ thì lần phát
lại **ghi đè** mất dấu vết của lần chết.

---

## ĐỢT 3 ĐÓNG — trạng thái

| | test | nội dung |
|---|---|---|
| 3A máy trạng thái | 13 | `RUNNING_WITH_WAITPOINTS` · `SYSTEM_FAILURE` · `ABANDONED` · ghi lần chuyển bị từ chối |
| 3B `finally` | 8 | `M10` 145 → 0, kết sổ trong **cùng transaction**, kiểm bằng rollback |
| 3C middleware cạnh | 11 | 3 hook, fail-closed, `WF-903` kiểm quyền lúc thi hành |
| 3D chaos | 5 | `M6` 10/10 điểm giết → cùng kết quả |
| **tổng** | **37** | migration `d7e24b9f1c53` |

Cộng Đợt 1 + 2 ⇒ **139 bài xanh**, và **98 xanh cả khi ngẫu nhiên hoá thứ tự**
(sổ hook là trạng thái toàn cục — fixture `sach` dọn trước/sau mỗi bài).

⛔ Vẫn **chưa nối vào đường chạy nào**. Ba hệ con còn lại của scheduler
(`enqueue` · `dequeue` · `attempt` · `foreach` · `ttl`) là Đợt 4–5.

## ĐỢT 2–5

Chưa bắt đầu. Xem `27_29 §28`.

**Tiền kiểm Đợt 2 đã làm** (chỉ đọc): 14 bảng đề xuất so với **78 bảng đang có**
⇒ **0 va chạm tên, 0 tên gần giống**. Bảng nền tảng không mang tiền tố (đúng quy
ước: `jobs`, `users`, `credit_entries`), và `AppManifest.table_prefix` đã bảo vệ
chiều ngược lại — app muốn có `artifact` riêng vẫn phải viết `<prefix>_artifact`.

---

*Cập nhật sau mỗi đợt. Đợt chỉ được ✅ khi cổng đầy đủ xanh trên cây đứng yên.*
