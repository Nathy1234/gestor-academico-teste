// ── THEME ────────────────────────────────────────────────────────
function toggleTheme() {
  const html = document.documentElement;
  const next = html.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
  html.setAttribute('data-theme', next);
  localStorage.setItem('theme', next);
}

// ── GLOBAL SEARCH ────────────────────────────────────────────────
const searchInput = document.getElementById('globalSearch');
const searchResults = document.getElementById('searchResults');

if (searchInput) {
  let timer;
  searchInput.addEventListener('input', () => {
    clearTimeout(timer);
    const q = searchInput.value.trim();
    if (q.length < 2) { closeSearch(); return; }
    timer = setTimeout(() => fetchSearch(q), 250);
  });
  document.addEventListener('click', e => {
    if (!searchInput.closest('.search-bar').contains(e.target)) closeSearch();
  });
}

function fetchSearch(q) {
  fetch(`/api/busca?q=${encodeURIComponent(q)}`)
    .then(r => r.json())
    .then(data => {
      if (!data.length) { closeSearch(); return; }
      searchResults.innerHTML = data.map(c => `
        <a href="/cursos/${c.id}" class="search-item">
          <div>
            <div class="search-item-name">${c.nome}</div>
            <div class="search-item-meta">${tipoLabel(c.tipo)} · <span class="badge badge-${c.status}" style="font-size:10px;padding:1px 6px">${c.status}</span></div>
          </div>
        </a>
      `).join('');
      searchResults.classList.add('open');
    });
}

function closeSearch() { searchResults.classList.remove('open'); searchResults.innerHTML = ''; }

function tipoLabel(t) {
  const m = {
    pos:'Pós-Graduação', profissionalizante:'Profissionalizante', rapido:'Rápido',
    pacote:'Pacote', terceiros:'Terceiros', evento:'Evento',
    pratica_conectada:'Prática Conectada', pratica_estagio:'Prática Estágio',
    projeto_ambiental:'Proj. Ambiental', ggbr:'GGBR', integra_edu:'Integra Edu'
  };
  return m[t] || t;
}

// ── MATRIX EDITOR ────────────────────────────────────────────────
let disciplines = [];

function initMatrix(existing) {
  disciplines = existing && existing.length ? existing : [];
  renderMatrix();
}

function renderMatrix() {
  const tbody = document.getElementById('matrixBody');
  if (!tbody) return;
  tbody.innerHTML = disciplines.map((d, i) => `
    <div class="matrix-row">
      <input type="text" value="${d.modulo||''}" placeholder="Mód. 01" oninput="updateDisc(${i},'modulo',this.value)">
      <input type="number" value="${d.ordem||i+1}" placeholder="#" oninput="updateDisc(${i},'ordem',this.value)">
      <input type="text" value="${d.nome||''}" placeholder="Nome da disciplina" oninput="updateDisc(${i},'nome',this.value)">
      <input type="text" value="${d.carga||''}" placeholder="30h" oninput="updateDisc(${i},'carga',this.value)">
      <input type="text" value="${d.professor||''}" placeholder="Professor" oninput="updateDisc(${i},'professor',this.value)">
      <input type="text" value="${d.titulacao||''}" placeholder="MSc" oninput="updateDisc(${i},'titulacao',this.value)">
      <button type="button" class="btn-del-row" onclick="removeDisc(${i})" title="Remover linha">
        <svg viewBox="0 0 24 24"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14H6L5 6"/><path d="M10 11v6M14 11v6"/><path d="M9 6V4h6v2"/></svg>
      </button>
    </div>
  `).join('');
  updateHidden();
}

function updateDisc(i, key, val) { disciplines[i][key] = val; updateHidden(); }
function removeDisc(i) { disciplines.splice(i, 1); renderMatrix(); }

function addDisc() {
  disciplines.push({ modulo:'', ordem: disciplines.length + 1, nome:'', carga:'', professor:'', titulacao:'' });
  renderMatrix();
  document.getElementById('matrixBody')?.lastElementChild?.scrollIntoView({ behavior:'smooth', block:'nearest' });
}

function updateHidden() {
  const h = document.getElementById('disciplinas_json');
  if (h) h.value = JSON.stringify(disciplines);
}

// ── CONFIRM ACTIONS ──────────────────────────────────────────────
document.addEventListener('click', e => {
  const btn = e.target.closest('[data-confirm]');
  if (!btn) return;
  if (!confirm(btn.dataset.confirm)) e.preventDefault();
});

// ── AUTO-DISMISS ALERTS ──────────────────────────────────────────
document.querySelectorAll('.alert').forEach(a => {
  a.style.transition = 'opacity .5s';
  setTimeout(() => a.style.opacity = '0', 3500);
  setTimeout(() => a.remove(), 4000);
});
