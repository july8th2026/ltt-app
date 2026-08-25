/* O chon be mat tren trang huong dan cam.
 *
 * 🔴 VI SAO CAN. Trang cam cu do ca nam be mat len nhau, va hai gia tri de sai
 *    nhat cua khu API — dia chi (/api vs /api/v1) va ten model (ltt_llm vs ban
 *    -compat cua Claude Desktop) — nam canh nhau tren cung mot man hinh. Chep
 *    nham thi Codex nhan 404, hoac nut gui cua Claude Desktop im lang khong lam
 *    gi ca. Chon mot be mat thi chi con MOT dia chi va MOT ten model tren trang.
 *
 * ⭐ Tang cuong dan. Khong co JS thi moi khu deu hien, moi khu co tieu de rieng
 *    (`.cam-khu-ten`), va trang van dung — chi la dai hon. Script nay AN bot,
 *    chu khong DUNG ra noi dung; nen no khong the lam trang trong.
 *
 * ⚠️ Nho lua chon vao localStorage: nguoi cam Codex thuong quay lai trang nay
 *    vai lan trong cung mot buoi, va bat ho chon lai moi lan la mot buoc thua
 *    lap lai. Hong localStorage (che do rieng tu, cookie bi chan) thi bo qua,
 *    khong lam trang chet.
 */
(function () {
  "use strict";

  var KHOA = "ltt.cam.be_mat";

  function nho(ma) {
    // Khong boc im lang cho co: localStorage nem that khi bi chan, va thu duy
    // nhat mat di la viec ghi nho. Trang van chay dung.
    try { window.localStorage.setItem(KHOA, ma); } catch (e) { /* khong nho duoc */ }
  }

  function daNho() {
    try { return window.localStorage.getItem(KHOA); } catch (e) { return null; }
  }

  function chay() {
    var boc = document.querySelector("[data-cam-chon]");
    if (!boc) return;

    var nut = [].slice.call(boc.querySelectorAll(".chon-o"));
    var khu = [].slice.call(document.querySelectorAll("[data-khu]"));
    if (!nut.length || !khu.length) return;

    // Chi bat che do "mot khu mot luc" KHI script chay duoc. Dat class len
    // <body> de CSS an cac khu — neu script chet truoc dong nay thi khong co
    // gi bi an, va do dung la hanh vi ta muon.
    document.body.classList.add("cam-co-js");

    function mo(ma) {
      var thay = false;
      khu.forEach(function (k) {
        var hop = k.getAttribute("data-khu") === ma;
        k.classList.toggle("hien", hop);
        if (hop) thay = true;
      });
      if (!thay) return false;
      nut.forEach(function (n) {
        var hop = n.getAttribute("data-ma") === ma;
        n.classList.toggle("dang-chon", hop);
        n.setAttribute("aria-selected", hop ? "true" : "false");
      });
      return true;
    }

    nut.forEach(function (n) {
      n.addEventListener("click", function () {
        var ma = n.getAttribute("data-ma");
        if (mo(ma)) nho(ma);
      });
    });

    // Thu tu uu tien: #neo tren URL (de gui duoc duong dan thang toi mot be
    // mat trong tin nhan ho tro) → lua chon da nho → be mat dau tien.
    var neo = (window.location.hash || "").replace(/^#khu-/, "");
    if (!(neo && mo(neo)) && !mo(daNho() || "")) {
      mo(nut[0].getAttribute("data-ma"));
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", chay);
  } else {
    chay();
  }
})();
