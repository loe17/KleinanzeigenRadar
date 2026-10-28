// KleinanzeigenRadar - Modernes Frontend im Notion / Kaneo Stil

let activeSearchId = null;
let activeStatus = "all";
let allSearches = [];
let allResults = [];
let selectedResult = null;

// DOM Geladen
document.addEventListener("DOMContentLoaded", () => {
  initApp();
  setupEventListeners();
  // Regelmäßige Aktualisierung der Statistiken und Treffer alle 30 Sekunden
  setInterval(() => {
    loadSearches(false);
    loadResults(false);
  }, 30000);
});

async function initApp() {
  await loadSearches();
  await loadResults();
  loadStats();
}

function setupEventListeners() {
  // Navigation & Filter
  document.getElementById("nav-all").addEventListener("click", () => setNavFilter("all", null));
  document.getElementById("nav-new").addEventListener("click", () => setNavFilter("new", null));
  document.getElementById("nav-starred").addEventListener("click", () => setNavFilter("starred", null));
  document.getElementById("nav-dismissed").addEventListener("click", () => setNavFilter("dismissed", null));

  // Filter-Bar
  document.getElementById("filter-search-input").addEventListener("input", debounce(filterResultsLocally, 250));
  document.getElementById("filter-shipping").addEventListener("change", () => loadResults());
  document.getElementById("filter-min-price").addEventListener("input", debounce(() => loadResults(), 400));
  document.getElementById("filter-max-price").addEventListener("input", debounce(() => loadResults(), 400));

  // Buttons
  document.getElementById("btn-add-search").addEventListener("click", () => openSearchModal());
  document.getElementById("btn-refresh-results").addEventListener("click", () => {
    loadSearches();
    loadResults();
    showToast("Trefferliste aktualisiert", "success");
  });
  document.getElementById("btn-mark-all-read").addEventListener("click", markAllAsRead);
  document.getElementById("btn-open-settings").addEventListener("click", openSettingsModal);

  // Modals schließen per Klick auf Overlay oder Close-Button
  document.querySelectorAll(".modal-overlay").forEach(overlay => {
    overlay.addEventListener("click", (e) => {
      if (e.target === overlay) closeModal(overlay.id);
    });
  });

  document.querySelectorAll("[data-close-modal]").forEach(btn => {
    btn.addEventListener("click", (e) => {
      const modalId = btn.getAttribute("data-close-modal");
      closeModal(modalId);
    });
  });

  // Formulare
  document.getElementById("search-form").addEventListener("submit", handleSearchFormSubmit);
  document.getElementById("settings-form").addEventListener("submit", handleSettingsFormSubmit);
  document.getElementById("btn-test-telegram").addEventListener("click", testTelegram);
  document.getElementById("btn-test-email").addEventListener("click", testEmail);
  document.getElementById("btn-check-update").addEventListener("click", checkUpdate);
  document.getElementById("btn-perform-update").addEventListener("click", performUpdate);
}

// --- Navigation & Filter Handhabung ---

function setNavFilter(status, searchId) {
  activeStatus = status;
  activeSearchId = searchId;

  // Aktive Klassen im Menü aktualisieren
  document.querySelectorAll(".nav-item").forEach(item => item.classList.remove("active"));
  
  if (searchId) {
    const el = document.getElementById(`search-nav-${searchId}`);
    if (el) el.classList.add("active");
    const s = allSearches.find(x => x.id === searchId);
    document.getElementById("header-title").innerText = s ? s.name : "Suchauftrag";
    document.getElementById("header-desc").innerText = s ? `Hauptbegriff: "${s.query}"` : "";
  } else {
    const el = document.getElementById(`nav-${status}`);
    if (el) el.classList.add("active");
    const titles = {
      all: "Alle Treffer",
      new: "Neue Treffer",
      starred: "Favoriten ⭐",
      dismissed: "Archiv / Ignoriert"
    };
    document.getElementById("header-title").innerText = titles[status] || "Treffer";
    document.getElementById("header-desc").innerText = "Übersicht über alle gefundenen Kleinanzeigen";
  }

  loadResults();
}

// --- API Aufrufe & Laden ---

