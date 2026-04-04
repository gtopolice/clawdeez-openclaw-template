/**
 * ClawDeez: re-skin OpenClaw Control UI connect shell (Gateway Dashboard) using
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

  function applyIcons() {
    if (!AVATAR || AVATAR.indexOf("http") !== 0) return;
    var links = document.querySelectorAll('link[rel="icon"], link[rel="apple-touch-icon"]');
    var i;
    for (i = 0; i < links.length; i++) links[i].href = AVATAR;
  }

  function tick() {
    applyTitle();
    applyIcons();
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
