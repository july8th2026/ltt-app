/* Nút "sao chép" cho mọi khối mã trên trang tài liệu.
 *
 * 🔴 VÌ SAO CẦN. Trang hướng dẫn tồn tại để khách **chép cấu hình**. Trước
 *    25/08 họ phải tự tô bằng chuột một khối `pre` nhiều dòng — và tô hụt một
 *    dòng trong `config.toml` thì lỗi hiện ra ở tận lúc gọi API, dưới dạng một
 *    thông điệp không liên quan gì tới việc chép thiếu.
 *
 * ⭐ Tăng cường dần (progressive enhancement): không có JS thì không có nút, và
 *    trang vẫn đọc được y nguyên. Không phụ thuộc thư viện nào.
 *
 * ⚠️ `navigator.clipboard` chỉ tồn tại trên ngữ cảnh bảo mật (https hoặc
 *    localhost). Trang này luôn https, nhưng vẫn phải kiểm — thiếu bước đó thì
 *    trên một ngữ cảnh lạ nút sẽ ném lỗi và **không nói gì**, đúng kiểu hỏng
 *    im lặng mà dự án này đã trả giá nhiều lần.
 */
(function () {
  "use strict";

  function gan(pre) {
    if (!pre || pre.dataset.chep === "1") return;
    pre.dataset.chep = "1";

    var boc = document.createElement("div");
    boc.className = "khoi-ma";
    pre.parentNode.insertBefore(boc, pre);
    boc.appendChild(pre);

    var nut = document.createElement("button");
    nut.type = "button";
    nut.className = "nut-chep";
    nut.textContent = "Sao chép";
    // Người dùng bàn phím và trình đọc màn hình cũng phải dùng được.
    nut.setAttribute("aria-label", "Sao chép khối mã");
    boc.appendChild(nut);

    nut.addEventListener("click", function () {
      var chu = pre.innerText;
      var xong = function () {
        nut.textContent = "Đã chép";
        nut.classList.add("xong");
        setTimeout(function () {
          nut.textContent = "Sao chép";
          nut.classList.remove("xong");
        }, 1600);
      };
      var hong = function () {
        // Nói thật là không chép được, thay vì im lặng như chưa bấm.
        nut.textContent = "Hãy tự chọn rồi Ctrl+C";
        setTimeout(function () { nut.textContent = "Sao chép"; }, 2600);
      };
      if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(chu).then(xong, hong);
      } else {
        hong();
      }
    });
  }

  function chay() {
    var ds = document.querySelectorAll("main pre");
    for (var i = 0; i < ds.length; i++) gan(ds[i]);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", chay);
  } else {
    chay();
  }
})();
