/* Helper condiviso dagli effetti di OverPowerPoint.
 * Un effetto è una pagina HTML autonoma; questo file aggiunge solo il ponte
 * verso OPP quando la pagina è aperta dentro la modale (iframe ?embed=1).
 */
window.OPPFrame = {
  isEmbed() {
    return window.parent !== window && new URLSearchParams(location.search).has("embed");
  },
  apply() {
    if (this.isEmbed()) document.body.classList.add("embed");
  },
  sendImage(canvas, name) {
    if (!this.isEmbed()) return false;
    window.parent.postMessage(
      {
        type: "opp:image",
        dataUrl: canvas.toDataURL("image/png"),
        name: name || "effect.png",
      },
      "*",
    );
    return true;
  },
  toast(msg) {
    const el = document.createElement("div");
    el.textContent = msg;
    el.style.cssText =
      "position:fixed;left:50%;bottom:24px;transform:translateX(-50%);background:#1c2434;color:#fff;padding:9px 16px;border-radius:8px;font:13px sans-serif;z-index:9999;box-shadow:0 8px 24px rgba(0,0,0,.4)";
    document.body.appendChild(el);
    setTimeout(() => el.remove(), 2200);
  },
};

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", () => window.OPPFrame.apply());
} else {
  window.OPPFrame.apply();
}
