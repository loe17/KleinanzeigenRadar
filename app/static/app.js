// KleinanzeigenRadar - Modernes Frontend mit SVG-Icons & Mehrsprachigkeit (DE/EN)

let activeSearchId = null;
let activeStatus = "all";
let allSearches = [];
let allResults = [];
let selectedResult = null;

// DOM Geladen
document.addEventListener("DOMContentLoaded", () => {
  initIcons();
  updateStaticTranslations();
  initApp();
  setupEventListeners();

  // Regelmäßige Aktualisierung der Statistiken und Treffer alle 30 Sekunden
  setInterval(() => {
    loadSearches(false);
    loadResults(false);
  }, 30000);
});

// --- Statische SVG-Icons im DOM initialisieren ---

function initIcons() {
  const globeContainer = document.getElementById("globe-icon-container");
  if (globeContainer) globeContainer.innerHTML = getSvgIcon("globe", 13);
  const cfgLangIcon = document.getElementById("icon-cfg-lang");
  if (cfgLangIcon) cfgLangIcon.innerHTML = getSvgIcon("globe", 16);
  const addTermIcon = document.getElementById("icon-btn-add-term");
  if (addTermIcon) addTermIcon.innerHTML = getSvgIcon("plus", 14);
  const livePreviewIcon = document.getElementById("icon-live-preview");
  if (livePreviewIcon) livePreviewIcon.innerHTML = getSvgIcon("search", 14);

  document.getElementById("icon-nav-all").innerHTML = getSvgIcon("inbox", 15);
  document.getElementById("icon-nav-new").innerHTML = getSvgIcon("sparkles", 15);
  document.getElementById("icon-nav-starred").innerHTML = getSvgIcon("star", 15);
  document.getElementById("icon-nav-dismissed").innerHTML = getSvgIcon("archive", 15);
  document.getElementById("btn-add-search").innerHTML = getSvgIcon("plus", 14);
  document.getElementById("icon-nav-settings").innerHTML = getSvgIcon("settings", 15);
  document.getElementById("icon-btn-check").innerHTML = getSvgIcon("check", 14);
  document.getElementById("icon-btn-refresh").innerHTML = getSvgIcon("refresh", 14);
  const iconBtnPlus = document.getElementById("icon-btn-plus");
  if (iconBtnPlus) iconBtnPlus.innerHTML = getSvgIcon("plus", 14);
  const searchBarIcon = document.getElementById("search-bar-icon");
  if (searchBarIcon) searchBarIcon.innerHTML = getSvgIcon("search", 14);
  document.getElementById("btn-close-search-modal").innerHTML = getSvgIcon("x", 16);
  document.getElementById("btn-close-detail-modal").innerHTML = getSvgIcon("x", 16);
  document.getElementById("btn-close-settings-modal").innerHTML = getSvgIcon("x", 16);
  document.getElementById("icon-detail-ext").innerHTML = getSvgIcon("externalLink", 13);
  document.getElementById("icon-cfg-telegram").innerHTML = getSvgIcon("telegram", 16);
  document.getElementById("icon-test-telegram").innerHTML = getSvgIcon("bell", 14);
  document.getElementById("icon-cfg-email").innerHTML = getSvgIcon("mail", 16);
  document.getElementById("icon-test-email").innerHTML = getSvgIcon("mail", 14);
  document.getElementById("icon-cfg-github").innerHTML = getSvgIcon("github", 16);
  document.getElementById("icon-check-update").innerHTML = getSvgIcon("search", 14);
  document.getElementById("icon-perform-update").innerHTML = getSvgIcon("download", 14);
}

// --- Sprachwechsel & Übersetzungsaktualisierung ---

function changeLanguage(lang) {
  setLanguage(lang);
  updateStaticTranslations();
  renderSearchesList();
  renderResultsGrid();
  loadStats();
}

function updateStaticTranslations() {
  const cfgLang = document.getElementById("cfg-language");
  if (cfgLang) cfgLang.value = currentLang;

  // Alle Elemente mit data-i18n Attribut übersetzen
  document.querySelectorAll("[data-i18n]").forEach(el => {
    const key = el.getAttribute("data-i18n");
    if (key) {
      el.innerText = t(key);
    }
  });

  // Platzhalter übersetzen
  const fSearch = document.getElementById("filter-search-input");
  if (fSearch) fSearch.placeholder = t("filter_search_placeholder");
  const fMin = document.getElementById("filter-min-price");
  if (fMin) fMin.placeholder = t("filter_min_price");
  const fMax = document.getElementById("filter-max-price");
  if (fMax) fMax.placeholder = t("filter_max_price");
  const sName = document.getElementById("s-name");
  if (sName) sName.placeholder = t("ph_search_name");
  const termIn = document.getElementById("term-input");
  if (termIn) termIn.placeholder = t("ph_term_input");
  const sMin = document.getElementById("s-min-price");
  if (sMin) sMin.placeholder = t("ph_price_any");
  const sMax = document.getElementById("s-max-price");
  if (sMax) sMax.placeholder = t("ph_price_any");
  const sPlz = document.getElementById("s-plz");
  if (sPlz) sPlz.placeholder = t("ph_plz");
  const cfgTelTok = document.getElementById("cfg-telegram-token");
  if (cfgTelTok) cfgTelTok.placeholder = t("ph_bot_token");
  const cfgTelChat = document.getElementById("cfg-telegram-chat-id");
  if (cfgTelChat) cfgTelChat.placeholder = t("ph_chat_id");

  // Header-Titel je nach aktuellem Tab
  if (!activeSearchId) {
    const titleKey = `header_${activeStatus}_title`;
    const descKey = `header_${activeStatus}_desc`;
    document.getElementById("header-title").innerText = t(titleKey);
    document.getElementById("header-desc").innerText = t(descKey);
  }
}

