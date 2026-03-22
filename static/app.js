let listings = [];
let selected = new Set();
let lastRunId = null;
let pollInterval = null;
let filterDebounce = null;
let activeSite = 'all';

// ---------------------------------------------------------------------------
// Data fetching
// ---------------------------------------------------------------------------

function _getSelectedOptions(selectId) {
  const el = document.getElementById(selectId);
  if (!el) return [];
  return Array.from(el.selectedOptions)
    .map(o => o.value)
    .filter(v => v !== '');
}

function _buildFilterParams() {
  const params = new URLSearchParams();
  const keyword = (document.getElementById('f-keyword')?.value || '').trim();
  if (keyword) params.set('keyword', keyword);

  const labels = _getSelectedOptions('f-label');
  if (labels.length) params.set('label', labels.join(','));

  const sizes = _getSelectedOptions('f-size');
  if (sizes.length) params.set('sizes', sizes.join(','));

  const brands = _getSelectedOptions('f-brand');
  if (brands.length) params.set('brands', brands.join(','));

  const conditions = _getSelectedOptions('f-condition');
  if (conditions.length) params.set('conditions', conditions.join(','));

  const priceMax = (document.getElementById('f-price-max')?.value || '').trim();
  if (priceMax) params.set('price_max', priceMax);

  return params;
}

function _filtersActive() {
  const params = _buildFilterParams();
  return params.toString() !== '';
}

async function fetchListings() {
  const params = _buildFilterParams();
  const url = '/api/listings' + (params.toString() ? '?' + params.toString() : '');
  const res = await fetch(url);
  listings = await res.json();
  const countEl = document.getElementById('filter-count');
  if (countEl) {
    countEl.textContent = _filtersActive()
      ? `${listings.length} listing(s) matching filters`
      : `${listings.length} listing(s)`;
  }
  renderListings();
}

async function fetchFilterOptions() {
  try {
    const res = await fetch('/api/filter-options');
    const data = await res.json();
    _populateSelect('f-label',     data.labels     || []);
    _populateSelect('f-size',      data.sizes      || []);
    _populateSelect('f-brand',     data.brands     || []);
    _populateSelect('f-condition', data.conditions || []);
  } catch (e) {
    // non-fatal: filter dropdowns just stay empty
  }
}

function _populateSelect(id, values) {
  const el = document.getElementById(id);
  if (!el) return;
  // Keep first "All …" option, replace the rest
  while (el.options.length > 1) el.remove(1);
  for (const v of values) {
    const opt = document.createElement('option');
    opt.value = v;
    opt.textContent = v;
    el.appendChild(opt);
  }
}

async function fetchStatus() {
  const res = await fetch('/api/status');
  const data = await res.json();
  if (data.last_run) {
    lastRunId = data.last_run.id;
    const ts = data.last_run.finished_at || data.last_run.started_at;
    const count = data.last_run.new_count ?? 0;
    document.getElementById('status-bar').textContent =
      `Last scrape: ${ts} — ${count} new listing(s) found.`;
  }
}

async function runScrape() {
  const res = await fetch('/api/scrape', { method: 'POST' });
  const data = await res.json();
  if (data.status === 'busy') {
    document.getElementById('status-bar').textContent = 'Scrape already in progress.';
    return;
  }
  document.getElementById('status-bar').textContent = 'Scrape started — checking for new listings…';
  startPolling();
}

async function markReviewed() {
  const ids = [...selected];
  await fetch('/api/listings/reviewed', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ids }),
  });
  listings = listings.filter(l => !selected.has(l.id));
  selected.clear();
  renderListings();
}

// ---------------------------------------------------------------------------
// Polling
// ---------------------------------------------------------------------------

function startPolling() {
  if (pollInterval) return;
  pollInterval = setInterval(async () => {
    const res = await fetch('/api/status');
    const data = await res.json();
    if (data.last_run && data.last_run.id !== lastRunId) {
      clearInterval(pollInterval);
      pollInterval = null;
      lastRunId = data.last_run.id;
      const ts = data.last_run.finished_at || data.last_run.started_at;
      const count = data.last_run.new_count ?? 0;
      document.getElementById('status-bar').textContent =
        `Last scrape: ${ts} — ${count} new listing(s) found.`;
      fetchListings();
    }
  }, 5000);
}

// ---------------------------------------------------------------------------
// Actions
// ---------------------------------------------------------------------------

function openSelected() {
  if (selected.size > 1) {
    document.getElementById('popup-warning').hidden = false;
  }
  for (const id of selected) {
    const listing = listings.find(l => l.id === id);
    if (listing) {
      window.open(listing.listing_url, '_blank');
    }
  }
}

// ---------------------------------------------------------------------------
// Rendering
// ---------------------------------------------------------------------------

