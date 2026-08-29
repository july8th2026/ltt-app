"""App upscalevideo — di tru tu video_upscale (BOT GEMINI). Nang video x4 (Real-ESRGAN NCNN).

BE MAT CONG KHAI CUA APP NAY (H41.5)
====================================

App nay la **app duy nhat trong kho** duoc mot app khac goi sang: `taovideo`
dieu phoi "nang cap mot video vua tao" ngay tren trang khach vua bam nut.

⛔ Canh do KHONG bi cat, va do la mot quyet dinh chu khong phai mot khoan no:
   cat no nghia la doi viec dieu phoi di dau do, va khong cho nao tot hon cho
   hien tai. Bao gia phai la bao gia THAT cua app nay, khong phai mot ban sao
   se troi.

⭐ Cai da thieu truoc 2026-08-29 khong phai hang rao — `tools/lint_app_contract.py`
   da chot dung hai ten nay tu A-04. Cai thieu la app **tu noi ra** dau la be
   mat cua no. Khi hieu biet do chi song trong `tools/`, doi ten mot ham o day
   la mot thay doi trong lang: linter bat CHO GOI, con app nay khong he biet
   minh vua pha hop dong cua ai.

`BE_MAT_CONG_KHAI` duoi day la ban khai do. `lint_app_contract.py` doc no va
doi chieu hai chieu voi `APP_DUOC_DUNG_APP` — lech mot ten la gate DO.

⚠️ Them mot dong vao day la MOT QUYET DINH KIEN TRUC, khong phai mot tien nghi:
   moi ten o day la mot thu app khac duoc phep dua vao, va tu do khong doi duoc
   nua neu khong sua ca hai ben.
"""

#: `(module, ten)` — nhung thu app KHAC duoc phep goi. Moi dong mot use case.
#:
#: Co y de la TUPLE LITERAL, khong boc `frozenset(...)`: linter doc ban khai nay
#: bang `ast.literal_eval` tren cay nguon, khong import app (import mot app keo
#: theo ca phu thuoc cua no). Mot loi goi ham thi literal_eval khong doc duoc,
#: va hang rao se im lang tuong nhu app chua khai gi.
BE_MAT_CONG_KHAI = (
    ("apps.upscalevideo", "cost"),                        # bao gia nang cap
    ("apps.upscalevideo.service", "submit_upscale_job"),  # nop job nang cap
)
