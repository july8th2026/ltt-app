# LTT OPERATING CONTRACT — hợp đồng vận hành canonical

> **Nguồn chân lý DUY NHẤT cho quy trình làm việc**: vòng đời phiên, nhịp
> test/gate, git, commit, gộp `main`, điều kiện dừng. Tệp nào khác định nghĩa lại
> những điều đó là **sai** — xoá luật ở đó, đừng sửa hợp đồng cho khớp.
> `tools/check_luat_van_hanh.py` (một bước của gate) chặn nhịp gate chép ra ngoài.
>
> Lập 2026-09-08 · chuẩn hoá lại 2026-09-16 (một luồng, mỗi chủ đề một chủ).

## Mỗi chủ đề MỘT chủ

| Chủ đề | Chủ — chỉ nơi này định nghĩa |
|---|---|
| Vòng đời phiên · test/gate · git · commit · gộp `main` · dừng/không dừng | **tệp này** |
| Tạo worktree · kết thúc phiên (thao tác) | `docs/QUY_TRINH_WORKTREE.md` |
| Lệnh nặng · CPU · hộp đen khi treo | `docs/QUY_TAC_CHAY_LENH_NANG.md` |
| Deploy · push · nghiệm thu sau deploy | `docs/16_CAP_NHAT_VA_DEPLOY.md` |
| Kỹ thuật: Windows/BOM, bí mật, bố cục app, cách viết test, tệp dùng chung | `AGENTS.md` |
| Chuyện kể · sự cố · bài học đo lường | `docs/BAY_TRONG_CONG_CHAT_LUONG.md` |
| Sản phẩm đã chốt gì | `docs/QUYET_DINH_NEN_TANG.md` |
| Cái gì đang sống trên production | `python tools\api_prod_canary.py trang-thai` |
| Bước gate nào tồn tại, chứng minh gì | `tools/gate.py::_steps` · `tools/gate.py::HO_SO` |

⛔ **Không chép số.** Con số nằm trong mã (`tools/gate.py`, lint, `ngan_sach.py`);
tài liệu trỏ tên hằng. Một con số chép tay không có cách nào tự biết nó đã cũ.

---

# 1. Vòng đời một phiên

```
MỞ PHIÊN
  1. CLAUDE.md (tự nạp) → tệp này
  2. python tools\ho_so_cay.py trang-thai      (hồ sơ cây, governance có lệch main không)
  3. git status · ListAgents                  (ai đang làm gì; dòng ?? lạ = phiên khác)
  4. viết ra PHẠM VI
LÀM — PHA 1..N
  5. đọc trước khi ghi (§2) → một changeset nguyên tử (§4.4)
  6. TEST NHẮM cụm vừa sửa (§4.1) — KHÔNG gate
  7. đỏ → sửa TẠI CHỖ → chạy lại ĐÚNG phép đỏ → pha kế tiếp, không dừng xin phép (§10b)
KẾT THÚC — khi MỌI pha xong
  8. L3 MỘT lần (§4.2) · đỏ → khép (§4.6)
  9. commit → GỘP main (§7) → deploy nếu phạm vi cần (§8)
 10. nghiệm thu thật (§9)
 11. ghi docs/NHAT_KY.md (sự thật đã xảy ra) · memory chỉ khi có sự thật mới không suy ra được từ kho
```

Đang ở máy nào: `Test-Path C:\LTTPlatform` → có = **máy chủ đang chạy thật**.

## 1b. 🔴 TRA NGUỒN TRƯỚC KHI TỰ SUY — chủ sản phẩm chốt 2026-09-13

*"Nên lên cộng đồng GitHub hoặc tra cứu tài liệu từ model để lấy thông số, hoặc
cách làm — thay vì tự suy."* Gặp hành vi lạ của model/engine/thư viện ngoài: **tra
nguồn trước**, rồi đo để **kiểm chứng** nguồn — không đo để **thay** nguồn.

