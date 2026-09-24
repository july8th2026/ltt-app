# P4 Task 5 + 6 — Hạn chờ cộng dồn · Quét hết hạn bằng keyset

## Nguồn đã tra
- Spec §5.7 (`het_han_luc`, `che_do_het_han`), §5.9.
- Báo cáo làn p3b (`docs/superpowers/reports/p3b-do-tai/report.md`): **127 000 hàng đọc / 31,67 giây** cho `N=1000, P=8` vì mỗi tick đọc lại cả tập. Và bài học đo lường đi kèm: **số câu SQL gần như không đổi theo N**, nên một phép kiểm đếm *câu* sẽ báo "không có vấn đề" và **sai**.

## Đỏ → xanh
```
# tiem loi: con tro bo `id`; neo han vao "bay gio" thay vi `run.created_at`
6 failed, 6 passed   tests/test_1794_wf_han_cho_va_quet_het_han.py
# khoi phuc
12 passed            tests/test_1794_wf_han_cho_va_quet_het_han.py
```

## Đã làm
- **T5** `han_cho.py`: mọi điểm chờ bị kẹp bởi **một** mốc chung `run.created_at + TRAN_CHO_CONG_DON` (≤ `dong_co.TRAN_RUN`). Neo vào *lúc mở điểm chờ* cộng dồn vô hạn: mười `core.delay` × 7 ngày = 70 ngày, và suốt 70 ngày ấy khoản giữ chỗ credit vẫn treo. **Không ai khai con số 70 ngày; nó chỉ xuất hiện.**
- **T6** `cho_doi.het_han_den_han` + `noi_lai.quet_het_han`: keyset trên **cặp** `(het_han_luc, id)`. Một con trỏ chỉ có thời gian sẽ **bỏ sót** hoặc **lặp** khi nhiều điểm chờ cùng một mốc — chuyện thường, vì một run mở nhiều điểm chờ trong cùng transaction.
- `mo_diem_cho` hẹn wakeup ở **cả hai** mốc (`due_at` **và** `het_han_luc`): một `core.wait` không có `due_at`, nên chỉ hẹn theo `due_at` thì hạn chờ của nó không bao giờ được ai đánh thức.
- `dong_co.mot_vong` gọi bộ quét trong **transaction riêng** (cùng hình dạng cách ly lỗi với `ttl`, F3).

## Chưa làm được
- Bộ quét chưa khoá hàng (`FOR UPDATE SKIP LOCKED`); hai vòng động cơ song song có thể cùng hẹn một wakeup — vô hại vì `hen_luy_dang` nuốt trùng, nhưng là công thừa chưa đo.
