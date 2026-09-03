/**
 * Đợt 6 — TẠO GIỌNG TRONG HỘI THOẠI.
 *
 * 🔴 Cùng lý do với đợt 5: `speech.ltt` là đường **thứ hai** tiêu tiền theo
 *    job, và trước đợt này không hạng mục nào thật sự tạo một đoạn tiếng.
 *
 * ⛔ Nhưng tiếng có một thứ ảnh không có: **giọng nhân bản là dữ liệu sinh trắc
 *    của một con người.** `apps/ltt_voice/tables.py` ghi thẳng điều đó, và
 *    `features.giai_giong` kiểm chủ sở hữu ở **một chỗ duy nhất**. Một lỗi ở
 *    đó không phải "thấy nhầm dữ liệu" — nó là dùng giọng của người khác.
 *
 * ⭐ Nên đợt này kiểm ba tầng khác nhau của cùng một mệnh đề "giọng là của ai":
 *    danh sách trong catalog (đợt 0 đã chốt), tham số gửi lên, và cửa tải
 *    artifact.
 *
 * ## Chi phí
 *
 * Mỗi lượt ~1 credit (tiền theo **giây** `ffprobe`, không theo ký tự). Cả đợt
 * ~3 credit. Con số đọc lại từ báo giá, không gõ cứng.
 */

