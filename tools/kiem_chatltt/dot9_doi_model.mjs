/**
 * Đợt 9 — ĐỔI MODEL GIỮA HỘI THOẠI.
 *
 * 🔴 VÌ SAO ĐỢT NÀY CẦN. Model đang chọn nằm ở **ba nơi**, và ba nơi đó phải
 *    luôn nói cùng một điều:
 *
 *      · trạng thái React (`alias`)          — thứ ô chọn đang hiện
 *      · thân yêu cầu (`model_alias`)        — thứ máy chủ thật sự dùng
 *      · `conversation.model_alias` trong DB — thứ sống sót qua F5
 *
 * ⛔ Lệch giữa ba nơi đó là một lỗi **im lặng**: giao diện hiện "vision", câu
 *    trả lời do model text sinh ra, và không có thông báo nào. Khách chỉ thấy
 *    model "kém đi" một cách khó hiểu — và họ trả tiền cho một model khác thứ
 *    họ chọn.
 *
 * ⭐ Nên đợt này không kiểm "đổi được không" (dễ), mà kiểm **ba nơi có khớp
 *    nhau không** (chỗ lỗi thật nấp).
 */

export function dot9({ cho, doiDen, soBai, guiChu, xong, hoiThoaiMoi, nangLuc }) {
  const oModel = (p) => p.getByRole('combobox', { name: 'Chọn model' });

  /** Danh sách alias, **sau khi danh mục đã nạp**.
   *
   * ⛔ Đọc ngay là đọc một ô chọn còn RỖNG. Đo 04/09: `9.1` báo *"chỉ có 0
   *    model"* trong khi `9.3` ngay sau đó thấy đủ hai — hai hạng mục cùng lượt
   *    nói ngược nhau, và cái sai là cái đọc sớm.
   *
   * ⭐ Đây là lần thứ sáu trong dự án cùng một gốc: đọc trước khi dữ liệu tới.
   *    Nên phép đọc này **tự đợi**, thay vì để mỗi hạng mục nhớ mà đợi.
   */
  const cacAlias = async (p) => doiDen('danh sach model da nap', async () => {
    const ds = await oModel(p).locator('option')
      .evaluateAll((o) => o.map((x) => x.value).filter(Boolean));
    return ds.length ? ds : null;
  }, 25).catch(() => []);

  /** `conversation.model_alias` theo MÁY CHỦ, không theo màn hình. */
  const aliasMayChu = (p) => p.evaluate(() => {
    const cid = location.hash.slice(1);
    if (!cid) return null;
    return fetch('/chatltt/api/hoi-thoai/' + cid).then((r) => r.json())
      .then((s) => s.conversation?.model_alias ?? null).catch(() => null);
  });

  return [
    {
      dot: 9,
      ten: '9.1-doi-model-thi-luot-SAU-dung-model-moi',
      hoi: 'Đổi model giữa chừng — lượt sau có thật sự dùng model mới không?',
      async chay(p) {
        if (!(await oModel(p).count())) return { bo_qua: 'khong co o chon model' };
        const cac = await cacAlias(p);
        if (cac.length < 2) {
          return { bo_qua: `chi co ${cac.length} model — khong doi duoc` };
        }
        await hoiThoaiMoi(p);
        await guiChu(p, 'Chao.');
        await xong(p);
        const dau = await oModel(p).inputValue();
        const moi = cac.find((x) => x !== dau);

        const batDuoc = [];
        const nghe = (req) => {
          if (req.url().includes('/api/hoi-thoai/') && req.url().endsWith('/luot')) {
            batDuoc.push(req.postData() || '');
          }
        };
        p.on('request', nghe);
        try {
          await oModel(p).selectOption(moi);
          // ⛔ XAC MINH LUA CHON DA BAM, DUNG CHO MOT `cho(600)` NGAU NHIEN.
          //
          //    `napSuThat` dat lai `alias` tu `conversation.model_alias` moi lan
          //    hoi thoai duoc nap (`App.tsx:178`). Neu no chay SAU cu chon cua
          //    nguoi dung, no ghi de len — va luot gui di mang model CU trong
          //    khi man hinh hien model MOI. Do dung la loai lech ba-noi ma dot
          //    nay sinh ra de bat.
          //
          // ⭐ Doi den khi gia tri ON DINH (hai lan doc lien tiep bang nhau) roi
          //    moi gui. Neu no khong bao gio bam, day la mot LOI THAT va hang
          //    muc phai noi ro dieu do — chu khong lang le gui roi bao "than sai".
          let onDinh = false;
          for (let i = 0; i < 12; i += 1) {
            await cho(700);
            const a = await oModel(p).inputValue();
            await cho(700);
            const b2 = await oModel(p).inputValue();
            if (a === moi && b2 === moi) { onDinh = true; break; }
          }
          if (!onDinh) {
            throw new Error(`chon ${moi} nhung o chon khong giu duoc gia tri do — `
              + `nghi \`napSuThat\` ghi de lua chon cua nguoi dung `
              + `(dang hien: ${await oModel(p).inputValue()})`);
          }
          await guiChu(p, 'Chao lan hai.');
          await doiDen('yeu cau luot da di ra', () => batDuoc.length > 0, 30);
          const than = batDuoc[batDuoc.length - 1];
          // ⛔ Doi DUNG khoa `model_alias` trong than, khong chi doi chuoi alias
          //    xuat hien dau do: mot alias co the trung voi mot manh chu khac
          //    trong than, va khi ay phep kiem xanh vi mot ly do sai.
          const j = JSON.parse(than);
          if (j.model_alias !== moi) {
            throw new Error(`than gui \`model_alias\`=${JSON.stringify(j.model_alias)}, `
              + `mong ${JSON.stringify(moi)}`);
          }
          await xong(p);
          return { tu: dau, sang: moi, than_dung_model_moi: true };
        } finally {
          p.off('request', nghe);
        }
      },
    },
    {
      dot: 9,
      ten: '9.2-model-da-chon-song-qua-F5-VA-khop-may-chu',
      hoi: 'F5 xong, ô chọn có hiện đúng model mà máy chủ đang giữ không?',
      async chay(p) {
        if (!(await oModel(p).count())) return { bo_qua: 'khong co o chon model' };
        const truoc = await oModel(p).inputValue();
        const mayTruoc = await aliasMayChu(p);
        if (!mayTruoc) return { bo_qua: 'chua o trong mot hoi thoai — chay 9.1 truoc' };

        await p.reload({ waitUntil: 'domcontentloaded' });
        await doiDen('hoi thoai hien lai', async () => (await soBai(p)) >= 2, 40);
        // ⛔ DOI O CHON NAP XONG. Doc ngay sau reload la doc gia tri MAC DINH
        //    truoc khi `napSuThat` kip dat lai alias cua hoi thoai — va bao cao
        //    se noi "F5 lam mat model" tren mot san pham hoan toan dung. Cung
        //    goc voi nam lan "doc truoc khi du lieu toi" da ghi o dot 2.
        await doiDen('o chon nap xong', async () =>
          (await oModel(p).inputValue()) === mayTruoc, 25);
        const sau = await oModel(p).inputValue();
        const maySau = await aliasMayChu(p);

        if (sau !== truoc) throw new Error(`F5 lam doi model: ${truoc} -> ${sau}`);
        // ⭐ Nua quan trong hon: man hinh phai khop MAY CHU, khong chi khop
        //    chinh no truoc do. Hai gia tri cung sai van "khong doi".
        if (sau !== maySau) {
          throw new Error(`man hinh (${sau}) khac may chu (${maySau})`);
        }
        return { truoc, sau, may_chu: maySau, khop: true };
      },
    },
    {
      dot: 9,
      ten: '9.3-doi-sang-model-KHONG-doc-anh-thi-noi-ra',
      hoi: 'Đang đính ảnh mà đổi sang model text — giao diện có nói không?',
      async chay(p) {
        // 🔴 Day la cho mat du lieu IM LANG neu lam sai: khach dinh ba anh, doi
        //    model, roi bam Gui — va anh bien mat khong mot loi nao. `dot4` da
        //    chot rang anh BI GO; hang muc nay chot rang viec go do duoc NOI RA.
        const tt = await nangLuc(p, 'text.chat');
        if (tt !== 'san_sang') return { bo_qua: `text.chat=${tt}` };
        if (!(await oModel(p).count())) return { bo_qua: 'khong co o chon model' };
        const cac = await cacAlias(p);
        const vision = cac.find((x) => x.includes('vision'));
        const chu = cac.find((x) => !x.includes('vision'));
        if (!vision || !chu) return { bo_qua: `khong du hai loai model: ${cac}` };

        await hoiThoaiMoi(p);
        await oModel(p).selectOption(vision);
        await cho(600);
        const oTep = p.locator('input[type=file]').first();
        if (!(await oTep.count())) return { bo_qua: 'model vision khong mo o dinh anh' };

        const { anhHopLe } = await import('./dot4_dinh_kem.mjs');
        await oTep.setInputFiles([anhHopLe(64, 64)]);
        await doiDen('chip anh hien ra', async () =>
          (await p.locator('.ltc-soan__anh-mot').count()) > 0, 30);

        await oModel(p).selectOption(chu);
        await cho(1200);
        const conChip = await p.locator('.ltc-soan__anh-mot').count();
        if (conChip) {
          throw new Error(`doi sang model khong doc anh ma van con ${conChip} anh dinh kem`);
        }
        // ⭐ Go anh la dung. Nhung go IM LANG thi khach khong biet minh vua mat
        //    gi — nen phai co mot cau noi ra, o dau do tren man hinh.
        const chuMan = await p.locator('.ltc-soan, .ltc-loi').allInnerTexts()
          .then((x) => x.join(' ')).catch(() => '');
        if (!/ảnh|anh/i.test(chuMan)) {
          throw new Error(`da go anh nhung KHONG noi gi: ${JSON.stringify(chuMan.slice(0, 160))}`);
        }
        return { tu: vision, sang: chu, da_go_anh: true, co_noi_ra: true };
      },
    },
  ];
}
