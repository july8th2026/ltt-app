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

export function dot6({ cho, doiDen, soDu, hoiThoaiMoi, guiChu, xong, chuBaiCuoi }) {
  const nutGiong = (p) => p.getByRole('button', { name: 'Tạo giọng' });
  const oChu = (p) => p.getByLabel('Văn bản cần đọc');
  const chonGiong = (p) => p.getByRole('combobox', { name: 'Chọn giọng' });
  const soAm = (p) => p.locator('article audio').count();

  async function moPanelGiong(p) {
    if (!(await nutGiong(p).count())) {
      await hoiThoaiMoi(p);
      await guiChu(p, 'Chao.');
      await xong(p);
    }
    await doiDen('nut media san sang', async () =>
      (await nutGiong(p).count()) > 0 && !(await nutGiong(p).isDisabled()), 60);
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
        await moPanelGiong(p);
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
        await moPanelGiong(p);
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
      ten: '6.3-giong-cua-NGUOI-KHAC-bi-tu-choi',
      hoi: 'Gõ tay một voice_id không thuộc mình — máy chủ có nhận không?',
      // May chu PHAI tu choi; 4xx la ket qua dung.
      loi_mong_doi: [/40\d POST .*\/(tao|bao-gia)/, /Failed to load resource/],
      async chay(p) {
        // 🔴 Giong nhan ban la du lieu sinh trac. `tim_profile` kiem `public_id`
        //    VA chu so huu trong MOT truy van — vi tach lam hai buoc thi co mot
        //    khoang trong o giua ma mot ban va sau nay rat de quen buoc hai.
        //    Hang muc nay do chinh menh de do tu ngoai vao.
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
        if (r.status === 202 || r.status === 200) {
          throw new Error(`may chu NHAN mot voice_id khong thuoc nguoi goi: ${r.than}`);
        }
        if (r.status >= 500) throw new Error(`may chu 5xx thay vi tu choi sach: ${r.status}`);
        return r;
      },
    },
    {
      dot: 6,
      ten: '6.4-Doc-to-tra-loi-cua-chinh-luot-do',
      hoi: 'Nút "Đọc to" có đọc đúng câu trả lời của lượt nó nằm cạnh không?',
      async chay(p) {
        const nut = p.getByRole('button', { name: 'Đọc to' }).last();
        if (!(await nut.count())) return { bo_qua: 'khong co nut Doc to — nang luc tieng chua san sang' };

        // Chu cua bai CUOI, truoc khi bam.
        const chuBai = (await chuBaiCuoi(p)).replace(/\s+/g, ' ');
        const batDuoc = [];
        const nghe = (req) => {
          const u = req.url();
          if (u.includes('/api/bao-gia') || u.endsWith('/tao')) batDuoc.push(req.postData() || '');
        };
        p.on('request', nghe);
        try {
          await nut.click();
          await doiDen('yeu cau doc to da di ra', () => batDuoc.length > 0, 30);
          const than = batDuoc.join(' ');
          // ⭐ Lay mot manh chu DAC TRUNG cua bai do va doi thay no trong than
          //    yeu cau. Doc nham bai khac la mot loi im lang: khach nghe mot
          //    doan hop ly, chi khong phai doan ho bam.
          const manh = (chuBai.match(/[\p{L}\d ]{18,}/u) || [''])[0].trim().slice(0, 18);
          if (manh.length >= 10 && !than.includes(manh)) {
            throw new Error(`than yeu cau khong chua chu cua bai nay (${JSON.stringify(manh)}): `
              + than.slice(0, 220));
          }
          return { manh_doi_chieu: manh, so_yeu_cau: batDuoc.length };
        } finally {
          p.off('request', nghe);
        }
      },
    },
  ];
}
