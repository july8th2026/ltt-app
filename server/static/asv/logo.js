/* asv/logo.js — LOGO anh.
 *
 * 🔴 **Anh di CUNG bieu mau, khong qua mot cua tai len rieng.**
 *
 *    Mot cua rieng cap ra mot KHOA khach cam theo, roi lan chay sau nhac lai
 *    khoa do — tuc may chu phai tra loi *"khoa nay co that su cua nguoi dang
 *    goi khong"* o moi lan dung. Do dung la be mat IDOR ma
 *    `upload_sessions.owned(...)` phai loc ngay trong truy van de dong lai.
 *
 * ⇒ Moi logo co mot `<input type=file name=logo_anh>` RIENG, dung trong hang
 *   cua no. Chung di theo form, va may chu doi chieu SO LUONG voi mang hinh
 *   hoc — lech thi tu choi, khong zip mu.
 *
 * ⚠️ Thu tu cua cac `<input>` trong DOM la thu tu chung di trong multipart,
 *    va do la thu ta dua vao. Nen khi xoa mot hang, ta VE LAI ca danh sach
 *    thay vi go mot phan tu — ve lai thi hai mang khong the lech.
 */
(function () {
  "use strict";
  if (!window.ASV || !ASV.co) return;

  var t = ASV.t;
  var chu = ASV.chu;

  var nhomLg = document.getElementById("asv-nhom-logo");
  var dsLg = document.getElementById("asv-logo-ds");
  var oLg = document.getElementById("asv-logo");
  var ttLg = document.getElementById("asv-logo-tt");
  var chanLg = document.getElementById("asv-logo-chan");
  var nutLgThem = document.getElementById("asv-logo-them");
  var thanhLg = nhomLg ? nhomLg.querySelector(".asv-vung-thanh") : null;
  var dsLogo = [];
  var LG_TOI_DA = nhomLg
    ? (parseInt(nhomLg.getAttribute("data-toi-da"), 10) || 2) : 2;
  var LG_TRAN_MB = nhomLg
    ? (parseInt(nhomLg.getAttribute("data-tran-mb"), 10) || 8) : 8;
  var LG_KIEU = ["image/png", "image/jpeg", "image/webp"];

  function dongBoLogo() {
    /* ⛔ Chi gui nhung hang DA CO ANH. Mot hang chua chon anh la mot hang khach
     *    chua lam xong, va gui no se lam hai mang lech do dai — may chu tu choi
     *    ca lo. Bo qua thi phai NOI RA, va dong trang thai noi. */
    var gui = dsLogo.filter(function (l) { return !!l.tep; });
    if (oLg) {
      oLg.value = gui.length ? JSON.stringify(gui.map(function (l) {
        /* ⛔ KHONG gui `khoa`. May chu dat no sau khi `run.id` ton tai; bia
         *    mot chuoi gia o day roi de may chu ghi de la day client toi cho
         *    tao du lieu khong co that. */
        return {x: l.x, y: l.y, rong: l.rong, do_mo: l.do_mo};
      })) : "";
    }
    if (!dsLogo.length) { chu(ttLg, t("lg_chua_co")); return; }
    if (gui.length < dsLogo.length) { chu(ttLg, t("lg_chua_chon")); return; }
    chu(ttLg, t("lg_dem", {so: gui.length}));
  }

  function oLgSo(l, khoa, nhan, thap, cao) {
    var lb = document.createElement("label");
    lb.className = "asv-vung-gio";
    var s = document.createElement("span");
    s.textContent = nhan;
    var i = document.createElement("input");
    i.type = "number";
    i.className = "asv-cat-so";
    i.min = String(thap);
    i.max = String(cao);
    i.step = "1";
    i.value = String(Math.round(l[khoa] * 100));
    i.addEventListener("input", function () {
      var x = parseFloat(i.value);
      /* Khong kep ve bien — may chu la cho phat bieu duy nhat cua luat do. */
      if (isFinite(x)) { l[khoa] = x / 100; dongBoLogo(); }
    });
    lb.appendChild(s);
    lb.appendChild(i);
    return lb;
  }

  function veDanhSachLogo() {
    if (!dsLg) return;
    while (dsLg.firstChild) dsLg.removeChild(dsLg.firstChild);
    dsLogo.forEach(function (l, i) {
      var li = document.createElement("li");
      li.className = "asv-vung-muc";

      var lbTep = document.createElement("label");
      lbTep.className = "asv-lp-chu";
      var sTep = document.createElement("span");
      sTep.textContent = t("lg_chon_anh");
      var iTep = document.createElement("input");
      iTep.type = "file";
      iTep.name = "logo_anh";
      iTep.accept = LG_KIEU.join(",");
      iTep.addEventListener("change", function () {
        var f = iTep.files && iTep.files[0];
        if (!f) { l.tep = null; dongBoLogo(); return; }
        if (LG_KIEU.indexOf(f.type) < 0) {
          iTep.value = ""; l.tep = null;
          chu(ttLg, t("lg_sai_kieu"));
          return;
        }
        if (f.size > LG_TRAN_MB * 1024 * 1024) {
          iTep.value = ""; l.tep = null;
          chu(ttLg, t("lg_qua_lon", {mb: LG_TRAN_MB}));
          return;
        }
        l.tep = f.name;
        dongBoLogo();
      });
      lbTep.appendChild(sTep);
      lbTep.appendChild(iTep);

      var so = document.createElement("div");
      so.className = "asv-vung-gio-o asv-lp-o";
      so.appendChild(oLgSo(l, "x", t("lp_ngang"), 0, 100));
      so.appendChild(oLgSo(l, "y", t("lp_doc"), 0, 100));
      so.appendChild(oLgSo(l, "rong", t("lg_rong"), 3, 40));

      var xoa = document.createElement("button");
      xoa.type = "button";
      xoa.className = "btn ghost";
      xoa.textContent = t("lg_xoa_mot");
      xoa.addEventListener("click", function () {
        /* ⚠️ Ve lai CA danh sach, khong go mot phan tu: thu tu cac `<input
         *    type=file>` trong DOM la thu tu chung di trong multipart, va ve
         *    lai la cach duy nhat chac chan hai mang khong lech. Cai gia la
         *    khach phai chon lai anh cua nhung hang con lai — noi ra bang dong
         *    trang thai, chu khong de ho tu phat hien. */
        dsLogo.splice(i, 1);
        dsLogo.forEach(function (m) { m.tep = null; });
        veDanhSachLogo();
        dongBoLogo();
      });

      li.appendChild(lbTep);
      li.appendChild(so);
      li.appendChild(xoa);
      dsLg.appendChild(li);
    });
  }

  if (nutLgThem) {
    nutLgThem.addEventListener("click", function () {
      if (dsLogo.length >= LG_TOI_DA) {
        chu(ttLg, t("lg_het_cho", {n: LG_TOI_DA}));
        return;
      }
      dsLogo.push({x: 0.05, y: 0.05, rong: 0.15, do_mo: 1.0, tep: null});
      veDanhSachLogo();
      dongBoLogo();
    });
  }

  function capNhatLogoTheoPreset() {
    if (!nhomLg) return;
    var duoc = ASV.hopPreset(nhomLg);
    if (thanhLg) thanhLg.hidden = !duoc;
    if (dsLg) dsLg.hidden = !duoc;
    if (chanLg) chanLg.hidden = duoc;
    /* ⛔ Xoa han khi doi preset: giu lai mot `<input type=file>` da chon anh la
     *    van gui anh do len may chu theo form. An di khong phai la go. */
    if (!duoc && dsLogo.length) {
      dsLogo.length = 0;
      veDanhSachLogo();
    }
    if (!duoc && oLg) oLg.value = "";
    dongBoLogo();
  }

  ASV.khiDoiPreset(capNhatLogoTheoPreset);
  capNhatLogoTheoPreset();
})();
