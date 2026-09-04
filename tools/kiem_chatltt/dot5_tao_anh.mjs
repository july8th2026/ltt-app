/**
 * Đợt 5 — TẠO ẢNH TRONG HỘI THOẠI.
 *
 * 🔴 VÌ SAO ĐỢT NÀY TỒN TẠI, VÀ VÌ SAO NÓ ĐẾN MUỘN. Trước nó, bộ kiểm có 45
 *    hạng mục và **không hạng mục nào thật sự tạo một bức ảnh**. Thứ đang có
 *    chỉ là "hai nút có mặt" và "báo giá rồi bấm Huỷ".
 *
 * ⛔ Đó là lỗ hổng nằm đúng chỗ đắt nhất: `image.ltt` là một trong hai đường
 *    duy nhất **tiêu tiền theo job**. Một lỗi ở đây không làm vỡ giao diện —
 *    nó làm sai sổ tiền, và sổ tiền sai thì không ai thấy cho tới khi khách
 *    hỏi.
 *
 * ## Đợt này TIÊU TIỀN THẬT
 *
 * Mỗi lượt tạo ảnh: **3 credit** trên tài khoản test. Cả đợt ~9 credit. Con số
 * đó được **đọc lại từ báo giá**, không gõ cứng — nếu giá đổi thì hạng mục vẫn
 * đúng, chỉ khác số.
 *
 * ⭐ Và mọi hạng mục ở đây đo **cả hai đầu**: thứ người dùng thấy, và **số dư
 *    credit trước/sau**. Một artifact hiện ra mà sổ tiền sai thì vẫn là hỏng.
 */

import { anhHopLe } from './dot4_dinh_kem.mjs';

