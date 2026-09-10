# Bo cong cu chay WanGP tren RunPod

Dung cho **Pod** (khong phai Serverless). Moi thu ghi ra network volume nen
song qua moi lan xoa pod, va doc ve tu may A qua S3 — **khong can shell**.

| Tep | Viec |
|---|---|
| `tao_pod.py` | tao Pod A100, **ghi so ID ngay sau khi co `id`** |
| `khoi_dong.sh` | diem vao cua pod: cai -> do -> danh dau xong |
| `cai_dat.sh` | cai WanGP theo **dung cac buoc trong `Dockerfile` chinh chu**, nhung vao `/data` de ton tai lau |
| `do_luong.py` | ma tran do, goi API theo `docs/API.md` (`from shared.api import init`) |
| `theo_doi.py` | doc tien do tu may A qua S3 |
| `wgp_config.json` | dat `checkpoints_paths` -> `/data/ckpts` (co che cua chinh WanGP) |

## Hai xung dot voi RunPod da xu ly san

1. **`/workspace` dung nhau** — WanGP dat `WORKDIR /workspace` va
   `ENTRYPOINT /workspace/entrypoint.sh`, con RunPod mac dinh gan volume vao
   dung do. ⇒ `volumeMountPath = /data`.
2. **Model roi vao o container** — `HF_HOME` va `default_checkpoints_paths`
   deu tro vao o container, mat sach khi xoa pod va khong du 20 GB.
   ⇒ `checkpoints_paths` trong `wgp_config.json` + `HF_HOME=/data/hf`.

## Ba mac dinh nguy hiem cua `POST /pods`

`containerDiskInGb=50` (ton tien) · `minRAMPerGPU=8` (qua it cho profile 1/2)
· `dataCenterIds` = ca 28 DC (khong ghim thi khong gan duoc o dia).

⛔ Sau moi luot: `video_cloud.py kiem-ke` phai tra `pods: []`.
