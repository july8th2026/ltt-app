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
      return;
    }
    var ho = { che_do: oCheDo.value, xuat_srt: srt };
    /* ⛔ Chi gui `kieu` khi that su khac vao hinh: mot `.srt` khong mang kieu
     *    chu nao, va may chu bo truong do o `chuan_hoa`. Gui thua o day se lam
     *    hai lan chay giong het nhau co hai van tay khac nhau. */
    if (dangKhac() && oKieu && oKieu.value) ho.kieu = oKieu.value;
    /* ⛔ Cung luat voi `kieu`: mot `.srt` khong mang kieu chu nao, nen no cung
     *    khong mang tinh chinh nao. Va gui mot `{}` rong o moi lan chay se lam
     *    ho so cua nhung lan khong tinh chinh khac di ma khong vi ly do gi. */
    if (dangKhac()) {
      var tc = docTinhChinh();
      if (Object.keys(tc).length) ho.tinh_chinh = tc;
    }
    oPd.value = JSON.stringify(ho);
  }

  function veKieu() {
    if (boKieu) boKieu.hidden = oCheDo.value !== CAN_KIEU;
    /* ⭐ Bang tinh chinh theo `dangKhac()`, KHONG theo `CAN_KIEU`: mot ho so
     *    "kieu mac dinh" van dot vao hinh, nen no van tinh chinh duoc. Buoc
     *    bang nay vao o chon kieu se lam mot nua khach khong bao gio thay no. */
    if (boTC) boTC.hidden = !dangKhac();
  }

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

  traVeGoc();
  ASV.khiDoiPreset(capNhatPhuDeTheoPreset);
  capNhatPhuDeTheoPreset();
})();
