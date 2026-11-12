// Small enhancements; the site works without JavaScript.
(function () {
  "use strict";

  // ---- email: assemble the address from data attributes so it isn't in the page source as text
  document.querySelectorAll(".js-email").forEach(function (a) {
    var addr = a.dataset.u + "@" + a.dataset.d;
    a.href = "mailto:" + addr;
    if (!a.hasAttribute("data-keep")) a.textContent = addr;
  });

  // ---- figure viewer: open figures in a dialog instead of navigating to the image file
  var box = document.getElementById("lightbox");
  if (box && typeof box.showModal === "function") {
    var img = box.querySelector("img");
    var cap = box.querySelector("figcaption");
    document.addEventListener("click", function (e) {
      var a = e.target.closest("a[data-lightbox]");
      if (!a || e.metaKey || e.ctrlKey || e.shiftKey) return;
      e.preventDefault();
      var inner = a.querySelector("img");
      img.src = a.getAttribute("href");
      img.alt = inner ? inner.alt : "";
      cap.textContent = a.dataset.caption || "";
      box.showModal();
    });
    box.querySelector(".lightbox__close").addEventListener("click", function () { box.close(); });
    box.addEventListener("click", function (e) { if (e.target === box) box.close(); });
    box.addEventListener("close", function () { img.removeAttribute("src"); });
  }

  // ---- animations: pause / play / replay. The images loop three times, then stop.
  var reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  document.querySelectorAll(".card__fig").forEach(function (fig) {
    var anim = fig.querySelector("img.js-anim");
    var btn = fig.querySelector(".anim-toggle");
    if (!anim || !btn || reduce) return;
    var loops = 3, timer = null;
    var cycle = parseInt(anim.dataset.loopMs || "0", 10);

    function setState(state) { btn.dataset.state = state; btn.textContent = state === "playing" ? "Pause" : state === "ended" ? "Replay" : "Play"; }
    function play() {
      var a0 = anim.dataset.anim; anim.src = a0 + (a0.indexOf("?") < 0 ? "?" : "&") + "play=" + Date.now();   // a new URL restarts the animation
      setState("playing");
      clearTimeout(timer);
      if (cycle > 0) timer = setTimeout(function () { setState("ended"); }, cycle * loops);
    }
    function pause() { clearTimeout(timer); anim.src = anim.dataset.still || anim.src; setState("paused"); }

    btn.hidden = false;
    setState("playing");
    if (cycle > 0) timer = setTimeout(function () { setState("ended"); }, cycle * loops);
    btn.addEventListener("click", function () { btn.dataset.state === "playing" ? pause() : play(); });
  });
})();
