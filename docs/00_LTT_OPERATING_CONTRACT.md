# LTT OPERATING CONTRACT — hợp đồng vận hành canonical

> **Đây là nguồn chân lý DUY NHẤT cho quy trình làm việc.** Nếu một tệp `.md`
> nào khác định nghĩa lại "khi nào chạy test", "sau khi sửa phải làm gì",
> "trước khi commit phải làm gì" — **tệp đó sai**, và việc đúng là xoá luật ở đó
> chứ không phải sửa hợp đồng này cho khớp.
>
> Lập **2026-09-08**. Thay thế cadence rải rác ở 10 tệp kế hoạch khác nhau —
> xem `docs/OPERATING_STANDARDIZATION/RULE_INVENTORY.md`.

## Hợp đồng này KHÔNG chứa gì

Nó không chép lại một con số nào từ nơi khác. Con số chép tay là con số sẽ trôi —
cơ chế ấy đã hỏng năm lần trong kho này (`CLAUDE.md` §Hiện giờ cái gì đang sống).
Chỗ nào cần một giá trị, hợp đồng **trỏ** tới nơi giữ nó.

| Cần biết | Hỏi ở đâu |
|---|---|
| Bước gate nào tồn tại, giá bao nhiêu | `tools/gate.py::_steps` · `docs/OPERATING_STANDARDIZATION/GATE_COMPONENT_MAP.md` |
| Hồ sơ gate chứng minh gì | `tools/gate.py::HO_SO` — mỗi hồ sơ có hợp đồng viết thành chữ |
| Thành phần nào tồn tại | `python tools/thanh_phan.py` |
| Ngân sách lõi, cửa sổ yên | `docs/QUY_TAC_CHAY_LENH_NANG.md` · `~/.claude/CLAUDE.md` |
| Quy trình deploy | `docs/16_CAP_NHAT_VA_DEPLOY.md` |
| Worktree | `docs/QUY_TRINH_WORKTREE.md` · `docs/DEVELOPMENT_WORKFLOW.md` |
| Cây này đang ở hồ sơ nào, nợ kiểm bao nhiêu | `python tools/ho_so_cay.py trang-thai` · `no-kiem` (luật ở §4.10) |
| Cạm bẫy của chính gate | `docs/BAY_TRONG_CONG_CHAT_LUONG.md` |
| Quy ước kỹ thuật (Windows, bố cục app, memory) | `AGENTS.md` |
| Cái gì đang sống trên production | `python tools/api_prod_canary.py trang-thai` |

---

# 1. Vòng đời một phiên

```
BẮT ĐẦU
  ↓  đọc hợp đồng này + CLAUDE.md
  ↓  git worktree list --porcelain · git status · git branch -vv · ListAgents
  ↓  xác định PHẠM VI, viết ra
  ↓  ĐỌC TRƯỚC KHI GHI
  ↓  ┌─ định nghĩa một CHANGESET NGUYÊN TỬ
  │  ├─ thi hành
  │  ├─ chạy đúng CẤP TEST (§4)
  │  └─ lặp
  ↓  chốt phase → cấp cao hơn
  ↓  commit / merge / deploy theo §7–§8
  ↓  nghiệm thu THẬT (§9)
KẾT THÚC — cập nhật `docs/_luutru/PROJECT_MEMORY.md` + memory
```

## 2. Đọc trước khi ghi

Không sửa một dòng mã trước khi biết:

- ai **gọi** nó;
- nó **phụ thuộc** vào gì;
- bất biến nào đang đứng trên nó;
- **test nào** chạm tới nó — `python tools/thanh_phan.py --test <thành phần>`.

⛔ Định vị bằng `grep`/`Glob`, không bằng đọc cả thư mục. `docs/` có 872 tệp
`.md` và 788 tệp ảnh; đọc theo nhu cầu, không theo thứ tự.

## 3. Kỷ luật phạm vi

Thấy một khiếm khuyết **ngoài** phạm vi thì **ghi lại, đừng sửa**. Mở rộng nhiệm
vụ vì tiện tay là cách một phiên biến một việc hai giờ thành một việc hai ngày,
và là cách hai phiên giẫm lên nhau.

