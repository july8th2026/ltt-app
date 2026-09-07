# P06 — tệp · tri thức · tìm kiếm · MCP. Kế hoạch viết SAU khi làn A đóng

**2026-09-06.** `00_KE_HOACH_V3.md` cố ý hoãn kế hoạch này: *"viết bây giờ là
viết trên một kiến trúc chưa tồn tại"*. Làn A đóng 06/09 (17,0/17,0 ngày công,
deploy `334004d4`), nên viết được rồi.

⛔ Tệp này **không** mô tả thứ sẽ xây. Nó ghi **thứ đã đo được** và những quyết
định mà các số ấy ép ra. Phần nào chưa đo thì ghi **CHƯA ĐO**, không đoán.

---

## §1 — Đo trước: cái gì đã có, cái gì chưa

Đo 06/09 bằng `git grep` có **ranh giới từ** (`\b…\b`) — bản đo đầu dùng
substring và cho `rag` khớp trong `storage`, `mcp` khớp trong tên khác.

| Năng lực | Trạng thái | Ở đâu |
|---|---|---|
| Tải lên + phiên tải lên | ✅ **có** | `platform_core/upload_sessions.py`, `server/api/uploads.py` |
| Lưu trữ + sở hữu | ✅ **có** | `platform_core/storage.py` |
| Kiểm ảnh đầu vào | ✅ **có** | `platform_core/image_input.py` |
| Trích văn bản PDF | 🟡 **một chỗ** | `apps/chataistudio/features.py:48` — `pypdf`, chưa phải hạ tầng |
| Hàng đợi job + lease | ✅ **có** | `platform_core/job_runner.py`, `leases.py` |
| Trích `.docx`/`.xlsx`/… | ❌ **chưa** | — |
| Chỉ số + truy hồi | ❌ **chưa** | — |
| Trích dẫn có nguồn | ❌ **chưa** | — |
| Tìm kiếm web | ❌ **chưa** | (`codex_sidecar` có cờ `web_search` nhưng đó là đường ChatGPT, **không** phải tool LTT) |
| MCP | ❌ **chưa** | chỉ có tên trong tài liệu; `codex_sidecar` **tắt** MCP có chủ ý |

⇒ P06 xây **bốn** thứ mới trên một nền đã có tải lên/lưu trữ/hàng đợi. Đó là lý
do ước 3–5 tuần chứ không phải 3–5 ngày.

---

## §2 — 🔴 Quyết định lớn nhất: KHÔNG dùng vector, và đây là số ép ra nó

Đo trên chính máy chủ production (chỉ đọc catalogue, không chạm một hàng dữ liệu
người dùng nào):

```
PostgreSQL 17.10
so phan mo rong ten chua 'vector'  ->  0        <- pgvector KHONG CO
pg_trgm  1.6   co san, chua cai
unaccent 1.1   co san, chua cai
```

**Ba lý do, và lý do thứ hai là lý do thật:**

1. **`pgvector` không có.** Cài nó là một thao tác **cấp máy chủ** (build/cài
   phần mở rộng, cần quyền), tức một ranh giới phải có người — cùng hạng với
   deploy.
2. 🔑 **Model nhà phục vụ MỘT lượt tại một thời điểm** (R1, đo ở P01/P02, và
   `--parallel 1` của llama-swap). Sinh embedding cho một kho tài liệu là hàng
   nghìn lời gọi — chúng sẽ **xếp hàng cùng chỗ với chat của khách**. Một tính
   năng nền không được phép cạnh tranh với đường người dùng đang ngồi đợi.
3. Không có `pgvector` thì kho vector phải nằm **ngoài** CSDL ⇒ một nguồn chân
   lý thứ hai, một lượt sao lưu thứ hai, một tầng ACL thứ hai. Ba thứ đó lệch
   nhau vào đúng ngày không ai nhìn.

⇒ **Truy hồi bản đầu = tìm kiếm toàn văn của chính Postgres.** Cùng CSDL, cùng
ACL, cùng lượt sao lưu, không tiến trình nền nào.

