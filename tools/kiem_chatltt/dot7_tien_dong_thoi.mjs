/**
 * Đợt 7 — TIỀN VÀ ĐỒNG THỜI, NHÌN TỪ GIAO DIỆN.
 *
 * 🔴 `test_627` đã chốt sổ tiền ở **tầng dịch vụ**, và nó chốt đúng. Nhưng
 *    không phép kiểm nào ở đó chạm vào cái nút — mà chỗ khách mất tiền oan là
 *    cái nút, không phải hàm.
 *
 * ⛔ Ba đường mất tiền mà tầng dịch vụ **không thể** thấy:
 *
 *      · giao diện gửi **hai** yêu cầu cho một cú bấm (nhấp đúp, mạng chậm);
 *      · hai tab cùng mở một hội thoại, mỗi tab tưởng mình là duy nhất;
 *      · máy chủ từ chối vì hết tiền, mà giao diện treo một vòng xoay vĩnh viễn
 *        — khách không biết mình đã bị từ chối hay đang chờ.
 *
 * ⭐ Cả ba đều là "sổ đúng, người dùng vẫn thiệt". Nên đợt này đo bằng **số dư
 *    trên thanh app** và **số lượt trong hội thoại**, đúng hai thứ khách nhìn.
 *
 * ## Chi phí
 *
 * ~3 lượt chữ. Hạng mục hết-tiền **không** tiêu gì: nó chặn ngay ở cửa mạng
 * chứ không làm nghèo tài khoản thật đi để kiểm — làm nghèo thật thì hạng mục
 * chỉ chạy được đúng một lần.
 */