⛔ **Không tự sáng tạo quy trình.** Nếu hợp đồng này thiếu một luật bạn cần:
ghi một đề xuất vào `docs/OPERATING_STANDARDIZATION/`, **tiếp tục theo luật hiện
có**, và đừng đẻ ra một luật cạnh tranh trong tệp kế hoạch của bạn. Mười tệp kế
hoạch tự khai cadence riêng chính là thứ đã buộc phải viết hợp đồng này.

---

# 4. 🔑 CHÍNH SÁCH TEST — bốn cấp

**Bốn cấp này KHÔNG phải cờ mới.** Chúng là tên gọi cho bốn hồ sơ `gate.py` đã có.
Không có "gate cũ" và "gate mới".

| Cấp | Lệnh | Chạy gì | Chứng minh gì | ⛔ KHÔNG chứng minh gì |
|---|---|---|---|---|
| **L0** | `python tools\gate.py --quick` | 28/30 bước — bỏ 2 bước nặng | không có lỗi tĩnh | **không phải bằng chứng** — bỏ đúng bước `pytest` nơi lỗi thật hay nằm |
| **L0+** | `python tools\gate.py --vong-lap` | tĩnh + `test_nhanh --lf` | test **vừa đỏ** đã xanh lại | **không phải bằng chứng** — test đang xanh mà thay đổi này làm hỏng thì nó không hề chạy |
| **L1** | `python tools\gate.py --doi` | tĩnh + test của phần **đã đổi** | mọi test **chạm tới** phần đã đổi đều xanh | không nói gì về phần còn lại. **Tự hạ cấp** xuống đầy đủ khi không chắc |
| **L2** | `python tools\gate.py --pham-vi <tp>` | như L1, phạm vi **chọn tay** | như trên | ⚠️ **tin người gọi** — L1 tự kiểm, cấp này thì không |
| **L3** | `python tools\gate.py` | tất cả 30 bước | toàn bộ cổng chất lượng **trên cây này** | không nói gì về deploy hay production |

Hai hồ sơ chuyên dụng: `--noi-tiep` (nghi kết quả bị nhiễu bởi song song/tải máy)
và `--ho-so phat-hanh` (L3 + đường cài/rollback). `--tuan-tu` **không phải**
`--noi-tiep` — xem `AGENTS.md` §4b.

## 4.1 Cấp nào cho việc gì

**Mặc định của vòng lặp là L1 (`--doi`), không phải L0+.**

```
sửa → L1 → sửa → L1 → … → (chốt phase) L2 → (trước khi báo xong) L3 → commit
```

⭐ Vì sao L1 chứ không phải `--vong-lap`: `--lf` chỉ chạy lại test **đã đỏ**. Sau
một lượt xanh nó không chứng minh gì cả, và khi cache `lastfailed` đầy id đã chết
nó **chạy toàn bộ** — đo được **543,7 giây** cho một chế độ tên là "~15 giây".
`--doi` chạy đúng những test **chạm tới thứ bạn vừa sửa**, và nó **tự hạ cấp**
xuống đầy đủ khi không chắc.

Dùng L0/L0+ khi: sửa nhiều tệp liên tiếp và muốn bắt lỗi tĩnh sớm; hoặc vừa có
một lượt đỏ và đang xác nhận nó đã xanh lại.

## 4.2 ⛔ KHÔNG chạy L3 sau mỗi lần sửa

**Chạy gate đầy đủ sau mỗi lần sửa là VI PHẠM hợp đồng này.**

🔑 **Gate là công cụ ra PHÁN QUYẾT, không phải công cụ CHẨN ĐOÁN.**

Ngày 27/08 gate đầy đủ bị chạy **sáu lần** chỉ để dò lỗi. Bốn trong sáu lượt đỏ
vì một thứ mà một bước con lẻ trả lời trong nửa giây. Đo thật: L3 trung vị
**682,8 giây ≈ 11,4 phút** trên 43 bản ghi — **không phải "5 phút"** như tài liệu
cũ nói.

