"""Theo doi luot do tren Pod — doc /data qua S3, khong can shell."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))
from tools.wangp.may_cloud import nap_env, tao_client, tim_app_env  # noqa: E402

nap_env(tim_app_env())
import boto3  # noqa: E402
from botocore.config import Config  # noqa: E402

# Cung nguon voi `jobs._dieu_phoi_that()`; khong go tay mot pod nao.
POD = (os.environ.get("LTTV_POD_ID") or "").strip()
if not POD:
    raise SystemExit("Thieu LTTV_POD_ID — khong doan pod nao.")
BUCKET = "uizchbiet5"
s3 = boto3.client("s3", endpoint_url=os.environ["RUNPOD_S3_ENDPOINT"],
                  region_name=os.environ["RUNPOD_S3_REGION"],
                  aws_access_key_id=os.environ["RUNPOD_S3_ACCESS_KEY"],
                  aws_secret_access_key=os.environ["RUNPOD_S3_SECRET_KEY"],
                  config=Config(signature_version="s3v4", retries={"max_attempts": 2}))


def doc(key, duoi=2500):
    try:
        b = s3.get_object(Bucket=BUCKET, Key=key)["Body"].read()
        return b.decode("utf-8", "replace")[-duoi:]
    except Exception as e:                    # noqa: BLE001
        print(f"  (khong doc duoc {key}: {type(e).__name__})")
        return None


api = tao_client()
try:
    p = api.rest("GET", f"/pods/{POD}")
    print(f"POD {POD}: {p.get('desiredStatus')} | ${p.get('costPerHr')}/gio")
except Exception as e:
    print("khong doc duoc pod:", str(e)[:90])

# Tien do: liet ke moi thu tren /data
tong = 0
ckpt = 0
r, tok = None, None
n = 0
while True:
    kw = {"Bucket": BUCKET, "MaxKeys": 1000}
    if tok:
        kw["ContinuationToken"] = tok
    r = s3.list_objects_v2(**kw)
    for o in r.get("Contents", []):
        tong += o["Size"]
        n += 1
        if o["Key"].startswith("ckpts/"):
            ckpt += o["Size"]
    if not r.get("IsTruncated"):
        break
    tok = r["NextContinuationToken"]
print(f"/data: {n} doi tuong | tong {tong/1e9:.2f} GB | trong do ckpts {ckpt/1e9:.2f} GB")

for ten, key in (("cai dat", "ket_qua/cai_dat.jsonl"),
                 ("khoi dong (duoi)", "ket_qua/khoi_dong.log"),
                 ("do luong (duoi)", "ket_qua/do_luong.log"),
                 ("moc", "ket_qua/moc.json")):
    t = doc(key, 1200)
    if t:
        print(f"\n───── {ten} ─────\n{t.strip()}")

for moc in ("ket_qua/_CAI_DAT_XONG", "ket_qua/_DO_XONG", "ket_qua/_POD_XONG"):
    if doc(moc, 50) is not None:
        print(f"\n[MOC] {moc} DA CO")
