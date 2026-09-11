/* asv/tai_len.js — TAI LEN BEN VUNG: trinh duyet -> kho, khong qua may chu.
 *
 * 🔑 Day la thu go bo tran 90 MB. Tran do ton tai vi Cloudflare cat o 100 MB
 *    **tren duong vao may chu** — mot duong ma tep khong con di khi ta PUT
 *    thang len kho.
 *
 * Ba buoc: xin ve (`/ve`) -> PUT tep -> nop form kem `upload_id`.
 *
 * ⛔ **Phai TAT o chon tep truoc khi nop.** `routes.tao` uu tien `upload_id`
 *    va tra ve truoc khi cham toi `video` — nhung trinh duyet thi **da gui
 *    ca than multipart roi**. Tuc tep se di len HAI LAN, va lan thu hai dam
 *    thang vao dung cai tran ta vua tranh. `disabled` chu khong `value=""`:
 *    o nay co `required`, va mot o rong nhung con `required` chan ca form.
 *
 * ⚠️ Hong o BAT KY buoc nao deu lui ve duong multipart, khong bao loi cho
 *    khach. Duong multipart van chay (duoi 90 MB), nen mot lan xin ve that
 *    bai khong duoc bien thanh mot lan chay khong xay ra.
 *
 * ⚠️ Module nay nap CUOI, nhung `asv/xem_truoc.js` van goi duoc
 *    `ASV.benVungKieuDuocKhong` — loi goi do xay ra luc khach CHON TEP, tuc
 *    sau khi ca tam module da nap xong.
 */
