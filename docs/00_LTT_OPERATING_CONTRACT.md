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

## 1b. 🔴 TRA NGUỒN TRƯỚC KHI TỰ SUY — chủ sản phẩm chốt 2026-09-13

*"Nên lên cộng đồng GitHub hoặc tra cứu tài liệu từ model để lấy thông số, hoặc
cách làm — thay vì tự suy."*

Gặp một hành vi lạ của model, engine hay thư viện ngoài: **tra nguồn trước**, và
đo để **kiểm chứng** nguồn — không đo để **thay** nguồn.

| Thứ tự | Nguồn | Ví dụ đường |
|---|---|---|
| 1 | model card của nhà sản xuất | `huggingface.co/<org>/<model>/raw/main/README.md` |
| 2 | README của chính engine | `raw.githubusercontent.com/ggml-org/llama.cpp/master/tools/server/README.md` |
| 3 | kho bản vá / issue của cộng đồng cho **đúng** model ấy | `huggingface.co/api/models/<repo>/tree/main` |
| 4 | **rồi mới** đo trên máy ta, để xác nhận nó áp đúng ở đây | |

⚠️ `WebFetch`/`WebSearch` **hỏng trên máy này** — dùng
`curl -sL --max-time 60 -A "Mozilla/5.0" <url>`.

### Ca đã trả giá, 13/09/2026 — L-02

Tôi đo `ltt-3.5` trả **rỗng 5/5 lượt** ở `max_tokens` 150/200/250, rồi định đặt
một **sàn `max_tokens`** ở cửa vào. Con số đo **đúng**; bản sửa **sai tầng**.
Bốn phút tra nguồn đổi hẳn kết luận:

* model card Qwen: *"we recommend an output length of **32.768 tokens**"*, và có
  **hai nút riêng biệt** — `max_tokens` (độ dài) vs `enable_thinking=False` /
  `/no_think` (tắt suy nghĩ). Tôi đang nhầm chúng làm một.
* `froggeric/Qwen-Fixed-Chat-Templates`: template **chính thức** của Qwen
  *"hardcodes `xhigh` by default, **burns token budgets with zero content
  returned**"*. Bản vá mặc định `medium`, thêm `none`/`off`.

⇒ Gốc không phải *"khách đặt `max_tokens` thấp"* mà là **template hardcode
  `xhigh`**. Chặn ở cửa vào là chữa triệu chứng, và nó còn **cướp mất của khách
  một tham số hợp lệ**.

### ⭐ Phép đo phân biệt rẻ hơn mọi suy luận

Nghi một tham số **không được engine tôn trọng**? Gửi ba giá trị khác nhau của
nó và xem đầu ra có đổi không. Đo 13/09:

```
ltt-3.5  reasoning_effort = None / low / xhigh  ->  token_ra = 250 / 250 / 250
                                                    (dung bang max_tokens, RONG ca ba)
ltt-3.8  cung ba gia tri                        ->  token_ra =  63 /  63 /  62, dung ca ba
```

Một tham số không đổi được gì là một tham số **đang bị hardcode ghi đè**.

⛔ Và chỗ tinh tế nhất: kho **đã** cân nhắc áp bản vá cho 3.5 rồi cố ý **không**
làm, với lý do viết rõ trong `llama-swap.yaml` — *"áp nó cho 3.5 là áp một bản vá
cho một lỗi **chưa được đo** ở model này"*. Lý do ấy **đúng lúc nó được viết**.
Phép đo L-02 chính là thứ còn thiếu. **Một chú thích nói về lúc nó được viết,
không nói về lúc bạn đọc nó** — luôn hỏi điều kiện nó đặt ra đã đổi chưa.

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

# 5. Worktree — ai sở hữu cái gì

Mỗi chiến dịch có **một** cây và **một** chủ. Phiên khác không sửa cùng vùng thi
hành nếu chưa bàn giao.

- Không gỡ worktree đang hoạt động.
- Không `reset`/`checkout`/đổi nhánh cây của phiên khác.
- Không vứt thay đổi chưa commit mà bạn không tạo ra.

Vòng đời và mẫu bàn giao canonical nằm duy nhất ở
`docs/QUY_TRINH_WORKTREE.md` §5. Phiên task kết thúc ở
`HANDOFF_READY_FINAL`; chỉ canonical integrator được đưa capability vào `main`
và retire branch/worktree sau chứng nhận cùng ledger được duyệt.

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

# 10b. 🔴 KHÔNG DỪNG GIỮA CÁC PHA — chủ sản phẩm chốt 2026-09-13

*"Thực hiện full quy trình, không dừng lại giữa các phase, tiếp quản chạy full
plan tự động."*

Một pha xong **không** phải một điểm xin phép. Chạy thẳng sang pha kế tiếp.

| ⛔ Đừng làm | ✅ Làm |
|---|---|
| "Pha 1 xong, tôi có nên tiếp?" | tiếp luôn, báo kết quả **sau** |
| dừng lại xin duyệt deploy | deploy, rồi báo kèm phép đo trước/sau |
| kết một báo cáo bằng câu hỏi | kết bằng **việc đã làm** + việc **đang làm tiếp** |
| chờ trả lời rồi mới chạy gate | bấm gate, dùng thời gian chờ làm việc khác |

⭐ **Làm việc song song trong lúc chờ.** Một lượt gate ~12 phút; ràng buộc thật
trong khoảng đó **không phải CPU** (đo 13/09: CPU 3 %, gate dùng ~6/10 lõi) mà
là **cấm ghi cây**. Nên: gom mọi việc ghi vào **trước** khi bấm gate, rồi trong
lúc gate chạy chỉ làm việc **đọc/đo** — đo production, đo máy B, đọc mã. Phép đo
thẳng máy B chạy được ngay giữa một lượt gate, vì việc thật nằm ở máy B.

## ⛔ Bốn thứ VẪN dừng — và không cái nào là chuyện xin phép

| | Vì sao |
|---|---|
| **Gate đỏ** | dừng, sửa, chạy lại. Không đi tiếp trên một cây chưa xanh |
| **Thao tác không đảo được** trên dữ liệu thật (`DROP`, xoá, ghi đè backup) | §10 mục 3 — uỷ quyền không làm một lệnh `DROP` đảo lại được |
| **Thay đổi chưa commit không rõ của ai** | §10 mục 1 |
| **Rủi ro bảo mật / mất dữ liệu chưa giải quyết** | §10 mục 4 |

⚠️ Và một thứ **không còn** là điểm dừng: **UAC**. Máy đặt
`ConsentPromptBehaviorAdmin = 0` ⇒ nâng quyền **im lặng**, không có hộp thoại
nào hiện lên. Đừng bảo chủ dự án "bấm Yes" — sẽ không có gì để bấm. Đường chuẩn:
`python tools\nang_quyen.py <script.py> [-- <tham số>]`.

⛔ Uỷ quyền này **không** bao gồm nới ACL hay `icacls`. ACL ở `secrets\` và
`D:\LTTBackups` là một bản vá bảo mật **đã hoàn thành** (W1.5). "Full quyền"
nghĩa là *đừng dừng lại hỏi*, không phải *hạ mức an toàn xuống*.

---

# 11. Khi bạn nghi mình đi sai hướng

Người dùng nói *"Check LTT execution policy"* hoặc *"Check lại quy tắc gate/pytest"*
⇒ đọc lại **`CLAUDE.md`** và **tệp này**, xác định lại đúng cấp test, rồi tiếp tục
công việc đang làm. **Không** khởi động lại việc phân tích dự án từ đầu.
