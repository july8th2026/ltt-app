# FAST BUILD — thiết kế và bằng chứng

> **Tệp này không phải nguồn luật.** Luật của hai hồ sơ `NORMAL`/`FAST_BUILD`
> nằm ở `docs/00_LTT_OPERATING_CONTRACT.md` §4.10, và chỉ ở đó. Ở đây là *vì
> sao nó có hình dạng như vậy* và *phép đo nào buộc phải chọn như vậy*.
>
> Viết 2026-09-09.
>
> ⚠️ **Từ 2026-09-16 `NORMAL` cũng không chạy gate trong phiên** (hợp đồng §4.1).
> Câu *"vòng lặp mặc định là L1"* ở §1 dưới đây là bối cảnh lúc viết, không còn
> là luật. Khác biệt còn lại của `FAST_BUILD`: xem hợp đồng §4.10.

## 1. Vấn đề thật, không phải vấn đề giả định

Hợp đồng §4.1 đặt vòng lặp mặc định là L1 (`gate.py --doi`). Với một sửa đổi
nhỏ trên một hệ đã đứng, đó là lựa chọn đúng và không có gì phải bàn.

Nó **không** còn đúng cho một chiến dịch nhiều ngày, nơi phần lớn thay đổi còn
chưa thành hình. Ở đó L1 trả lời một câu không ai hỏi: *"cây nửa vời này có
xanh không"* — và câu trả lời đã biết trước là **không**. Hợp đồng §4.4 đã ghi
đúng điều này bằng một câu khác: *"Đừng test một trạng thái trung gian mà bạn
đã biết chắc là dở."*

`FAST_BUILD` chỉ là §4.4 được kéo dài từ *một changeset* ra *một chiến dịch*,
kèm một điều kiện: tập thay đổi phải được **đóng băng** rồi mới chứng nhận, và
phép đo chứng nhận phải nhìn thấy **toàn bộ** tập đó.

## 2. Chỗ hỏng thật sự nằm ở phép đo, không ở kỷ luật

Đây là phần đáng giá nhất của thiết kế, và nó không hiển nhiên.

`gate.py --doi` suy phạm vi bằng `thanh_phan.duong_da_doi()`, mà hàm đó mặc
định hỏi hai câu: `git status` (phần chưa commit) + `git diff HEAD`. Cả hai đều
neo vào **`HEAD`**.

Một chiến dịch dài **có** commit checkpoint — hợp đồng §7 khuyến khích. Và ngay
sau commit checkpoint đầu tiên:

```
HEAD đã nuốt phần trước đó   ⇒   `--doi` báo "cây không đổi gì"
                             ⇒   nó hạ cấp xuống đầy đủ, hoặc chạy 0 test
```

🔴 **Đây không phải một phép đo hẹp — đây là một phép đo bỏ sót, và nó báo
xanh.** Một phép đo hẹp mà tự khai là hẹp thì vô hại; một phép đo tưởng là rộng
mới nguy hiểm. Đúng hạng lỗi mà memory *phạm vi phép đo hẹp hơn lời tuyên bố*
mô tả.

Bản sửa **không** phải một cơ chế mới: `duong_da_doi(root, goc_so=...)` **vốn
đã** nhận mốc so sánh. Thứ thiếu là một chỗ để nói mốc đó ra.

```
tools/gate.py   +--tu <ref>      → chuyển thẳng vào `goc_so`
tools/ho_so_cay.py  bat …        → ghi `baseline_sha = HEAD` lúc opt-in
                    no-kiem      → in kế hoạch chứng nhận TỪ baseline
```

Chốt của mệnh đề này: `tests/test_1100_ho_so_cay.py`
`::test_moc_baseline_bao_trum_pham_vi_mac_dinh` và
`::test_moc_baseline_thay_doi_that_su_ket_qua`. Phép thứ hai là **đối chứng**:
phép thứ nhất một mình vẫn xanh nếu `goc_so` bị nuốt im lặng.

## 3. Vì sao trạng thái nằm ngoài cây làm việc