| Thứ tự | Nguồn | Công cụ |
|---|---|---|
| 1 | model card của nhà sản xuất | `curl` `huggingface.co/<org>/<model>/raw/main/README.md` |
| 2 | README / tài liệu của chính engine, thư viện | **GitHub MCP** `get_file_contents` (vd `ggml-org/llama.cpp` · `tools/server/README.md`) |
| 3 | issue / PR / mã cộng đồng cho **đúng** model/thư viện ấy | **GitHub MCP** `search_issues` (theo repo) · `search_code` (theo ký hiệu) · `search_repositories` |
| 4 | **rồi mới** đo trên máy ta | |

⭐ **GitHub đi qua plugin GitHub MCP** (`mcp__plugin_github_github__*`, đã cấp token) —
không cào HTML. Gặp một lỗi/hành vi lạ: `search_issues` trong repo của thư viện đó
**trước** khi đặt giả thuyết; trích số issue/PR vào nhật ký làm nguồn.

⚠️ `WebFetch`/`WebSearch` **hỏng trên máy này** — nguồn ngoài GitHub dùng
`curl -sL --max-time 60 -A "Mozilla/5.0" <url>`.

⭐ **Phép đo phân biệt rẻ hơn mọi suy luận.** Nghi một tham số không được tôn trọng?
Gửi ba giá trị, xem đầu ra có đổi:

```
ltt-3.5  reasoning_effort = None / low / xhigh  ->  token_ra = 250 / 250 / 250  (bị hardcode ghi đè)
ltt-3.8  cung ba gia tri                        ->  token_ra =  63 /  63 /  62  (ton trong)
```

Ca L-02 (13/09) đầy đủ: `docs/BAY_TRONG_CONG_CHAT_LUONG.md`. Bài học: **một chú
thích nói về lúc nó được viết, không nói về lúc bạn đọc nó.**

## 2. Đọc trước khi ghi

Không sửa một dòng mã trước khi biết: ai **gọi** nó · nó **phụ thuộc** gì · bất
biến nào đứng trên nó · **test nào** chạm tới nó (`python tools\thanh_phan.py --test <tp>`).

⛔ Định vị bằng `grep`/`Glob`, không đọc cả thư mục. Không nạp sản phẩm build, log,
cache, dữ liệu vận hành.

## 3. Kỷ luật phạm vi

Khiếm khuyết **ngoài** phạm vi: **ghi lại, đừng sửa** (hoặc tách thành việc riêng).

⛔ **Không tự sáng tạo quy trình.** Thiếu luật: ghi đề xuất vào
`docs/NHAT_KY.md`, **tiếp tục theo luật hiện có**, không đẻ luật cạnh tranh trong
tệp kế hoạch.

---

# 4. 🔑 CHÍNH SÁCH TEST — một nhịp duy nhất

```
TRONG PHIÊN  : test NHẮM đúng cụm vừa sửa. Đỏ → sửa TẠI CHỖ → chạy lại ĐÚNG phép đỏ.
               ⛔ KHÔNG gate.py ở bất kỳ chế độ nào.
CUỐI PHIÊN   : mọi pha xong → python tools\gate.py (L3) MỘT lần.
L3 ĐỎ        : sửa tại chỗ → chạy lại đúng phép đỏ → khép bằng `gate.py --doi --tu <sha>`.
               ⛔ KHÔNG chạy L3 lần hai. Một L3 mỗi nhánh.
```

## Các cấp — tên gọi cho hồ sơ `gate.py`

| Cấp | Lệnh | Dùng khi | ⛔ KHÔNG chứng minh gì |
|---|---|---|---|
| **T** | `python -m pytest <tệp…> -q` · `python tools\check_<x>.py` | **mọi lúc trong phiên** (§4.1) | không nói gì ngoài cụm đó |
| **L1** | `python tools\gate.py --doi --tu <sha>` | **khép** bản sửa sau L3 đỏ (§4.6) · hoà `main` (§7) | phần còn lại. **Tự nâng lên L3** khi không chắc |
| **L2** | `python tools\gate.py --pham-vi <tp>` | chứng nhận riêng một changeset lõi (§4.10) | ⚠️ tin người gọi |
| **L3** | `python tools\gate.py` | **một lần, khi mọi pha xong** (§4.2) | deploy hay production |
| — | `--quick` · `--vong-lap` | **không dùng** trong nhịp chuẩn | không phải bằng chứng |