⛔ **KHÔNG phải "vector là sai".** Nó là **HOÃN có điều kiện**, và điều kiện viết
ra được: *khi có `pgvector` trên máy chủ **và** có một đường sinh embedding không
đi qua suất chat của khách*. Ngày đủ hai điều đó, đây là một quyết định để mở
lại, không phải một bức tường.

---

## §3 — Tìm kiếm toàn văn có dùng được cho TIẾNG VIỆT không? Đo, không suy

Postgres **không có** cấu hình `vietnamese` (30 cấu hình có sẵn, không cái nào).
Nên câu hỏi thật là: `simple` có đủ không?

Đo bằng cách gọi thẳng `to_tsvector`/`plainto_tsquery` trên một đoạn tiếng Việt
thật (không tạo bảng, không ghi gì):

```
van ban: "Gia moi luot goi duoc tinh theo so token that su dung.
          Phan le duoi mot credit duoc cong don sang luot sau."   (co dau day du)

to_tsvector('simple', ...) -> 'credit':17 'cộng':19 'dùng':12 'dưới':15
                              'dồn':20 'giá':1 'gọi':4 'lượt':3,22 'lẻ':14 ...
```

⭐ **`simple` tách từ tiếng Việt ĐÚNG** — tách theo khoảng trắng, hạ chữ thường,
**giữ nguyên dấu**. Không cần từ điển.

Khớp câu hỏi (đo lại **sau khi cài `unaccent`** trên `lttplatform_test`):

| Câu hỏi | không `unaccent` | có `unaccent` |
|---|---|---|
| `"phần lẻ credit"` (có dấu) | ✅ KHỚP | ✅ KHỚP |
| `"phan le credit"` (không dấu) | ❌ | ✅ **KHỚP** |
| `"cong don luot sau"` | ❌ | ✅ **KHỚP** |
| `"so token that su dung"` | ❌ | ✅ **KHỚP** |
| `"tinh theo token"` | ❌ | ✅ **KHỚP** |

🔴 **Bốn dòng giữa là cái lỗ thật**, và chúng là ca **thường gặp nhất**: người
Việt gõ nhanh thì gõ không dấu. Một tìm kiếm không tìm được `"phan le credit"`
là một tính năng phần lớn người dùng thấy là hỏng.

### ⛔ Và ví dụ ĐẦU TIÊN tôi dùng ở đây là một ví dụ BẨN

Bản đầu của mục này ghi `"tinh tien theo token"` → ❌, và kết luận *"không khớp
**vì không dấu**"*. **Sai.** Đo lại:

```
"tinh tien theo token"   (khong dau)  ->  KHONG khop
"tính tiền theo token"   (CO dau)     ->  KHONG khop     <- van truot!
```

Từ `"tiền"` **không có** trong văn bản mẫu. `plainto_tsquery` nối các từ bằng
**AND**, nên **một** từ vắng mặt làm cả câu trượt — **giống hệt** triệu chứng
thiếu dấu. Hai nguyên nhân, một triệu chứng.

⭐ Thứ bác nó không phải một lần đọc lại, mà là **chạy phép kiểm trên máy chủ
thật**: `test_821` đỏ đúng ở ca ấy và xanh ở bốn ca sạch. Nếu tôi chỉ chạy nó ở
chế độ `skipped` — như lần đầu, vì thiếu `LTT_TEST_DATABASE_URL` — thì ví dụ bẩn
đã nằm lại trong kế hoạch và trong docstring của migration.

🔑 Đã ghim sự phân biệt ấy bằng `test_MOT_TU_VANG_MAT_truot_GIONG_HET_thieu_dau`,
để nó là một phép kiểm chứ không phải một dòng ghi chú.

⇒ **`unaccent` là bắt buộc, không phải tuỳ chọn.** Nó **có sẵn** trên máy chủ
nhưng **chưa cài**:

```
SELECT unaccent('Phần lẻ')
  -> UndefinedFunction: function unaccent(unknown) does not exist
```

