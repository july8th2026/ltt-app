/* asv/nen.js — VO cua man Studio. Nap DAU TIEN, moi module khac dua vao no.
 *
 * Pha 06 tach `asv.js` (1.154 dong) thanh tam module. Tep nay giu dung nhung
 * thu ma **nhieu hon mot** module can, va khong giu gi khac:
 *
 *   · `t()` — chuoi hien cho khach, do TEMPLATE cung cap
 *   · `chu()`, `phutGiay()`, `pt()` — ba tien ich DOM/dinh dang
 *   · `thoiLuongVideo` — do dai video, mot nguoi ghi (xem truoc) nhieu nguoi doc
 *   · hai cho noi: "da co video" va "doi preset"
 *
 * ⛔ KHONG dat logic nghiep vu o day, va KHONG dat gi chi mot module dung. Mot
 *    tep "dung chung" nhan moi thu roi vao chinh la cai giant form ma pha nay
 *    ton tai de go — chi doi ten.
 *
 * ⚠️ Toan bo cac module chay sau `defer` va theo THU TU trong the `<script>`.
 *    Chi mot rang buoc thu tu duy nhat: tep nay truoc het. Moi loi goi cheo
 *    module khac deu xay ra luc **su kien**, khong phai luc **nap**, nen thu tu
 *    cua bay tep con lai khong quan trong.
 */
window.ASV = (function () {
  "use strict";

  var form = document.getElementById("asv-form");

  /* Chuoi hien cho khach — do TEMPLATE cung cap, khong go o day.
   * Xem khoi `#asv-chu` trong `asv_trang_chinh.html` va ly do o do. */
  var CHU = {};
  try {
    var oChu = document.getElementById("asv-chu");
    if (oChu) CHU = JSON.parse(oChu.textContent) || {};
  } catch (e) { CHU = {}; }

  /* 🔴 `%%` -> `%`, va day la mot lo hong CO SAN tim ra khi kiem trinh duyet o
   *    pha 12b, khong phai mot nhu cau moi.
   *
   *    Cac chuoi o `#asv-chu` viet theo quy uoc printf cua Python, nen mot dau
   *    phan tram THAT phai go doi: `"Đang tải video lên… %(pct)s%%"`. Ham nay
   *    truoc day chi thay cho tham so va **khong go doi lai**, nen khach doc
   *    "tải lên… 50%%". Ban dau toi tuong do la loi cua chuoi minh vua them; do
   *    lai thi `tai_dang` cua V5 dinh y het.
   *
   * ⚠️ Go doi SAU khi thay tham so: mot gia tri thay vao co the chua `%`, va
   *    go truoc se an vao chinh no.
   *
   * ⭐ Va thay TOAN CUC: `String.replace` voi mot chuoi chi doi **lan dau**, nen
   *    mot chuoi dung `%(x)s` hai lan se lang le giu nguyen lan thu hai.
   */
  function t(khoa, thay) {
    var s = CHU[khoa] || "";
    if (thay) {
      Object.keys(thay).forEach(function (k) {
        s = s.split("%(" + k + ")s").join(thay[k]);
      });
    }
    return s.split("%%").join("%");
  }

  function chu(el, s) { if (el) el.textContent = s; }

  function phutGiay(giay) {
    var g = Math.max(0, Math.round(giay));
    var p = Math.floor(g / 60);
    return p > 0 ? p + " " + t("phut") + " " + (g % 60) + " " + t("giay")
                 : g + " " + t("giay");
  }

  function pt(x) { return Math.round(x * 100); }

  /* ── Hai cho noi ──────────────────────────────────────────────────────────
   *
   * 🔑 Truoc pha 06, thu tu giua hai viec nay duoc giu bang mot CHU THICH:
   *
   *      // ⚠️ `batCat` TRUOC `veLai`: no dat `thoiLuongVideo`, va danh sach
   *      //    vung doc bien do de dat `max` cho hai o gio.
   *      batCat(giay);
   *      veLai();
   *
   *    Mot chu thich giu duoc thu tu chung nao ca hai dong con nam canh nhau
   *    trong mot tep. Tach ra tam tep thi no khong giu duoc gi nua.
   *
   * ⭐ Nen luat doi cho: `phatCoVideo` dat `thoiLuongVideo` **truoc khi goi bat
   *    ky nguoi dang ky nao**. Sau doi nay thu tu dang ky khong con y nghia —
   *    tuc rang buoc bien mat thay vi duoc chep sang mot chu thich moi. Do la
   *    ranh gioi CO HOC thang giao uoc, cung luat ma phan con lai cua kho dung.
   */
  var dsCoVideo = [];
  var dsDoiPreset = [];

  /* ⛔ KHONG nuot loi cua nguoi dang ky. Mot module hong khong duoc lam sau
   *    module kia khong chay — nhung no cung khong duoc bien mat. Nem LAI o
   *    mot luot khac cua vong lap su kien: cac module con lai van chay, va loi
   *    van toi `window.onerror` nguyen ven. */
  function goiHet(ds, doiSo) {
    ds.forEach(function (fn) {
      try {
        fn(doiSo);
      } catch (e) {
        setTimeout(function () { throw e; }, 0);
      }
    });
  }

  var api = {
    /* `false` khi trang hien tai khong phai man Studio. Moi module hoi dong nay
       truoc, va thoat im lang — dung nhu `asv.js` cu lam voi `if (!form)`. */
    co: !!form,
    form: form,

    t: t,
    chu: chu,
    phutGiay: phutGiay,
    pt: pt,

    /* Do dai video, doc mot lan o `loadedmetadata`. Dung CHUNG: phan CAT doi
       giay -> phan so, con danh sach VUNG dat tran cho hai o gio. */
    thoiLuongVideo: 0,

    khiCoVideo: function (fn) { dsCoVideo.push(fn); },
    phatCoVideo: function (giay) {
      api.thoiLuongVideo = giay;
      goiHet(dsCoVideo, giay);
    },

    khiDoiPreset: function (fn) { dsDoiPreset.push(fn); },

    /* ⭐ Bon module tung chep NGUYEN ba dong nay. Mot ban duy nhat o day, va
     *    module chi con hoi mot cau: *"nhom cua toi co song o preset dang chon
     *    khong"*.
     *
     * ⛔ Tra `false` khi khong co nhom hay khong co preset nao duoc chon — tuc
     *    doan ve phia TAT. Mot cong cu bat nham o preset khong ho tro la mot
     *    **false feature**: khach ve xong, thay trong "Cai dat da dung", roi
     *    nhan mot video khong doi gi. */
    hopPreset: function (nhom) {
      if (!nhom || !form) return false;
      var can = nhom.getAttribute("data-preset-can") || "";
      var chon = form.querySelector('input[name="preset"]:checked');
      return !!chon && chon.value === can;
    }
  };

  if (form) {
    Array.prototype.forEach.call(
      form.querySelectorAll('input[name="preset"]'), function (o) {
        o.addEventListener("change", function () { goiHet(dsDoiPreset); });
      });
  }

  return api;
})();
