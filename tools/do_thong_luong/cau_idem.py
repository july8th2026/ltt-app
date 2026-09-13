"""cau_idem.py — cau noi mong: chen `Idempotency-Key` DUY NHAT cho moi request.

## Vi sao can no

Cua ghi `/api/v1/chat/completions` **doi** header ay, mot ma cho moi lan goi:

    400 invalid_request: "This endpoint requires an Idempotency-Key header,
                          one per call"

Moi bo do LLM chuan (GuideLLM, AIPerf, vllm bench) deu noi OpenAI thuan: chung
gui mot bo header CO DINH, khong sinh ma moi moi luot. Nen chung khong ban thang
vao cua nay duoc.

⭐ Cach dung duoc ma khong sua bo do: mot cau noi tai cho, chen ma vao duong di.
   Bo do van la ban goc, khong vet va; phan rieng cua ta nam gon trong 40 dong
   doc duoc.

## ⛔ Toi da ket luan SAI mot lan o day, va day la cho ghi lai

Toi tung bao *"Idempotency-Key khong bat buoc"* vi goi thu qua
`tools/do_tai_hai_model.Khach` va nhan 200. Nhung `Khach.goi()` dong 194 **tu
chen** mot ma cho moi POST:

    dau["Idempotency-Key"] = idem or str(uuid.uuid4())

Tuc toi do CONG CU cua minh chu khong do API. Mot phep thu di qua mot lop co
hanh vi an khong tra loi duoc cau hoi ve lop BEN DUOI no.

## Cau noi nay them gi vao phep do

Mot chang loopback. `/_cau/tre` in ra thoi gian chang NGUOC DONG (cau noi ->
API); phu troi cua chinh cau noi la HIEU giua thoi gian bo do thay va con so ay.
Do duoc, va nho — nhung phai doc dung ten no.
"""
import argparse
import time
import uuid

import httpx
from fastapi import FastAPI, Request, Response
from fastapi.responses import StreamingResponse

app = FastAPI()
DICH = ""
KHOA = ""
_tre = []


@app.get("/_cau/tre")
def tre():
    """Thoi gian cua chang NGUOC DONG (cau noi -> API), khong phai phu troi cua
    cau noi.

    ⛔ Ban dau doc-string o day viet *"do tre cua chinh cau noi"* — SAI. Con so
       nay bao gom ca luot goi len `app.lttstudios.com`, tuc no lon gan bang
       thoi gian ca request. Phu troi cua cau noi la HIEU: (thoi gian bo do
       thay) - (con so nay). Mot ten sai o day se lam nguoi doc tru nham mot
       khoan gap hang tram lan.
    """
    if not _tre:
        return {"n": 0}
    v = sorted(_tre)
    return {"n": len(v), "trung_vi_ms": round(v[len(v) // 2] * 1000, 3),
            "p95_ms": round(v[int(len(v) * 0.95)] * 1000, 3)}


#: GuideLLM **cat duoi `/v1`** khoi target roi tu them lai `/v1/<route>`:
#:
#:      target `https://.../api/v1`  ->  `https://.../api` + `/v1/chat/completions`
#:      target `http://127.0.0.1:18099` ->        no       + `/v1/chat/completions`
#:
#: Nen cau noi nhan duong `v1/chat/completions` va phai BO tien to ay truoc khi
#: noi vao dich (`.../api/v1`), khong thi thanh `.../api/v1/v1/chat/completions`
#: -> 404. Do duoc: 12/12 luot dau tien hong dung vi vay.
TIEN_TO_BO = ("v1/",)


@app.api_route("/{duong:path}", methods=["GET", "POST"])
async def chuyen(duong: str, request: Request):
    for tt in TIEN_TO_BO:
        if duong.startswith(tt):
            duong = duong[len(tt):]
            break
    than = await request.body()
    dau = {k: v for k, v in request.headers.items()
           if k.lower() not in ("host", "content-length", "authorization",
                                "idempotency-key")}
    dau["Authorization"] = "Bearer " + KHOA
    # 🔴 MOT MA MOI CHO MOI LUOT. Dung mot ma co dinh thi luot thu hai nhan lai
    #    cau tra loi CU (khong co luot chay nao moi) — phep do se bao mot thong
    #    luong khong ton tai. `test_259::test_BAY_khoa_co_dinh_o_default_headers`
    #    chot dung cai bay do.
    if request.method == "POST":
        dau["Idempotency-Key"] = str(uuid.uuid4())

    t0 = time.perf_counter()
    async with httpx.AsyncClient(timeout=900) as c:
        r = await c.request(request.method, DICH + "/" + duong,
                            content=than, headers=dau,
                            params=dict(request.query_params))
    _tre.append(time.perf_counter() - t0)
    bo = {"content-encoding", "transfer-encoding", "content-length",
          "connection"}
    return Response(content=r.content, status_code=r.status_code,
                    headers={k: v for k, v in r.headers.items()
                             if k.lower() not in bo})


if __name__ == "__main__":
    import uvicorn

    ap = argparse.ArgumentParser()
    ap.add_argument("--dich", default="https://app.lttstudios.com/api/v1")
    ap.add_argument("--khoa-tep", required=True)
    ap.add_argument("--cong", type=int, default=18099)
    a = ap.parse_args()
    DICH = a.dich.rstrip("/")
    with open(a.khoa_tep) as f:
        KHOA = f.read().strip()
    print(f"cau noi: 127.0.0.1:{a.cong}  ->  {DICH}   (chen Idempotency-Key moi luot)")
    uvicorn.run(app, host="127.0.0.1", port=a.cong, log_level="warning")