Tệp trạng thái ở `.git/worktrees/<tên>/ltt_ho_so.json`, không ở trong cây. Ba
lý do, cả ba là lỗi **đã xảy ra thật** trong kho này:

| Nếu để trong cây | Hậu quả |
|---|---|
| `gate._anh_chup_cay()` chụp `tools/ tests/ apps/ …` trước/sau | ghi trạng thái giữa lượt ⇒ gate tự vứt bỏ phép đo — mất ~12 phút |
| deploy `robocopy` chép **cả cây**, kể cả tệp chưa theo dõi | trạng thái của một phiên đi lên máy chủ |
| commit vào nhánh | mọi cây khác checkout cùng nhánh nhận trạng thái của bạn |

`git rev-parse --absolute-git-dir` trả đúng thư mục riêng của từng worktree, nên
**không** cần bật `extensions.worktreeConfig` và không đụng `.git/config` dùng
chung — một thay đổi cấu hình toàn kho để phục vụ một cây là cái giá không cần
trả. `.gitignore` vẫn chặn thêm một bản sao đặt nhầm chỗ.

## 4. Governance cũ phải suy từ Git, không từ một chuỗi phiên bản

`docs/QUY_TRINH_WORKTREE.md` mục 2 dạy kiểm bằng `findstr /C:"loi_cho_bo_test"`.
Nó đúng, nhưng nó trả lời về **một hàm**: thêm một hàm mới thì phép kiểm ấy im
lặng bỏ qua, và cây vẫn cũ.

`ho_so_cay.py` so **blob SHA** của tập tệp quyết định luật giữa `HEAD` của cây và
trunk. Không có con số nào chép tay, nên không có gì để trôi.

⭐ **Đo 2026-09-09 15:12, trunk `05464239`** — 5/10 cây đang lệch:

| Cây | Tệp governance lệch trunk |
|---|---|
| `chatltt-v3-agentic` | contract · `gate.py` · `thanh_phan.py` |
| `video-v2-wangp` | contract · `gate.py` · `thanh_phan.py` |
| `LTTSTUDIOSAPP-aiclean` | `gate.py` |
| `LTTSTUDIOSAPP-wf2` | `gate.py` |
| `LTTSTUDIOSAPP_RELEASE_H42` | contract · `gate.py` · `thanh_phan.py` · quy trình worktree |

Con số này là lý do tồn tại của phép kiểm, không phải một lời than: một cây lệch
`gate.py` chạy một cổng chất lượng **khác** với cổng mà người đọc kết quả tưởng
là đã chạy.

## 5. Cái đã cân nhắc rồi bỏ

| Phương án | Vì sao bỏ |
|---|---|
| Thêm một hồ sơ `fast-build` vào `gate.HO_SO` | `HO_SO` trả lời "lượt chạy này chứng minh gì". `FAST_BUILD` là trạng thái **của cây, giữa các lượt chạy** — nhét vào đó là trộn hai trục |
| Ghi trạng thái bằng `git config --worktree` | phải bật `extensions.worktreeConfig` cho **toàn kho** để phục vụ một cây |
| Một công cụ tự dựng danh sách bước chứng nhận | đó là bản sao thứ hai của ánh xạ test. Kho này đã có ba bản `gate.py` song song một lần rồi |
| Viết lại `gate.py` cho baseline | không cần: `goc_so` đã có sẵn. Thay đổi thật là **12 dòng** |

## 6. Ranh giới — cái cơ chế này KHÔNG làm

- Không tự merge/reset/stash bất kỳ cây nào, kể cả cây của chính bạn.
- Không đổi cadence của `NORMAL`. Cây chính và nhánh phát hành bị **từ chối cơ
  học** khi bật, không phải được khuyên là đừng bật.
- Không thay thế `cua_so_yen.py`: ngân sách máy là một trục khác, và hợp đồng
  §4.8–4.9 vẫn áp nguyên.
- Không nói gì về deploy. Đó là §8 và `docs/16_CAP_NHAT_VA_DEPLOY.md`.

## 7. Thao tác

`docs/OPERATING_STANDARDIZATION/FAST_BUILD_OPERATOR_GUIDE.md`.
