/**
 * ClawDeez: re-skin OpenClaw Control UI (connect shell + sidebar/login chrome) using
 * payload in #clawdeez-brand-json (injected by patch-openclaw-branding.py).
 */
(function () {
  "use strict";

  var el = document.getElementById("clawdeez-brand-json");
  if (!el || !el.textContent) return;

  var brand;
  try {
    brand = JSON.parse(el.textContent);
  } catch (e) {
    return;
  }
  if (!brand.assistantName) return;

  var NAME = String(brand.assistantName);
  var SUB = brand.gatewaySubtitle != null ? String(brand.gatewaySubtitle) : "";
  var AVATAR = brand.avatarUrl != null ? String(brand.avatarUrl).trim() : "";
  var BAKED_LOGO = "./clawdeez-brand-logo.png";

  function queryDeepAll(root, selector) {
    var out = [];
    if (!root || !root.querySelectorAll) return out;
    try {
      var found = root.querySelectorAll(selector);
      var i;
      for (i = 0; i < found.length; i++) out.push(found[i]);
    } catch (e) {
      /* ignore */
    }
    var all = root.querySelectorAll("*");
    var j;
    for (j = 0; j < all.length; j++) {
      var sr = all[j].shadowRoot;
      if (sr) {
        var inner = queryDeepAll(sr, selector);
        out.push.apply(out, inner);
      }
    }
    return out;
  }

  function walkTextNodes(root, fn) {
    var tw = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, null);
    var n;
    while ((n = tw.nextNode())) fn(n);
    var all = root.querySelectorAll("*");
    var i;
    for (i = 0; i < all.length; i++) {
      var sr = all[i].shadowRoot;
      if (sr) walkTextNodes(sr, fn);
    }
  }

  function applyText() {
    if (!document.body) return;
    walkTextNodes(document.body, function (node) {
      var v = node.nodeValue;
      if (!v) return;
      var hasOpenClaw = v.indexOf("OpenClaw") !== -1;
      var hasGatewayDash = v.indexOf("Gateway Dashboard") !== -1;
      if (!hasOpenClaw && !(SUB && hasGatewayDash)) return;
      var next = hasOpenClaw ? v.split("OpenClaw").join(NAME) : v;
      if (SUB && hasGatewayDash) next = next.split("Gateway Dashboard").join(SUB);
      if (next !== v) node.nodeValue = next;
    });
  }

  function applyTitle() {
    var t = document.title;
    if (t && t.indexOf("OpenClaw") !== -1) {
      document.title = t.split("OpenClaw").join(NAME);
    }
  }

  /** OpenClaw hardcodes alt="OpenClaw" and favicon.svg in bundled templates. */
  function applyLogosAndTitles() {
    if (!document.body) return;
    var root = document.body;
    var imgs = queryDeepAll(root, "img");
    var i;
    for (i = 0; i < imgs.length; i++) {
      var img = imgs[i];
      if (img.getAttribute("alt") !== "OpenClaw") continue;
      img.setAttribute("alt", NAME);
      var current = img.src || "";
      if (AVATAR.indexOf("http") === 0) {
        img.src = AVATAR;
      } else if (
        current.indexOf("favicon.svg") !== -1 ||
        current.indexOf("favicon.ico") !== -1 ||
        !current
      ) {
        try {
          img.src = new URL(BAKED_LOGO, window.location.href).href;
        } catch (e2) {
          img.setAttribute("src", BAKED_LOGO);
        }
      }
    }
    var titleEls = queryDeepAll(root, ".sidebar-brand__title, .login-gate__title");
    for (i = 0; i < titleEls.length; i++) {
      var te = titleEls[i];
      if (te.textContent && te.textContent.trim() === "OpenClaw") {
        te.textContent = NAME;
      }
    }
  }

  function tick() {
    applyTitle();
    applyLogosAndTitles();
    applyText();
  }

  if (document.body) {
    var ob = new MutationObserver(tick);
    ob.observe(document.body, { childList: true, subtree: true });
    window.setTimeout(function () {
      ob.disconnect();
    }, 30000);
  }
  window.addEventListener("DOMContentLoaded", tick);
  tick();
  var k = 0;
  var iv = window.setInterval(function () {
    tick();
    k += 1;
    if (k >= 40) window.clearInterval(iv);
  }, 500);
})();