(function () {
  "use strict";
  if (!window.ASV || !ASV.co) return;

  var form = ASV.form;
  var t = ASV.t;
  var chu = ASV.chu;

  var oTep = document.getElementById("asv-video");
  var nutBatDau = document.getElementById("asv-batdau");
  var oVe = document.getElementById("asv-ve");
  var oUploadId = document.getElementById("asv-upload-id");
  var khoiTai = document.getElementById("asv-tai");
  var thanhTai = document.getElementById("asv-tai-thanh");
  var ttTai = document.getElementById("asv-tai-tt");

  function datTienDo(pct) {
    if (!khoiTai) return;
    khoiTai.hidden = false;
    var i = thanhTai && thanhTai.querySelector("i");
    if (i) i.style.width = pct + "%";
    if (thanhTai) thanhTai.setAttribute("aria-valuenow", String(pct));
    chu(ttTai, t("tai_dang", {pct: pct}));
  }

  /* ⚠️ Duong ben vung nhan IT kieu hon o chon tep (`KIEU_VIDEO_HOP_LE` khong co
     `x-matroska`/`webm`). Kieu ngoai danh sach -> lui ve multipart NGAY, dung
     xin mot cai ve chac chan bi tu choi.

     ⭐ Tach RIENG phep kiem kieu vi `moTep` can dung mot minh no: no phai biet
        tep se di duong nao **truoc** khi do kich thuoc, de chon dung cai tran.
        Gop hai phep kiem lam mot chinh la ly do dong ay tung do voi tran sai.

     ⭐ Dat len `ASV` vi `asv/xem_truoc.js` la nguoi goi duy nhat o ngoai — day
        la be mat cong khai DUY NHAT ma module nay mo ra. */
  function benVungKieuDuocKhong(f) {
    if (!oVe || !f) return false;
    var duoc = (oVe.getAttribute("data-kieu-ben-vung") || "").split(",");
    return duoc.indexOf(f.type) >= 0;
  }
  ASV.benVungKieuDuocKhong = benVungKieuDuocKhong;

  function benVungDuocKhong(f) {
    if (!benVungKieuDuocKhong(f)) return false;
    var tran = parseInt(oVe.getAttribute("data-tran-ben-vung") || "0", 10);
    return !(tran > 0 && f.size > tran * 1024 * 1024);
  }

  function xinVe(f) {
    var d = new FormData();
    d.append("csrf_token", form.querySelector('[name="csrf_token"]').value);
    d.append("ten_tep", f.name);
    d.append("kieu", f.type);
    d.append("co", String(f.size));
    return fetch(oVe.getAttribute("data-url"), {
      method: "POST", body: d, credentials: "same-origin"
    }).then(function (r) { return r.ok ? r.json() : null; });
  }

  function dayLen(ve, f) {
    // XHR chu khong `fetch`: chi XHR bao duoc tien do TAI LEN. Voi mot tep
    // hang tram MB, mot thanh tien do khong phai trang tri — khong co no thi
    // trang dung im vai phut va khach tuong may treo.
    return new Promise(function (ok, hong) {
      var x = new XMLHttpRequest();
      x.open(ve.method || "PUT", ve.url, true);
      Object.keys(ve.headers || {}).forEach(function (k) {
        x.setRequestHeader(k, ve.headers[k]);
      });
      x.upload.onprogress = function (e) {
        if (e.lengthComputable) {
          datTienDo(Math.round(e.loaded * 100 / e.total));
        }
      };
      x.onload = function () {
        (x.status >= 200 && x.status < 300) ? ok() : hong(x.status);
      };
      x.onerror = function () { hong(0); };
      x.send(f);
    });
  }

  var nutTaiLai = document.getElementById("asv-tai-lai");

  /* So lan THU LAI mot PUT hong. Ve presigned con han sau mot lan hong mang,
     nen thu lai chinh no la phep sua re nhat — khong phai xin ve moi.

     ⚠️ Ba lan tong cong, khong nhieu hon: mot loi CO HE THONG (sai chu ky, kho
        tu choi) se hong y het ca ba lan, va lam khach cho ba luot cho cung mot
        cau tra loi la dung cai gia ma `loi.py` tu choi tra o tang job. */
  var LAN_THU_TOI_DA = 3;
  var CHO_THU_LAI_MS = 1500;

  function dayLenCoThuLai(ve, f, lan) {
    lan = lan || 1;
    return dayLen(ve, f).catch(function (ma) {
      if (lan >= LAN_THU_TOI_DA) throw ma;
      chu(ttTai, t("tai_thu_lai", {lan: lan + 1}));
      return new Promise(function (ok) {
        setTimeout(ok, CHO_THU_LAI_MS * lan);
      }).then(function () { return dayLenCoThuLai(ve, f, lan + 1); });
    });
  }

  /* 🔴 **Duong lui phai HOI KICH THUOC truoc khi lui.**

     Truoc pha 08, moi that bai cua duong ben vung deu `form.submit()` — tuc
     day lai NGUYEN tep qua duong multipart. Voi mot tep 1,5 GB vua PUT hong o
     90%, duong lui ay:

       · day lai 1,5 GB qua Cloudflare (tran 100 MB)
       · bi cat, hoac bi may chu tu choi o `TRAN_TAI_LEN` = 90 MB
       · tra ve *"Video vuot qua 90 MB. Hay cat ngan hoac giam chat luong"*

     ⛔ Cau cuoi la mot loi khuyen SAI. Tep cua khach khong qua lon — tran that
        la 2 GiB — thu hong la duong tai len. Ta gui ho di sua nham thu, sau
        khi da bat ho cho hai lan.

     ⇒ Duong lui chi con hop le khi tep THUC SU di qua duong multipart duoc.
       Lon hon thi noi that va cho mot nut bam. */
  function luiVeMultipartDuocKhong(f) {
    var tran = parseInt(form.getAttribute("data-tran-mb") || "0", 10);
    return !(tran > 0 && f && f.size > tran * 1024 * 1024);
  }

  function taiThatBai(f) {
    dangTai = false;
    if (oUploadId) oUploadId.value = "";
    if (luiVeMultipartDuocKhong(f)) {
      /* Duoi tran multipart: duong cu van chay that, nen lui la dung. Van NOI
         ra — mot lan lui im lang la mot lan khach khong hieu vi sao cham. */
      chu(ttTai, t("tai_hong_nho"));
      form.submit();
      return;
    }
    var tran = parseInt(form.getAttribute("data-tran-mb") || "0", 10);
    chu(ttTai, t("tai_hong_lon", {mb: tran}));
    if (khoiTai) khoiTai.hidden = false;
    if (nutTaiLai) nutTaiLai.hidden = false;
    /* Mo khoa nut Bat dau: khach phai bam duoc "Thu tai len lai". */
    if (nutBatDau) {
      nutBatDau.disabled = false;
      nutBatDau.classList.remove("asv-dang-gui");
    }
  }

  var dangTai = false;

  if (nutTaiLai) {
    nutTaiLai.addEventListener("click", function () {
      nutTaiLai.hidden = true;
      /* `requestSubmit` chu khong `submit`: `submit()` **khong** phat su kien
         `submit`, nen no se bo qua chinh doan xu ly ben vung o duoi va day tep
         qua duong multipart — dung cai ta vua tu choi lam. */
      if (form.requestSubmit) form.requestSubmit();
      else form.dispatchEvent(new Event("submit", {cancelable: true}));
    });
  }

  form.addEventListener("submit", function (ev) {
    var f = oTep && oTep.files && oTep.files[0];

    // 🔴 Loi RE NHAT trong ban audit, va la loi DUY NHAT co the tao ra hai lan
    //    tru tien cho mot y dinh: nut khong disable, va trang dung im.
    function khoaNut() {
      if (!nutBatDau) return;
      nutBatDau.disabled = true;
      nutBatDau.classList.add("asv-dang-gui");
      chu(nutBatDau, t("dang_gui"));
    }

    // Da tai xong roi (lan nop thu hai sau khi PUT) -> di tiep binh thuong.
    if (dangTai || !f || (oUploadId && oUploadId.value)) {
      khoaNut();
      return;
    }
    if (!benVungDuocKhong(f)) {
      khoaNut();                 // lui ve multipart — duong cu, van chay
      return;
    }

    ev.preventDefault();
    dangTai = true;
    khoaNut();
    datTienDo(0);

    xinVe(f).then(function (ve) {
      // `{"mode":"local"}` = kho khong cap presigned duoc (LocalStorage tren
      // may phat trien va trong bo test). Khong phai loi — lui ve multipart.
      if (!ve || ve.mode !== "direct" || !ve.url) {
        throw new Error("khong-co-ve");
      }
      return dayLenCoThuLai(ve, f).then(function () {
        oUploadId.value = ve.upload_id;
        // ⛔ TAT o chon tep: xem ghi chu dai o dau tep nay.
        oTep.disabled = true;
        chu(ttTai, t("tai_xong"));
        form.submit();
      });
    }).catch(function () {
      // ⛔ KHONG lui vo dieu kien nua. `taiThatBai` hoi kich thuoc truoc: duoi
      //    tran multipart thi lui (va NOI ra), tren tran thi noi that va cho
      //    mot nut bam. Xem ghi chu dai o `luiVeMultipartDuocKhong`.
      taiThatBai(f);
    });
  });
})();
