/**
 * ClawDeez: prefill OpenClaw Control UI "Gateway token" from URL hash or sessionStorage,
 * then strip the hash from the address bar (history.replaceState).
 *
 * URL: https://your-agent.example/#clawdeez-gw=<encodeURIComponent(token)>
 *
 * sessionStorage: key "clawdeez.openclawGatewayToken" (removed after read). Same-origin only;
 * useful for manual scripting or future same-origin tooling.
 */
(function () {
  "use strict";

  var HASH_PREFIX = "#clawdeez-gw=";
  var STORAGE_KEY = "clawdeez.openclawGatewayToken";
  var POLL_MS = 50;
  var TIMEOUT_MS = 45000;

  function collectInputs(node, acc) {
    if (!node) return;
    if (node.nodeName === "INPUT") acc.push(node);
    var sr = node.shadowRoot;
    if (sr) collectInputs(sr, acc);
    var ch = node.firstElementChild;
    while (ch) {
      collectInputs(ch, acc);
      ch = ch.nextElementSibling;
    }
  }

  function isVisible(el) {
    if (!(el instanceof HTMLElement)) return false;
    if (el.disabled) return false;
    var st = window.getComputedStyle(el);
    if (st.display === "none" || st.visibility === "hidden" || st.opacity === "0")
      return false;
    var r = el.getBoundingClientRect();
    return r.width > 0 && r.height > 0;
  }

  function pickGatewayInput(inputs) {
    var i;
    var pwd = null;
    var text = null;
    for (i = 0; i < inputs.length; i++) {
      var el = inputs[i];
      if (!isVisible(el)) continue;
      if (el.type === "password") {
        pwd = el;
        break;
      }
      if (el.type === "text" && !text) text = el;
    }
    return pwd || text;
  }

  function tryFill(token) {
    var acc = [];
    if (!document.body) return false;
    collectInputs(document.body, acc);
    var el = pickGatewayInput(acc);
    if (!el) return false;
    el.focus();
    el.value = token;
    el.dispatchEvent(new Event("input", { bubbles: true, composed: true }));
    el.dispatchEvent(new Event("change", { bubbles: true, composed: true }));
    return true;
  }

  function readTokenFromHash() {
    var h = window.location.hash;
    if (h.indexOf(HASH_PREFIX) !== 0) return null;
    try {
      return decodeURIComponent(h.slice(HASH_PREFIX.length));
    } catch (e) {
      return null;
    }
  }

  function stripHashFromUrl() {
    var path = window.location.pathname + window.location.search;
    window.history.replaceState(null, "", path);
  }

  var token = readTokenFromHash();
  var fromHash = token !== null && token !== "";

  if (fromHash) {
    stripHashFromUrl();
  } else {
    try {
      token = sessionStorage.getItem(STORAGE_KEY);
      if (token) sessionStorage.removeItem(STORAGE_KEY);
    } catch (e) {
      token = null;
    }
  }

  if (!token || !String(token).trim()) return;

  token = String(token).trim();

  var start = Date.now();

  function tick() {
    if (tryFill(token)) return;
    if (Date.now() - start > TIMEOUT_MS) return;
    window.setTimeout(tick, POLL_MS);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () {
      tick();
    });
  } else {
    tick();
  }
})();