Hồ sơ chuyên dụng: `--noi-tiep` (nghi nhiễu do song song/tải máy) · `--ho-so
phat-hanh` (L3 + cài/rollback). `--tuan-tu` ≠ `--noi-tiep` — `AGENTS.md` §4b.

## 4.1 Trong phiên — chỉ TEST NHẮM

```powershell
python tools\thanh_phan.py --doi              # cây hiện tại chạm tới thành phần nào
python tools\thanh_phan.py --test <tp>        # tệp test của thành phần đó
python -m pytest tests\test_A.py tests\test_B.py -q
```

- **≤ 2 tệp test**: chạy thẳng.
- **≥ 3 tệp test**: là lệnh nặng — kiểm theo §4.8, `-n` tối đa 6.
- Bước kiểm tĩnh lẻ (mypy, i18n, kiểu xuống dòng…): chạy **đúng công cụ đó**; tên
  lệnh ở `tools/gate.py::_steps`, và gate in sẵn khi đỏ.

⛔ **Không `gate.py` ở bất kỳ chế độ nào trong phiên** — kể cả `--doi`, `--quick`,
`--vong-lap`. Chủ sản phẩm chốt 16/09/2026: *"gate chỉ là tổng duyệt."*

## 4.2 ⛔ L3 chạy MỘT lần — khi mọi pha đã xong

🔑 **Gate là công cụ ra PHÁN QUYẾT, không phải công cụ CHẨN ĐOÁN.**

L3 chạy **một lần** khi toàn bộ phạm vi đã làm xong — là phán quyết dùng chung cho
báo xong, gộp `main` và deploy. Không chạy L3 sau một pha, đợt, hạng mục, lát cắt
hay lần sửa. **Còn việc nào chưa làm thì chưa bấm.**

Trước khi bấm: `npm run build` nếu frontend đổi (`AGENTS.md` §4b) · commit hết ·
§4.8 · trong lúc chạy **không ghi vào cây của mình** (§4.9).

Vì sao (đo 16/09 trên `test-results/gates/*.json`): 114 lượt L3 trong 11 ngày,
100 lượt nằm trong chuỗi chạy lại liền nhau — gate bị dùng để xác nhận từng bản
sửa. Chi tiết: `docs/BAY_TRONG_CONG_CHAT_LUONG.md`.

## 4.3 ⛔ Đừng gọi `pytest` cho toàn kho, và đừng trả tiền hai lần

- `python -m pytest` **toàn kho** không chạy test frontend ⇒ "full regression xanh"
  là câu sai. (`pytest` cho **đúng các tệp** của cụm là test nhắm — khuyến khích.)
- `test_nhanh.py` rồi `gate.py` = trả tiền hai lần: bước `bo test` trong gate
  *chính là* `test_nhanh.py`.

## 4.4 Changeset nguyên tử

Gộp các sửa đổi có quan hệ logic (gỡ import cũ + nối phụ thuộc mới + chỉnh ánh xạ
+ cập nhật test) rồi mới test. ⛔ Đừng test một trạng thái trung gian đã biết là dở.

## 4.5 Bán kính ảnh hưởng → test nhắm rộng tới đâu

Bán kính quyết định **tập test nhắm**, **không** đổi số lượt L3.

| Bán kính | Ví dụ | Test nhắm |
|---|---|---|
| **THẤP** | tài liệu, chú thích, CSS lẻ | bước kiểm tĩnh liên quan + trình duyệt nếu đụng giao diện |
| **VỪA** | route/service/adapter của app | `thanh_phan.py --test <tp>` |
| **CAO** | `runtime_noi_bo`, provider, storage chung, worker | + người tiêu thụ (`thanh_phan.py --do-thi <tp>`) |
| **NGHIÊM TRỌNG** | `jobs`, `credit`, auth, quyền sở hữu, migration, khoá/đa tiến trình, phát hành | + test tích hợp/PostgreSQL chạm tới nó |

## 4.6 Khi một lượt đỏ — sửa TẠI CHỖ, khép HẸP

```
Trong phiên : sửa tại chỗ → chạy lại ĐÚNG tệp/bước đã đỏ → đi tiếp
L3 đỏ       : đọc bước/tệp đỏ (gate in sẵn "CHAY LAI DUNG PHEP DO")
              → sửa tại chỗ → chạy lại đúng các phép đỏ
              → KHÉP: python tools\gate.py --doi --tu <sha của lượt L3>  → xong
```