Cài là `CREATE EXTENSION unaccent` — một migration, cần quyền tạo extension.

### ✅ ĐÃ ĐO (06/09): cài được bằng migration thường, KHÔNG cần người

```
tai khoan : ltt_app     superuser: False
CSDL      : lttplatform  co quyen CREATE tren CSDL: True
unaccent  1.1   trusted=True
pg_trgm   1.6   trusted=True
```

Từ PostgreSQL 13, một phần mở rộng đánh dấu **trusted** cài được bởi người dùng
chỉ cần `CREATE` trên CSDL — **không** cần superuser. `ltt_app` có đúng thế.

⇒ `CREATE EXTENSION unaccent` là **một migration bình thường**, không phải một
ranh giới cần người. Đây là khác biệt lớn so với `pgvector` (§2): cùng là "một
phần mở rộng", nhưng một cái **có sẵn và trusted**, cái kia **không có trên máy**.

⭐ Và phép đo này rẻ hơn hẳn hậu quả của việc đoán: đoán "cần người" thì P06 bị
xếp sau một ranh giới không tồn tại; đoán "tự cài được" mà sai thì migration
hỏng giữa lượt deploy.

---

## §4 — Thứ tự làm, và vì sao thứ tự ấy

Mỗi bước phải **đứng một mình được** và có phép kiểm riêng. Không bước nào mở
cho model gọi cho tới bước cuối — cùng luật P05 (`CHO_MODEL_GOI` mở **sau cùng**).

| # | Việc | Vì sao trước/sau |
|---|---|---|
| 1 | **Đo quyền `CREATE EXTENSION`** + cài `unaccent` (migration chỉ-thêm) | Rẻ nhất, và nó **quyết định** bước 4 làm được hay phải xin người |
| 2 | **Bảng tệp + sở hữu + vòng đời** (`chatltt_tep`), tái dùng `upload_sessions` + `storage` | Mọi thứ sau đều treo vào đây. Sở hữu là **bề mặt quyền mới** ⇒ test ACL trước, không sau |
| 3 | **Trích văn bản** → `chatltt_doan` (chunk có `tep_id`, `thu_tu`, `trang`) | Trích là việc **dài** ⇒ đi qua hàng đợi job (trần Cloudflare 100 s). Tái dùng `pypdf` đã có, không thêm phụ thuộc mới nếu chưa cần |
| 4 | **Chỉ số FTS + truy hồi** (`tsvector` + GIN, `unaccent`) | Cần bước 1 và 3 |
| 5 | **Trích dẫn** — mỗi câu trả lời trỏ về `(tep_id, doan_id, trang)` | Không có bước này thì truy hồi là một cái máy nói linh tinh có tự tin |
| 6 | **Mở cho model** (`CHO_MODEL_GOI` + `chinh_sach`) | **Bước cuối.** Trước đó không một hành vi nào người dùng thấy đổi |

⛔ **MCP KHÔNG nằm trong sáu bước trên.** Nó là một **cửa vào thứ hai** cho
những tool ta không viết, tức một bề mặt chính sách mới hoàn toàn. Nó chỉ được
xét **sau khi** sáu bước trên chạy — và khi ấy nó phải là **adapter về hợp đồng
tool LTT** (đi qua `chieu_tool` + `thi_hanh` + duyệt), **không** phải một đường
vòng qua chính sách. Ghi ở đây để không ai coi nó là "một phần của P06 nên làm
luôn".

---

## §5 — Ba ràng buộc đã trả giá, chép sang từ làn A

1. **Kết quả tool là dữ liệu KHÔNG TIN ĐƯỢC.** P01 đo: model **tin dữ liệu** của
   tool (5/5 lặp lại một con số sai) trong khi **không nghe mệnh lệnh** tiêm vào
   (30/30 từ chối). ⇒ Bề mặt lớn hơn không phải lệnh tiêm, mà là **dữ liệu sai
   đi thẳng vào câu trả lời**. Với tệp/web thì đó là ca **thường**, không phải ca
   hiếm.