## 4.3 ⛔ Đừng gọi `pytest` trực tiếp, và đừng chạy nó HAI LẦN

- `python -m pytest` cho toàn kho: **không** chạy test frontend ⇒ "full
  regression xanh" là một câu nói sai. Và nó chạy một luồng.
- **`test_nhanh.py` rồi `gate.py` là trả tiền hai lần.** Bước `bo test` **bên
  trong** gate *chính là* `test_nhanh.py` (`tools/gate.py:844`). Gõ tay
  `test_nhanh.py` chỉ khi bạn **không** định chạy gate sau đó.

## 4.4 Changeset nguyên tử

Gộp các sửa đổi có quan hệ logic thành **một** changeset rồi mới chạy test:

```
gỡ import cũ  +  nối phụ thuộc mới  +  chỉnh ánh xạ phản hồi  +  cập nhật test
```

⛔ **Đừng test một trạng thái trung gian mà bạn đã biết chắc là dở.** Một lượt đỏ
đã biết trước không mang thông tin gì, và nó làm bẩn cache `lastfailed` khiến
lượt `--lf` sau đó phình ra.

## 4.5 Bán kính ảnh hưởng → cấp mặc định

| Bán kính | Ví dụ | Cấp |
|---|---|---|
| **THẤP** | tài liệu, chú thích, template/CSS lẻ | L0 + kiểm trình duyệt nếu đụng giao diện |
| **VỪA** | route của app, service của app, adapter | **L1** |
| **CAO** | `runtime_noi_bo`, điều phối provider, storage dùng chung, tích hợp worker | **L1 + L2** |
| **NGHIÊM TRỌNG** | `jobs`, `credit`, auth/bảo mật, quyền sở hữu, migration, khoá/đa tiến trình, đường phát hành | **L2**, và **L3 ở checkpoint** |

⛔ Tệp nghiêm trọng **không** có nghĩa là chạy L3 sau **mỗi** lần sửa. Hoàn tất
changeset nguyên tử trước, rồi mới lên cấp.

## 4.6 Khi một lượt đỏ

```
sửa → chạy lại ĐÚNG phép kiểm đã đỏ → L1 → (chỉ khi checkpoint đòi) L3
```

Đừng chạy lại L3 ngay. Chỉ chạy lại toàn bộ khi checkpoint yêu cầu, **hoặc** khi
chính lỗi đó cho thấy bán kính rộng hơn bạn tưởng.

⚠️ Một lượt đỏ **không** tự động là lỗi của bạn. Trước khi đi sửa, loại trừ: máy
đang quá tải · một phiên khác đổi cây giữa lượt chạy · baseline của phiên khác.
`docs/BAY_TRONG_CONG_CHAT_LUONG.md` liệt kê 17 trường hợp đã xảy ra thật.

## 4.7 Test nặng

Test nạp model thật (`demucs`/`whisper`/TTS) phải nằm sau rào `LTT_TEST_NANG` /
marker `nang` (`pytest.ini`, `tests/rao_chan_nang.py`). Một worker pytest gọi một
model thật biến thành ~10 luồng torch, và ngân sách `-n` **không đếm tiến trình con**.

## 4.8 Lệnh nặng và máy dùng chung

Trước **mọi** lệnh nặng (gate mọi chế độ, `test_nhanh.py`, từ 3 tệp test trở lên):

```powershell
python tools\cua_so_yen.py trang-thai
```

Có phiên khác đang giữ → **chờ**. `cua_so_yen` là điều kiện **cần**, không phải
**đủ** — nó chỉ thấy ai *xin khoá*, không thấy `pytest` gõ tay hay bốn dịch vụ
production. Luật đầy đủ: `docs/QUY_TAC_CHAY_LENH_NANG.md`.

## 4.9 🔴 Một lượt L3 cần HAI điều kiện — và `cua_so_yen` chỉ đo được MỘT