export function dot5({ cho, doiDen, soDu, hoiThoaiMoi, guiChu, xong, nangLuc }) {
  const nutAnh = (p) => p.getByRole('button', { name: 'Tạo ảnh' });
  const oMoTa = (p) => p.getByLabel('Mô tả ảnh');

  /** Mở panel ảnh trong một hội thoại đã có ít nhất một lượt. */
  async function moPanelAnh(p) {
    if (!(await nutAnh(p).count())) {
      // Nút media chỉ có trong một hội thoại đã mở. Tạo một lượt rẻ nhất.
      await hoiThoaiMoi(p);
      await guiChu(p, 'Chao.');
      await xong(p);
    }
    // ⛔ NUT VO HIEU KHONG PHAI LOI GIAO DIEN — xem chu thich day du o
    //    `dot6_tao_giong.mjs`. Nut tat khi `san_sang !== 'san_sang'`, tuc model
    //    chua nap tren may B. Bo qua o day phai KEM con so may chu tra ve.
    try {
      await doiDen('model anh nap xong (nut het vo hieu)', async () =>
        (await nutAnh(p).count()) > 0 && !(await nutAnh(p).isDisabled()), 210);
    } catch {
      return { bo_qua: `model anh chua nap — may chu noi image.ltt=`
        + `${await nangLuc(p, 'image.ltt')}` };
    }
    // ⛔ NUT NAY LA MOT CONG TAC BAT/TAT. Bam khi panel DA MO thi no DONG lai,
    //    va hang muc doi mai mot o nhap vua bi an di. Hang muc `5.1` ket thuc
    //    bang "Huy" va de panel mo — nen `5.2` bam mot phat la tat.
    //
    // ⭐ Kiem trang thai truoc khi thao tac, dung bam mu. Mot phep do khong
    //    duoc gia dinh no la thu duy nhat da cham vao trang.
    if (!(await oMoTa(p).count())) await nutAnh(p).click();
    await doiDen('o mo ta anh hien ra', async () => (await oMoTa(p).count()) > 0, 20);
  }

  /** Lấy con số credit trong hộp xác nhận giá — KHÔNG gõ cứng. */
  async function xemGia(p, moTa) {
    await oMoTa(p).fill(moTa);
    await p.getByRole('button', { name: 'Xem giá' }).click();
    const chu = await doiDen('hien xac nhan gia', async () => {
      const t = await p.getByRole('group', { name: 'Xác nhận giá' })
        .innerText().catch(() => '');
      return t.includes('credit') ? t.replace(/\s+/g, ' ') : null;
    }, 30);
    const m = chu.match(/(\d+)\s*credit/);
    if (!m) throw new Error(`khong doc duoc gia tu: ${JSON.stringify(chu)}`);
    return { chu, gia: Number(m[1]) };
  }

  const soAnh = (p) => p.locator('article img').count();

  return [
    {
      dot: 5,
      ten: '5.1-bao-gia-khong-tru-tien-va-Huy-khong-de-lai-gi',
      hoi: 'Xem giá rồi Huỷ — có mất tiền hay để lại rác trong hội thoại không?',
      async chay(p) {
        const bq = await moPanelAnh(p);
        if (bq) return bq;
        const truoc = await soDu(p);
        const anhTruoc = await soAnh(p);
        const { gia } = await xemGia(p, 'mot con meo tam mau ngoi tren bau cua so');
        const giuaChung = await soDu(p);
        await p.getByRole('button', { name: 'Huỷ' }).click();
        await cho(2500);
        const sau = await soDu(p);
        const anhSau = await soAnh(p);

        if (truoc !== giuaChung) throw new Error(`BAO GIA da tru tien: ${truoc} -> ${giuaChung}`);
        if (truoc !== sau) throw new Error(`HUY van tru tien: ${truoc} -> ${sau}`);
        if (anhSau !== anhTruoc) throw new Error(`HUY van de lai ${anhSau - anhTruoc} anh`);
        return { gia_bao: gia, so_du: truoc, khong_doi: true };
      },
    },
    {
      dot: 5,
      ten: '5.2-tao-anh-tron-vong-va-thu-DUNG-so-da-bao',
      hoi: 'Tạo thật: có ảnh không, và có thu đúng số đã báo không?',
      async chay(p) {
        // 🔴 Bat bien tien cua ca app: `runtime_noi_bo.job` giu cho theo tran
        //    UOC cao, roi `_quyet_toan_credit` thu theo **anh THAT** va hoan
        //    phan du (`test_606`). Hang muc nay do dieu do tu phia NGUOI DUNG:
        //    so du giam dung bang so da bao, khong hon.
        const bq = await moPanelAnh(p);
        if (bq) return bq;
        const truoc = await soDu(p);
        const anhTruoc = await soAnh(p);
        const { gia } = await xemGia(p, 'mot ngon hai dang tren vach da luc hoang hon');
        await p.getByRole('button', { name: 'Đồng ý, tạo' }).click();

        // ⛔ PHAN BIET "HONG" VOI "MAY DANG BAN". Do 04/09: job nam `queued`
        //    180 giay, va log worker cho thay he thong lam DUNG — nhat job moi
        //    21 giay, cong render tra `/health` 200, nhung bao `DangBan: May
        //    tao anh dang ban` roi hoan lai va **khong thu tien** (`thu: 0`).
        //    GPU may B luc do dang chay phep do cua mot phien khac.
        //
        // ⭐ Mot hang muc bao HONG o day la vu khong san pham. Nhung bao DAT
        //    thi cung sai. Dung la: hoi CHINH may chu xem job dang o dau, roi
        //    noi ra ly do that.
        try {
          await doiDen('anh hien ra trong hoi thoai', async () =>
            (await soAnh(p)) > anhTruoc, 180);
        } catch (e) {
          const tt = await p.evaluate(async () => {
            const cid = location.hash.slice(1);
            const s = await fetch('/chatltt/api/hoi-thoai/' + cid).then((r) => r.json());
            const m = [...s.messages].reverse().find((x) => x.execution?.mode === 'job');
            return m ? { status: m.status, ex: m.execution.status,
                         credit: m.execution.credit, ma: m.execution.error_code || '' } : null;
          }).catch(() => null);
          if (tt && (tt.status === 'queued' || tt.ex === 'queued') && (tt.credit?.thu ?? 0) === 0) {
            return { bo_qua: 'may tao anh dang ban — job van `queued`, chua thu tien '
              + `(giu ${tt.credit?.giu}, thu ${tt.credit?.thu}). He thong hoan lai dung.` };
          }
          throw new Error(`${e.message} | trang thai job: ${JSON.stringify(tt)}`);
        }
        await doiDen('anh tai xong (qua 302 -> R2)', async () => p.evaluate(() => {
          const im = [...document.querySelectorAll('article img')].pop();
          return !!im && im.complete && im.naturalWidth > 0;
        }), 60);
        await cho(3000);                       // để sổ tiền kịp quyết toán
        const sau = await soDu(p);

        const thu = truoc - sau;
        if (thu !== gia) throw new Error(`bao ${gia} credit ma thu ${thu} (${truoc} -> ${sau})`);
        const anh = await p.evaluate(() => {
          const im = [...document.querySelectorAll('article img')].pop();
          return { rong: im.naturalWidth, cao: im.naturalHeight, alt: im.alt,
                   qua_cua_so_huu: (im.getAttribute('src') || '').includes('/tai-san/') };
        });
        if (!anh.qua_cua_so_huu) throw new Error('anh khong di qua cua kiem so huu');
        if (!/ChatLTT tạo/i.test(anh.alt)) {
          throw new Error(`alt sai cho anh DO CHATLTT TAO: ${JSON.stringify(anh.alt)}`);
        }
        return { gia_bao: gia, da_thu: thu, ...anh };
      },
    },
    {
      dot: 5,
      ten: '5.3-anh-song-qua-F5-va-thuoc-dung-hoi-thoai',
      hoi: 'Tải lại trang — ảnh vừa tạo còn không, và còn đúng chỗ không?',
      async chay(p) {
        const hashTruoc = await p.evaluate(() => location.hash);
        const truoc = await soAnh(p);
        if (!truoc) return { bo_qua: 'chua co anh nao — chay 5.2 truoc' };

        await p.reload({ waitUntil: 'domcontentloaded' });
        await doiDen('hoi thoai hien lai', async () =>
          (await p.locator('article').count()) >= 2, 40);
        await doiDen('anh hien lai va tai xong', async () => p.evaluate(() => {
          const im = [...document.querySelectorAll('article img')].pop();
          return !!im && im.complete && im.naturalWidth > 0;
        }), 60);
        const hashSau = await p.evaluate(() => location.hash);
        if (hashSau !== hashTruoc) throw new Error(`F5 doi hoi thoai: ${hashTruoc} -> ${hashSau}`);
        const sau = await soAnh(p);
        if (sau < truoc) throw new Error(`mat anh sau F5: ${truoc} -> ${sau}`);
        return { anh_truoc: truoc, anh_sau: sau, hash_giu: true };
      },
    },
    {
      dot: 5,
      ten: '5.4-artifact-cua-nguoi-khac-khong-tai-duoc',
      hoi: 'Đoán một khoá ảnh của người khác — máy chủ có trả về không?',
      // Hang muc nay CO Y goi mot khoa khong thuoc minh; 404 la ket qua DUNG.
      loi_mong_doi: [/404 GET .*\/tai-san\//, /Failed to load resource/],
      async chay(p) {
        // 🔴 Kiem o TANG MAY CHU. Giao dien chi hien anh cua chinh minh, nen
        //    "khong thay anh nguoi khac" tren man hinh khong chung minh gi —
        //    ke tan cong khong dung giao dien, ho go thang duong dan.
        const r = await p.evaluate(async () => {
          const thu = async (khoa) => {
            const res = await fetch('/chatltt/tai-san/' + khoa, { redirect: 'manual' });
            return res.status;
          };
          return {
            nguoi_khac: await thu('anhnoibo/00000000-0000-0000-0000-000000000000/job/0.png'),
            thoat: await thu('anhnoibo/00000000-0000-0000-0000-000000000000/../../secrets/app.env'),
            la: await thu('khong-phai-hinh-nao-ca/x.png'),
          };
        });
        for (const [ten, ma] of Object.entries(r)) {
          if (ma !== 404) throw new Error(`"${ten}" tra ${ma}, phai la 404`);
        }
        // ⭐ Ba truong hop phai tra CUNG mot ma. Khac nhau la noi cho ke do biet
        //    khoa nao co that — mot kenh do ri du lieu bang chinh ma trang thai.
        return r;
      },
    },
    {
      dot: 5,
      ten: '5.5-tat-model-anh-thi-nut-khoa-VA-may-chu-tu-choi',
      hoi: 'Khi ảnh không khả dụng, giao diện khoá — và máy chủ có khoá theo không?',
      // May chu tu choi mot bao gia cho nang luc khong mo — 400 la ket qua dung.
      loi_mong_doi: [/40\d POST .*\/api\/bao-gia/, /Failed to load resource/],
      async chay(p) {
        // ⚠️ Khong tat that nang luc anh tren production — do la thao tac van
        //    hanh, khong phai mot phep kiem. Thay vao do kiem menh de con lai:
        //    may chu KHONG tin giao dien, va tu choi mot nang luc ngoai
        //    allowlist du giao dien co goi hay khong.
        const r = await p.evaluate(async () => {
          const csrf = document.querySelector('[data-csrf]')?.getAttribute('data-csrf') || '';
          const res = await fetch('/chatltt/api/bao-gia', {
            method: 'POST',
            headers: { 'content-type': 'application/json', 'X-CSRF-Token': csrf },
            body: JSON.stringify({ nang_luc: 'video.khong_he_co', tham_so: { prompt: 'x' } }),
          });
          const chu = await res.text();
          return { status: res.status, than: chu.slice(0, 160),
                   la_html: chu.trim().startsWith('<') };
        });
        if (r.status === 200) throw new Error('may chu BAO GIA cho mot nang luc ngoai allowlist');
        if (r.status >= 500) throw new Error(`may chu 5xx thay vi tu choi sach: ${r.status}`);
        // ⛔ CON SO 403 KHONG DU. Lat 04/09 bao DAT voi than la
        //    `<!DOCTYPE html>...Just a moment...` — mot trang thu thach cua
        //    Cloudflare, khong phai loi cua ung dung. Hai loai 403 do khong
        //    phan biet duoc neu chi doc ma trang thai.
        //
        // ⭐ Doi THAN JSON cua chinh ung dung: `khong_duoc_phep` la cau tra
        //    loi cua san pham, va no khong the den tu mot lop bien nao khac.
        if (r.la_html) throw new Error(`bi mot lop BIEN chan (than la HTML), khong phai ung dung tu choi: ${r.than.slice(0, 90)}`);
        if (!/khong_duoc_phep/.test(r.than)) {
          throw new Error(`than tu choi khong phai cua ung dung: ${r.than.slice(0, 120)}`);
        }
        return r;
      },
    },
    {
      dot: 5,
      ten: '5.6-KHONG-co-anh-tham-chieu-thi-che-do-la-t2i',
      hoi: 'Không đính ảnh — yêu cầu gửi đi có đúng `mode=t2i` không?',
      async chay(p) {
        const bq = await moPanelAnh(p);
        if (bq) return bq;
        const batDuoc = [];
        const nghe = (req) => {
          if (req.url().includes('/api/bao-gia')) batDuoc.push(req.postData() || '');
        };
        p.on('request', nghe);
        try {
          await xemGia(p, 'mot chiec la phong tren mat ho luc sang som');
          await doiDen('bao gia da di ra', () => batDuoc.length > 0, 25);
          const than = JSON.parse(batDuoc[0]);
          const ts = than.tham_so || {};
          if (ts.mode !== 't2i') throw new Error(`mong mode=t2i, nhan ${JSON.stringify(ts.mode)}`);
          if (ts.image_keys && ts.image_keys.length) {
            throw new Error(`t2i ma van kem anh: ${JSON.stringify(ts.image_keys)}`);
          }
          await p.getByRole('button', { name: 'Huỷ' }).click().catch(() => {});
          return { mode: ts.mode, khong_kem_anh: true };
        } finally {
          p.off('request', nghe);
        }
      },
    },
    {
      dot: 5,
      ten: '5.7-tao-anh-TU-ANH-tham-chieu-di-dung-vao-yeu-cau',
      hoi: 'Đính một ảnh tham chiếu — nó có thật sự đi theo yêu cầu, đúng chế độ?',
      async chay(p) {
        // 🔴 HANG MUC NAY DO MOT THU DA TUNG KHONG THE CHAY DUOC.
        //
        //    Khoa anh cua ChatLTT truoc 04/09 la `chatltt/anh-vao/<uid>/...`,
        //    nen doan thu HAI la `"anh-vao"` chu khong phai id nguoi dung. Ma
        //    `anhnoibo/features._kiem_chu_so_huu` kiem dung doan thu hai. Ket
        //    qua: MOI anh khach tai len trong chat deu bi tu choi voi cau "Anh
        //    tham chieu khong thuoc nguoi dung hien tai".
        //
        // ⭐ Mot hang rao an toan DUNG, chan mot thao tac HOP LE, chi vi mot dau
        //    `/` dat sai cho — va no khong bao gi ca, no chi lam tinh nang
        //    trong nhu chua duoc xay. Hang muc nay la thu ngan no quay lai.
        const bq = await moPanelAnh(p);
        if (bq) return bq;
        const o = p.getByLabel('Ảnh tham chiếu');
        if (!(await o.count())) throw new Error('khong co o dinh anh tham chieu');
        await o.setInputFiles([anhHopLe(64, 64)]);
        await doiDen('chip anh tham chieu hien ra', async () =>
          (await p.locator('.ltc-media__ref .ltc-chip').count()) > 0, 30);

        const batDuoc = [];
        const nghe = (req) => {
          if (req.url().includes('/api/bao-gia')) batDuoc.push(req.postData() || '');
        };
        p.on('request', nghe);
        try {
          const { gia } = await xemGia(p, 'doi bau troi trong anh thanh mau tim');
          await doiDen('bao gia da di ra', () => batDuoc.length > 0, 25);
          const ts = (JSON.parse(batDuoc[0]).tham_so) || {};
          if (ts.mode !== 'edit') throw new Error(`mong mode=edit, nhan ${JSON.stringify(ts.mode)}`);
          const khoa = ts.image_keys || [];
          if (khoa.length !== 1) throw new Error(`mong 1 anh tham chieu, nhan ${khoa.length}`);
          // ⛔ VA KHOA PHAI DUNG HINH: id nguoi dung o DOAN THU HAI. Doc chinh
          //    cai chuoi do la cach duy nhat phat hien lai loi cu tu ngoai vao.
          const doan = String(khoa[0]).split('/');
          if (doan[0] !== 'chatltt' || doan[2] !== 'anh-vao') {
            throw new Error(`khoa sai hinh (uid phai o doan 2): ${khoa[0]}`);
          }
          await p.getByRole('button', { name: 'Huỷ' }).click().catch(() => {});
          return { mode: ts.mode, so_anh_tham_chieu: khoa.length,
                   hinh_khoa: `${doan[0]}/<uid>/${doan[2]}/…`, gia_bao: gia };
        } finally {
          p.off('request', nghe);
        }
      },
    },
  ];
}