2. **Việc dài hơn vài giây bắt buộc qua hàng đợi job.** Trần Cloudflare 100 s.
   Trích một PDF 300 trang không nằm trong một request.
3. **Đừng dựng hàng đợi thứ hai.** `job_runner` + `leases` đã có. Một vòng
   `while` chờ trong luồng web là một bộ đợi thứ hai, và nó không sống qua
   restart mà `job_runner` sống qua.

---

## §6 — Điều kiện dừng của P06

**Đạt khi:**

- tải lên → trích → chỉ số → hỏi → **trích dẫn trỏ đúng trang** cho cả PDF lẫn
  văn bản thuần;
- hỏi **không dấu** tìm được tài liệu **có dấu** (đây là phép kiểm phân biệt
  được `unaccent` đã cài với chưa);
- **test ACL**: người dùng A không đọc được tệp, đoạn, hay trích dẫn của B —
  kiểm ở **cả ba** tầng, không chỉ tầng route;
- một tệp bị xoá thì đoạn và chỉ số của nó **biến mất cùng lượt**, không để lại
  trích dẫn mồ côi;
- injection từ nội dung tệp là **kịch bản kiểm bắt buộc**, không phải ghi chú.

⛔ **DEFERRED, ghi rõ chứ không tính PASS:** code sandbox (chỉ khi có sandbox
chứng minh được), tìm kiếm web (cần một nhà cung cấp và một quyết định chi phí),
MCP (xem §4).

---

## §7 — 🔴 Ngã ba của bước 2: tệp treo vào ĐÂU, và ai trả tiền cho chỗ ấy

Đo 06/09 — `platform_core/upload_sessions.py` **đã có** trọn vòng đời tệp, giàu
hơn tôi tưởng:

```
create -> confirm -> { promote | attach_to_project }
trang thai : draft · confirmed · promoted · attached
han luu    : PROMOTED_RETENTION_DAYS = 30 · DRAFT_RETENTION_DAYS = 30
tran       : 20 phien dang mo · 2 GiB · 12 lan tao/phut
so huu     : user_id + app_slug + tien to "{app_slug}/{user_id}/"
```

⇒ **Không dựng bảng tệp song song.** `UploadSession` *là* bản ghi tệp bền.

### Nhưng cả hai cửa đều đòi một thứ chatltt chưa có

| Cửa | Đòi | Hạn lưu |
|---|---|---|
| `promote(job=…)` | job **đang giữ credit** (`credit.so_da_giu > 0`) | 30 ngày |
| `attach_to_project(project_id=…)` | một `AppProject` của người dùng | 30 ngày |

🔴 **chatltt KHÔNG có `AppProject`.** `git grep AppProject` khớp
`apps/chatltt/services/hoi_thoai.py`, nhưng đọc ra thì đó là một **chú thích**
trích con số 30 ngày của nền tảng — không phải một lần dùng. *(Cùng bẫy đã ghi:
`grep` **thấy** cũng không chứng minh năng lực **có**.)*

Và cửa thứ nhất mang theo một **quyết định sản phẩm**, viết sẵn trong docstring
của chính nó:

> *"Cửa 'phải giữ credit mới được lưu file' tồn tại để **không ai biến input của
> job thành kho lưu trữ miễn phí**."*

### Quyết định: đi cửa `promote`, và trích văn bản LÀ một job có phí

**Bốn lý do, và lý do thứ ba là lý do quyết:**

1. **Không sửa nền tảng.** Hai cửa đã có; thêm cửa thứ ba là sửa
   `platform_core/upload_sessions.py` — ngoài ranh giới app, và `CLAUDE.md` đòi
   dừng lại nói rõ vì sao trước khi làm thế.
2. **Trích văn bản thật sự là một job**: dài hơn vài giây (trần Cloudflare
   100 s), cần hàng đợi, cần lease. Nó **đã** đúng hình dạng một job.