async function loadSearches(showSpinner = true) {
  try {
    const res = await fetch("/api/searches");
    allSearches = await res.json();
    renderSearchesList();
  } catch (err) {
    console.error("Fehler beim Laden der Suchen:", err);
  }
}

async function loadResults(showSpinner = true) {
  const container = document.getElementById("results-container");
  if (showSpinner && allResults.length === 0) {
    container.innerHTML = `<div class="empty-state"><div class="empty-state-icon">⏳</div><p>Lade Treffer...</p></div>`;
  }

  const shipping = document.getElementById("filter-shipping").value;
  const minPrice = document.getElementById("filter-min-price").value;
  const maxPrice = document.getElementById("filter-max-price").value;
  const searchTerm = document.getElementById("filter-search-input").value;

  const params = new URLSearchParams();
  if (activeSearchId) params.append("search_id", activeSearchId);
  if (activeStatus && activeStatus !== "all") params.append("status", activeStatus);
  if (shipping && shipping !== "all") params.append("shipping_filter", shipping);
  if (minPrice) params.append("min_price", minPrice);
  if (maxPrice) params.append("max_price", maxPrice);
  if (searchTerm) params.append("search_term", searchTerm);

  try {
    const res = await fetch(`/api/results?${params.toString()}`);
    allResults = await res.json();
    renderResultsGrid();
    loadStats();
  } catch (err) {
    console.error("Fehler beim Laden der Ergebnisse:", err);
    container.innerHTML = `<div class="empty-state"><div class="empty-state-icon">⚠️</div><p>Fehler beim Laden der Treffer.</p></div>`;
  }
}

async function loadStats() {
  try {
    const res = await fetch("/api/stats");
    const stats = await res.json();
    
    document.getElementById("count-all").innerText = stats.total_results || 0;
    document.getElementById("count-new").innerText = stats.new_results || 0;
    document.getElementById("count-starred").innerText = stats.starred_results || 0;
  } catch (err) {
    console.error("Fehler bei Statistiken:", err);
  }
}

// --- Render-Funktionen ---

function renderSearchesList() {
  const list = document.getElementById("searches-list");
  list.innerHTML = "";

  if (allSearches.length === 0) {
    list.innerHTML = `<div style="padding: 10px; font-size: 12px; color: var(--text-muted); text-align: center;">Noch keine Suchaufträge angelegt.</div>`;
    return;
  }

  allSearches.forEach(s => {
    const item = document.createElement("div");
    item.className = `nav-item ${activeSearchId === s.id ? "active" : ""}`;
    item.id = `search-nav-${s.id}`;
    
    const statusIcon = s.is_active ? "🟢" : "⚪";
    item.innerHTML = `
      <span style="font-size: 11px;">${statusIcon}</span>
      <span style="flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${escapeHtml(s.name)}</span>
      <div class="search-item-actions">
        <button class="btn-icon-tiny" title="Jetzt ausführen" onclick="runSearchNow(event, ${s.id})">▶</button>
        <button class="btn-icon-tiny" title="Bearbeiten" onclick="editSearch(event, ${s.id})">✏️</button>
        <button class="btn-icon-tiny" title="Löschen" onclick="confirmDeleteSearch(event, ${s.id})">🗑️</button>
      </div>
    `;

    item.addEventListener("click", () => setNavFilter("all", s.id));
    list.appendChild(item);
  });
}

