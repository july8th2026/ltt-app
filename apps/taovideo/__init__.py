"""App taovideo — dat hang tao video qua Seedance/ModelArk.

BE MAT CONG KHAI CUA APP NAY (spec pha 1 PROMPT AI, G-3b)
==========================================================

App nay duoc mot app khac goi sang: `prompt_ai_ommi` doc `apps.taovideo.refs`
de chuan hoa anh tham chieu (resize/inline base64) va kiem role hop le TRUOC
khi nop job `video.generate` — thay vi tu viet lai logic chuan hoa (da tung
gay loi N-1: prompt nhac anh ma refs rong).

⛔ Canh CHI gioi han o mot module thuan `apps.taovideo.refs` — khong xuyen
   qua `routes.py`/`jobs.py`. `refs.py` khong goi job, khong doc CSDL cua
   taovideo, nen dung no khong keo theo hanh vi hay trang thai cua app nay.

`BE_MAT_CONG_KHAI` duoi day la ban khai do. `lint_app_contract.py` doc no va
doi chieu hai chieu voi `APP_DUOC_DUNG_APP` — lech mot ten la gate DO.

⚠️ Them mot dong vao day la MOT QUYET DINH KIEN TRUC, khong phai mot tien
   nghi: moi ten o day la mot thu app khac duoc phep dua vao, va tu do khong
   doi duoc nua neu khong sua ca hai ben.
"""

#: `(module, ten)` — nhung thu app KHAC duoc phep goi. Moi dong mot use case.
#:
#: Co y de la TUPLE LITERAL, khong boc `frozenset(...)`: linter doc ban khai
#: nay bang `ast.literal_eval` tren cay nguon, khong import app. Mot loi goi
#: ham thi `literal_eval` khong doc duoc, va hang rao se im lang tuong nhu
#: app chua khai gi.
BE_MAT_CONG_KHAI = (
    ("apps.taovideo.refs", "normalize_image"),     # chuan hoa anh -> PNG/JPEG
    ("apps.taovideo.refs", "image_to_inline"),     # anh -> data: URL, ep <=8MiB
    ("apps.taovideo.refs", "image_role"),          # chuan hoa + remap role legacy
    ("apps.taovideo.refs", "VALID_IMAGE_ROLES"),   # bo gia tri role hop le
    ("apps.taovideo.refs", "MAX_INLINE_BYTES"),    # nguong 8 MiB de bao ly do skip
)