async function initApp() {
  await loadSearches();
  await loadResults();
  loadStats();

  if (allSearches.length > 0 && allResults.length === 0) {
    setTimeout(async () => {
      await loadSearches(false);
      await loadResults(false);
      loadStats();
    }, 2500);
  }
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
  const sortSelect = document.getElementById("filter-sort");
  if (sortSelect) sortSelect.addEventListener("change", () => loadResults());
  document.getElementById("filter-min-price").addEventListener("input", debounce(() => loadResults(), 400));
  document.getElementById("filter-max-price").addEventListener("input", debounce(() => loadResults(), 400));

  // Buttons
  document.getElementById("btn-add-search").addEventListener("click", () => openSearchModal());
  document.getElementById("btn-refresh-results").addEventListener("click", async () => {
    if (activeSearchId) {
      showToast(t("toast_search_triggered"), "info");
      // Sofort vorhandene Treffer aus der Anzeige entfernen und Lade-Spinner anzeigen
      allResults = [];
      const container = document.getElementById("results-container");
      if (container) {
        container.innerHTML = `<div class="empty-state"><div class="empty-state-icon">${getSvgIcon('spinner', 32)}</div><p>${t('loading_results')}</p></div>`;
      }
      try {
        await fetch(`/api/searches/${activeSearchId}/run`, { method: "POST" });
        pollForResults(activeSearchId);
      } catch (err) {
        showToast("Error", "error");
      }
    } else {
      loadSearches();
      loadResults();
      showToast(t("toast_refresh"), "success");
    }
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
    btn.addEventListener("click", () => {
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

  // Begriff hinzufügen & Live-Vorschau
  const btnAddTerm = document.getElementById("btn-add-term");
  if (btnAddTerm) btnAddTerm.addEventListener("click", addTermFromInput);

  const termInput = document.getElementById("term-input");
  if (termInput) {
    termInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        addTermFromInput();
      }
    });
    termInput.addEventListener("input", debounce(updateLiveCountPreview, 350));
  }

  const termType = document.getElementById("term-type");
  if (termType) termType.addEventListener("change", debounce(updateLiveCountPreview, 350));

  ["s-min-price", "s-max-price", "s-plz", "s-radius"].forEach(id => {
    const el = document.getElementById(id);
    if (el) {
      el.addEventListener("input", debounce(updateLiveCountPreview, 400));
      el.addEventListener("change", debounce(updateLiveCountPreview, 400));
    }
  });
}

// --- Navigation & Filter Handhabung ---

function updateHeaderInfo() {
  if (activeSearchId) {
    const s = allSearches.find(x => x.id === activeSearchId);
    if (s) {
      document.getElementById("header-title").innerText = s.name;
      const created = s.created_at_formatted || "-";
      const lastRun = s.last_run_formatted || t("lbl_never_checked");
      const termsDesc = (s.terms && s.terms.length > 0)
        ? s.terms.map(t => (t.type === 'exclude' ? `-${t.text}` : `+${t.text}`)).join(", ")
        : (s.query || "");
      document.getElementById("header-desc").innerHTML = `
        <span><b>${t('lbl_created_at')}</b> ${escapeHtml(created)}</span> &bull; 
        <span><b>${t('lbl_last_checked')}</b> ${escapeHtml(lastRun)}</span>
        ${termsDesc ? ` &bull; <span><b>Begriffe:</b> ${escapeHtml(termsDesc)}</span>` : ''}
      `;
    } else {
      document.getElementById("header-desc").innerText = "";
    }
  } else {
    document.getElementById("header-title").innerText = t(`header_${activeStatus}_title`);
    document.getElementById("header-desc").innerText = t(`header_${activeStatus}_desc`);
  }
}

function setNavFilter(status, searchId) {
  activeStatus = status;
  activeSearchId = searchId;

  // Aktive Klassen im Menü aktualisieren
  document.querySelectorAll(".nav-item").forEach(item => item.classList.remove("active"));
  
  if (searchId) {
    const el = document.getElementById(`search-nav-${searchId}`);
    if (el) el.classList.add("active");
  } else {
    const el = document.getElementById(`nav-${status}`);
    if (el) el.classList.add("active");
  }

  updateHeaderInfo();
  loadResults();
}

// --- API Aufrufe & Laden ---

async function loadSearches(showSpinner = true) {
  try {
    const res = await fetch("/api/searches");
    allSearches = await res.json();
    renderSearchesList();
    updateHeaderInfo(); // Aktualisiert Kopfzeile unmittelbar mit neuem Namen, Begriffen & Zeitstempel
  } catch (err) {
    console.error("Fehler beim Laden der Suchen:", err);
  }
}

async function loadResults(showSpinner = true) {
  const container = document.getElementById("results-container");
  if (showSpinner && allResults.length === 0) {
    container.innerHTML = `<div class="empty-state"><div class="empty-state-icon">${getSvgIcon('spinner', 32)}</div><p>${t('loading_results')}</p></div>`;
  }

  const shipping = document.getElementById("filter-shipping").value;
  const minPrice = document.getElementById("filter-min-price").value;
  const maxPrice = document.getElementById("filter-max-price").value;
  const searchTerm = document.getElementById("filter-search-input").value;

  const sortEl = document.getElementById("filter-sort");
  const sortBy = sortEl ? sortEl.value : "newest";

  const params = new URLSearchParams();
  if (activeSearchId) params.append("search_id", activeSearchId);
  if (activeStatus && activeStatus !== "all") params.append("status", activeStatus);
  if (shipping && shipping !== "all") params.append("shipping_filter", shipping);
  if (minPrice) params.append("min_price", minPrice);
  if (maxPrice) params.append("max_price", maxPrice);
  if (searchTerm) params.append("search_term", searchTerm);
  if (sortBy) params.append("sort_by", sortBy);

  try {
    const res = await fetch(`/api/results?${params.toString()}`);
    allResults = await res.json();
    renderResultsGrid();
    loadStats();
  } catch (err) {
    console.error("Fehler beim Laden der Ergebnisse:", err);
    container.innerHTML = `<div class="empty-state"><div class="empty-state-icon">${getSvgIcon('alert', 32)}</div><p>${t('error_results')}</p></div>`;
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
    list.innerHTML = `<div style="padding: 10px; font-size: 12px; color: var(--text-muted); text-align: center;">${t('nav_no_searches')}</div>`;
    return;
  }

  allSearches.forEach(s => {
    const item = document.createElement("div");
    item.className = `nav-item ${activeSearchId === s.id ? "active" : ""}`;
    item.id = `search-nav-${s.id}`;
    
    const statusIcon = s.is_active ? getSvgIcon('dotActive', 10) : getSvgIcon('dotInactive', 10);
    const lastChecked = s.last_run_formatted || t('lbl_never_checked');
    const createdDate = s.created_at_formatted || "";

    item.innerHTML = `
      <span style="display: inline-flex; align-items: center; margin-top: 3px;">${statusIcon}</span>
      <div style="flex: 1; overflow: hidden; min-width: 0;">
        <div style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-weight: 500;">${escapeHtml(s.name)}</div>
        <div class="search-nav-sub" title="${t('lbl_created_at')} ${createdDate} | ${t('lbl_last_checked')} ${lastChecked}">
          ${t('lbl_last_checked')} ${escapeHtml(lastChecked)}
        </div>
      </div>
      <div class="search-item-actions">
        <button class="btn-icon-tiny" title="${currentLang === 'de' ? 'Jetzt ausführen' : 'Run now'}" onclick="runSearchNow(event, ${s.id})">${getSvgIcon('play', 12)}</button>
        <button class="btn-icon-tiny" title="${currentLang === 'de' ? 'Bearbeiten' : 'Edit'}" onclick="editSearch(event, ${s.id})">${getSvgIcon('pencil', 12)}</button>
        <button class="btn-icon-tiny" title="${currentLang === 'de' ? 'Löschen' : 'Delete'}" onclick="confirmDeleteSearch(event, ${s.id})">${getSvgIcon('trash', 12)}</button>
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
        <div class="empty-state-icon">${getSvgIcon('search', 40)}</div>
        <h3>${t('empty_title')}</h3>
        <p>${t('empty_desc')}</p>
      </div>
    `;
    return;
  }

  let html = `<div class="results-grid">`;
  allResults.forEach(r => {
    const isNew = r.status === "new";
    const isStarred = r.status === "starred";
    const starIcon = isStarred ? getSvgIcon('starFilled', 16) : getSvgIcon('star', 16);
    const starTitle = isStarred ? t('card_star_remove') : t('card_star_add');
    const shippingBadge = r.shipping_possible 
      ? `${getSvgIcon('package', 12)} ${t('card_shipping')}` 
      : `${getSvgIcon('mapPin', 12)} ${t('card_pickup')}`;
    const thumb = r.thumbnail_url || "/static/logo.svg";

    const priceHtml = r.price_reduced
      ? `<span style="text-decoration: line-through; opacity: 0.75; font-size: 11px; margin-right: 4px;">${escapeHtml(r.old_price)}</span>${escapeHtml(r.price)} <span style="font-size: 10px; background: rgba(34, 197, 94, 0.35); padding: 1px 4px; border-radius: 4px; font-weight: bold;">${escapeHtml(r.price_diff)}</span>`
      : escapeHtml(r.price || 'VB');

    html += `
      <div class="result-card ${isNew ? 'is-new' : ''}" onclick="openDetailModal(${r.id})">
        <div class="result-image-box">
          <img class="result-image" src="${escapeHtml(thumb)}" alt="${escapeHtml(r.title)}" loading="lazy" onerror="this.src='/static/logo.svg'">
          <div class="result-price-badge">${priceHtml}</div>
          <div class="result-shipping-badge">${shippingBadge}</div>
        </div>

        <div class="result-card-body">
          <div class="result-tags">
            <span class="tag tag-highlight">${escapeHtml(r.search_name || 'Suche')}</span>
            ${r.online_duration ? `<span class="tag" title="${t('lbl_online_since')}">${getSvgIcon('clock', 12)} ${escapeHtml(r.online_duration)}</span>` : ''}
            ${r.price_reduced ? `<span class="tag" style="background: rgba(34, 197, 94, 0.15); color: #16a34a; border-color: rgba(34, 197, 94, 0.3); font-weight: 600;" title="${t('badge_reduced')}">${getSvgIcon('trendingDown', 12)} ${escapeHtml(r.price_diff)}</span>` : ''}
            ${r.ocr_text ? `<span class="tag" title="Text in Fotos gefunden">${getSvgIcon('camera', 12)} ${t('card_image_text')}</span>` : ''}
          </div>

          <div class="result-title" style="cursor: pointer;" onclick="openDetailModal(${r.id})">
            ${escapeHtml(r.title)}
          </div>

          <div class="result-location">
            ${getSvgIcon('mapPin', 12)} ${escapeHtml(r.location || 'Deutschland')}
          </div>

          ${r.description ? `
            <div class="result-desc-snippet" style="font-size: 12px; color: var(--text-secondary); margin: 6px 0; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; line-height: 1.4; cursor: pointer;" onclick="openDetailModal(${r.id})">
              ${escapeHtml(r.description)}
            </div>
          ` : ''}

          ${r.match_reason ? `<div class="result-match-reason">${getSvgIcon('lightbulb', 13)} ${escapeHtml(r.match_reason)}</div>` : ''}

          <div class="result-footer-actions" onclick="event.stopPropagation()">
            <div style="display: flex; gap: 4px;">
              <button class="btn btn-ghost btn-sm" title="${starTitle}" onclick="toggleStar(${r.id}, '${r.status}')">
                ${starIcon}
              </button>
              ${isNew ? `
                <button class="btn btn-ghost btn-sm" title="${t('card_read')}" onclick="setResultStatus(${r.id}, 'read')">
                  ${getSvgIcon('check', 13)} ${t('card_read')}
                </button>
              ` : ''}
              <button class="btn btn-ghost btn-sm" title="${t('card_dismiss')}" onclick="setResultStatus(${r.id}, 'dismissed')">
                ${getSvgIcon('x', 14)}
              </button>
            </div>
            
            <a href="${escapeHtml(r.url)}" target="_blank" class="btn btn-secondary btn-sm" style="text-decoration: none; display: inline-flex; align-items: center; gap: 4px;">
              <span>${t('card_open')}</span>
              ${getSvgIcon('externalLink', 12)}
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

  if (r.status === "new") {
    setResultStatus(r.id, "read", false);
  }

  document.getElementById("detail-title").innerText = r.title;
  document.getElementById("detail-price").innerText = r.price || "K.A.";
  document.getElementById("detail-location").innerText = `${r.location} (${r.shipping_possible ? t('card_shipping') : t('card_pickup')})`;
  document.getElementById("detail-search-name").innerText = r.search_name || "Suchauftrag";
  document.getElementById("detail-match-reason").innerText = r.match_reason || "";
  document.getElementById("detail-link").href = r.url;
  document.getElementById("detail-description").innerText = r.description || t("no_description");

  // Online-Dauer
  const durEl = document.getElementById("detail-online-duration");
  if (durEl) {
    if (r.online_duration) {
      durEl.innerHTML = `${getSvgIcon('clock', 13)} ${t('lbl_online_since')}: ${escapeHtml(r.online_duration)}`;
      durEl.style.display = "block";
    } else {
      durEl.style.display = "none";
    }
  }

  // Preissenkung & Verlauf
  const redEl = document.getElementById("detail-price-reduction");
  if (redEl) {
    if (r.price_reduced) {
      redEl.innerHTML = `${getSvgIcon('trendingDown', 13)} ${t('badge_reduced')}: Vorher <s>${escapeHtml(r.old_price)}</s> (${escapeHtml(r.price_diff)})`;
      redEl.style.display = "block";
    } else {
      redEl.style.display = "none";
    }
  }

  const histBox = document.getElementById("detail-price-history-box");
  const histList = document.getElementById("detail-price-history-list");
  if (histBox && histList) {
    let history = [];
    try {
      if (typeof r.price_history === "string") {
        history = JSON.parse(r.price_history);
      } else if (Array.isArray(r.price_history)) {
        history = r.price_history;
      }
    } catch (e) {
      history = [];
    }
    if (history && history.length > 1) {
      histBox.style.display = "block";
      histList.innerHTML = history.map(item => {
        const d = item.date ? item.date.replace("T", " ") : "";
        return `<div style="display: flex; justify-content: space-between; padding: 2px 0; border-bottom: 1px dashed var(--border-color);">
          <span>${escapeHtml(d)}</span>
          <b>${escapeHtml(item.price)}</b>
        </div>`;
      }).join("");
    } else {
      histBox.style.display = "none";
    }
  }

  // Galerie
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
    gallery.innerHTML = `<span style="font-size: 12px; color: var(--text-muted);">${t('no_images')}</span>`;
  }

  // OCR Box
  const ocrContainer = document.getElementById("detail-ocr-box");
  if (r.ocr_text && r.ocr_text.trim()) {
    ocrContainer.style.display = "block";
    document.getElementById("detail-ocr-text").innerText = r.ocr_text;
  } else {
    ocrContainer.style.display = "none";
  }

  // Falls Beschreibung kurz oder leer ist, Details asynchron nachladen
  if (!r.description || r.description.length < 50 || !r.images || r.images.length <= 1) {
    fetch(`/api/results/${r.id}/details`)
      .then(res => res.json())
      .then(updated => {
        if (updated && selectedResult && selectedResult.id === r.id) {
          if (updated.description) {
            document.getElementById("detail-description").innerText = updated.description;
            r.description = updated.description;
          }
          if (updated.images && updated.images.length > 0) {
            r.images = updated.images;
            gallery.innerHTML = "";
            updated.images.forEach(imgUrl => {
              const img = document.createElement("img");
              img.src = imgUrl;
              img.loading = "lazy";
              img.onclick = () => window.open(imgUrl, "_blank");
              gallery.appendChild(img);
            });
          }
        }
      })
      .catch(() => {});
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
    showToast("Status error", "error");
  }
}

function toggleStar(id, currentStatus) {
  const nextStatus = currentStatus === "starred" ? "read" : "starred";
  setResultStatus(id, nextStatus);
  showToast(nextStatus === "starred" ? t("toast_starred") : t("toast_unstarred"), "success");
}

async function markAllAsRead() {
  try {
    await fetch(`/api/results/mark-all-read${activeSearchId ? `?search_id=${activeSearchId}` : ''}`, {
      method: "POST"
    });
    showToast(t("toast_all_read"), "success");
    loadResults();
  } catch (err) {
    showToast("Error", "error");
  }
}

// --- Suchen verwalten & Multi-Begriff Builder ---

let currentTerms = [];

function renderTermsList() {
  const container = document.getElementById("terms-list-container");
  if (!container) return;
  container.innerHTML = "";

  if (currentTerms.length === 0) {
    container.innerHTML = `<span style="font-size: 12px; color: var(--text-muted); font-style: italic;">${t('no_terms_yet')}</span>`;
    return;
  }

  currentTerms.forEach((term, idx) => {
    const pill = document.createElement("span");
    pill.className = `term-pill ${term.type}`;
    const icon = term.type === "include" ? getSvgIcon("check", 11) : getSvgIcon("x", 11);
    const prefix = term.type === "include" ? "+" : "-";

    pill.innerHTML = `
      ${icon}
      <span>${prefix} ${escapeHtml(term.text)}</span>
      <button type="button" class="btn-remove-term" title="Entfernen" onclick="removeTerm(${idx})">&times;</button>
    `;
    container.appendChild(pill);
  });
}

function addTermFromInput() {
  const input = document.getElementById("term-input");
  const typeSelect = document.getElementById("term-type");
  if (!input || !typeSelect) return;

  const text = input.value.trim();
  const type = typeSelect.value || "include";
  if (!text) return;

  // Verhindern von Duplikaten
  if (!currentTerms.some(t => t.text.toLowerCase() === text.toLowerCase())) {
    currentTerms.push({ text: text, type: type });
    renderTermsList();
    updateLiveCountPreview();
  }

  input.value = "";
  input.focus();
}

function removeTerm(index) {
  if (index >= 0 && index < currentTerms.length) {
    currentTerms.splice(index, 1);
    renderTermsList();
    updateLiveCountPreview();
  }
}

async function updateLiveCountPreview() {
  const box = document.getElementById("live-preview-box");
  const textEl = document.getElementById("live-preview-text");
  const iconEl = document.getElementById("icon-live-preview");
  if (!box || !textEl || !iconEl) return;

  // Suchbegriff für Vorschau ermitteln:
  // Entweder das aktuell im Feld eingetippte Wort (falls 'include')
  // oder der erste/alle Suchbegriffe aus currentTerms
  const typedVal = (document.getElementById("term-input") ? document.getElementById("term-input").value.trim() : "");
  const typedType = document.getElementById("term-type") ? document.getElementById("term-type").value : "include";
  
  const includeTerms = currentTerms.filter(t => t.type === "include").map(t => t.text.trim()).filter(Boolean);
  let allIncludeWords = [...includeTerms];
  if (typedVal && typedType === "include" && !allIncludeWords.some(w => w.toLowerCase() === typedVal.toLowerCase())) {
    allIncludeWords.push(typedVal);
  }
  const rawQuery = allIncludeWords.join(" ");
  const queryForPreview = rawQuery.replace(/[*?]+/g, " ").replace(/\s+/g, " ").trim();

  if (!queryForPreview) {
    box.className = "live-preview-box";
    iconEl.innerHTML = getSvgIcon("search", 14);
    textEl.innerText = t("live_count_prompt");
    return;
  }

  // Ladezustand anzeigen
  box.className = "live-preview-box is-loading";
  iconEl.innerHTML = getSvgIcon("spinner", 14);
  textEl.innerText = t("live_count_loading");

  const minPrice = document.getElementById("s-min-price") ? document.getElementById("s-min-price").value.trim() : "";
  const maxPrice = document.getElementById("s-max-price") ? document.getElementById("s-max-price").value.trim() : "";
  const plz = document.getElementById("s-plz") ? document.getElementById("s-plz").value.trim() : "";
  const radius = document.getElementById("s-radius") ? document.getElementById("s-radius").value : "0";

  const params = new URLSearchParams();
  params.append("query", queryForPreview);
  if (minPrice) params.append("min_price", minPrice);
  if (maxPrice) params.append("max_price", maxPrice);
  if (plz) params.append("postal_code", plz);
  if (radius && radius !== "0") params.append("radius", radius);

  try {
    const res = await fetch(`/api/searches/preview-count?${params.toString()}`);
    const data = await res.json();
    const count = data.count || 0;

    box.className = "live-preview-box";
    if (count > 0) {
      box.classList.add("has-results");
      iconEl.innerHTML = getSvgIcon("search", 14);
      const formatted = count.toLocaleString(currentLang === "de" ? "de-DE" : "en-US");
      textEl.innerText = t("live_count_results").replace("{count}", formatted);
    } else {
      iconEl.innerHTML = getSvgIcon("alert", 14);
      textEl.innerText = t("live_count_zero");
    }
  } catch (err) {
    box.className = "live-preview-box";
    iconEl.innerHTML = getSvgIcon("alert", 14);
    textEl.innerText = t("live_count_zero");
  }
}

function openSearchModal(searchData = null) {
  const form = document.getElementById("search-form");
  form.reset();

  const timeBox = document.getElementById("search-timestamps-info");
  const sCreatedAt = document.getElementById("s-created-at-text");
  const sLastRun = document.getElementById("s-last-run-text");

  if (searchData) {
    document.getElementById("search-modal-title").innerText = t("modal_search_edit_title");
    document.getElementById("search-id-input").value = searchData.id;
    document.getElementById("s-name").value = searchData.name || "";

    if (timeBox && sCreatedAt && sLastRun) {
      timeBox.style.display = "flex";
      sCreatedAt.innerText = searchData.created_at_formatted || "-";
      sLastRun.innerText = searchData.last_run_formatted || t("lbl_never_checked");
    }

    currentTerms = Array.isArray(searchData.terms) ? JSON.parse(JSON.stringify(searchData.terms)) : [];
    if (currentTerms.length === 0 && searchData.query) {
      currentTerms.push({ text: searchData.query, type: "include" });
    }

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
    document.getElementById("search-modal-title").innerText = t("modal_search_new_title");
    document.getElementById("search-id-input").value = "";
    if (timeBox) timeBox.style.display = "none";
    currentTerms = [];

    document.getElementById("s-interval").value = 15;
    document.getElementById("s-search-in-desc").checked = true;
    document.getElementById("s-ocr-images").checked = true;
    document.getElementById("s-notify-telegram").checked = true;
    document.getElementById("s-notify-email").checked = true;
    document.getElementById("s-is-active").checked = true;
  }

  renderTermsList();
  const termInput = document.getElementById("term-input");
  if (termInput) termInput.value = "";
  updateLiveCountPreview();

  openModal("modal-search");
}

async function editSearch(event, id) {
  event.stopPropagation();
  const s = allSearches.find(x => x.id === id);
  if (s) openSearchModal(s);
}

function pollForResults(searchId) {
  let attempts = 0;
  const maxAttempts = 12;
  const interval = setInterval(async () => {
    attempts++;
    await loadSearches(false);
    await loadResults(false);
    loadStats();
    if (allResults.length > 0 || attempts >= maxAttempts) {
      clearInterval(interval);
    }
  }, 1200);
}

async function runSearchNow(event, id) {
  event.stopPropagation();
  showToast(t("toast_search_triggered"), "success");
  if (activeSearchId === id) {
    allResults = [];
    const container = document.getElementById("results-container");
    if (container) {
      container.innerHTML = `
        <div class="loading-state" style="padding: 40px; text-align: center; color: var(--text-muted);">
          <div class="spinner"></div>
          <p style="margin-top: 12px;">${t("live_count_loading") || "Lade aktuelle Treffer..."}</p>
        </div>
      `;
    }
  }
  try {
    await fetch(`/api/searches/${id}/run`, { method: "POST" });
    pollForResults(id);
  } catch (err) {
    showToast("Error", "error");
  }
}

async function confirmDeleteSearch(event, id) {
  event.stopPropagation();
  if (confirm(t("confirm_delete_search"))) {
    try {
      await fetch(`/api/searches/${id}`, { method: "DELETE" });
      showToast(t("toast_search_deleted"), "success");
      if (activeSearchId === id) {
        setNavFilter("all", null);
      }
      loadSearches();
      loadResults();
    } catch (err) {
      showToast("Error", "error");
    }
  }
}

async function handleSearchFormSubmit(e) {
  e.preventDefault();

  // Falls der Nutzer im Begriff-Eingabefeld noch etwas stehen hat, automatisch hinzufügen
  const termInput = document.getElementById("term-input");
  if (termInput && termInput.value.trim()) {
    addTermFromInput();
  }

  // Prüfen, ob mindestens ein Suchbegriff hinterlegt wurde
  const hasInclude = currentTerms.some(t => t.type === "include" && t.text.trim());
  if (!hasInclude) {
    showToast(t("no_terms_yet"), "error");
    return;
  }

  const id = document.getElementById("search-id-input").value;
  const includeTerms = currentTerms.filter(t => t.type === "include").map(t => t.text.trim());
  const excludeTerms = currentTerms.filter(t => t.type === "exclude").map(t => `-${t.text.trim()}`);

  const payload = {
    name: document.getElementById("s-name").value.trim(),
    query: includeTerms[0] || "",
    keywords: includeTerms.slice(1).concat(excludeTerms).join(", "),
    terms: currentTerms,
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
    let targetSearchId = id;
    if (id) {
      await fetch(`/api/searches/${id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      showToast(t("toast_search_saved"), "success");
    } else {
      const res = await fetch("/api/searches", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      targetSearchId = data.id;
      showToast(t("toast_search_created"), "success");
    }

    closeModal("modal-search");
    allResults = [];
    const container = document.getElementById("results-container");
    if (container) {
      container.innerHTML = `
        <div class="loading-state" style="padding: 40px; text-align: center; color: var(--text-muted);">
          <div class="spinner"></div>
          <p style="margin-top: 12px;">${t("live_count_loading") || "Lade aktuelle Treffer..."}</p>
        </div>
      `;
    }
    await loadSearches();
    if (targetSearchId) {
      setNavFilter(null, parseInt(targetSearchId));
      pollForResults(parseInt(targetSearchId));
    } else {
      loadResults();
    }
  } catch (err) {
    showToast("Error saving monitor", "error");
  }
}

function applyEmailPreset(presetKey) {
  const hostEl = document.getElementById("cfg-email-host");
  const portEl = document.getElementById("cfg-email-port");
  const encEl = document.getElementById("cfg-email-encryption");

  if (presetKey === "netcup_465") {
    if (hostEl) hostEl.value = "mxe81b.netcup.net";
    if (portEl) portEl.value = "465";
    if (encEl) encEl.value = "ssl";
  } else if (presetKey === "netcup_587") {
    if (hostEl) hostEl.value = "mxe81b.netcup.net";
    if (portEl) portEl.value = "587";
    if (encEl) encEl.value = "starttls";
  } else if (presetKey === "gmail") {
    if (hostEl) hostEl.value = "smtp.gmail.com";
    if (portEl) portEl.value = "587";
    if (encEl) encEl.value = "starttls";
  } else if (presetKey === "outlook") {
    if (hostEl) hostEl.value = "smtp.office365.com";
    if (portEl) portEl.value = "587";
    if (encEl) encEl.value = "starttls";
  } else if (presetKey === "gmx") {
    if (hostEl) hostEl.value = "mail.gmx.net";
    if (portEl) portEl.value = "587";
    if (encEl) encEl.value = "starttls";
  } else if (presetKey === "webde") {
    if (hostEl) hostEl.value = "smtp.web.de";
    if (portEl) portEl.value = "587";
    if (encEl) encEl.value = "starttls";
  } else if (presetKey === "ionos") {
    if (hostEl) hostEl.value = "smtp.ionos.de";
    if (portEl) portEl.value = "465";
    if (encEl) encEl.value = "ssl";
  } else if (presetKey === "strato") {
    if (hostEl) hostEl.value = "smtp.strato.de";
    if (portEl) portEl.value = "465";
    if (encEl) encEl.value = "ssl";
  }
}

function handlePortChange(port) {
  const encEl = document.getElementById("cfg-email-encryption");
  if (!encEl) return;
  if (port == 465) {
    encEl.value = "ssl";
  } else if (port == 587) {
    encEl.value = "starttls";
  } else if (port == 25) {
    encEl.value = "none";
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
    document.getElementById("cfg-email-port").value = settings.email_smtp_port || "465";
    document.getElementById("cfg-email-user").value = settings.email_smtp_user || "";
    document.getElementById("cfg-email-password").value = "";
    document.getElementById("cfg-email-password").placeholder = settings.email_smtp_password_masked ? t("ph_password_unchanged") : "";
    document.getElementById("cfg-email-from").value = settings.email_from || "";
    document.getElementById("cfg-email-to").value = settings.email_to || "";
    document.getElementById("cfg-github-repo").value = settings.github_repo || "loe17/KleinanzeigenRadar";

    // Verschlüsselungsauswahl setzen
    const encEl = document.getElementById("cfg-email-encryption");
    if (encEl) {
      const tlsVal = String(settings.email_smtp_tls || "").toLowerCase();
      const portVal = String(settings.email_smtp_port || "");
      if (tlsVal === "ssl" || portVal === "465" || (tlsVal === "1" && portVal === "465")) {
        encEl.value = "ssl";
      } else if (tlsVal === "0" || tlsVal === "false" || tlsVal === "none") {
        encEl.value = "none";
      } else {
        encEl.value = "starttls";
      }
    }

    // Vorlage ermitteln
    const presetEl = document.getElementById("cfg-email-preset");
    if (presetEl) {
      const host = (settings.email_smtp_host || "").toLowerCase();
      const port = String(settings.email_smtp_port || "");
      if (host.includes("netcup") && port === "465") {
        presetEl.value = "netcup_465";
      } else if (host.includes("netcup") && port === "587") {
        presetEl.value = "netcup_587";
      } else if (host.includes("gmail")) {
        presetEl.value = "gmail";
      } else if (host.includes("office365") || host.includes("outlook")) {
        presetEl.value = "outlook";
      } else if (host.includes("gmx")) {
        presetEl.value = "gmx";
      } else if (host.includes("web.de")) {
        presetEl.value = "webde";
      } else if (host.includes("ionos") || host.includes("1und1")) {
        presetEl.value = "ionos";
      } else if (host.includes("strato")) {
        presetEl.value = "strato";
      } else {
        presetEl.value = "custom";
      }
    }

    const progressCard = document.getElementById("update-progress-card");
    if (progressCard) progressCard.style.display = "none";
    const btnPerform = document.getElementById("btn-perform-update");
    if (btnPerform) {
      btnPerform.disabled = false;
      btnPerform.style.display = "none";
    }
    const btnCheck = document.getElementById("btn-check-update");
    if (btnCheck) btnCheck.disabled = false;

    openModal("modal-settings");
  } catch (err) {
    showToast("Settings error", "error");
  }
}

async function handleSettingsFormSubmit(e) {
  e.preventDefault();
  const encEl = document.getElementById("cfg-email-encryption");
  const encVal = encEl ? encEl.value : "ssl";

  const payload = {
    telegram_bot_token: document.getElementById("cfg-telegram-token").value.trim(),
    telegram_chat_id: document.getElementById("cfg-telegram-chat-id").value.trim(),
    email_smtp_host: document.getElementById("cfg-email-host").value.trim(),
    email_smtp_port: document.getElementById("cfg-email-port").value.trim(),
    email_smtp_user: document.getElementById("cfg-email-user").value.trim(),
    email_smtp_tls: encVal,
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
    showToast(t("toast_settings_saved"), "success");
    closeModal("modal-settings");
  } catch (err) {
    showToast("Error saving settings", "error");
  }
}

async function testTelegram() {
  const token = document.getElementById("cfg-telegram-token").value.trim();
  const chatId = document.getElementById("cfg-telegram-chat-id").value.trim();
  showToast("Testing Telegram...", "info");

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
    showToast("Network error", "error");
  }
}

async function testEmail() {
  const encEl = document.getElementById("cfg-email-encryption");
  const encVal = encEl ? encEl.value : "ssl";

  const payload = {
    email_smtp_host: document.getElementById("cfg-email-host").value.trim(),
    email_smtp_port: document.getElementById("cfg-email-port").value.trim(),
    email_smtp_user: document.getElementById("cfg-email-user").value.trim(),
    email_smtp_tls: encVal,
    email_from: document.getElementById("cfg-email-from").value.trim(),
    email_to: document.getElementById("cfg-email-to").value.trim()
  };
  const pass = document.getElementById("cfg-email-password").value;
  if (pass) payload.email_smtp_password = pass;

  showToast("Testing Email...", "info");
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
    showToast("Network error", "error");
  }
}

async function checkUpdate() {
  const statusEl = document.getElementById("update-status-msg");
  statusEl.innerText = t("status_checking_update");
  try {
    const res = await fetch("/api/system/update/check");
    const data = await res.json();
    if (data.error) {
      statusEl.innerHTML = `<span style="color: #ef4444;">${escapeHtml(data.error)}</span>`;
    } else if (data.update_available) {
      statusEl.innerHTML = `
        <span style="color: #86b817; font-weight: bold;">${t('status_update_avail')} v${escapeHtml(data.latest_version)}</span>
        <p style="font-size: 11.5px; margin-top: 4px; color: var(--text-secondary);">${escapeHtml(data.release_notes)}</p>
      `;
      document.getElementById("btn-perform-update").style.display = "inline-flex";
    } else {
      statusEl.innerHTML = `<span style="color: #10b981;">${t('status_up_to_date')} (v${escapeHtml(data.current_version)}).</span>`;
      document.getElementById("btn-perform-update").style.display = "inline-flex";
    }
  } catch (err) {
    statusEl.innerText = "Error checking updates.";
  }
}

async function performUpdate() {
  const btnPerform = document.getElementById("btn-perform-update");
  const btnCheck = document.getElementById("btn-check-update");
  const progressCard = document.getElementById("update-progress-card");
  const progressBar = document.getElementById("update-progress-bar");
  const progressPercent = document.getElementById("update-progress-percent");
  const progressStatus = document.getElementById("update-progress-status");
  const statusEl = document.getElementById("update-status-msg");

  if (btnPerform) btnPerform.disabled = true;
  if (btnCheck) btnCheck.disabled = true;

  if (progressCard) {
    progressCard.style.display = "block";
    progressCard.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  function setProgress(pct, statusText) {
    if (progressBar) progressBar.style.width = pct + "%";
    if (progressPercent) progressPercent.innerText = pct + "%";
    if (progressStatus) progressStatus.innerText = statusText;
  }

  setProgress(15, t("update_downloading"));

  let updateSuccess = false;
  let updateData = null;

  try {
    setTimeout(() => {
      if (!updateSuccess && progressBar && parseInt(progressBar.style.width) < 40) {
        setProgress(35, t("update_downloading"));
      }
    }, 700);

    const res = await fetch("/api/system/update/perform", { method: "POST" });
    updateData = await res.json();
    updateSuccess = updateData && updateData.success;
  } catch (err) {
    updateSuccess = false;
    updateData = { message: "Netzwerkfehler beim Abrufen des Updates." };
  }

  if (!updateSuccess) {
    setProgress(100, t("update_failed") + (updateData ? updateData.message : ""));
    if (progressBar) progressBar.style.background = "#ef4444";
    if (btnPerform) btnPerform.disabled = false;
    if (btnCheck) btnCheck.disabled = false;
    showToast((updateData && updateData.message) || "Update fehlgeschlagen", "error");
    return;
  }

  // Update erfolgreich heruntergeladen
  setProgress(60, t("update_restarting"));
  showToast(t("toast_update_started"), "success");

  // Animiere weiter zu 80% während der Server herunterfährt und neu startet
  setTimeout(() => {
    setProgress(80, t("update_waiting_server"));
  }, 1600);

  // Poll den Server, bis er wieder antwortet
  let attempts = 0;
  const maxAttempts = 35; // max 35 Sekunden
  let reloaded = false;

  setTimeout(() => {
    const pollInterval = setInterval(async () => {
      attempts++;
      try {
        const pingRes = await fetch(`/api/system/version?t=${Date.now()}`, { cache: "no-store" });
        if (pingRes.ok && !reloaded) {
          reloaded = true;
          clearInterval(pollInterval);
          setProgress(100, t("update_finished"));
          setTimeout(() => {
            window.location.reload();
          }, 800);
          return;
        }
      } catch (e) {
        // Server startet gerade neu, Fehler ist hier normal
      }

      if (attempts >= maxAttempts && !reloaded) {
        reloaded = true;
        clearInterval(pollInterval);
        setProgress(100, t("update_reload_prompt"));
        setTimeout(() => {
          window.location.reload();
        }, 1500);
      }
    }, 1000);
  }, 2200);
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