function renderResultsGrid() {
  const container = document.getElementById("results-container");

  if (allResults.length === 0) {
    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-state-icon">🔍</div>
        <h3>Keine Treffer gefunden</h3>
        <p>Entweder wurden für diesen Filter noch keine passenden Kleinanzeigen gefunden oder der Wächter sucht gerade.</p>
      </div>
    `;
    return;
  }

  let html = `<div class="results-grid">`;
  allResults.forEach(r => {
    const isNew = r.status === "new";
    const isStarred = r.status === "starred";
    const starIcon = isStarred ? "⭐" : "☆";
    const starTitle = isStarred ? "Aus Favoriten entfernen" : "Als Favorit merken";
    const shippingBadge = r.shipping_possible ? "📦 Versand" : "📍 Abholung";
    const thumb = r.thumbnail_url || "/static/logo.svg";

    html += `
      <div class="result-card ${isNew ? 'is-new' : ''}" onclick="openDetailModal(${r.id})">
        <div class="result-image-box">
          <img class="result-image" src="${escapeHtml(thumb)}" alt="${escapeHtml(r.title)}" loading="lazy" onerror="this.src='/static/logo.svg'">
          <div class="result-price-badge">${escapeHtml(r.price || 'VB')}</div>
          <div class="result-shipping-badge">${shippingBadge}</div>
        </div>

        <div class="result-card-body">
          <div class="result-tags">
            <span class="tag tag-highlight">${escapeHtml(r.search_name || 'Suche')}</span>
            ${r.ocr_text ? '<span class="tag" title="Text in Fotos gefunden">📷 Bild-Text</span>' : ''}
          </div>

          <a href="${escapeHtml(r.url)}" target="_blank" class="result-title" onclick="event.stopPropagation()">
            ${escapeHtml(r.title)}
          </a>

          <div class="result-location">
            📍 ${escapeHtml(r.location || 'Deutschland')}
          </div>

          ${r.match_reason ? `<div class="result-match-reason">💡 ${escapeHtml(r.match_reason)}</div>` : ''}

          <div class="result-footer-actions" onclick="event.stopPropagation()">
            <div style="display: flex; gap: 4px;">
              <button class="btn btn-ghost btn-sm" title="${starTitle}" onclick="toggleStar(${r.id}, '${r.status}')">
                ${starIcon}
              </button>
              ${isNew ? `
                <button class="btn btn-ghost btn-sm" title="Als gelesen markieren" onclick="setResultStatus(${r.id}, 'read')">
                  ✓ Gelesen
                </button>
              ` : ''}
              <button class="btn btn-ghost btn-sm" title="Ignorieren / Archivieren" onclick="setResultStatus(${r.id}, 'dismissed')">
                ✕
              </button>
            </div>
            
            <a href="${escapeHtml(r.url)}" target="_blank" class="btn btn-secondary btn-sm" style="text-decoration: none;">
              Öffnen ↗
            </a>
          </div>
        </div>
      </div>
    `;
  });
  html += `</div>`;
  container.innerHTML = html;
}

function filterResultsLocally() {
  const term = document.getElementById("filter-search-input").value.toLowerCase().trim();
  if (!term) {
    renderResultsGrid();
    return;
  }
  const filtered = allResults.filter(r => {
    return (
      (r.title && r.title.toLowerCase().includes(term)) ||
      (r.description && r.description.toLowerCase().includes(term)) ||
      (r.ocr_text && r.ocr_text.toLowerCase().includes(term))
    );
  });
  renderResultsGridWithList(filtered);
}

function renderResultsGridWithList(list) {
  // Lokales Rendern bei Sofort-Tippen
  const prev = allResults;
  allResults = list;
  renderResultsGrid();
  allResults = prev;
}

// --- Detail-Modal ---

function openDetailModal(resultId) {
  const r = allResults.find(x => x.id === resultId);
  if (!r) return;
  selectedResult = r;

  // Wenn neu, direkt als gelesen markieren
  if (r.status === "new") {
    setResultStatus(r.id, "read", false);
  }

  document.getElementById("detail-title").innerText = r.title;
  document.getElementById("detail-price").innerText = r.price || "K.A.";
  document.getElementById("detail-location").innerText = `${r.location} (${r.shipping_possible ? "Versand möglich" : "Nur Abholung"})`;
  document.getElementById("detail-search-name").innerText = r.search_name || "Suchauftrag";
  document.getElementById("detail-match-reason").innerText = r.match_reason || "Gefunden";
  document.getElementById("detail-link").href = r.url;
  document.getElementById("detail-description").innerText = r.description || "Keine Beschreibung vorhanden.";

  // Bildergalerie
  const gallery = document.getElementById("detail-gallery");
  gallery.innerHTML = "";
  if (r.images && r.images.length > 0) {
    r.images.forEach(imgUrl => {
      const img = document.createElement("img");
      img.src = imgUrl;
      img.loading = "lazy";
      img.onclick = () => window.open(imgUrl, "_blank");
      gallery.appendChild(img);
    });
  } else {
    gallery.innerHTML = `<span style="font-size: 12px; color: var(--text-muted);">Keine weiteren Bilder vorhanden.</span>`;
  }

  // OCR Box
  const ocrContainer = document.getElementById("detail-ocr-box");
  if (r.ocr_text && r.ocr_text.trim()) {
    ocrContainer.style.display = "block";
    document.getElementById("detail-ocr-text").innerText = r.ocr_text;
  } else {
    ocrContainer.style.display = "none";
  }

  openModal("modal-detail");
}

// --- Status Aktionen ---

async function setResultStatus(id, newStatus, refresh = true) {
  try {
    await fetch(`/api/results/${id}/status`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status: newStatus })
    });
    if (refresh) {
      loadResults(false);
      loadStats();
    }
  } catch (err) {
    showToast("Status-Änderung fehlgeschlagen", "error");
  }
}

function toggleStar(id, currentStatus) {
  const nextStatus = currentStatus === "starred" ? "read" : "starred";
  setResultStatus(id, nextStatus);
  showToast(nextStatus === "starred" ? "Zu Favoriten hinzugefügt ⭐" : "Aus Favoriten entfernt", "success");
}

async function markAllAsRead() {
  try {
    await fetch(`/api/results/mark-all-read${activeSearchId ? `?search_id=${activeSearchId}` : ''}`, {
      method: "POST"
    });
    showToast("Alle Treffer als gelesen markiert", "success");
    loadResults();
  } catch (err) {
    showToast("Fehler beim Markieren", "error");
  }
}

// --- Suchen verwalten ---

function openSearchModal(searchData = null) {
  const form = document.getElementById("search-form");
  form.reset();

  if (searchData) {
    document.getElementById("search-modal-title").innerText = "Suchauftrag bearbeiten";
    document.getElementById("search-id-input").value = searchData.id;
    document.getElementById("s-name").value = searchData.name || "";
    document.getElementById("s-query").value = searchData.query || "";
    document.getElementById("s-keywords").value = searchData.keywords || "";
    document.getElementById("s-case-sensitive").checked = Boolean(searchData.case_sensitive);
    document.getElementById("s-search-in-desc").checked = Boolean(searchData.search_in_description);
    document.getElementById("s-ocr-images").checked = Boolean(searchData.ocr_images);
    document.getElementById("s-min-price").value = searchData.min_price || "";
    document.getElementById("s-max-price").value = searchData.max_price || "";
    document.getElementById("s-plz").value = searchData.postal_code || "";
    document.getElementById("s-radius").value = searchData.radius || "0";
    document.getElementById("s-shipping").value = searchData.shipping_type || "all";
    document.getElementById("s-notify-telegram").checked = Boolean(searchData.notify_telegram);
    document.getElementById("s-notify-email").checked = Boolean(searchData.notify_email);
    document.getElementById("s-interval").value = searchData.interval_minutes || 15;
    document.getElementById("s-is-active").checked = Boolean(searchData.is_active);
  } else {
    document.getElementById("search-modal-title").innerText = "Neuen Suchauftrag anlegen";
    document.getElementById("search-id-input").value = "";
    document.getElementById("s-interval").value = 15;
    document.getElementById("s-search-in-desc").checked = true;
    document.getElementById("s-ocr-images").checked = true;
    document.getElementById("s-notify-telegram").checked = true;
    document.getElementById("s-notify-email").checked = true;
    document.getElementById("s-is-active").checked = true;
  }

  openModal("modal-search");
}

async function editSearch(event, id) {
  event.stopPropagation();
  const s = allSearches.find(x => x.id === id);
  if (s) openSearchModal(s);
}

async function runSearchNow(event, id) {
  event.stopPropagation();
  showToast("Suche wird im Hintergrund ausgeführt...", "success");
  try {
    await fetch(`/api/searches/${id}/run`, { method: "POST" });
    setTimeout(() => {
      loadResults(false);
      loadStats();
    }, 3000);
  } catch (err) {
    showToast("Fehler beim Starten der Suche", "error");
  }
}

async function confirmDeleteSearch(event, id) {
  event.stopPropagation();
  if (confirm("Möchtest du diesen Suchauftrag und alle zugehörigen Treffer wirklich löschen?")) {
    try {
      await fetch(`/api/searches/${id}`, { method: "DELETE" });
      showToast("Suchauftrag gelöscht", "success");
      if (activeSearchId === id) {
        setNavFilter("all", null);
      }
      loadSearches();
      loadResults();
    } catch (err) {
      showToast("Fehler beim Löschen", "error");
    }
  }
}

async function handleSearchFormSubmit(e) {
  e.preventDefault();
  const id = document.getElementById("search-id-input").value;
  const payload = {
    name: document.getElementById("s-name").value.trim(),
    query: document.getElementById("s-query").value.trim(),
    keywords: document.getElementById("s-keywords").value.trim(),
    case_sensitive: document.getElementById("s-case-sensitive").checked,
    search_in_description: document.getElementById("s-search-in-desc").checked,
    ocr_images: document.getElementById("s-ocr-images").checked,
    min_price: parseFloat(document.getElementById("s-min-price").value) || null,
    max_price: parseFloat(document.getElementById("s-max-price").value) || null,
    postal_code: document.getElementById("s-plz").value.trim(),
    radius: parseInt(document.getElementById("s-radius").value) || 0,
    shipping_type: document.getElementById("s-shipping").value,
    notify_telegram: document.getElementById("s-notify-telegram").checked,
    notify_email: document.getElementById("s-notify-email").checked,
    interval_minutes: parseInt(document.getElementById("s-interval").value) || 15,
    is_active: document.getElementById("s-is-active").checked
  };

  try {
    if (id) {
      await fetch(`/api/searches/${id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      showToast("Suchauftrag aktualisiert", "success");
    } else {
      await fetch("/api/searches", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      showToast("Suchauftrag angelegt & Erstsuche gestartet", "success");
    }

    closeModal("modal-search");
    loadSearches();
    loadResults();
  } catch (err) {
    showToast("Fehler beim Speichern des Suchauftrags", "error");
  }
}

// --- Einstellungen & Updater Modal ---

async function openSettingsModal() {
  try {
    const res = await fetch("/api/settings");
    const settings = await res.json();

    document.getElementById("cfg-telegram-token").value = settings.telegram_bot_token || "";
    document.getElementById("cfg-telegram-chat-id").value = settings.telegram_chat_id || "";
    document.getElementById("cfg-email-host").value = settings.email_smtp_host || "";
    document.getElementById("cfg-email-port").value = settings.email_smtp_port || "587";
    document.getElementById("cfg-email-user").value = settings.email_smtp_user || "";
    document.getElementById("cfg-email-password").value = "";
    document.getElementById("cfg-email-password").placeholder = settings.email_smtp_password_masked ? "●●●●●●●● (Unverändert)" : "";
    document.getElementById("cfg-email-tls").checked = settings.email_smtp_tls === "1" || settings.email_smtp_tls === true;
    document.getElementById("cfg-email-from").value = settings.email_from || "";
    document.getElementById("cfg-email-to").value = settings.email_to || "";
    document.getElementById("cfg-github-repo").value = settings.github_repo || "loe17/KleinanzeigenRadar";

    openModal("modal-settings");
  } catch (err) {
    showToast("Einstellungen konnten nicht geladen werden", "error");
  }
}

async function handleSettingsFormSubmit(e) {
  e.preventDefault();
  const payload = {
    telegram_bot_token: document.getElementById("cfg-telegram-token").value.trim(),
    telegram_chat_id: document.getElementById("cfg-telegram-chat-id").value.trim(),
    email_smtp_host: document.getElementById("cfg-email-host").value.trim(),
    email_smtp_port: document.getElementById("cfg-email-port").value.trim(),
    email_smtp_user: document.getElementById("cfg-email-user").value.trim(),
    email_smtp_tls: document.getElementById("cfg-email-tls").checked ? "1" : "0",
    email_from: document.getElementById("cfg-email-from").value.trim(),
    email_to: document.getElementById("cfg-email-to").value.trim(),
    github_repo: document.getElementById("cfg-github-repo").value.trim()
  };

  const pass = document.getElementById("cfg-email-password").value;
  if (pass) {
    payload.email_smtp_password = pass;
  }

  try {
    await fetch("/api/settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    showToast("Einstellungen gespeichert", "success");
    closeModal("modal-settings");
  } catch (err) {
    showToast("Fehler beim Speichern der Einstellungen", "error");
  }
}

async function testTelegram() {
  const token = document.getElementById("cfg-telegram-token").value.trim();
  const chatId = document.getElementById("cfg-telegram-chat-id").value.trim();
  showToast("Sende Telegram Testnachricht...", "info");

  try {
    const res = await fetch("/api/settings/test-telegram", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ telegram_bot_token: token, telegram_chat_id: chatId })
    });
    const data = await res.json();
    if (data.success) {
      showToast(data.message, "success");
    } else {
      showToast(data.message, "error");
    }
  } catch (err) {
    showToast("Netzwerkfehler beim Telegram Test", "error");
  }
}