3. 🔑 **Cái cửa ấy chặn đúng lỗ hổng lớn nhất của chính tính năng này.** Một kho
   tri thức là **đúng thứ** người ta dùng để biến nền tảng thành ổ đĩa miễn phí.
   Gỡ cửa cho tiện là tự mở lỗ mà docstring kia viết ra để bịt.
4. Hạn 30 ngày + trần 2 GiB + 12 lần/phút **đã có sẵn**, không phải nghĩ lại.

⛔ **Hệ quả phải nói với người dùng, không được giấu:** tải một tài liệu lên để
hỏi **tốn credit**, vì nó chạy một job trích. Giá phải nhỏ và phải hiện **trước**
khi bấm — đi qua đúng đường duyệt của P04 (`bao_gia` → phiếu → bấm), không phải
một khoản trừ âm thầm.

⭐ Và điều này **hoãn được** phạm vi `project`: ba phạm vi của P06 là *lượt · hội
thoại · project*, nhưng project là chuyện của **P07**. Bản đầu chỉ làm phạm vi
**hội thoại**, và ghi rõ hai phạm vi kia là CHƯA LÀM chứ không phải đã cân nhắc
rồi bỏ.

### ✅ ĐÃ ĐO: `Job` mang được, nhưng KHÔNG nên là chỗ duy nhất

`Job` có `params: dict` (cột JSON), nên `conversation_id` **nhét được** vào đó.
Nhưng nếu đó là chỗ **duy nhất** thì hai thứ hỏng:

1. Liệt kê *"tệp của hội thoại X"* thành một truy vấn JSON xuyên bảng `jobs` —
   bảng nóng nhất của nền tảng, và là bảng của **mọi app**, không riêng chatltt.
2. 🔴 **Vòng đời tệp bị buộc vào vòng đời job.** Governance khai `jobs` là dữ
   liệu **vận hành** (tự già đi theo hạn riêng), còn `chatltt_*` là **CONTENT**
   (*"không tự già đi"*). Treo tri thức của khách vào một bảng tự dọn là đúng ca
   đã ghi ở P03 (`chatltt_run` **không thể** là `OPERATIONAL`), lặp lại y hệt.

⇒ **Một bảng liên kết nhỏ trong `apps/chatltt/tables.py`**, và nó **không** chứa
byte nào: `(user_id, conversation_id, upload_id, job_id, trạng thái trích)`.
`UploadSession` vẫn là bản ghi tệp; bảng này chỉ mang **phạm vi** và **tiến độ
trích**.

⭐ Đúng ranh giới app: thêm một bảng có `table_prefix` là việc của app, không
phải sửa nền tảng.

---

## §8 — Bước 2 đã làm xong: cái gì tồn tại, và cái gì CỐ TÌNH chưa tồn tại

| Thứ | Ở đâu |
|---|---|
| Bảng `chatltt_tep` (không byte nào) | `apps/chatltt/tables.py` |
| Migration chỉ-thêm `a3f92c5d7e14` | `alembic/versions/20260906_1100_chatltt_tep.py` |
| Bề mặt quyền `gan` / `cua_hoi_thoai` / `mot` / `danh_dau` | `apps/chatltt/services/kho_tep.py` |
| Hàng governance **CONTENT** | `platform_core/public_api/governance.py` |
| 15 phép kiểm ACL, viết **trước** mã | `tests/test_822_chatltt_kho_tep_so_huu.py` |

### Ba cửa quyền, và bằng chứng từng cửa CHỊU LỰC

15 phép kiểm xanh ngay lượt đầu là thứ **đáng nghi**, không đáng mừng — nên đo
bằng đột biến, gỡ đúng một dòng mỗi lần:

| Gỡ gì khỏi `kho_tep.py` | Kết quả |
|---|---|
| dòng lọc `user_id` ở `cua_hoi_thoai` | `test_nguoi_KHAC_khong_liet_ke_duoc…` **đỏ** |
| `danh_dau` không gọi `mot()` mà `db.get` thẳng | `test_nguoi_KHAC_khong_doi_duoc_trang_thai…` **đỏ** |
| bỏ cửa `status not in SAN_SANG` | `test_upload_CHUA_promote_thi_KHONG_gan_duoc` **đỏ** |

