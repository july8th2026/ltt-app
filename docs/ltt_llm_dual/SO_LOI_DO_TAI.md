# SO_LOI_DO_TAI — bo do hai model tren duong that

> Co che chong bo sot. Cau hoi "con loi nao chua xu" tra loi o **day**, khong
> tra loi bang tri nho hay bang cach cuon lai transcript.
>
> **CHAN** = cac tinh huong sau no khong con tin duoc ⇒ sua ngay.
> **DOC LAP** = ghi so, chay tiep, sua theo lo.

| ma | trieu chung ĐO ĐƯỢC | loai | sua o | doi chung | trang thai |
|---|---|---|---|---|---|
| L-01 | qua may A: mot model bi nen lam model KIA cham **2,1-8,1x** | **CHAN** | may A (chua khoanh xong) | goi THANG may B: **0,85x / 1,05x** | dang truy |
| L-02 | `ltt-3.5` voi `max_tokens <= 300` tra **RONG** va van bi tinh tien | DOC LAP | may B / ban khai | 300->rong, 600->"391" | cho |
| L-03 | `ltt-3.8` khai *"Text only"* du engine DA nap `mmproj` | DOC LAP | ban khai (may A) | `catalog.HO_SO` co_vision=True ca hai | cho |
| L-04 | bo cham `bia-01` cam chuoi tieng Viet, model tra loi tieng Anh -> **diem dung gia** | DOC LAP | bo do | — | cho |

## L-01 — nhung gi da LOAI TRU duoc

| Phep do | Ket qua | Loai tru |
|---|---|---|
| qua may A (Cloudflare) | 1,93x / 6,20x | — |
| qua may A (**loopback** 8100) | 2,09x / 8,11x | khong phai Cloudflare |
| **thang may B** (bo may A) | **0,85x / 1,05x** | **hai GPU DOC LAP — kien truc DUNG** |
| nen bang **tai khoan khac** | 7,15x / 2,36x | khong phai khoa advisory theo tai khoan |
| may B `/health` | `phuc_vu 170 / tu_choi 0`, moi bo dem chan = 0 | may B khong xep hang, khong tu choi |
| may B GPU | dung card sang (5060Ti 82%), VRAM on dinh, CPU-B 9-27% | khong nghen CPU/VRAM may B |
| may A, tien trinh nghe 8100 (pid that, **nang quyen**) | cpu 6-14%, luong 8->15, ket noi 8->12 | **khong CPU-bound**; cac luong dang CHO |

⭐ Ket luan chac chan: **kien truc dual-model khong hong**. Toan bo can thiep cheo
   do **ung dung may A** sinh ra.

⚠️ Chua xac dinh: cho nao trong may A. Con lai: pool ket noi CSDL (`db.py` khong
   dat `pool_size` => mac dinh 5+10), khoa advisory theo *tai nguyen*, hoac mot
   cho tuan tu hoa khac.

## Hai lan quy trinh nay SUA TOI

1. Phep do dau ket luan *"hai card can thiep nhau => kien truc hong"*. Goi thang
   may B lat nguoc han.
2. Gia thuyet "khoa advisory theo tai khoan" khop rat vua — co ca dong ma dung
   hinh dang. Doi chung bang tai khoan thu hai **bac bo** no.

Lam theo loi cu — thay 6,2x, doc ma, tim ra khoa, sua, deploy — la sua **nham
cho** va tin la xong.