async function testEmail() {
  const payload = {
    email_smtp_host: document.getElementById("cfg-email-host").value.trim(),
    email_smtp_port: document.getElementById("cfg-email-port").value.trim(),
    email_smtp_user: document.getElementById("cfg-email-user").value.trim(),
    email_smtp_tls: document.getElementById("cfg-email-tls").checked ? "1" : "0",
    email_from: document.getElementById("cfg-email-from").value.trim(),
    email_to: document.getElementById("cfg-email-to").value.trim()
  };
  const pass = document.getElementById("cfg-email-password").value;
  if (pass) payload.email_smtp_password = pass;

  showToast("Sende Test-E-Mail...", "info");
  try {
    const res = await fetch("/api/settings/test-email", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (data.success) {
      showToast(data.message, "success");
    } else {
      showToast(data.message, "error");
    }
  } catch (err) {
    showToast("Netzwerkfehler beim E-Mail Test", "error");
  }
}

async function checkUpdate() {
  const statusEl = document.getElementById("update-status-msg");
  statusEl.innerText = "Prüfe GitHub auf neue Versionen...";
  try {
    const res = await fetch("/api/system/update/check");
    const data = await res.json();
    if (data.error) {
      statusEl.innerHTML = `<span style="color: #ef4444;">⚠️ ${escapeHtml(data.error)}</span>`;
    } else if (data.update_available) {
      statusEl.innerHTML = `
        <span style="color: #86b817; font-weight: bold;">🎉 Neue Version verfügbar: v${escapeHtml(data.latest_version)}</span>
        <p style="font-size: 11.5px; margin-top: 4px; color: var(--text-secondary);">${escapeHtml(data.release_notes)}</p>
      `;
      document.getElementById("btn-perform-update").style.display = "inline-flex";
    } else {
      statusEl.innerHTML = `<span style="color: #10b981;">✓ KleinanzeigenRadar ist auf dem neuesten Stand (v${escapeHtml(data.current_version)}).</span>`;
    }
  } catch (err) {
    statusEl.innerText = "Fehler beim Abrufen der Update-Informationen.";
  }
}

async function performUpdate() {
  const statusEl = document.getElementById("update-status-msg");
  statusEl.innerText = "Aktualisierung wird ausgeführt...";
  try {
    const res = await fetch("/api/system/update/perform", { method: "POST" });
    const data = await res.json();
    if (data.success) {
      statusEl.innerHTML = `<span style="color: #10b981; font-weight: bold;">✓ ${escapeHtml(data.message)}</span>`;
      showToast("Update erfolgreich!", "success");
    } else {
      statusEl.innerHTML = `<span style="color: #ef4444;">⚠️ ${escapeHtml(data.message)}</span>`;
    }
  } catch (err) {
    statusEl.innerText = "Fehler beim Durchführen der Aktualisierung.";
  }
}

// --- Hilfsfunktionen ---

function openModal(id) {
  const modal = document.getElementById(id);
  if (modal) modal.classList.add("open");
}

function closeModal(id) {
  const modal = document.getElementById(id);
  if (modal) modal.classList.remove("open");
}

function showToast(message, type = "info") {
  const container = document.getElementById("toast-container");
  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  toast.innerText = message;
  container.appendChild(toast);
  setTimeout(() => {
    toast.remove();
  }, 4000);
}

function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
