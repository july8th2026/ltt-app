/**
 * Đợt 3 — KẾT XUẤT MARKDOWN, và Đợt A — TRẠNG THÁI NGỮ CẢNH.
 *
 * 🔴 Đợt 3 đứng cao hơn vị trí "rủi ro" thông thường vì ngày 03/09 ta vừa tìm
 *    ra một lỗi thật ở đây (**xuống dòng đơn bị nuốt**) — và một vùng vừa cho
 *    ra một lỗi thì gần như luôn còn nữa. Cộng đồng dính đúng vùng này ở
 *    *Numbered Lists are cut off*, *Numbers Displayed as "a" Character*,
 *    *Copying in dark mode copies the dark style*.
 *
 * ⭐ Nhóm A ở cuối tệp này là **phép kiểm ĐI TRƯỚC tính năng**. Nó sẽ ĐỎ cho tới
 *    khi dòng trạng thái ngữ cảnh được xây (`14_KE_HOACH_KIEM_SAU.md` phần A).
 *    Đó là chủ ý: một chỉ tiêu viết trong tài liệu là một lời hứa, một chỉ tiêu
 *    làm gate đỏ là một ràng buộc.
 */

export function dot3({ cho, doiDen, chuBaiCuoi, dangChay, guiChu, xong, hoiThoaiMoi }) {
  return [
    {
      dot: 3,
      ten: '3.1-xuong-dong-don-la-mot-xuong-dong',
      hoi: 'Model trả về mỗi ý một dòng — có dính thành một đoạn không?',
      async chay(p) {
        await hoiThoaiMoi(p);
        await guiChu(p, 'Liet ke dung 4 loai qua, moi loai mot dong, '
          + 'khong danh so, khong gach dau dong, khong giai thich.');
        await xong(p);
        // ⛔ MENH DE LA "MOI Y MOT DONG", KHONG PHAI "co the <br>".
        //
        //    Ban dau chi dem `<br>`. Nhung model hoan toan co the tra ve mot
        //    DANH SACH (`<ul><li>`) — moi y van tren mot dong, dung yeu cau, va
        //    dung 0 the `<br>`. Phep kiem bao do tren mot ket xuat hoan hao.
        //
        // ⭐ Do thu nguoi dung THAY: so dong that su tach ra. `<br>` va `<li>`
        //    la hai cach dat duoc no; con `Đỏ Xanh Vàng` dinh lien thi khong.
        const r = await p.evaluate(() => {
          const a = [...document.querySelectorAll('article')].pop();
          const noi = a.querySelector('.ltc-tin__chu');
          const dong = (noi?.innerText || '').split(String.fromCharCode(10))
            .map((d) => d.trim()).filter(Boolean);
          return { dong: dong.length, br: noi?.querySelectorAll('br').length ?? 0,
                   li: noi?.querySelectorAll('li').length ?? 0,
                   mau: dong.slice(0, 5) };
        });
        if (r.dong < 3) {
          throw new Error(`chi ${r.dong} dong (br=${r.br}, li=${r.li}) — `
            + `xuong dong don dang bi nuot: ${JSON.stringify(r.mau)}`);
        }
        return r;
      },
    },
    {
      dot: 3,
      ten: '3.2-danh-sach-danh-so-o-390px',
      hoi: 'Danh sách đánh số có bị cắt ở bề rộng điện thoại không?',
      async chay(p) {
        await hoiThoaiMoi(p);
        await guiChu(p, 'Liet ke 5 buoc pha mot tach ca phe, danh so 1 den 5, '
          + 'moi buoc mot cau ngan.');
        await xong(p);
        await p.setViewportSize({ width: 390, height: 844 });
        await cho(900);
        const r = await p.evaluate(() => {
          const a = [...document.querySelectorAll('article')].pop();
          const ol = a.querySelector('ol');
          const li = ol ? [...ol.querySelectorAll('li')] : [];
          const vo = a.getBoundingClientRect();
          return {
            coOl: !!ol, soLi: li.length,
            // Mot `li` bi cat khi so thu tu nam NGOAI khung cha.
            traiNhoNhat: li.length ? Math.min(...li.map((x) => Math.round(x.getBoundingClientRect().left))) : null,
            voTrai: Math.round(vo.left),
            tranNgang: document.documentElement.scrollWidth - document.documentElement.clientWidth,
          };
        });
        await p.setViewportSize({ width: 1280, height: 900 });
        // Model khong tra ve danh sach danh so ⇒ menh de CHUA duoc kiem, khong
        // phai bi vi pham. Bao BO QUA kem ly do; bao HONG la vu khong san pham.
        if (!r.coOl) return { bo_qua: 'model khong tra ve danh sach danh so o luot nay' };
        if (r.tranNgang > 1) throw new Error(`390px: trang cuon ngang ${r.tranNgang}px`);
        if (r.traiNhoNhat !== null && r.traiNhoNhat < r.voTrai - 1) {
          throw new Error(`so thu tu bi cat: li.left=${r.traiNhoNhat} < vo.left=${r.voTrai}`);
        }
        return r;
      },
    },
    {
      dot: 3,
      ten: '3.3-bang-rong-cuon-trong-bang',
      hoi: 'Bảng rộng hơn màn hình — cuộn trong bảng hay cuộn cả trang?',
      async chay(p) {
        await hoiThoaiMoi(p);
        await guiChu(p, 'Tao mot bang markdown 6 cot: ten, mo ta dai, gia, ngay, '
          + 'ghi chu dai, trang thai. Dien 3 dong voi noi dung dai.');
        await xong(p);
        await p.setViewportSize({ width: 390, height: 844 });
        await cho(900);
        const r = await p.evaluate(() => {
          const a = [...document.querySelectorAll('article')].pop();
          const t = a.querySelector('table');
          if (!t) return { coBang: false };
          let el = t.parentElement, cuonDuoc = false;
          for (let i = 0; i < 4 && el; i += 1) {
            const ox = getComputedStyle(el).overflowX;
            if (ox === 'auto' || ox === 'scroll') { cuonDuoc = true; break; }
            el = el.parentElement;
          }
          return { coBang: true, cuonDuoc,
                   tranNgang: document.documentElement.scrollWidth - document.documentElement.clientWidth };
        });
        await p.setViewportSize({ width: 1280, height: 900 });
        if (!r.coBang) return { bo_qua: 'model khong tra ve bang o luot nay' };
        if (r.tranNgang > 1) throw new Error(`bang lam CA TRANG cuon ngang ${r.tranNgang}px`);
        if (!r.cuonDuoc) throw new Error('bang khong nam trong vung cuon ngang rieng nao');
        return r;
      },
    },
    {
      dot: 3,
      ten: '3.4-HTML-tho-van-bi-escape',
      hoi: 'Sau khi thêm remark-breaks, HTML thô có bị bật lại không?',
      async chay(p) {
        await hoiThoaiMoi(p);
        await guiChu(p, 'Viet lai chinh xac chuoi nay trong mot khoi ma, '
          + 'roi viet lai lan nua ngoai khoi ma: <img src=x onerror=alert(1)>');
        await xong(p);
        const r = await p.evaluate(() => {
          const a = [...document.querySelectorAll('article')].pop();
          const noi = a.querySelector('.ltc-tin__chu');
          return { anhLa: noi ? noi.querySelectorAll('img[src="x"]').length : 0,
                   coChu: (noi?.innerText || '').includes('onerror') };
        });
        if (r.anhLa > 0) throw new Error('HTML tho da duoc DUNG THANH THE — lo hong XSS');
        return { the_img_tao_ra: r.anhLa, hien_thanh_chu: r.coChu };
      },
    },
    {
      dot: 3,
      ten: '3.5-che-do-toi-doc-duoc',
      hoi: 'Ở chế độ tối, chữ có đủ tương phản để đọc không?',
      async chay(p) {
        await p.emulateMedia({ colorScheme: 'dark' });
        await cho(1200);
        const r = await p.evaluate(() => {
          const doi = (s) => {
            const m = s.match(/[\d.]+/g) || [];
            const [r2, g, b] = m.map(Number);
            const f = (c) => { const x = c / 255; return x <= 0.03928 ? x / 12.92 : ((x + 0.055) / 1.055) ** 2.4; };
            return 0.2126 * f(r2) + 0.7152 * f(g) + 0.0722 * f(b);
          };
          const a = [...document.querySelectorAll('article')].pop();
          const el = a?.querySelector('.ltc-tin__chu') || document.body;
          const cs = getComputedStyle(el);
          let nen = cs.backgroundColor, n = el;
          while (n && (nen === 'rgba(0, 0, 0, 0)' || nen === 'transparent')) {
            n = n.parentElement; if (!n) break; nen = getComputedStyle(n).backgroundColor;
          }
          const L1 = doi(cs.color), L2 = doi(nen || 'rgb(255,255,255)');
          const tp = (Math.max(L1, L2) + 0.05) / (Math.min(L1, L2) + 0.05);
          return { chu: cs.color, nen, tuong_phan: +tp.toFixed(2) };
        });
        await p.emulateMedia({ colorScheme: 'light' });
        // WCAG AA cho chu thuong: 4,5:1.
        if (r.tuong_phan < 4.5) {
          throw new Error(`tuong phan che do toi ${r.tuong_phan}:1 < 4,5:1 (WCAG AA) — ${r.chu} tren ${r.nen}`);
        }
        return r;
      },
    },

    // ── Đợt A — trạng thái ngữ cảnh (phép kiểm ĐI TRƯỚC tính năng) ──────────
    {
      dot: 'A',
      ten: 'A.1-khong-de-nguoi-dung-cho-trong-im-lang',
      hoi: 'Có khoảng nào dài hơn 1,5s mà màn hình không nói đang làm gì không?',
      async chay(p) {
        await hoiThoaiMoi(p);
        await guiChu(p, 'Giai thich ngan gon vi sao nuoc bien man.');
        const bd = Date.now();
        let imLangDaiNhat = 0, imLangTu = Date.now();
        for (let i = 0; i < 120; i += 1) {
          await cho(250);
          const noi = await p.evaluate(() => {
            const a = [...document.querySelectorAll('article')].pop();
            if (!a) return '';
            const tt = a.querySelector('.ltc-trangthai, [data-trangthai]');
            const chu = a.querySelector('.ltc-tin__chu');
            return ((tt?.innerText || '') + (chu?.innerText || '')).trim();
          });
          if (noi.length > 0) { imLangDaiNhat = Math.max(imLangDaiNhat, Date.now() - imLangTu); imLangTu = Date.now(); }
          if (!(await dangChay(p)) && i > 4) break;
        }
        const tong = ((Date.now() - bd) / 1000).toFixed(1);
        if (imLangDaiNhat > 1500) {
          throw new Error(`co ${(imLangDaiNhat / 1000).toFixed(1)}s khong mot chu nao noi dang lam gi `
            + '(can dong trang thai: Dang xep hang / Dang chuan bi / Dang suy nghi)');
        }
        return { im_lang_dai_nhat_ms: imLangDaiNhat, tong_giay: tong };
      },
    },
    {
      dot: 'A',
      ten: 'A.3-CLS-luc-TAI-TRANG',
      hoi: 'Trang có nhảy khi React mount không?',
      async chay(p) {
        // 🔴 HANG MUC NAY RA DOI TU MOT CHAN DOAN SAI CUA CHINH TOI.
        //
        //    A.2 do CLS 0,1642 va toi ket luan thu pham la khoi "Suy luan" moc
        //    ra o giay 3,7. Do tung cu nhay mot thi khac han:
        //
        //      v=0,0749  t+0ms  FOOTER.platform-footer  truoc=109  sau=819
        //
        //    Cu nhay lon nhat o **giay thu khong**, va la CHAN TRANG: truoc khi
        //    React mount thi `#chatltt-root` rong ⇒ cao 0 ⇒ chan trang nam cao;
        //    mount xong no bi day xuong 710px.
        //
        // ⛔ A.2 dung `buffered: true` nen no GOP ca hai hien tuong vao mot con
        //    so. Mot phep do gop hai thu lai thi khi no do, khong ai biet phai
        //    sua cai nao — va toi da sua nham mot lan roi.
        await p.goto(p.url().split('#')[0], { waitUntil: 'commit' });
        await p.evaluate(() => {
          window.__clsTai = 0; window.__maxTai = 0; window.__nguon = '';
          new PerformanceObserver((l) => {
            for (const e of l.getEntries()) if (!e.hadRecentInput) {
              window.__clsTai += e.value;
              if (e.value > window.__maxTai) {
                window.__maxTai = e.value;
                const n = (e.sources || [])[0]?.node;
                const el = n && (n.nodeType === 1 ? n : n.parentElement);
                window.__nguon = (el?.tagName || '?') + '.' + String(el?.className || '').slice(0, 40);
              }
            }
          }).observe({ type: 'layout-shift', buffered: true });
        }).catch(() => {});
        await doiDen('app da mount', async () =>
          (await p.getByLabel('Nội dung tin nhắn').count()) > 0, 30);
        await cho(2500);
        const r = await p.evaluate(() => ({
          cls: +(window.__clsTai || 0).toFixed(4),
          lon_nhat: +(window.__maxTai || 0).toFixed(4),
          nguon: window.__nguon || '',
        }));
        if (r.cls > 0.02) {
          throw new Error(`CLS luc tai trang ${r.cls} > 0,02 — cu nhay lon nhat `
            + `${r.lon_nhat} tu ${r.nguon}. Goc mount phai GIU CHO truoc khi React ve.`);
        }
        return r;
      },
    },
    {
      dot: 'A',
      ten: 'A.2-CLS-cua-mot-luot-stream',
      hoi: 'Một lượt trả lời làm bố cục nhảy bao nhiêu?',
      async chay(p) {
        await hoiThoaiMoi(p);
        await p.evaluate(() => {
          window.__cls = 0; window.__max = 0;
          new PerformanceObserver((l) => {
            for (const e of l.getEntries()) if (!e.hadRecentInput) {
              window.__cls += e.value; window.__max = Math.max(window.__max, e.value);
            }
            // ⛔ `buffered: false`. Voi `true`, PerformanceObserver phat lai
            //    ca nhung cu nhay tu LUC TAI TRANG — va hang muc nay ten la
            //    "CLS cua mot luot stream". Do 03/09: 0,0749 trong tong 0,0836
            //    den tu chan trang nhay luc mount, khong lien quan gi toi
            //    stream. Mot phep do gop hai hien tuong lai thi khi no do,
            //    khong ai biet phai sua cai nao.
          }).observe({ type: 'layout-shift', buffered: false });
        });
        await guiChu(p, 'Viet mot doan 4 cau ve mua xuan, kem mot danh sach 3 gach dau dong.');
        await xong(p);
        await cho(1200);
        const r = await p.evaluate(() => ({ cls: +window.__cls.toFixed(4), lon_nhat: +window.__max.toFixed(4) }));
        // ⭐ 0,02 chu khong 0,1. Chuan Google la nguong "kem" cho CA MOT TRANG;
        //    day chi la MOT luot tra loi trong mot trang da tai xong, nen no
        //    phai chat hon han. Do 03/09 truoc khi sua: 0,0791.
        if (r.cls > 0.02) {
          throw new Error(`CLS ${r.cls} > 0,02 (cu nhay lon nhat ${r.lon_nhat}) — `
            + 'khoi suy luan/trang thai dang moc ra giua chung thay vi chiem cho san');
        }
        return r;
      },
    },
  ];
}
