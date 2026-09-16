# SESSION MIGRATION NOTE

# ⭐ 2026-09-16 — MỘT L3 MỖI PHIÊN (bản hiện hành)

## Câu để đưa cho một phiên đang chạy

> Nhịp test/gate đã đổi — đọc lại `docs/00_LTT_OPERATING_CONTRACT.md` §4. Từ giờ:
> trong phiên **chỉ test nhắm** đúng cụm vừa sửa, **không chạy `gate.py` ở bất kỳ
> chế độ nào**. Gặp lỗi thì sửa **tại chỗ** và chạy lại **đúng phép đã đỏ**.
> `python tools\gate.py` (L3) chạy **một lần** khi mọi pha đã xong. L3 đỏ ⇒ sửa
> tại chỗ ⇒ chạy lại đúng phép đỏ ⇒ khép bằng `gate.py --doi --tu <sha>` — **không**
> chạy L3 lần hai. Sau L3 xanh, **chính phiên bạn** gộp `main` và deploy
> (`docs/QUY_TRINH_WORKTREE.md`, `docs/16_CAP_NHAT_VA_DEPLOY.md`) — không còn vai
> "canonical integrator" riêng. Tiếp tục công việc đang làm, không phân tích lại từ đầu.

## Đổi cái gì — bốn dòng

1. **Vòng lặp không còn là `gate --doi`.** Trong phiên chỉ test nhắm
   (`thanh_phan.py --test <tp>` → `pytest <tệp>`).
2. **L3 một lần cuối phiên**, không phải ở mỗi pha/đợt/hạng mục/lát cắt.
3. **Một L3 mỗi nhánh.** L3 đỏ (hay có thay đổi sau L3 xanh) thì khép hẹp bằng
   `--doi --tu <sha>`. `gate.py` in sẵn lệnh chạy lại và **từ chối** L3 thứ hai
   trên cùng nhánh, kể cả sau L3 xanh (`--l3-lai` để vượt, có ghi).
4. **Phiên tự gộp `main` và tự deploy** sau L3 xanh, rồi báo. Không dừng ở
   `HANDOFF_READY_FINAL` chờ một integrator. `main` đã đi tiếp thì trên cây đã
   hoà chạy `gate.py --doi --tu <sha L3>`. Deploy chép cả cây ⇒ vẫn báo phiên
   khác trước (không chờ trả lời). Thao tác: `docs/QUY_TRINH_WORKTREE.md`,
   `docs/16_CAP_NHAT_VA_DEPLOY.md`.

## Vì sao — số đo

133 bản ghi gate 04/09 → 15/09: **114** lượt L3, **100** nằm trong chuỗi chạy lại
cách nhau < 45 phút, chuỗi dài nhất **7 lượt = 170 phút**; `--doi` được dùng đúng
**1** lần dù luật khi ấy gọi nó là vòng lặp mặc định. Toàn văn ở hợp đồng §4.2.

## Cây cũ chưa gộp `main`

Bản `CLAUDE.md`/`AGENTS.md`/hợp đồng trong cây của bạn có thể còn luật cũ, và
`~/.claude/CLAUDE.md` **không** chứa nhịp mới — đừng trông vào nó. Kiểm bằng
`python tools\ho_so_cay.py trang-thai`; governance lệch trunk ⇒ `git merge main`
**trước**, để có cả luật mới lẫn chốt cơ học trong `tools/gate.py`.

---

# 2026-09-08 — lịch sử (đã bị bản 16/09 thay phần nhịp)

## Câu để đưa cho một phiên đang chạy

> Kho đã cập nhật LTT Operating Contract mới. Đọc lại `CLAUDE.md` và
> `docs/00_LTT_OPERATING_CONTRACT.md`. Từ thời điểm này bỏ workflow gate/pytest
> cũ và tiếp tục theo canonical policy mới. Không tự giữ rule session cũ nếu
> mâu thuẫn.

⛔ **Đọc xong thì TIẾP TỤC công việc đang làm.** Không phân tích lại dự án từ đầu.

## Đổi cái gì — ba dòng

1. **Vòng lặp là `gate.py --doi`**, không phải `--vong-lap`. `--doi` nay thật sự
   thu hẹp (trước 08/09 nó luôn tự hạ cấp xuống đầy đủ — xem §4 dưới).
2. **Đừng chạy `test_nhanh.py` rồi `gate.py`.** Bước `bo test` bên trong gate
   *chính là* `test_nhanh.py`. Chạy cả hai là trả ~4 phút hai lần.
3. **Gate đầy đủ chỉ ở checkpoint**, không phải sau mỗi lần sửa. Đo thật: **11,4
   phút** trung vị trên 43 lượt — tài liệu cũ ghi "~5 phút".

## Việc còn lại của CHÍNH phiên bạn

