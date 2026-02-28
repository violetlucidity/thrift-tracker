// Site detection — must match DOMAIN_TO_SITE in import_links.py
const DOMAIN_TO_SITE = {
  "vinted.co.uk": "vinted",
  "vinted.com":   "vinted",
  "vinted.fr":    "vinted",
  "vinted.de":    "vinted",
  "vinted.nl":    "vinted",
  "vinted.be":    "vinted",
  "depop.com":    "depop",
  "ebay.co.uk":   "ebay",
  "ebay.com":     "ebay",
  "ebay.de":      "ebay",
  "ebay.fr":      "ebay",
  "ebay.com.au":  "ebay",
  "poshmark.com": "poshmark",
};

const SERVER = "http://127.0.0.1:5000";

function detectSite(url) {
  try {
    let host = new URL(url).hostname.toLowerCase();
    if (host.startsWith("www.")) host = host.slice(4);
    return DOMAIN_TO_SITE[host] || null;
  } catch {
    return null;
  }
}

function setStatus(text, type) {
  const el = document.getElementById("status");
  el.textContent = text;
  el.className = type; // "ok" | "err" | ""
}

document.addEventListener("DOMContentLoaded", async () => {
  const urlEl   = document.getElementById("url-display");
  const siteEl  = document.getElementById("site-display");
  const saveBtn = document.getElementById("save-btn");
  const hint    = document.getElementById("hint");

  // Get the active tab's URL
  const [tab] = await browser.tabs.query({ active: true, currentWindow: true });
  const url = tab.url || "";

  // Show (possibly truncated) URL
  urlEl.textContent = url.length > 120 ? url.slice(0, 117) + "…" : url;

  const site = detectSite(url);

  if (site) {
    siteEl.textContent = `Detected site: [${site}]`;
    siteEl.className = "site-tag";
    saveBtn.disabled = false;
  } else {
    siteEl.textContent = "Not a recognised search page (Vinted, Depop, eBay, Poshmark).";
    siteEl.className = "site-tag unknown";
  }

  saveBtn.addEventListener("click", async () => {
    saveBtn.disabled = true;
    setStatus("Saving…", "");

    try {
      const res = await fetch(`${SERVER}/api/save-link`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url }),
      });
      const data = await res.json();

      if (data.ok) {
        setStatus(`✓ Saved under [${data.site}] in thrift-links.txt`, "ok");
        hint.hidden = false;
      } else {
        setStatus(`✗ ${data.error}`, "err");
        saveBtn.disabled = false;
      }
    } catch {
      setStatus(
        "✗ Could not reach Thrift Tracker — is it running? (python run.py)",
        "err"
      );
      saveBtn.disabled = false;
    }
  });
});