export function dot6({ cho, doiDen, soDu, hoiThoaiMoi, guiChu, xong, chuBaiCuoi, nangLuc }) {
  const nutGiong = (p) => p.getByRole('button', { name: 'Tạo giọng' });
  const oChu = (p) => p.getByLabel('Văn bản cần đọc');
  const chonGiong = (p) => p.getByRole('combobox', { name: 'Chọn giọng' });
  const soAm = (p) => p.locator('article audio').count();

  /** Mo o soan tieng. Tra `null` khi mo duoc, `{bo_qua}` khi model chua nap. */
  async function moPanelGiong(p) {
    if (!(await nutGiong(p).count())) {
      await hoiThoaiMoi(p);
      await guiChu(p, 'Chao.');
      await xong(p);
    }
    // ⛔ NUT VO HIEU KHONG PHAI LOI GIAO DIEN. `TaoMedia.tsx` tat nut khi
    //    `san_sang !== 'san_sang'` — tuc **model chua nap tren may B**. Lat
    //    chay 04/09 bao HONG o day, va ket luan do sai: catalog ngay sau do
    //    tra `speech.ltt=san_sang`. GPU luc ay dang giu LLM cho dot 1-4.
    //
    // ⭐ Nen doi that lau (model nap ~1-2 phut), roi neu van chua thi HOI MAY
    //    CHU va bo qua KEM CON SO no tra ve. Bo qua co bang chung.
    try {
      await doiDen('model tieng nap xong (nut het vo hieu)', async () =>
        (await nutGiong(p).count()) > 0 && !(await nutGiong(p).isDisabled()), 210);
    } catch {
      return { bo_qua: `model tieng chua nap — may chu noi speech.ltt=`
        + `${await nangLuc(p, 'speech.ltt')}` };
    }
    // ⛔ NUT NAY LA MOT CONG TAC BAT/TAT. Bam khi panel DA MO thi no DONG lai,
    //    va hang muc doi mai mot o nhap vua bi an di. Hang muc `5.1` ket thuc
    //    bang "Huy" va de panel mo — nen `5.2` bam mot phat la tat.
    //
    // ⭐ Kiem trang thai truoc khi thao tac, dung bam mu. Mot phep do khong
    //    duoc gia dinh no la thu duy nhat da cham vao trang.
    if (!(await oChu(p).count())) await nutGiong(p).click();
    await doiDen('o van ban hien ra', async () => (await oChu(p).count()) > 0, 20);
  }

  async function xemGia(p, chu) {
    await oChu(p).fill(chu);
    await p.getByRole('button', { name: 'Xem giá' }).click();
    const t = await doiDen('hien xac nhan gia', async () => {
      const x = await p.getByRole('group', { name: 'Xác nhận giá' })
        .innerText().catch(() => '');
      return x.includes('credit') ? x.replace(/\s+/g, ' ') : null;
    }, 30);
    const m = t.match(/(\d+)\s*credit/);
    if (!m) throw new Error(`khong doc duoc gia tu: ${JSON.stringify(t)}`);
    return { chu: t, gia: Number(m[1]) };
  }

  return [
    {
      dot: 6,
      ten: '6.1-tao-giong-tron-vong-va-thu-DUNG-so-da-bao',
      hoi: 'Tạo tiếng thật: có audio không, và thu đúng số đã báo không?',
      async chay(p) {
        const bq = await moPanelGiong(p);
        if (bq) return bq;
        const truoc = await soDu(p);
        const amTruoc = await soAm(p);
        const { gia } = await xemGia(p, 'Xin chao, day la mot cau thu de kiem giong noi.');
        const giuaChung = await soDu(p);
        if (truoc !== giuaChung) throw new Error(`BAO GIA da tru tien: ${truoc} -> ${giuaChung}`);

        await p.getByRole('button', { name: 'Đồng ý, tạo' }).click();
        // Cung ly le nhu `5.2`: may ban la mot ket qua, khong phai mot loi.
        try {
          await doiDen('khoi am thanh hien ra', async () => (await soAm(p)) > amTruoc, 180);
        } catch (e) {
          const tt = await p.evaluate(async () => {
            const cid = location.hash.slice(1);
            const s2 = await fetch('/chatltt/api/hoi-thoai/' + cid).then((r) => r.json());
            const m = [...s2.messages].reverse().find((x) => x.execution?.mode === 'job');
            return m ? { status: m.status, ex: m.execution.status,
                         credit: m.execution.credit, ma: m.execution.error_code || '' } : null;
          }).catch(() => null);
          if (tt && (tt.status === 'queued' || tt.ex === 'queued') && (tt.credit?.thu ?? 0) === 0) {
            return { bo_qua: 'may tao tieng dang ban — job van `queued`, chua thu tien' };
          }
          throw new Error(`${e.message} | trang thai job: ${JSON.stringify(tt)}`);
        }
        await cho(3000);
        const sau = await soDu(p);
        const thu = truoc - sau;
        if (thu !== gia) throw new Error(`bao ${gia} credit ma thu ${thu} (${truoc} -> ${sau})`);

        const am = await p.evaluate(() => {
          const a = [...document.querySelectorAll('article audio')].pop();
          return { co: !!a, src: a?.getAttribute('src') || '',
                   dieuKhien: a?.hasAttribute('controls') ?? false };
        });
        if (!am.src.includes('/tai-san/')) throw new Error('am thanh khong di qua cua kiem so huu');
        // ⛔ `controls` khong phai trang tri: khong co no thi khong ai nghe duoc,
        //    va ban ghi tro thanh mot the vo hinh ma khach da tra tien.
        if (!am.dieuKhien) throw new Error('the <audio> khong co `controls` — khong nghe duoc');
        return { gia_bao: gia, da_thu: thu, qua_cua_so_huu: true };
      },
    },
    {
      dot: 6,
      ten: '6.2-giong-rieng-di-DUNG-vao-tham-so',
      hoi: 'Chọn giọng của mình — nó có thật sự đi theo yêu cầu không?',
      async chay(p) {
        const bq = await moPanelGiong(p);
        if (bq) return bq;
        if (!(await chonGiong(p).count())) {
          // ⭐ BO QUA, khong HONG. Bo chon chi hien khi nguoi dung CO giong
          //    nhan ban — mot tai khoan chua nhan ban giong nao thi menh de
          //    nay chua kiem duoc, khong phai bi vi pham.
          return { bo_qua: 'tai khoan nay chua co giong nhan ban nao' };
        }
        const cac = await chonGiong(p).locator('option')
          .evaluateAll((o) => o.map((x) => ({ v: x.value, t: x.textContent.trim() })));
        const rieng = cac.find((x) => x.v && x.v !== '');
        if (!rieng) return { bo_qua: 'chi co giong dung san' };

        // Bat yeu cau di ra de xem `voice_id` co that su duoc gui khong.
        const batDuoc = [];
        const nghe = (req) => {
          if (req.url().includes('/api/hoi-thoai/') && req.url().endsWith('/tao')) {
            batDuoc.push(req.postData() || '');
          }
        };
        p.on('request', nghe);
        try {
          await chonGiong(p).selectOption(rieng.v);
          await cho(600);
          const { gia } = await xemGia(p, 'Doc bang giong rieng cua toi.');
          await p.getByRole('button', { name: 'Đồng ý, tạo' }).click();
          await doiDen('yeu cau tao da di ra', () => batDuoc.length > 0, 30);
          const than = batDuoc[0];
          if (!than.includes(rieng.v)) {
            throw new Error(`giong da chon (${rieng.v}) KHONG co trong than yeu cau: ${than.slice(0, 200)}`);
          }
          return { giong: rieng.t.slice(0, 30), gia_bao: gia, di_vao_tham_so: true };
        } finally {
          p.off('request', nghe);
        }
      },
    },
    {
      dot: 6,
      ten: '6.3-giong-cua-NGUOI-KHAC-khong-bao-gio-thanh-tieng',
      hoi: 'Gõ tay một voice_id không thuộc mình — có ra tiếng không, và tiền có về không?',
      loi_mong_doi: [/40\d POST .*\/(tao|bao-gia)/, /Failed to load resource/],
      async chay(p) {
        // 🔴 PHIEN BAN DAU CUA HANG MUC NAY DOI SAI THU, VA NO BAO DO MOT LAN.
        //
        //    No doi may chu tra 4xx **ngay luc nop**, roi bao HONG khi nhan
        //    202. Nhung do khong phai lo hong — do la thiet ke, va thiet ke ay
        //    duoc ghi ro trong `tham_chieu.tim_profile`:
        //
        //      "Dung tach thanh 'tim theo id roi so owner': hai buoc thi co mot
        //       khoang trong o giua ma mot ban va sau nay rat de quen buoc hai."
        //
        //    `features.giai_giong` la cho kiem **duy nhat**, va no phai la duy
        //    nhat: no can `cho_dung_chung=True` de kho giong chung van doc
        //    duoc. Mot phep kiem o route se KHONG thay kho chung, nen no vua
        //    thanh cho kiem **thu hai** vua chan nham giong hop le.
        //
        // ⛔ Nen doi mot cai chan o route la doi san pham TE DI de phep kiem
        //    xanh. Menh de that khong phai "nop bi tu choi" ma la:
        //    **khong bao gio ra tieng, va tien ve du.**
        //
        // ⭐ Do 04/09 tren production, chinh cai job bi bao la "lo hong":
        //    `failed`, giu 1 / thu 0 / **hoan 1**, kem cau
        //    "Khong tim thay giong nay trong tai khoan cua ban." Bat bien giu.
        const r = await p.evaluate(async () => {
          const csrf = document.querySelector('[data-csrf]')?.getAttribute('data-csrf') || '';
          const cid = location.hash.slice(1);
          if (!cid) return { bo_qua: 'chua mo hoi thoai nao' };
          const res = await fetch(`/chatltt/api/hoi-thoai/${cid}/tao`, {
            method: 'POST',
            headers: { 'content-type': 'application/json', 'X-CSRF-Token': csrf },
            body: JSON.stringify({
              nang_luc: 'speech.ltt', credit: 1,
              tham_so: { text: 'thu giong nguoi khac', voice_id: 'vc_00000000000000000000000000000000' },
            }),
          });
          return { status: res.status, than: (await res.text()).slice(0, 200) };
        });
        if (r.bo_qua) return r;
        if (r.status >= 500) throw new Error(`may chu 5xx thay vi tu choi sach: ${r.status}`);
        // Duong MOT: tu choi ngay. Sach nhat, va cung dat.
        if (r.status >= 400) return { chan_luc_nop: r.status, ra_tieng: false };

        // Duong HAI: nhan job, roi job hong va tra tien. Cung dat, mien la
        // ca HAI ve deu dung — va ta doi ca hai, khong chi mot.
        const amTruoc = await soAm(p);
        const truoc = await soDu(p);
        let cuoiCung = null;
        const ket = await doiDen('job giong la ket thuc', async () => {
          const t = await p.evaluate(() => {
            const cid = location.hash.slice(1);
            return fetch('/chatltt/api/hoi-thoai/' + cid).then((x) => x.json())
              .then((s) => {
                const m = [...s.messages].reverse().find((y) => y.execution?.mode === 'job');
                return m ? { ex: m.execution.status, credit: m.execution.credit,
                             loi: (m.execution.error_text || '').slice(0, 120) } : null;
              });
          }).catch((e) => ({ ex: 'khong_doc_duoc', vi_sao: String(e).slice(0, 160) }));
          // ⛔ DUNG NUOT LOI THANH `null`. Lat truoc bao "lan cuoi: null" va
          //    con so do khong noi duoc no la "chua xong" hay "khong doc duoc"
          //    hay "khong co job nao" — ba nguyen nhan khac han nhau, cung mot
          //    hien thi. Mot chan doan mo la mot lat chay phai lam lai.
          if (t && t.ex === 'khong_doc_duoc') throw new Error('doc trang thai job hong: ' + t.vi_sao);
          if (t === null) { cuoiCung = 'chua thay tin nhan nao mode=job trong hoi thoai'; return null; }
          cuoiCung = t;
          return ['done', 'failed', 'cancelled'].includes(t.ex) ? t : null;
        }, 240).catch((e) => {
          // ⭐ Cung ly le nhu `5.2` va `6.1`: **may ban la mot ket qua**. Job
          //    van `queued` voi thu=0 nghia la hang doi dai, khong phai bat
          //    bien bi vi pham — va cai ta dang do o day (khong ra tieng,
          //    tien ve du) VAN chua the ket luan. Bo qua, kem bang chung.
          const c = cuoiCung && cuoiCung.credit;
          if (cuoiCung && cuoiCung.ex === 'queued' && (c?.thu ?? 0) === 0) {
            return { bo_qua: 'may tao tieng dang ban — job van `queued`, chua thu tien '
              + `(giu ${c?.giu ?? 0}, thu ${c?.thu ?? 0})` };
          }
          throw new Error(e.message + ' | ' + JSON.stringify(cuoiCung));
        });
        if (ket.bo_qua) return ket;

        if (ket.ex === 'done') {
          throw new Error(`giong cua NGUOI KHAC da doc THANH CONG: ${JSON.stringify(ket)}`);
        }
        if ((await soAm(p)) > amTruoc) throw new Error('co them mot khoi am thanh cho mot giong khong duoc phep');
        // ⛔ Tien PHAI ve. Mot job khong bao gio chay duoc ma van giu tien la
        //    mot lan mat tien am tham — khach khong thay bao gia nao ca.
        const c = ket.credit || {};
        if ((c.thu ?? 0) !== 0) throw new Error(`da THU ${c.thu} credit cho mot giong bi tu choi`);
        if ((c.giu ?? 0) > 0 && (c.hoan ?? 0) !== c.giu) {
          throw new Error(`giu ${c.giu} ma chi hoan ${c.hoan}: ${JSON.stringify(ket)}`);
        }
        await cho(2500);
        const sau = await soDu(p);
        if (truoc !== null && sau !== null && sau < truoc) {
          throw new Error(`so du GIAM sau mot lan bi tu choi: ${truoc} -> ${sau}`);
        }
        return { nhan_luc_nop: r.status, ket_cuc: ket.ex, credit: c,
                 ra_tieng: false, loi: ket.loi };
      },
    },
    {
      dot: 6,
      ten: '6.4-Doc-to-dien-DUNG-bai-do-va-KHONG-tu-tieu-tien',
      hoi: '"Đọc to" có lấy đúng chữ của lượt đó, và có chờ xác nhận giá không?',
      async chay(p) {
        // 🔴 PHIEN BAN DAU DOI MOT YEU CAU DI RA NGAY SAU CU BAM, va bao HONG
        //    khi khong thay. Nhung san pham CO Y khong lam the — chu thich nam
        //    ngay canh nut, o `ThongDiepView.tsx`:
        //
        //      "Van phai qua o xac nhan gia."
        //
        //    `onDocTo` chi goi `datChuDocTo(chu)`: no DIEN san o soan tieng.
        //
        // ⛔ Doi mot cu bam tu tieu tien la doi sai HUONG cua mot quy tac an
        //    toan. Neu ta "sua" cho phep kiem xanh, ta vua bo mat o xac nhan
        //    gia — mot cu bam nham thanh mot lan mat tien khong hoi.
        //
        // ⭐ Nen do hai menh de ma san pham THAT SU giu, va ca hai deu dang gia:
        //      1. chu duoc dien la chu cua DUNG bai do (khong doc nham bai);
        //      2. tien KHONG nhuc nhich khi chua bam "Dong y, tao".
        //    Va do duoc ca hai ma khong ton mot credit nao.
        if (!(await p.getByRole('button', { name: 'Đọc to' }).count())) {
          return { bo_qua: 'khong co nut Doc to — may chu noi speech.ltt='
            + `${await nangLuc(p, 'speech.ltt')}` };
        }
        // ⛔ LAT TRUOC "DAT" VOI `manh_doi_chieu: \"\"` — tuc nua menh de
        //    "dung bai" DA BI BO QUA IM LANG. Bai cuoi luc ay la khoi am thanh
        //    cua `6.1`, khong co chu nao, nen `manh` rong va phep kiem tu tat
        //    minh di. Mot lat xanh khong chung minh gi thi te hon mot lat do:
        //    no dong ho so lai.
        //
        // ⭐ Nen TU TAO lay du lieu thay vi nhat lay thu dang co: mot luot chu
        //    voi mot chuoi dac trung minh biet truoc. Va neu van khong co chu
        //    de doi chieu thi BAO HONG, khong lang le di qua.
        await hoiThoaiMoi(p);
        await guiChu(p, 'Chep lai dung mot dong nay, khong them gi: CANHCUT DOCTO 4471.');
        await xong(p);
        const nut = p.getByRole('button', { name: 'Đọc to' }).last();
        if (!(await nut.count())) throw new Error('bai vua tao khong co nut "Doc to"');
        const chuBai = (await chuBaiCuoi(p)).replace(/\s+/g, ' ');
        const truoc = await soDu(p);
        const batDuoc = [];
        const nghe = (req) => {
          const u = req.url();
          if (u.includes('bao-gia') || u.endsWith('/tao')) batDuoc.push(req.postData() || '');
        };
        p.on('request', nghe);
        try {
          await nut.click();
          await doiDen('o soan tieng duoc dien san', async () =>
            ((await oChu(p).inputValue().catch(() => '')) || '').trim().length > 0, 20);
          const daDien = (await oChu(p).inputValue()).replace(/\s+/g, ' ');

          // ⭐ Mot manh chu DAC TRUNG cua bai do. Doc nham bai khac la loi im
          //    lang: khach nghe mot doan hop ly, chi khong phai doan ho bam.
          // ⛔ DUNG BOC MANH CHU TU MAN HINH. Lat 04/09 boc phai `"Suy luan
          //    CANHCUT D"` — vi `innerText` cua bai GOM CA khoi suy luan, con
          //    prefill (dung dan) chi lay phan TRA LOI. Phep kiem bao HONG mot
          //    san pham dang lam dung.
          //
          // ⭐ Doi chieu bang **dau hieu chinh minh dat vao**, khong bang thu
          //    nhat duoc tu giao dien: nguon doi chieu phai doc lap voi thu
          //    dang do.
          const manh = 'CANHCUT DOCTO 4471';
          // ⛔ DAU HIEU NAY NAM TRONG CHINH CAU TOI GUI DI, nen "o soan co
          //    chua no" KHONG phan biet duoc hai truong hop:
          //      · dien cau TRA LOI cua model  (dung)
          //      · dien lai cau HOI cua nguoi dung (sai, va la mot loại sai
          //        that: doc to cau cua chinh minh, va tra tien theo giay)
          //
          // ⭐ Nen doi chieu them mot manh chi co o PHIA NGUOI DUNG. Cau lenh
          //    ("Chep lai dung mot dong nay") khong bao gio xuat hien trong mot
          //    cau tra loi dung, nen su vang mat cua no la bang chung phan biet.
          if (/Chep lai dung mot dong nay/i.test(daDien)) {
            throw new Error(`"Doc to" dien lai CAU HOI chu khong phai cau tra loi: `
              + daDien.slice(0, 200));
          }
          if (!chuBai.includes(manh)) {
            throw new Error(`model khong chep lai dau hieu (${manh}) — khong doi chieu duoc: `
              + JSON.stringify(chuBai.slice(0, 200)));
          }
          // ⛔ VA KHOI SUY LUAN KHONG DUOC DI THEO. Doc to phai doc CAU TRA
          //    LOI. Doc chuoi suy luan len thanh tieng vua sai y khach, vua
          //    phat ra ngoai phan noi bo cua model — va khach TRA TIEN cho no,
          //    vi tien tinh theo giay.
          if (/Suy luận/i.test(daDien)) {
            throw new Error(`o soan lan ca khoi suy luan: ${daDien.slice(0, 220)}`);
          }
          if (!daDien.includes(manh)) {
            throw new Error(`o soan khong chua chu cua bai nay (${JSON.stringify(manh)}): `
              + daDien.slice(0, 220));
          }
          if (batDuoc.length) {
            throw new Error(`cu bam "Doc to" da tu gui yeu cau — mat o xac nhan gia: `
              + batDuoc[0].slice(0, 200));
          }

          // Bao gia KHONG duoc tru tien, va no phai mang dung chu vua dien.
          const { gia } = await xemGia(p, daDien.slice(0, 300));
          await doiDen('bao gia da di ra', () => batDuoc.length > 0, 20);
          if (!batDuoc.join(' ').includes(manh)) {
            throw new Error(`than bao gia khong mang chu cua bai nay: ${batDuoc.join(' ').slice(0, 220)}`);
          }
          await p.getByRole('button', { name: 'Huỷ' }).click().catch(() => {});
          await cho(1500);
          const sau = await soDu(p);
          if (truoc !== null && sau !== null && sau !== truoc) {
            throw new Error(`chua bam tao ma so du da doi: ${truoc} -> ${sau}`);
          }
          return { manh_doi_chieu: manh, gia_bao: gia, cho_xac_nhan: true, so_du_khong_doi: true };
        } finally {
          p.off('request', nghe);
        }
      },
    },
  ];
}