⭐ Mỗi lần chỉ **một** phép kiểm đỏ. Đó là dấu hiệu ba cửa độc lập, không phải
một cửa được đếm ba lần.

### Một phép kiểm đã tự mạnh hơn thứ nó đo, và đã bị sửa

Bản đầu của `test_migration_…` quét AST **cả module** và cấm `drop_table`. Nó sẽ
đỏ vì `downgrade()` — một dòng **đúng**, và chính là dòng chứng minh migration
này hạ lại được mà không mất hàng nào. Mệnh đề thật là *"**`upgrade`** chỉ
thêm"*, nên phép kiểm giờ đọc riêng thân `upgrade()`, và chốt thêm rằng
`downgrade()` **phải** có `drop_table`.

### Cái CỐ TÌNH chưa có

- **Chưa có route.** Không HTTP nào gọi được `kho_tep` — người dùng chưa đính
  tệp được. Đúng luật §4: không bước nào đổi hành vi người dùng thấy cho tới
  bước 6.
- **Chưa trích chữ.** `trang_thai_trich` mới chỉ là một cột; thứ đổi nó là job ở
  bước 3.
- **`chatltt_doan` chưa tồn tại.** Nó thuộc bước 3, và tạo trước là tạo một bảng
  rỗng không ai ghi vào — thứ trông như tính năng đã có.

---

## §9 — 🔴 Bước 3 dựa trên một câu SAI, và phép đo bác nó

§4 dòng 3 viết: *"Tái dùng `pypdf` **đã có**, không thêm phụ thuộc mới nếu chưa
cần"*. Câu ấy dựa vào việc `apps/chataistudio/features.py:48` có dòng
`from pypdf import PdfReader` — tức tôi đọc **một lời gọi** và kết luận về **một
thứ được cài**. Hai chuyện khác nhau.

Đo 06/09 lúc ~10:46:

| Hỏi | Trả lời |
|---|---|
| `grep -in pypdf requirements*.txt` (cả 4 tệp) | **không dòng nào** |
| `C:\LTTPlatform\venv\Scripts\python.exe -c "import pypdf"` | `ModuleNotFoundError` |
| Dịch vụ web thật chạy venv nào | pid 14476 / 26056 → đúng `C:\LTTPlatform\venv` |
| `python -c "import pypdf"` (trình chạy test) | `ModuleNotFoundError` |

⇒ **`pypdf` không tồn tại ở đâu cả.** Bước 3 không "tái dùng" được thứ gì; nó
phải **thêm một phụ thuộc**, và điều đó đổi hình dạng bước 3: có một bước cài
đặt trên máy chủ, tức chạm vào ranh giới cần chủ dự án.

### Và nó lôi ra một lỗi ĐANG SỐNG, không thuộc P06

`chataistudio` khai `enabled=True, public=True`, còn ô chọn tệp
(`templates/chataistudio.html:44`) có `accept=...,application/pdf` — giao diện
**mời** khách chọn PDF. Nhánh PDF bọc `except Exception` rồi báo lại *"Không đọc
được nội dung PDF."* ⇒ `ImportError` bị nuốt và trình bày thành **lỗi của tệp
khách**, trong khi nguyên nhân là máy chủ thiếu thư viện.

⛔ Không sửa ở đây. Nó nằm ngoài P06 và thuộc một app khác đang phục vụ khách —
gộp vào một commit H44 là trộn hai việc có mức rủi ro khác nhau. Đã tách thành
một việc riêng.

### Bài học, và nó lặp lại một dòng đã có trong memory

