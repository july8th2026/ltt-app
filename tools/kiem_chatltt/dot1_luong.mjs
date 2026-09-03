/**
 * Đợt 1 — TOÀN VẸN LUỒNG. Rủi ro cao nhất trong bảy đợt.
 *
 * 🔴 VÌ SAO ĐỢT NÀY ĐỨNG ĐẦU. Trong 150+ issue `🐛 bug` của LibreChat, nhóm
 *    đông nhất và dai nhất là nhóm luồng: *Garbled Characters in Chinese
 *    Outputs*, *Failed to parse stream*, *JSON.parse: unexpected end of data*,
 *    *response flashes blank*, *The response stream has expired*.
 *
 * ⛔ Và ChatLTT phơi ra **nhiều hơn** họ ở đúng chỗ đau nhất. Tiếng Việt có dấu
 *    là UTF-8 ba byte; SSE cắt chunk theo BYTE, không theo ký tự. Một chunk cắt
 *    giữa "ế" thì hai nửa ghép lại phải ra "ế" — nếu tầng nào decode từng chunk
 *    riêng, ta được `U+FFFD`. Tiếng Anh gần như không bao giờ chạm vào lỗi này.
 *
 * ⭐ Mỗi hạng mục ở đây là một CÂU HỎI CÓ THỂ SAI, không phải một thao tác.
 */

