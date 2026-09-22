/* asv/phu_de.js — PHU DE (V6 pha 14).
 *
 * 🔴 **Module DUY NHAT o day co HAI truc, va do la ca thiet ke.**
 *
 *      · khac vao hinh — doi DIEM ANH, nen BAT KHA o preset giu hinh
 *      · xuat tep .srt — khong cham diem anh, chay o CA HAI preset
 *
 *    Bon module kia (`vung`, `cat`, `lop_phu`, `logo`) an ca nhom khi preset
 *    khong hop. Lam vay o day se khoa mat lua chon phu de DUY NHAT con lai o
 *    preset giu hinh — va khoa **im lang**: khach khong thay o nao de hoi.
 *
 * ⇒ Nen `hopPreset` o day chi dieu khien o CHE DO. O `.srt` khong bao gio bi an.
 *
 * ⛔ Va doi preset thi phai ha GIA TRI ve `tat`, khong chi an o di. An ma giu
 *    gia tri la giu lai dung cai loi vua tranh: gia tri van di theo form len
 *    may chu. Cung luat ma bon module kia da viet ra.
 */
(function () {
  "use strict";
  if (!window.ASV || !ASV.co) return;

  var nhomPd = document.getElementById("asv-nhom-phu-de");
  var oCheDo = document.getElementById("asv-phu-de-che-do");
  var oKieu = document.getElementById("asv-phu-de-kieu");
  var boKieu = document.getElementById("asv-phu-de-kieu-o");
  var oSrt = document.getElementById("asv-phu-de-srt");
  var chanPd = document.getElementById("asv-phu-de-chan");
  var oPd = document.getElementById("asv-phu-de");
  var oChu = document.getElementById("asv-phu-de-chu");
  var boChu = document.getElementById("asv-phu-de-chu-o");
  if (!nhomPd || !oCheDo || !oPd) return;

  var CAN_KIEU = nhomPd.getAttribute("data-can-kieu") || "";
  var TAT = nhomPd.getAttribute("data-che-do-tat") || "tat";

  function dangKhac() {
    return oCheDo.value !== TAT;
  }


  /* ── Tinh chinh kieu chu (pha 16) ───────────────────────────────────────
   *
   * 🔑 **Chi gui nhung o khach THAT SU doi.** Moc so sanh la gia tri khoi diem
   *    cua PRESET dang chon, khong phai mac dinh cua mo hinh — hai thu do khac
   *    nhau (`tiktok_bold` khoi diem co 64, mo hinh mac dinh 48).
   *
   * ⛔ Gui het 18 truong o moi lan chay se lam ho so cua hai lan chay dung cung
   *    preset khac nhau ngay khi app kia doi mot mac dinh — tuc van tay doi
   *    trong khi cau hinh thi khong. Cung luat ma `cai_dat.KHOA_THUA` dat ra.
   */
  var boTC = document.getElementById("asv-phu-de-tinh-chinh");
  var nutTraLai = document.getElementById("asv-phu-de-tra-lai");
  var oTC = boTC ? boTC.querySelectorAll("[data-tc]") : [];
  var GOC = {};
  try {
    var the = document.getElementById("asv-phu-de-goc");
    if (the) GOC = JSON.parse(the.textContent || "{}");
  } catch (e) { GOC = {}; }

  function gocCuaKieu() {
    return (oKieu && GOC[oKieu.value]) || {};
  }

  function datO(o, gt) {
    if (o.type === "checkbox") o.checked = !!gt;
    else o.value = (gt === null || gt === undefined) ? "" : String(gt);
  }

  function docO(o) {
    if (o.type === "checkbox") return o.checked;
    if (o.value === "") return null;
    if (o.type === "number") {
      var s = parseFloat(o.value);
      return isNaN(s) ? null : s;
    }
    return o.value;
  }

  /* Dat moi o ve dung gia tri khoi diem cua preset dang chon. */
  function traVeGoc() {
    var g = gocCuaKieu();
    Array.prototype.forEach.call(oTC, function (o) {
      datO(o, g[o.getAttribute("data-tc")]);
    });
    dongBoPhuDe();
  }

  /* ⚠️ So sanh bang CHUOI: mot `<input type=color>` tra `#ffffff` cho gia tri
   *    khoi diem `#FFFFFF`, va mot `<input type=number>` tra so 48 cho `48`.
   *    So sanh thang `!==` se bao "da doi" cho ca hai — tuc gui thua o moi lan
   *    chay, dung dieu ca khoi nay ton tai de tranh. */
  function khac(a, b) {
    if (typeof a === "boolean" || typeof b === "boolean") return !!a !== !!b;
    if (a === null || a === undefined) return false;
    return String(a).toLowerCase() !== String(b).toLowerCase();
  }

  function docTinhChinh() {
    var g = gocCuaKieu();
    var ra = {};
    Array.prototype.forEach.call(oTC, function (o) {
      var ten = o.getAttribute("data-tc");
      var gt = docO(o);
      if (khac(gt, g[ten])) ra[ten] = gt;
    });
    return ra;
  }

  /* ⭐ Ho so di len may chu la JSON, va no VANG MAT khi khach khong dung gi.
   *    Mot chuoi `{"che_do":"tat"}` gui o moi lan chay se lam ho so cua nhung
   *    lan khong dung phu de khac di ma khong vi ly do gi — dung dieu
   *    `cai_dat.KHOA_THUA` ton tai de tranh. */
  function dongBoPhuDe() {
    var srt = !!(oSrt && oSrt.checked);
    if (!dangKhac() && !srt) {
      oPd.value = "";
      veGoiY();
      henXemTruoc();
      return;
    }
    var ho = { che_do: oCheDo.value, xuat_srt: srt };
    /* ⛔ `kieu`, `tinh_chinh`, `chu` CHI o "tu chon kieu" (asv-final): bon che
     *    do con lai da co dinh kieu + nguon chu, va may chu tu choi `chu` o do.
     *    Gui thua se lam hai lan chay giong het nhau co hai van tay khac nhau. */
    if (tuChon()) {
      if (oKieu && oKieu.value) ho.kieu = oKieu.value;
      var tc = docTinhChinh();
      if (Object.keys(tc).length) ho.tinh_chinh = tc;
      if (oChu && oChu.value && oChu.value !== "dich") ho.chu = oChu.value;
    }
    oPd.value = JSON.stringify(ho);
    veGoiY();
    henXemTruoc();
  }

  function tuChon() { return oCheDo.value === CAN_KIEU; }

  function veKieu() {
    /* ⭐ Kieu, nguon chu va tinh chinh la MOT nhom: che do "tu chon kieu".
     *    Bon che do con lai la nhung goi da chot — do chinh la cho chung khac
     *    nhau tren giao dien, khong chi o ten. */
    if (boKieu) boKieu.hidden = !tuChon();
    if (boChu) boChu.hidden = !tuChon();
    if (boTC) boTC.hidden = !tuChon();
  }

  /* Goi y danh dau dai phu de goc: chi khi "tu dong" va CHUA co dai nao. */
  var goiY = document.getElementById("asv-phu-de-goi-y");
  var oVung = document.getElementById("asv-vung");
  function coDaiGoc() {
    try {
      return JSON.parse((oVung && oVung.value) || "[]").some(function (v) {
        return v && v.loai === "danh_dau_phu_de";
      });
    } catch (e) { return false; }
  }
  function veGoiY() {
    if (goiY) goiY.hidden = !(boXem && oCheDo.value === TU_DONG && !coDaiGoc());
  }

  /* ── Xem truoc: MAY CHU dung khung, bang dung ho so + .ass + chuoi loc
   *    cua ban render (`phu_de.xem_truoc`). Khong ve phu de bang CSS. ── */
  var boXem = document.getElementById("asv-phu-de-xem");
  var nutXem = document.getElementById("asv-phu-de-xem-nut");
  var anhXem = document.getElementById("asv-phu-de-xem-anh");
  var loiXem = document.getElementById("asv-phu-de-xem-loi");
  var video = document.getElementById("asv-xem");
  var TU_DONG = boXem ? boXem.getAttribute("data-tu-dong") : "";
  var hen = null;

  function henXemTruoc() {
    if (!anhXem || anhXem.hidden) return;   /* chi tu lam moi khi dang xem */
    clearTimeout(hen);
    hen = setTimeout(xemTruoc, 400);
  }

  /* ⛔ Hai yeu cau chay song song (doi o -> hen gio, roi bam nut) VE KHONG
   *    THEO THU TU. Do tren trinh duyet that: khung cua che do TRUOC de len
   *    che do vua chon. Chi hien phan hoi cua yeu cau MOI NHAT. */
  var lanXem = 0;

  function xemTruoc() {
    if (!boXem || !video || video.readyState < 2) return;
    clearTimeout(hen);
    var lan = ++lanXem;
    var cv = document.createElement("canvas");
    cv.width = video.videoWidth; cv.height = video.videoHeight;
    cv.getContext("2d").drawImage(video, 0, 0, cv.width, cv.height);
    cv.toBlob(function (b) {
      if (!b) return;
      var fd = new FormData(), f = new FormData(ASV.form);
      fd.append("anh", b, "khung.png");
      fd.append("phu_de", oPd.value || "");
      fd.append("vung", (oVung && oVung.value) || "");
      ["preset", "ngon_ngu_nguon", "ngon_ngu_dich", "csrf_token"].forEach(function (k) {
        fd.append(k, f.get(k) || "");
      });
      fetch(boXem.getAttribute("data-duong"), {
        method: "POST", body: fd, credentials: "same-origin"
      }).then(function (r) {
        if (r.ok) return r.blob();
        return r.json().then(function (j) { throw new Error(j.detail || r.status); },
                             function () { throw new Error(String(r.status)); });
      }).then(function (png) {
        if (lan !== lanXem) return;
        var cu = anhXem.src;
        anhXem.onload = function () { if (cu) URL.revokeObjectURL(cu); };
        anhXem.src = URL.createObjectURL(png);
        anhXem.hidden = false;
        if (loiXem) loiXem.hidden = true;
      }).catch(function (e) {
        if (lan === lanXem && loiXem) { loiXem.textContent = String(e.message || e); loiXem.hidden = false; }
      });
    }, "image/png");
  }

  if (nutXem) nutXem.addEventListener("click", function () { veGoiY(); xemTruoc(); });
  if (video && nutXem) video.addEventListener("loadeddata", function () {
    nutXem.disabled = false;
  });
  if (video) video.addEventListener("seeked", henXemTruoc);

  /* ⛔ CHI o che do bi chan, khong phai ca nhom. Xem dau tep. */
  function capNhatPhuDeTheoPreset() {
    var duoc = ASV.hopPreset(nhomPd);
    oCheDo.hidden = !duoc;
    if (chanPd) chanPd.hidden = duoc;
    if (!duoc && dangKhac()) oCheDo.value = TAT;
    veKieu();
    dongBoPhuDe();
  }

  oCheDo.addEventListener("change", function () {
    veKieu();
    dongBoPhuDe();
  });
  if (oKieu) oKieu.addEventListener("change", function () {
    /* Doi kieu = doi diem KHOI DIEM. Giu lai so cu la giu mot bang so khong
     * con thuoc ve kieu nao — va moi o trong do se duoc gui di nhu mot tinh
     * chinh du khach khong doi y gi. */
    traVeGoc();
  });
  Array.prototype.forEach.call(oTC, function (o) {
    o.addEventListener("change", dongBoPhuDe);
  });
  if (nutTraLai) nutTraLai.addEventListener("click", traVeGoc);
  if (oSrt) oSrt.addEventListener("change", dongBoPhuDe);
  if (oChu) oChu.addEventListener("change", dongBoPhuDe);
  /* Vung che doi (ve/xoa dai phu de goc) -> goi y + xem truoc theo. `vung.js`
   * ghi o an bang `.value`, khong ban su kien, nen nghe o muc form. */
  ASV.form.addEventListener("click", function () { setTimeout(veGoiY, 0); });

  traVeGoc();
  ASV.khiDoiPreset(capNhatPhuDeTheoPreset);
  capNhatPhuDeTheoPreset();
})();