| Điều kiện | Ai trả lời |
|---|---|
| máy có rảnh không | `cua_so_yen` + cây tiến trình |
| **cây có đứng yên không** | ⛔ **không công cụ nào**, trước khi chạy |

Vế thứ hai hiện chỉ có ảnh chụp trước/sau của `gate.py` — tức nó báo cho bạn
**sau khi đã mất ~12 phút**.

⭐ **Đo 08/09/2026, và đây là ca đáng nhớ vì mọi người đều làm đúng.** Chủ sản
phẩm bảo các phiên khác **"dừng chạy pytest"**. Họ **giữ lời tuyệt đối**: máy chỉ
`0.9/20 loi dang ban` suốt cả 12,4 phút. Lượt gate vẫn ra:

```
RESULT: FAIL (1/30)  [CAY DA DOI GIUA CHUNG - KHONG DUNG LAM BANG CHUNG]   16 tep
```

Họ không **chạy** gì cả — họ **gõ**. Và phép kiểm đỏ duy nhất trong 30 bước là
hai `skip` trong một tệp test tạo ra **năm phút sau khi lượt gate bắt đầu**.

🔑 **Cái bẫy không nằm ở sự sơ ý, mà ở chỗ hai câu nghe giống nhau.** *"Đừng dùng
CPU"* thoả mãn được bằng cách **viết mã suốt 12 phút**. Một phiên tuân thủ hoàn
hảo vẫn phá lượt đo của bạn.

### ⇒ Giao ước bắt buộc quanh một lượt L3

1. **Nhắn trước, chờ xác nhận, rồi mới bấm.** Nói rõ **giờ bắt đầu và thời
   lượng**: *"tôi bấm gate lúc 15:32, ~13 phút"*.
2. Câu xin đúng là **"đừng GHI TỆP"**, không phải "đừng chạy nặng".
3. Trong khoảng đó **chính bạn cũng không ghi** — kể cả `docs/`.
4. Luật đi **cả hai chiều**: phiên khác sắp bấm thì bạn đứng yên.

⚠️ Điều 3 không thừa. Ngày 08/09 tôi sửa `docs/BAY_TRONG_CONG_CHAT_LUONG.md`
giữa lượt gate của **chính mình**, và chỉ thoát vì `docs/` tình cờ không nằm
trong `gate.THU_MUC_CHUP` — không phải vì tôi cẩn thận.

---

## 4.10 Hai HỒ SƠ VẬN HÀNH — `NORMAL` và `FAST_BUILD`

Thêm 2026-09-09. **Đây là chỗ duy nhất định nghĩa hai hồ sơ này.** Một tệp kế
hoạch mô tả lại chúng là một bản sao sẽ trôi — §3 đã nói vì sao.

Hồ sơ là trạng thái **của một cây**, không phải của kho. Hai cây cạnh nhau được
phép ở hai hồ sơ khác nhau, và đó là điểm chính: một cây trunk đang phục vụ
deploy không được nới cadence chỉ vì một cây tính năng nào đó đang xây nhanh.

```powershell
python tools\ho_so_cay.py trang-thai
```

### `NORMAL` — mặc định, và là hồ sơ duy nhất của cây chính

Đúng §4.1: vòng lặp là L1 (`--doi`), lên cấp ở chốt, L3 trước khi báo xong.

⛔ Cây chính, `master`, nhánh phát hành và mọi cây dùng để deploy **luôn** ở
`NORMAL`. `ho_so_cay.py bat` từ chối bật ở những chỗ đó, và đó là một chốt cơ
học chứ không phải một giao ước — memory *luật viết ra không miễn nhiễm cho
người viết*.

### `FAST_BUILD` — chỉ trong một cây tính năng riêng đã opt-in

Dành cho một chiến dịch **dài, một chủ, một cây**, nơi phần lớn thay đổi còn
chưa thành hình. Nó không nới chuẩn chất lượng; nó **dời** chi phí kiểm chứng
từ *giữa* các thay đổi sang *cuối* một tập thay đổi đã đóng băng.

```
RESEARCH → BUILDING → FEATURE_COMPLETE → CERTIFYING → READY_TO_MERGE
```