Vì sao khép chứ không L3 lần hai: lượt L3 **đã** phán quyết phần không đổi; `--doi
--tu <sha>` chạy đúng test chạm tới bản sửa (kể cả phần chưa commit), và **tự nâng
lên L3** khi bản sửa chạm tệp dùng chung — lúc đó là máy quyết, không phải thói quen.

⛔ **MỘT L3 mỗi nhánh — máy thi hành.** Nhánh đã có một lượt L3 (xanh hay đỏ) trong
12 giờ thì `gate.py` **từ chối** L3 gõ tay và in lệnh khép. Không tính: lượt mang
nhãn `CAY DA DOI`, và lượt **bị ngắt giữa chừng** (phiên đóng, bị dừng) — lượt đó
không ghi bản ghi `test-results/gates/*.json`, tức **chưa có phán quyết**, nên được
chạy lại. Lượt trước bị nhiễu thật (máy `QUA TAI`) → `--l3-lai`, có ghi.

⚠️ Đỏ **không** tự động là lỗi của bạn: loại trừ máy quá tải và thay đổi có sẵn trên
`main` trước khi sửa. Sửa tại chỗ vẫn là sửa — kể cả khi lỗi có sẵn, gom vào cùng
lượt khép thay vì mỗi người một lượt L3.

## 4.7 Test nặng

Test nạp model thật (`demucs`/`whisper`/TTS) nằm sau rào `LTT_TEST_NANG` / marker
`nang` (`tests/rao_chan_nang.py`). Ngân sách `-n` **không đếm tiến trình con**.

## 4.8 Trước lệnh nặng — MỘT bộ kiểm

Lệnh nặng = `gate.py` (mọi chế độ) · `test_nhanh.py` · ≥ 3 tệp test ·
`build_system_profile.py`. Trước khi chạy:

```powershell
python tools\cua_so_yen.py trang-thai    # ai đang giữ khoá -> có thì CHỜ
```

rồi đọc tải máy: gate tự in `[tai may] N/M loi dang ban -> RANH/BAN/QUA TAI`; pytest
gõ tay thì xem cùng dòng đó bằng `python tools\tai_may.py`. `QUA TAI` ⇒ chờ.
Chi tiết kỹ thuật (vì sao hai thứ, hộp đen): `docs/QUY_TAC_CHAY_LENH_NANG.md`.

## 4.9 Trong lúc L3 chạy

- **Chính bạn không ghi vào cây đang chạy gate** — gate chụp cây trước/sau; ghi giữa
  chừng thì kết quả mang nhãn `CAY DA DOI GIUA CHUNG` và vô giá trị.
- Mỗi phiên có worktree riêng (§5), nên phiên khác ghi vào **cây của họ** không làm
  hỏng lượt của bạn — không cần xin ai đứng yên, không chờ xác nhận.
- Buộc chung một cây (ngoại lệ): báo phiên kia giờ bấm + thời lượng, câu xin là
  **"đừng GHI TỆP"**, rồi bấm — không chờ trả lời.
- Thời gian chờ: làm việc **đọc/đo** (§10b).

## 4.10 Hai HỒ SƠ VẬN HÀNH — `NORMAL` và `FAST_BUILD`

Hồ sơ là trạng thái **của một cây**. `python tools\ho_so_cay.py trang-thai`.

### `NORMAL` — mặc định

§4.1–§4.2: trong phiên chỉ test nhắm, L3 **một lần** khi mọi pha xong. ⛔ Cây chính,
`main`, nhánh phát hành và mọi cây dùng để deploy **luôn** ở `NORMAL`
(`ho_so_cay.py bat` từ chối — chốt cơ học).

### `FAST_BUILD` — chỉ trong một cây tính năng riêng đã opt-in

Chiến dịch **dài, một chủ, một cây**. Khác `NORMAL` ba thứ: commit checkpoint
**không** cần test nhắm xanh · một `baseline_sha` để đo nợ kiểm · máy trạng thái:

```
RESEARCH → BUILDING → FEATURE_COMPLETE → CERTIFYING → READY_TO_MERGE
```

| Trạng thái | Được làm gì |
|---|---|
| `RESEARCH` | đọc, đo, viết kế hoạch. Không sửa mã sản phẩm |
| `BUILDING` | sửa mã. **Không** gate, **không** ≥ 3 tệp test, **không** model thật, **không** deploy. Được microcheck rẻ (cú pháp, import, `json.loads`, render template) |
| `FEATURE_COMPLETE` | đóng băng tập tính năng |
| `CERTIFYING` | chỉ chạy kiểm và sửa nguyên nhân gốc tối thiểu |
| `READY_TO_MERGE` | gộp `main` theo §7 |

```powershell
python tools\ho_so_cay.py bat --pham-vi "<mo ta ngan>"   # baseline = HEAD
python tools\ho_so_cay.py no-kiem                        # nợ kiểm từ baseline + lệnh test nhắm
```

**Thứ tự ở `CERTIFYING`** — rẻ trước, gate đúng một lần: test nhắm đã dedupe →
tích hợp → parity → E2E → trình duyệt URL công khai → **L3 một lần** (đỏ ⇒ §4.6).
⛔ Không `gate.py --quick`/`--doi` trước L3 — tập con của L3, trả tiền hai lần.

**Ngoại lệ lõi.** Bị chặn bởi khiếm khuyết chung ở `jobs`/`credit`/auth/migration/
đa tiến trình/workflow-core: tách changeset lõi **riêng**, chứng nhận riêng (L2),
rồi quay lại. Không phải cửa để chạy gate sau mỗi lần sửa.

---

# 5. Worktree — mỗi phiên một cây

- Mỗi phiên ghi code làm trong **worktree riêng** sinh từ `main`, ghi `BASE_SHA`.
  Cách tạo và kết thúc: `docs/QUY_TRINH_WORKTREE.md`.
- Không gỡ worktree đang hoạt động · không `reset`/`checkout`/đổi nhánh cây của
  phiên khác · không vứt thay đổi chưa commit mà bạn không tạo ra.
- ⛔ **Một dòng `??` lạ trong `git status` là một phiên khác đang làm việc, không
  phải rác.** `ListAgents` chỉ thấy phiên tồn tại lúc hỏi.
- Buộc chung một cây: lập giao ước tệp ngay; tệp dùng chung chỉ `Edit`, không
  `Write` — `AGENTS.md` §10.

# 6. An toàn git

- Không `reset --hard`, `push --force`, `checkout --`, `stash` trần lên việc bạn không
  tạo ra. Cần đo baseline: `git worktree add --detach` (`AGENTS.md` §10).
- Commit vào nhánh dùng chung là **đã xuất bản** (mọi worktree chung một `.git`) —
  không `--amend` ở đó.
- `git add` **tường minh** từng tệp; không `-A`, không `.`; xem `git diff --cached`.

# 7. Commit và GỘP `main`

- Commit khi một changeset nguyên tử xong và **test nhắm** của nó xanh. Commit
  checkpoint trên nhánh phiên **không** đòi gate.
- **Chính phiên làm việc tự gộp `main`** (chủ sản phẩm chốt 16/09/2026) — không chờ
  người tích hợp. Điều kiện: L3 xanh, hoặc L3 đỏ đã khép (§4.6).

```
main CHƯA đi tiếp kể từ BASE_SHA  → fast-forward main tới nhánh của bạn
main ĐÃ đi tiếp                   → merge main vào nhánh
                                   → python tools\gate.py --doi --tu <sha lượt L3>  (chỉ chỗ hai bên gặp nhau)
                                   → fast-forward main
```

Thao tác cụ thể (cây chính đang có việc dở của phiên khác, push GitHub):
`docs/QUY_TRINH_WORKTREE.md` §5. ⛔ Không bao giờ ghi đè thay đổi chưa commit của
phiên khác để gộp — gặp thì dừng theo §10.

# 8. Deploy

Chính phiên đã gộp `main` deploy khi phạm vi cần, **rồi báo** — không xin duyệt
(§10b). Quy trình và cổng riêng: `docs/16_CAP_NHAT_VA_DEPLOY.md`.

