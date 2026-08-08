# A10 — Release audit H26.10A

Trạng thái: **PASS development · chưa deploy · G8 BLOCKED H26.12**.

## Browser evidence

- Fixture cô lập 8116; user 100 credit; file thật
  `tools/3video/pages_show_list.mp4` 7,2 MB / 52 giây.
- Source preview/summary/clear hoạt động; advanced mặc định đóng. Khi mở chỉ
  hiện Best/Balanced/Fast, không lộ `large-v3` hoặc `high_quality` trong copy.
- Fast quote 20 credit cho 3 clip; fake worker trả 2 clip, settle chi phí thật
  15 credit và hoàn phần dư, số dư 100→85.
- History có 2 output, compare hai video, save package revision 1, Download ZIP
  và Activity log đúng job.
- Mobile 390×844 và desktop 1920×1080 không overflow; console 0 error/0 warning;
  estimate 200, media range 206.
- Browser bắt lỗi source summary hiện khi `hidden`; đã thêm CSS scoped và
  regression trước khi nghiệm thu lại.

## Test evidence

| Lệnh/phạm vi | Kết quả |
|---|---|
| Regression đỏ ban đầu | FAIL 2/2 đúng gap |
| Clip targeted sau triển khai | PASS 16/16 trong 9,04 giây |
| `python tools\\gate.py --quick` | PASS 8/8 trong 26,6 giây |
| `python tools\\gate.py` | PASS 9/9 trong 1.670,8 giây; pytest 1.645,4 giây |
| English catalog | 967 chuỗi, 0 thiếu, 0 fuzzy |

Rollback: revert commit H26.10A. Không migration, không thay engine/job/cost,
không xóa project/package/output; presentation quay về layout H15.