*"Đọc thứ đại diện thay vì đọc thứ thật"* — một câu `import` là **đại diện** cho
một phụ thuộc, không phải **bản thân** phụ thuộc. Cách hỏi đúng là hỏi chính
trình thông dịch **đang chạy dịch vụ**, và đó là cùng một luật CLAUDE.md đã đặt
cho câu "hiện giờ cái gì đang sống": **hỏi máy chủ, đừng đọc tài liệu**.

### Đo rộng ra: **không** thư viện trích chữ nào tồn tại

Hỏi thẳng venv sản phẩm, chín tên một lượt:

    pypdf  PyPDF2  fitz  pdfminer  pdfplumber  docx  openpyxl  markitdown  unstructured
      -      -      -       -          -        -       -          -            -

Và `grep -rln "extract_text\|PdfReader\|pdfminer" apps/ platform_core/` trả về
**đúng một** tệp: `apps/chataistudio/features.py`. Tức nền tảng chưa từng trích
chữ khỏi tệp được lần nào — dòng mã trông như một năng lực đã có chỉ là một lời
gọi chưa bao giờ chạy tới.

### Hệ quả cho thứ tự làm

Bước 3 **bị chặn** bởi một lần cài đặt trên máy chủ, và lần cài ấy trùng với bản
vá của việc đã tách ra. Hai việc, một phụ thuộc ⇒ ai cài trước thì mở đường cho
người kia; không ai được cài **hai** thư viện khác nhau cho cùng một bài.

⛔ Vẫn không gộp hai việc vào một commit: bản vá `chataistudio` chạm một app
**đang phục vụ khách** và phải deploy, còn P06 nằm sau cờ tắt. Gộp là trộn hai
mức rủi ro, và khi cần hạ lại thì hạ luôn cả thứ không hỏng.

---

## §10 — Hình dạng bước 3 sau khi §9 bác một giả định

### `chatltt` hiện KHÔNG có job của riêng nó

Đo: `apps/chatltt/manifest.py:47` khai `job_types=()`, và thư mục app **không có
`jobs.py`**. ChatLTT tới nay chỉ **nộp** job sang app khác (`anhnoibo`,
`ltt_voice`) qua `tao_media`. Trích văn bản là việc đầu tiên ChatLTT tự chạy.

⇒ Bước 3 mở một thứ chưa từng có: một loại job **thuộc về** ChatLTT. Đó không
phải chi tiết kỹ thuật — nó thêm một dòng vào `job_types`, tức thêm một thứ
`job_runner` biết chạy, tức một bề mặt mới cho `leases` và cho sổ tiền.

### Bốn thứ phải quyết trước khi viết một dòng nào

| Câu hỏi | Vì sao không hoãn được |
|---|---|
| Thư viện trích nào | §9 đo: **không có cái nào**. Chọn = thêm phụ thuộc = chạm máy chủ |
| Giá của một lần trích | P06 §7 đã chấm *tốn credit*; giá phải hiện **trước** khi bấm (đường P04) |
| Trích hỏng thì tính tiền thế nào | Hoàn, hay thu? PDF ảnh scan là ca **thường**, không phải góc hiếm |
| `chatltt_doan` giữ **chữ của khách** | ⇒ CONTENT, và lần này đừng đợi bánh cóc nhắc |

⛔ Câu thứ ba là câu dễ bỏ quên nhất và tốn nhất. Một job trích chạy hết CPU rồi
   phát hiện PDF không có lớp chữ thì **đã tiêu tài nguyên thật**, nhưng khách
   không nhận được gì. Thu tiền cho một kết quả rỗng là thứ khách nhớ rất lâu.
   Đây đúng ca `credit_hoan_tong` đã có ở `chatltt_run` — dùng, đừng nghĩ lại.

### Điều kiện dừng của bước 3

Bước 3 xong **không** có nghĩa là người dùng trích được tệp. Nó có nghĩa là:
job chạy được, ghi `chatltt_doan`, đổi `trang_thai_trich`, và **hoàn tiền đúng**
khi trích ra rỗng. Vẫn chưa route, vẫn chưa `CHO_MODEL_GOI` — theo §4.