export function dot7({ cho, doiDen, soBai, soDu, hoiThoaiMoi, guiChu, xong, dangChay }) {
  const oSoan = (p) => p.getByLabel('Nội dung tin nhắn');
  const soLuotNguoi = (p) => p.getByRole('button', { name: 'Sửa và gửi lại' }).count();
  const bao = (p) => p.locator('.ltc-loi[role=alert]');

  return [
    {
      dot: 7,
      ten: '7.1-nhap-dup-nut-Gui-chi-ra-MOT-luot',
      hoi: 'Bấm Gửi hai lần thật nhanh — có thành hai lượt và trừ tiền hai lần không?',
      async chay(p) {
        await hoiThoaiMoi(p);
        await doiDen('o soan mo khoa', async () => !(await oSoan(p).isDisabled()), 60);
        await oSoan(p).fill('Dem tu mot den ba, moi so mot dong.');
        const nguoiTruoc = await soLuotNguoi(p);
        const duTruoc = await soDu(p);

        // ⛔ HAI CU BAM PHAI O CUNG MOT NHIP. Neu de Playwright bam hai lan roi
        //    rac, React kip vo hieu nut giua chung va ta do mot thu de hon han
        //    thu that. Cai ta muon do la hai `click` **truoc khi** vong render
        //    nao kip chay — dung canh tranh ma nguoi dung tao ra khi nhap dup.
        const soCu = await p.evaluate(() => {
          const n = [...document.querySelectorAll('button')]
            .find((b) => b.textContent.trim() === 'Gửi');
          if (!n) return 'khong thay nut Gui';
          n.click();
          n.click();
          return n.disabled;
        });
        if (typeof soCu === 'string') throw new Error(soCu);

        await doiDen('luot da bat dau', async () => (await soLuotNguoi(p)) > nguoiTruoc, 40);
        await xong(p);
        await cho(2500);

        const nguoiSau = await soLuotNguoi(p);
        const them = nguoiSau - nguoiTruoc;
        if (them !== 1) {
          throw new Error(`mot cu nhap dup tao ra ${them} luot nguoi dung (mong 1)`);
        }
        // ⭐ Va so du: hai lan giu tien cho mot cau hoi la mat tien that, du
        //    hoi thoai chi hien mot luot.
        const duSau = await soDu(p);
        const tru = duTruoc !== null && duSau !== null ? duTruoc - duSau : null;
        return { them_luot: them, nut_khoa_ngay: soCu, tru_credit: tru };
      },
    },
    {
      dot: 7,
      ten: '7.2-hai-tab-cung-mot-hoi-thoai',
      hoi: 'Hai tab cùng mở một hội thoại — lượt có lẫn vào nhau không?',
      async chay(p) {
        const cid = await p.evaluate(() => location.hash.slice(1));
        if (!cid) throw new Error('chua o trong mot hoi thoai — chay 7.1 truoc');

        const q = await p.context().newPage();
        try {
          await q.goto(p.url(), { waitUntil: 'domcontentloaded' });
          await doiDen('tab hai vao duoc hoi thoai', async () =>
            (await q.getByLabel('Nội dung tin nhắn').count()) > 0
            && (await q.evaluate(() => location.hash.slice(1))) === cid, 45);

          // Moi tab mot dau hieu rieng, de biet cau tra loi thuoc ve ai.
          await doiDen('tab hai mo khoa', async () =>
            !(await q.getByLabel('Nội dung tin nhắn').isDisabled()), 60);
          await guiChu(q, 'Chep lai dung dong nay: TABHAI 8829.');
          await xong(q);

          // ⛔ TAB MOT KHONG DUOC TU BIA. No khong gui gi ca, nen neu no hien
          //    them mot luot thi luot do den tu tab kia — dung thu ta muon
          //    thay. Nhung noi dung phai la cua TABHAI, khong phai mot ban sao
          //    mo ho hay mot luot rong.
          await p.reload({ waitUntil: 'domcontentloaded' });
          await doiDen('tab mot thay luot cua tab hai', async () => {
            const t = await p.locator('article').last().innerText().catch(() => '');
            return /TABHAI\s*8829/.test(t);
          }, 60);

          const trang = await p.evaluate(async () => {
            const c = location.hash.slice(1);
            const s = await fetch('/chatltt/api/hoi-thoai/' + c).then((r) => r.json());
            // ⛔ KHONG doc `m.text`. Do 04/09: DOM da hien TABHAI ma phep dem
            //    tren `m.text` van ra 0 — vi noi dung tin nhan nam trong KHOI
            //    (`blocks`), con `text` co the rong. Doc dung mot truong roi ket
            //    luan "khong co du lieu" la cach de nhat de vu khong san pham.
            //
            // ⭐ Soi ca ban ghi: phep dem khong nen phu thuoc vao hinh dang
            //    trong cua mot lop du lieu ma no khong so huu.
            // ⛔ VA DUNG DEM SO LAN XUAT HIEN TRONG CA BAN GHI: do 04/09 ra
            //    **11** — dau hieu nam trong cau hoi, trong cau tra loi chep
            //    lai, trong `text` LAN trong `blocks`, cong ban ghi do dang.
            //    Toi da chot nguong `<= 3` ma chua he do thang cua chinh no.
            //
            // ⭐ Menh de that khong dinh gi toi cach luu: **dung MOT tin nhan
            //    NGUOI DUNG mang dau hieu do**. Hai tab nhan doi luot thi con
            //    so nay thanh 2, du du lieu duoc bieu dien kieu gi.
            const chu = JSON.stringify(
              s.messages.filter((m) => m.role === 'user'));
            return {
              tong: s.messages.length,
              lan_TABHAI: (chu.match(/TABHAI\s*8829/g) || []).length,
            };
          });
          // Mot dau hieu xuat hien dung hai lan: cau hoi + cau tra loi chep lai.
          if (trang.lan_TABHAI !== 1) {
            throw new Error(`mong DUNG MOT tin nhan nguoi dung mang TABHAI, dem duoc `
              + `${trang.lan_TABHAI}: ${JSON.stringify(trang)}`);
          }
          return { tong_tin_nhan: trang.tong, lan_dau_hieu: trang.lan_TABHAI };
        } finally {
          await q.close().catch(() => {});
        }
      },
    },
    {
      dot: 7,
      ten: '7.3-het-credit-thi-noi-ro-va-KHONG-treo',
      hoi: 'Máy chủ từ chối vì hết tiền — giao diện có nói rõ và mở khoá lại không?',
      loi_mong_doi: [/402 POST .*\/luot/, /Failed to load resource/],
      async chay(p) {
        // ⭐ CHAN O CUA MANG, KHONG LAM NGHEO TAI KHOAN THAT.
        //
        //    Tai khoan kiem dang co ~970 credit; de tieu het no chi de kiem
        //    mot man hinh loi thi vua lau vua chi chay duoc DUNG MOT LAN — va
        //    lan sau khong ai nap lai duoc de chay tiep. Mot hang muc chi chay
        //    mot lan la mot hang muc se bi tat.
        //
        // ⛔ Va thu dang do o day KHONG phai so tien: sổ tiền da co `test_627`.
        //    Thu dang do la **giao dien lam gi khi bi tu choi** — no phai noi
        //    ra cau nguoi doc duoc, va phai mo khoa o soan lai. Mot vong xoay
        //    vinh vien la cach khach ngoi doi mot thu khong bao gio toi.
        await hoiThoaiMoi(p);
        await doiDen('o soan mo khoa', async () => !(await oSoan(p).isDisabled()), 60);

        await p.route('**/chatltt/api/hoi-thoai/*/luot', (route) =>
          route.fulfill({
            status: 402,
            contentType: 'application/json',
            // ⛔ MA PHAI LA MA THAT (`luot.py:315` tra `het_credit`, `_p_media.py`
            //    tra 402). Ban dau toi bia `khong_du_credit` — va vi `nhanLoi`
            //    roi ve `e.message` khi khong biet ma, hang muc SE XANH nho
            //    chinh cau tieng Viet ma toi vua gui vao. Mot phep kiem tu cung
            //    cap cau tra loi cho no.
            //
            // ⭐ Va `message` co Y la tieng Anh ky thuat: neu man hinh hien
            //    cau tieng Viet trong `MA_LOI`, thi anh xa cua san pham DA chay
            //    that. Nguon doi chieu doc lap voi thu dang do.
            body: JSON.stringify({ error: { code: 'het_credit',
              message: 'insufficient credit balance for execution' } }),
          }));
        try {
          await oSoan(p).fill('Cau hoi khi da het tien.');
          await p.getByRole('button', { name: 'Gửi', exact: true }).click();

          await doiDen('hien mot cau bao loi doc duoc', async () => {
            const t = (await bao(p).innerText().catch(() => '')).trim();
            return t.length > 0 ? t : null;
          }, 30);
          const chuLoi = (await bao(p).innerText()).trim();
          // `MA_LOI.het_credit` = "Khong du credit cho luot nay." (co dau).
          if (!/Không đủ credit/i.test(chuLoi)) {
            throw new Error(`khong hien cau da dich cua \`het_credit\`, nhan: ${JSON.stringify(chuLoi)}`);
          }
          if (/insufficient|http_\d+|undefined|\[object/i.test(chuLoi)) {
            throw new Error(`lot chu ky thuat cua may chu ra man hinh: ${JSON.stringify(chuLoi)}`);
          }
          // ⛔ VA PHAI HET TREO. Day moi la nua quan trong: mot thong bao dung
          //    ben canh mot o soan bi khoa vinh vien van la mot trang chet.
          await doiDen('khong con dang chay', async () => !(await dangChay(p)), 25);
          await doiDen('o soan dung duoc lai', async () => !(await oSoan(p).isDisabled()), 25);
          return { bao_loi: chuLoi.slice(0, 90), mo_khoa_lai: true };
        } finally {
          await p.unroute('**/chatltt/api/hoi-thoai/*/luot').catch(() => {});
        }
      },
    },
    {
      dot: 7,
      ten: '7.4-so-du-tu-cap-nhat-khong-can-F5',
      hoi: 'Tiêu tiền xong, số dư trên thanh app có tự đổi không?',
      async chay(p) {
        await hoiThoaiMoi(p);
        await doiDen('o soan mo khoa', async () => !(await oSoan(p).isDisabled()), 60);
        const truoc = await soDu(p);
        if (truoc === null) throw new Error('khong doc duoc so du tren thanh app');

        await guiChu(p, 'Ke ba mau sac, moi mau mot dong.');
        await xong(p);

        // ⛔ KHONG F5 O DAY. Ca menh de nam o cho do: neu phai tai lai trang
        //    thi con so tren thanh app la mot con so CU, va khach tin vao mot
        //    so du khong con dung nua. LibreChat co dung mot issue y het the.
        // ⛔ DUNG CHOT "SO DU PHAI GIAM". Lat 04/09 do duoc 921 -> **933**,
        //    va so tang do dung: mot khoan HOAN cua luot truoc vua ve (giu roi
        //    tra lai phan du). So tien o day khong don dieu theo thoi gian, vi
        //    giu/thu/hoan quyet toan khong dong bo voi luot dang chay.
        //
        // ⭐ Menh de that khong phai ve HUONG, ma ve DO TUOI: con so tren thanh
        //    app co bang con so may chu dang giu khong — **ma khong can F5**.
        //    Do la thu khach tin vao, va no do duoc chinh xac.
        let sau = truoc;
        await doiDen('so du tren thanh app tu doi', async () => {
          sau = await soDu(p);
          return sau !== null && sau !== truoc;
        }, 45);
        // Doi chieu voi chinh may chu, khong tai lai trang.
        const may = await p.evaluate(() =>
          fetch('/chatltt/api/so-du').then((r) => r.json()).then((d) => d.credit));
        await doiDen('thanh app bat kip may chu', async () => (await soDu(p)) === may, 30);
        const cuoi = await soDu(p);
        return { truoc, sau, may_chu: may, tren_thanh: cuoi, khong_F5: true };
      },
    },
  ];
}