| Trạng thái | Được làm gì |
|---|---|
| `RESEARCH` | đọc, đo, viết kế hoạch. Không sửa mã sản phẩm |
| `BUILDING` | sửa mã. **Không** `gate.py` (mọi chế độ), **không** `test_nhanh.py`, **không** từ 3 tệp test trở lên, **không** model thật, **không** deploy |
| `FEATURE_COMPLETE` | đóng băng tập tính năng. Từ đây không thêm tính năng, không refactor tiện tay |
| `CERTIFYING` | chỉ chạy kiểm và sửa nguyên nhân gốc tối thiểu |
| `READY_TO_MERGE` | hoà về trunk theo §7 |

**Trong `BUILDING` vẫn được microcheck rẻ** khi cần: cú pháp/import/biên dịch,
`json.loads`, khám phá manifest, render một template, một phép kiểm nhỏ tất
định. Mục tiêu không phải là *không kiểm gì*, mà là không xây tiếp trên mã
không parse được.

🔑 **Vì sao điều này không mâu thuẫn §4.2.** §4.2 cấm chạy L3 **để chẩn đoán**.
`FAST_BUILD` cấm nhiều hơn thế trong `BUILDING`, rồi trả lại đủ ở `CERTIFYING`.
Cả hai nói cùng một câu: gate là công cụ ra **phán quyết**.

### Chứng nhận đo từ `baseline_sha`, không từ `HEAD`

Đây là vế cơ chế, không phải vế kỷ luật. `--doi` mặc định so với `HEAD`; một
chiến dịch có commit checkpoint sẽ làm `HEAD` nuốt mất phần đầu, và `--doi` khi
đó **báo xanh trên một phép đo bỏ sót**.

```powershell
python tools\ho_so_cay.py bat --pham-vi "<mo ta ngan>"   # ghi baseline = HEAD
python tools\ho_so_cay.py no-kiem                        # nợ kiểm, đã dedupe
python tools\gate.py --doi --tu <baseline_sha>           # phạm vi TỪ baseline
```

`--tu` không phải một chế độ mới: nó chỉ đổi **mốc so sánh** của `--doi`, và
`thanh_phan.duong_da_doi` vốn đã nhận mốc đó.

### Thứ tự ở `CERTIFYING` — rẻ trước

```
1. tĩnh/micro          2. gom targeted đã dedupe (--doi --tu <baseline>)
3. tích hợp            4. đối chiếu legacy/parity
5. E2E                 6. trình duyệt trên URL công khai, nếu giao diện đổi
7. L3 một lần
```

Một lượt đỏ ⇒ sửa nguyên nhân gốc **tối thiểu** ⇒ chạy lại đúng phép kiểm đã đỏ
⇒ đi tiếp. **Không** quay lại làm tính năng; nếu buộc phải, hạ trạng thái về
`BUILDING` — công cụ cho phép, và nó ghi lại lần hạ đó.

### Ngoại lệ lõi

Bị chặn bởi một khiếm khuyết **chung** ở `jobs`/`credit`/auth/migration/đa tiến
trình/workflow-core: **dừng** App, tách một changeset lõi **riêng**, chứng nhận
riêng nó, xanh rồi mới quay lại. §4.5 và §7 vẫn áp cho changeset lõi đó — tức nó
đi theo `NORMAL`, kể cả khi cây đang ở `FAST_BUILD`.

⛔ Ngoại lệ này **không** phải cửa để quay về chạy gate sau mỗi lần sửa.

---

# 5. Worktree — ai sở hữu cái gì

Mỗi chiến dịch có **một** cây và **một** chủ. Phiên khác không sửa cùng vùng thi
hành nếu chưa bàn giao.

- Không gỡ worktree đang hoạt động.
- Không `reset`/`checkout`/đổi nhánh cây của phiên khác.
- Không vứt thay đổi chưa commit mà bạn không tạo ra.

⛔ **Một dòng `??` lạ trong `git status` là một phiên khác đang làm việc, không
phải rác.** `ListAgents` chỉ thấy phiên **tồn tại lúc hỏi**.