export function dot1({ cho, doiDen, soBai, chuBaiCuoi, dangChay, guiChu, xong, hoiThoaiMoi }) {
  return [
    {
      dot: 1,
      ten: '1.1-tieng-viet-qua-luong-dai',
      hoi: 'Chữ có dấu đi qua hàng trăm chunk SSE có nguyên vẹn không?',
      async chay(p) {
        await hoiThoaiMoi(p);
        await guiChu(p, 'Viet mot doan van 12 cau ve am thuc Ha Noi. '
          + 'Dung nhieu tu co dau: pho, bun cha, che, banh cuon, ca phe trung, '
          + 'nem ran, xoi xeo, banh mi, mien luon, bun thang.');
        await xong(p);
        const chu = await chuBaiCuoi(p);
        if (/�/.test(chu)) {
          const i = chu.indexOf('�');
          throw new Error(`co U+FFFD o vi tri ${i}: ${JSON.stringify(chu.slice(Math.max(0, i - 40), i + 40))}`);
        }
        // Phai THAT SU co dau — mot cau tra loi khong dau cung "khong co FFFD".
        const soDau = (chu.match(/[àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ]/gi) || []).length;
        if (soDau < 40) throw new Error(`chi ${soDau} ky tu co dau — nghi ngo mat dau`);
        return { ky_tu: chu.length, ky_tu_co_dau: soDau };
      },
    },
    {
      dot: 1,
      ten: '1.2-emoji-va-ky-tu-ngoai-BMP',
      hoi: 'Emoji (4 byte, cặp surrogate) có bị cắt đôi giữa hai chunk không?',
      async chay(p) {
        await hoiThoaiMoi(p);
        await guiChu(p, 'Viet lai chinh xac day nay, khong them gi: '
          + '🎉 🇻🇳 👨‍👩‍👧‍👦 ✅ 数学 α β γ ∑ ∫ 𝕏');
        await xong(p);
        const chu = await chuBaiCuoi(p);
        if (/�/.test(chu)) throw new Error('co U+FFFD — surrogate bi cat');
        // Surrogate le la dau hieu chac chan cua mot cap bi xe doi.
        const le = [...chu].some((c) => {
          const m = c.codePointAt(0);
          return m >= 0xD800 && m <= 0xDFFF;
        });
        if (le) throw new Error('co surrogate LE — mot cap emoji da bi xe doi');
        return { co_emoji: /[\u{1F300}-\u{1FAFF}]/u.test(chu), ky_tu: chu.length };
      },
    },
    {
      dot: 1,
      ten: '1.3-suy-luan-khong-lan-vao-tra-loi',
      hoi: 'Nội dung suy luận có rò vào phần trả lời không?',
      async chay(p) {
        // ⛔ LibreChat dinh dung loi nay hai lan: *o4-mini thinking output mixed
        //    with response* va *Think tags still displayed, not properly
        //    rendered*. Ta co khoi suy luan rieng nen cung phoi ra y het.
        await hoiThoaiMoi(p);
        await guiChu(p, 'Mot cai ao gia 250 nghin, giam 20%. Con bao nhieu? '
          + 'Suy nghi ky roi tra loi.');
        await xong(p);
        const r = await p.evaluate(() => {
          const a = [...document.querySelectorAll('article')].pop();
          const suy = a.querySelector('.ltc-suyluan__chu');
          const noi = a.querySelector('.ltc-tin__chu');
          return { suyLuan: (suy?.innerText || '').slice(0, 4000),
                   traLoi: (noi?.innerText || '').slice(0, 4000) };
        });
        for (const the of ['<think>', '</think>', ':::thinking']) {
          if (r.traLoi.includes(the)) throw new Error(`the "${the}" lot vao phan tra loi`);
        }
        if (r.suyLuan && r.traLoi && r.suyLuan.length > 80
            && r.traLoi.includes(r.suyLuan.slice(0, 80))) {
          throw new Error('80 ky tu dau cua SUY LUAN xuat hien nguyen van trong TRA LOI');
        }
        return { suy_luan: r.suyLuan.length, tra_loi: r.traLoi.length };
      },
    },
    {
      dot: 1,
      ten: '1.4-dong-tab-giua-luong-tien-van-dung',
      hoi: 'Rời trang giữa lúc đang stream thì lượt có được quyết toán không?',
      async chay(p) {
        await hoiThoaiMoi(p);
        // Cau hoi DAI han, de con kip roi trang giua chung.
        await guiChu(p, 'Viet mot doan van 15 cau ve mua dong o mien Bac, '
          + 'moi cau tren mot dong rieng.');
        // ⛔ LUAT ② CUA CHINH KE HOACH NAY, VA TOI VUA VI PHAM NO.
        //
        //    `guiChu` da doi luot BAT DAU roi moi tra ve. Neu model tra loi
        //    nhanh, luot co the KET THUC truoc khi dong duoi day kip nhin —
        //    va `doiDen('luong da chay')` bao HONG mot san pham dang chay dung.
        //    Do la "khong quan sat duoc", khong phai "bi vi pham".
        //
        // ⭐ Nen phan biet hai kha nang: van dang chay (do tiep), hay da xong
        //    (bo qua, kem ly do). Dung de mot cai bien thanh cai kia.
        let kipNhin = false;
        try {
          await doiDen('luong da chay', () => dangChay(p), 30);
          kipNhin = true;
        } catch (e) {
          const xongRoi = await p.locator('article').last()
            .getByRole('button', { name: 'Tạo lại' }).count();
          if (xongRoi > 0) {
            return { bo_qua: 'luot ket thuc truoc khi kip roi trang — menh de nay '
              + 'chua kiem duoc o lan chay nay' };
          }
          throw e;
        }
        if (!kipNhin) return { bo_qua: 'khong quan sat duoc luong' };
        await cho(1500);
        const hash = await p.evaluate(() => location.hash);
        // Roi trang giua chung — dung nhu nguoi dung dong tab.
        await p.goto(p.url().split('#')[0].replace(/\/chatltt.*$/, '/chatltt'),
          { waitUntil: 'domcontentloaded' });
        await cho(6000);
        await p.goto(p.url().split('#')[0] + hash, { waitUntil: 'domcontentloaded' });
        await doiDen('hoi thoai hien lai', async () => (await soBai(p)) >= 2, 30);
        await doiDen('luot khong con treo o trang thai dang chay', async () => {
          const cuoi = p.locator('article').last();
          return (await cuoi.getByRole('button', { name: 'Tạo lại' }).count()) > 0;
        }, 60);
        const chu = (await chuBaiCuoi(p)).replace(/\s/g, '');
        if (chu.length < 30) throw new Error(`mat phan da sinh: chi con ${chu.length} ky tu`);
        return { con_lai_ky_tu: chu.length };
      },
    },
    {
      dot: 1,
      ten: '1.5-khoi-ma-rat-lon-khong-treo',
      hoi: 'Một khối mã lớn có làm trình duyệt treo hay vỡ bố cục không?',
      async chay(p) {
        await hoiThoaiMoi(p);
        await guiChu(p, 'Viet mot ham Python in ra bang cuu chuong, '
          + 'trong mot khoi ma markdown. Them chu thich cho tung dong.');
        await xong(p);
        const r = await p.evaluate(() => {
          const a = [...document.querySelectorAll('article')].pop();
          const pre = a.querySelector('pre, code');
          const doc = document.documentElement;
          return { coKhoiMa: !!pre,
                   tranNgang: doc.scrollWidth - doc.clientWidth,
                   maCuonDuoc: pre ? getComputedStyle(pre.closest('pre') || pre).overflowX : '' };
        });
        if (!r.coKhoiMa) throw new Error('khong ve ra khoi ma nao');
        if (r.tranNgang > 1) throw new Error(`khoi ma lam CA TRANG cuon ngang ${r.tranNgang}px`);
        return r;
      },
    },
    {
      dot: 1,
      ten: '1.6-markdown-chua-dong-the-giua-luong',
      hoi: 'Giữa luồng, một ``` chưa đóng có làm vỡ bố cục không?',
      async chay(p) {
        // ⭐ Day la trang thai TAM THOI ma moi cau tra loi co khoi ma deu di qua:
        //    co ``` mo, chua co ``` dong. Neu bo cuc vo o day thi no vo o MOI
        //    luot, chi la vo trong nua giay nen khong ai bao cao.
        await hoiThoaiMoi(p);
        await guiChu(p, 'Viet mot doan ma JavaScript dai khoang 25 dong trong khoi markdown.');
        await doiDen('luong da chay', () => dangChay(p), 30);
        let tranMax = 0;
        for (let i = 0; i < 24; i += 1) {
          await cho(500);
          const t = await p.evaluate(() =>
            document.documentElement.scrollWidth - document.documentElement.clientWidth);
          tranMax = Math.max(tranMax, t);
          if (!(await dangChay(p))) break;
        }
        if (tranMax > 1) throw new Error(`GIUA luong, trang cuon ngang toi ${tranMax}px`);
        return { tran_ngang_lon_nhat: tranMax };
      },
    },
    {
      dot: 1,
      ten: '1.7-hai-luot-lien-tiep-khong-lan-noi-dung',
      hoi: 'Gửi lượt thứ hai ngay sau lượt thứ nhất, nội dung có lẫn không?',
      async chay(p) {
        await hoiThoaiMoi(p);
        await guiChu(p, 'Tra loi dung mot tu: thu do cua Nhat Ban?');
        await xong(p);
        const mot = (await chuBaiCuoi(p)).toLowerCase();
        await guiChu(p, 'Tra loi dung mot tu: thu do cua Han Quoc?');
        await xong(p);
        const hai = (await chuBaiCuoi(p)).toLowerCase();
        if (!/tokyo|đông kinh/.test(mot)) throw new Error(`luot 1 sai: ${JSON.stringify(mot.slice(0, 120))}`);
        if (!/seoul|hán thành|hàn thành/.test(hai)) throw new Error(`luot 2 sai: ${JSON.stringify(hai.slice(0, 120))}`);
        if (hai.includes('tokyo')) throw new Error('luot 2 con dinh noi dung cua luot 1');
        return { luot1: 'tokyo', luot2: 'seoul', bai: await soBai(p) };
      },
    },
  ];
}
