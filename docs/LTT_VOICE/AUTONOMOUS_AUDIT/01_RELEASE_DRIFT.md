# 01 — RELEASE DRIFT (2026-09-05)

## OBSERVED

    master  <-> admin-mvp-v3  =  0 sau / 94 truoc
    merge-base                =  d225a480

Bản chạy ở `C:\LTTPlatform\app` khớp **`master`**, không khớp nhánh làm việc.

## ⛔ VÀ ĐÂY LÀ CHỖ DỄ LÀM SAI NHẤT

Bản yêu cầu nói thẳng, và nó đúng: **"94 commit ahead → merge tất cả vì prompt
nói vậy"** là một quyết định tồi. 94 commit không phải một đơn vị; chúng là 94
quyết định riêng, và một số có thể không liên quan gì tới Voice.

Nhưng phân loại 94 commit rồi cherry-pick một tập con lại **tạo ra một trạng
thái chưa ai QA**. Đó là đánh đổi thật, và nó nghiêng hẳn về một phía ở đây:

| phương án | thứ được deploy | đã QA chưa |
|---|---|---|
| cherry-pick tập con Voice | một cây **mới**, chưa từng tồn tại | ⛔ **không** |
| deploy cả nhánh | đúng cây vừa chạy gate + kiểm trình duyệt | ✅ có |

⭐ Mục tiêu của mục 24 trong bản yêu cầu là *"code đã QA chính là code runtime
sẽ chạy"*. Chỉ phương án thứ hai đạt được điều đó.

## Vì sao deploy cả nhánh là an toàn Ở ĐÂY (không phải luôn luôn)

1. `admin-mvp-v3` là nhánh tích hợp của dự án này, không phải một nhánh tính
   năng. `docs/16_CAP_NHAT_VA_DEPLOY.md` mô tả nó như vậy.
2. Nó **0 commit sau** `master` ⇒ deploy không mất gì của `master`.
3. Cổng chất lượng đầy đủ chạy trên **đúng cây này**, không phải trên một tập
   con giả định.
4. `docs/_luutru/…` ghi lại rằng deploy chép **cả cây** — không có cơ chế nào
   tách phần của một phiên ra, nên "chỉ deploy phần Voice" không phải một thao
   tác tồn tại.

## ⚠️ ĐIỀU KIỆN, và nó KHÔNG được bỏ qua

Cây này chứa công việc của **nhiều phiên**. Trước khi deploy phải:

- `git status` sạch ✅
- gate đầy đủ xanh trên chính cây ấy
- kiểm còn phiên nào đang ghi vào cây không (`ListAgents`, nhịp ghi tệp)
- xem có migration alembic mới không, và `alembic heads` chỉ có **một** đầu

Đây là bốn bước mà `deploy-copy-ca-cay-va-alembic-head` (memory) đã ghi lại từ
một lần trả giá trước.

## DECISION

Deploy **cả nhánh `admin-mvp-v3`** bằng `setup/2-cai-dat.ps1` — đúng đường chính
thức, không robocopy tay, vì chỉ đường ấy mới ghi `dau_van_tay.json`.

⛔ Bước chạy script **cần UAC** và đó là ranh giới của người dùng
(`lenh-nang-quyen-tren-may-chu`). Claude chuẩn bị toàn bộ; người dùng bấm.

## STATUS

⏸ Chờ deploy. Xem `07_RELEASE_REPORT.md` cho trạng thái cuối và lệnh chính xác.