Bốn thư mục dưới đây **có** cadence trùng lặp, nhưng chiến dịch **cố ý không sửa
hộ** — sửa một tệp bạn đang mở là tạo xung đột merge, và bạn sẽ giải bằng cách
giữ bản của bạn.

| Nếu bạn là phiên | Sửa giúp |
|---|---|
| `claude/chatltt-v3-agentic` | `docs/CHATLTT_V3/00_KE_HOACH_V3.md:253` — thay dòng `\| Cổng \|` bằng con trỏ tới hợp đồng |
| `phien/asv-v4` | `docs/auto_scan_video_v4/STATE_V4.md:400` — cadence `VONG_NHANH` riêng |
| phiên LTT VOICE (cây chính) | `docs/LTT_VOICE/VOICE_UI_EXECUTION_PLAN.md:463-464` |
| `phien/video-v2-wangp` | rà `docs/VIDEO_AI_V2/` xem còn cadence riêng không |

Kiểm bằng: `python tools\check_luat_van_hanh.py` — nó chỉ ra đúng dòng.
Dòng của `CHATLTT_V3` đang nằm trong bảng `NO_CU` của bộ dò; **gỡ khỏi bảng đó
luôn** khi bạn sửa xong, nếu không bộ dò sẽ đỏ vì "nợ cũ đã được dọn".

## ⚠️ Hai thứ bắt được ở khu người khác

- **Việc dở của phiên LTT VOICE đang làm ĐỎ BA bánh cóc**, tức gate đầy đủ của
  **bất kỳ ai** trên cây này cũng đỏ:

  | Bánh cóc | Mốc → nay | Vị trí |
  |---|---|---|
  | ruff `F401` | 416 → **417** | `apps/ltt_voice/routes/_p_tao.py:5` (`File` không dùng) |
  | mypy `var-annotated` | 44 → **45** | `tools/do_ho_so_giong.py:110` |
  | mypy `arg-type` | 124 → **126** | `tools/do_ho_so_giong.py:114` (×2) |
  | nuốt lỗi lặng lẽ | 62 → **63** | `tools/do_ho_so_giong.py:94` |

  ⇒ `test_306::test_ruff_hien_tai_dat_moc`, `test_306::test_mypy_hien_tai_dat_moc`
  và `test_145::test_banh_coc_nuot_loi_khong_cho_tang_them` **đang đỏ**.

  **Đã đối chứng, không phải suy đoán:** `ruff --select F,B` trên ba tệp của
  chiến dịch cho **0** phát hiện mới (một `B007` ở `thanh_phan.py:124` là mã
  **có sẵn**, ngoài mọi hunk của chiến dịch, và đã nằm trong mốc); mypy trên
  `tools/thanh_phan.py`+`tools/gate.py` cho **0**; `check_silent_except.py
  --list` **không** liệt kê tệp nào của chiến dịch.

  ⚠️ Và một bài học về **cách đọc**: `check_ruff.py` in dòng `[ruff] dat moc: 943
  phat hien` rồi vẫn **thoát mã 1**. Đọc `returncode`, đừng khớp mẫu stdout —
  lượt đọc đầu của chiến dịch này đã hiểu nhầm đúng dòng đó.
- `docs/auto_scan_video_v4/STATE_V4.md:756` viết *"There is no `pytest.ini` /
  pyproject pytest config in the repo at all"*. **Sai** — `pytest.ini` có trong
  HEAD và khai marker `nang`. Kết luận rút ra từ câu đó nên được đọc lại.

## Tệp chiến dịch này đụng vào

```
CLAUDE.md                        viet lai — bootstrap ngan
docs/00_LTT_OPERATING_CONTRACT.md   MOI — nguon chan ly quy trinh
tools/thanh_phan.py              bi_anh_huong + tep_test_da_doi   (DUNG CHUNG ⚠️)
tools/gate.py                    _thu_hep + buoc `luat van hanh`  (DUNG CHUNG ⚠️)
tools/check_luat_van_hanh.py     MOI — banh coc chong moc lai luat
docs/KE_HOACH_NOI_TIEP_2026-08-29.md · docs/MOBILE/00_KE_HOACH.md
docs/VPS/UI_MVP_V2/00_KE_HOACH_GIAO_DIEN.md · docs/admin_mvp_v3/00_KE_HOACH_TRIEN_KHAI.md
docs/CHATLTT/00_PHUONG_AN_VA_LO_TRINH.md · docs/auto_scan_video/{BASELINE_COMMANDS,reports/04_REPORT}.md
```

⚠️ Hai tệp `DUNG CHUNG` ⇒ lượt `--doi` đầu tiên của bạn sau khi kéo về sẽ **tự hạ
cấp xuống đầy đủ**. Đúng như thiết kế, không phải hỏng.