- Cần phán quyết xanh trên **đúng SHA được deploy** (§7).
- ⛔ **Deploy chép CẢ CÂY**, không tách được phần một phiên ⇒ trước khi deploy
  **báo** các phiên đang chạy (`ListAgents` → `SendMessage`) — báo, không chờ.
- Nâng quyền: `python tools\nang_quyen.py <script.py> [-- <tham số>]` (im lặng, §10b).

# 9. Nghiệm thu THẬT

Test xanh không chứng minh trang hiển thị đúng; L3 không nói gì về production.

- Đổi giao diện/luồng ⇒ trình duyệt, tái hiện luồng, console error, request hỏng.
- Chốt trên **URL công khai** (`https://app.lttstudios.com`) — loopback bỏ qua
  Cloudflare (cache, CSP biên, minify).
- Sau deploy: `/health/version` — máy chủ đang chạy đúng bản nào.

# 10. Điều kiện DỪNG

Dừng **hành động phá huỷ** và hỏi khi gặp:

1. thay đổi chưa commit **không rõ của ai**;
2. xung đột với một phiên đang hoạt động;
3. thao tác **không đảo được** trên dữ liệu thật (xoá, `DROP`, ghi đè backup);
4. rủi ro bảo mật / mất dữ liệu chưa giải quyết.

"Chưa có khách" **không** nới bốn điều trên.

---

# 10b. 🔴 KHÔNG DỪNG GIỮA CÁC PHA — chủ sản phẩm chốt 2026-09-13

*"Thực hiện full quy trình, không dừng lại giữa các phase, tiếp quản chạy full
plan tự động."* Một pha xong **không** phải điểm xin phép.

| ⛔ Đừng làm | ✅ Làm |
|---|---|
| "Pha 1 xong, tôi có nên tiếp?" | tiếp luôn, báo kết quả **sau** |
| dừng xin duyệt deploy/gộp `main` | làm, rồi báo kèm phép đo trước/sau |
| kết báo cáo bằng câu hỏi | kết bằng **việc đã làm** + việc **đang làm tiếp** |
| chờ trả lời rồi mới làm | làm, dùng thời gian chờ cho việc đọc/đo |

Kế hoạch nhiều việc: ghi `.claude/pha_dang_chay.json` với `{"con_lai": ["việc 1",
"việc 2"]}` ở gốc cây — hook Stop (`tools/hook_khong_dung_giua_pha.py`) chặn phiên
dừng khi còn việc; xong một việc thì bỏ nó khỏi `con_lai`.

## ⛔ Bốn thứ VẪN dừng — không cái nào là chuyện xin phép

| | Vì sao |
|---|---|
| **Gate đỏ** | dừng, sửa tại chỗ, chạy lại **đúng phép đã đỏ**, khép theo §4.6 — không chạy lại L3. Không đi tiếp trên một cây chưa xanh |
| **Thao tác không đảo được** trên dữ liệu thật | §10 mục 3 — uỷ quyền không làm một lệnh `DROP` đảo lại được |
| **Thay đổi chưa commit không rõ của ai** | §10 mục 1 |
| **Rủi ro bảo mật / mất dữ liệu chưa giải quyết** | §10 mục 4 |

⚠️ **UAC không còn là điểm dừng.** Máy đặt `ConsentPromptBehaviorAdmin = 0` ⇒ nâng
quyền **im lặng**. Đừng bảo chủ dự án "bấm Yes". Đường chuẩn:
`python tools\nang_quyen.py <script.py> [-- <tham số>]`.

⛔ Uỷ quyền **không** bao gồm nới ACL hay `icacls`. ACL ở `secrets\` và
`D:\LTTBackups` là bản vá bảo mật **đã hoàn thành** (W1.5). "Full quyền" nghĩa là
*đừng dừng lại hỏi*, không phải *hạ mức an toàn*.

---

# 11. Khi bạn nghi mình đi sai hướng

Người dùng nói *"Check LTT execution policy"* / *"Check lại quy tắc gate/pytest"* ⇒
đọc lại `CLAUDE.md` và tệp này, xác định lại đúng cấp test, rồi **tiếp tục** việc
đang làm. Không phân tích lại dự án từ đầu.