function renderTabs() {
  const tabBar = document.getElementById('site-tabs');
  const sites = [...new Set(listings.map(l => l.site).filter(Boolean))].sort();

  // Only show tabs when there are listings from more than one site
  if (sites.length <= 1) {
    tabBar.hidden = true;
    return;
  }

  // If the active site was filtered away (e.g. all reviewed), fall back to All
  if (activeSite !== 'all' && !sites.includes(activeSite)) {
    activeSite = 'all';
  }

  tabBar.hidden = false;
  tabBar.innerHTML = '';

  const allBtn = document.createElement('button');
  allBtn.textContent = `All (${listings.length})`;
  allBtn.className = 'tab-btn' + (activeSite === 'all' ? ' active' : '');
  allBtn.addEventListener('click', () => { activeSite = 'all'; renderListings(); });
  tabBar.appendChild(allBtn);

  for (const site of sites) {
    const count = listings.filter(l => l.site === site).length;
    const label = site.charAt(0).toUpperCase() + site.slice(1);
    const btn = document.createElement('button');
    btn.textContent = `${label} (${count})`;
    btn.className = 'tab-btn' + (activeSite === site ? ' active' : '');
    btn.addEventListener('click', () => { activeSite = site; renderListings(); });
    tabBar.appendChild(btn);
  }
}

function renderListings() {
  const container = document.getElementById('listings-container');
  const emptyState = document.getElementById('empty-state');
  container.innerHTML = '';

  renderTabs();

  const visible = activeSite === 'all'
    ? listings
    : listings.filter(l => l.site === activeSite);

  if (visible.length === 0) {
    emptyState.hidden = false;
  } else {
    emptyState.hidden = true;
    for (const listing of visible) {
      const card = createCard(listing);
      container.appendChild(card);
    }
  }
  updateFooter();
}

function createCard(listing) {
  const card = document.createElement('div');
  card.className = 'listing-card' + (selected.has(listing.id) ? ' selected' : '');

  // Checkbox
  const checkbox = document.createElement('input');
  checkbox.type = 'checkbox';
  checkbox.dataset.id = listing.id;
  checkbox.checked = selected.has(listing.id);
  checkbox.addEventListener('change', () => {
    if (checkbox.checked) {
      selected.add(listing.id);
      card.classList.add('selected');
    } else {
      selected.delete(listing.id);
      card.classList.remove('selected');
    }
    updateFooter();
  });
  card.appendChild(checkbox);

  // Image
  const imgDiv = document.createElement('div');
  imgDiv.className = 'listing-image';
  if (listing.image_url) {
    const img = document.createElement('img');
    img.src = listing.image_url;
    img.alt = listing.title || '';
    imgDiv.appendChild(img);
  } else {
    const placeholder = document.createElement('div');
    placeholder.className = 'img-placeholder';
    placeholder.textContent = 'No image';
    imgDiv.appendChild(placeholder);
  }
  card.appendChild(imgDiv);

  // Info
  const info = document.createElement('div');
  info.className = 'listing-info';

  const title = document.createElement('h3');
  title.textContent = listing.title || '(no title)';
  info.appendChild(title);

  const size = document.createElement('span');
  size.className = 'listing-size';
  size.textContent = `Size: ${listing.size ?? '—'}`;
  info.appendChild(size);

  const price = document.createElement('span');
  price.className = 'listing-price';
  price.textContent = listing.price ?? '—';
  info.appendChild(price);

  const label = document.createElement('span');
  label.className = 'listing-label';
  const siteName = listing.site
    ? listing.site.charAt(0).toUpperCase() + listing.site.slice(1)
    : '';
  label.innerHTML = `${listing.label || ''}<br><span class="listing-label-site">${siteName}</span>`;
  info.appendChild(label);

  const link = document.createElement('a');
  link.href = listing.listing_url;
  link.target = '_blank';
  link.rel = 'noopener';
  link.textContent = 'View listing ↗';
  info.appendChild(link);

  card.appendChild(info);
  return card;
}

function updateFooter() {
  document.getElementById('selected-count').textContent = `${selected.size} selected`;
  const hasSelection = selected.size > 0;
  document.getElementById('btn-open').disabled = !hasSelection;
  document.getElementById('btn-reviewed').disabled = !hasSelection;
}

// ---------------------------------------------------------------------------
// Init
// ---------------------------------------------------------------------------

document.addEventListener('DOMContentLoaded', () => {
  fetchStatus();
  fetchListings().then(() => fetchFilterOptions());

  document.getElementById('btn-close-warning').addEventListener('click', () => {
    document.getElementById('popup-warning').hidden = true;
  });

  // Keyword — debounced 300 ms
  document.getElementById('f-keyword')?.addEventListener('input', () => {
    clearTimeout(filterDebounce);
    filterDebounce = setTimeout(fetchListings, 300);
  });

  // Price max — debounced 500 ms
  document.getElementById('f-price-max')?.addEventListener('input', () => {
    clearTimeout(filterDebounce);
    filterDebounce = setTimeout(fetchListings, 500);
  });

  // Multi-selects — immediate
  for (const id of ['f-label', 'f-size', 'f-brand', 'f-condition']) {
    document.getElementById(id)?.addEventListener('change', fetchListings);
  }

  // Clear filters
  document.getElementById('btn-clear-filters')?.addEventListener('click', () => {
    document.getElementById('f-keyword').value = '';
    document.getElementById('f-price-max').value = '';
    for (const id of ['f-label', 'f-size', 'f-brand', 'f-condition']) {
      const el = document.getElementById(id);
      if (el) Array.from(el.options).forEach(o => o.selected = false);
    }
    fetchListings();
  });
});