## 5.1 Hai phiên cùng một cây

Lập giao ước **ngay khi phát hiện**: ai sở hữu tệp nào. Với tệp dùng chung
(`CLAUDE.md`, `AGENTS.md`, `tools/gate.py`, `messages.po`) dùng **`Edit`, không
bao giờ `Write`** — `Write` đè im lặng cả tệp. Chi tiết: `AGENTS.md` §10.

# 6. An toàn git

- Không `reset --hard`, `push --force`, `checkout --` lên việc bạn không tạo ra.
- Không `--amend` một commit trên nhánh dùng chung. **Commit vào nhánh dùng chung
  là ĐÃ xuất bản** — sáu worktree chung một `.git`, "chưa push" không bảo vệ gì.
- `git add` **tường minh** từng tệp. Không `-A`, không `.` — cây chính mang việc
  dở của phiên khác.

# 7. Chính sách commit

Commit khi một changeset nguyên tử hoàn tất và **đúng cấp test của nó** đã xanh.

⛔ **Không phải mọi commit đều đòi L3.** Một commit checkpoint giữa chiến dịch cần
L1 xanh. L3 chỉ bắt buộc ở các checkpoint canonical:

⚠️ **Ngoại lệ duy nhất của câu "commit checkpoint cần L1 xanh"**: một cây đang ở
`FAST_BUILD`/`BUILDING` (§4.10) commit checkpoint **không** kèm L1 — đó chính là
thứ hồ sơ ấy dời đi. Đổi lại, `CERTIFYING` phải đo từ `baseline_sha` chứ không
từ `HEAD`, nếu không thì phần đã commit sẽ không có ai kiểm.

```
TRƯỚC KHI MERGE một chiến dịch lớn
NGHIỆM THU CUỐI một chiến dịch
PHÁT HÀNH · TRƯỚC DEPLOY
Thay đổi core: credit · jobs · auth/bảo mật · migration
```

# 8. Deploy

Deploy có cổng **riêng** — `docs/16_CAP_NHAT_VA_DEPLOY.md`. Nó không phải một cấp
test; nó là một quy trình.

⛔ **Deploy chép CẢ CÂY nguồn**, không tách được phần của một phiên. Trước khi
deploy: `git status` sạch phần tracked · hỏi phiên khác (`ListAgents`) ·
đối chiếu migration.

# 9. Nghiệm thu THẬT

Test xanh **không** chứng minh trang hiển thị đúng, và L3 **không** nói gì về
production.

- Đổi giao diện hoặc luồng người dùng ⇒ mở trình duyệt, tái hiện luồng, xem
  console error, xem request hỏng, xác minh trên giao diện thật.
- Chốt trên **URL công khai** (`https://app.lttstudios.com`), không chỉ loopback.
  Loopback bỏ qua Cloudflare (cache, CSP biên, minify).
- Sau deploy, hỏi máy chủ đang chạy bản nào: `/health/version`.

# 10. Điều kiện DỪNG

Gặp một trong bốn thứ này thì **dừng hành động phá huỷ** và hỏi:

1. thay đổi chưa commit **không rõ của ai**;
2. xung đột với một phiên đang hoạt động;
3. một thao tác **không đảo được** trên production (xoá dữ liệu, `DROP`, ghi đè backup);
4. một rủi ro bảo mật / mất dữ liệu chưa được giải quyết.

⭐ "Chưa có khách" **không** nới bốn điều trên. Nó nới việc rà soát tương thích
ngược — xem `CLAUDE.md`. Một lệnh `DROP` không đảo lại được dù không ai đang xem.

---

# 11. Khi bạn nghi mình đi sai hướng

Người dùng nói *"Check LTT execution policy"* hoặc *"Check lại quy tắc gate/pytest"*
⇒ đọc lại **`CLAUDE.md`** và **tệp này**, xác định lại đúng cấp test, rồi tiếp tục
công việc đang làm. **Không** khởi động lại việc phân tích dự án từ đầu.
