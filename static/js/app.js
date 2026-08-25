// ── NOTIFICAÇÕES ─────────────────────────────────────────────────
function toggleNotif(event) {
  if (event) event.stopPropagation();
  const d = document.getElementById('notifDropdown');
  if (!d) return;
  if (d.style.display === 'none' || !d.style.display) {
    const btn = document.getElementById('notifBtn');
    const rect = btn.getBoundingClientRect();
    d.style.top = (rect.bottom + 8) + 'px';
    d.style.right = (window.innerWidth - rect.right) + 'px';
    d.style.left = 'auto';
    d.style.display = 'block';
  } else {
    d.style.display = 'none';
  }
}
document.addEventListener('click', e => {
  const d = document.getElementById('notifDropdown');
  const btn = document.getElementById('notifBtn');
  if (d && btn && !btn.contains(e.target) && !d.contains(e.target)) {
    d.style.display = 'none';
  }
});

// ── SEÇÕES RECOLHÍVEIS DO MENU LATERAL ──────────────────────────────
// Preferência pessoal de cada um (não é permissão nem ordem) — fica salva
// só neste navegador. Por padrão a seção que contém a página atual já
// abre expandida, as outras ficam fechadas, pra poluir menos a tela.
function toggleSidebarSection(header) {
  const bloco = header.closest('.sidebar-section-block');
  if (!bloco) return;
  const items = bloco.querySelector('.sidebar-section-items');
  const chevron = header.querySelector('.section-chevron');
  const abrir = items.classList.contains('is-collapsed');
  items.classList.toggle('is-collapsed', !abrir);
  if (chevron) chevron.classList.toggle('is-open', abrir);
  const id = bloco.dataset.sectionId;
  if (id) localStorage.setItem('navSecaoAberta_' + id, abrir ? '1' : '0');
}

document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.sidebar-section-block').forEach(bloco => {
    const id = bloco.dataset.sectionId;
    const items = bloco.querySelector('.sidebar-section-items');
    const chevron = bloco.querySelector('.section-chevron');
    if (!items || !id) return;
    const temPaginaAtual = !!items.querySelector('.nav-item.active');
    const salvo = localStorage.getItem('navSecaoAberta_' + id);
    const abrir = salvo !== null ? salvo === '1' : temPaginaAtual;
    items.classList.toggle('is-collapsed', !abrir);
    if (chevron) chevron.classList.toggle('is-open', abrir);
  });
});

// ── ORDEM DAS SEÇÕES DO MENU LATERAL ────────────────────────────────
// A ordem é global (escolhida pelo admin, salva no servidor) — todo mundo
// vê nessa ordem; só o admin pode arrastar pra mudar.
(function() {
  const container = document.getElementById('sidebarSections');
  if (!container) return;
  const ordemSalva = window.SIDEBAR_ORDEM || [];
  const ehAdmin = window.SIDEBAR_IS_ADMIN === true;

  if (ordemSalva.length) {
    const blocos = {};
    container.querySelectorAll('.sidebar-section-block').forEach(b => { blocos[b.dataset.sectionId] = b; });
    ordemSalva.forEach(id => { if (blocos[id]) container.appendChild(blocos[id]); });
  }

  if (!ehAdmin) return;

  let arrastando = null;
  container.querySelectorAll('.sidebar-section-block[draggable="true"]').forEach(bloco => {
    bloco.addEventListener('dragstart', () => {
      arrastando = bloco;
      bloco.classList.add('section-dragging');
    });
    bloco.addEventListener('dragend', () => {
      bloco.classList.remove('section-dragging');
      container.querySelectorAll('.section-drop-target').forEach(b => b.classList.remove('section-drop-target'));
      arrastando = null;
      salvarOrdemSidebar();
    });
    bloco.addEventListener('dragover', e => {
      e.preventDefault();
      if (!arrastando || arrastando === bloco) return;
      container.querySelectorAll('.section-drop-target').forEach(b => b.classList.remove('section-drop-target'));
      bloco.classList.add('section-drop-target');
    });
    bloco.addEventListener('dragleave', () => bloco.classList.remove('section-drop-target'));
    bloco.addEventListener('drop', e => {
      e.preventDefault();
      bloco.classList.remove('section-drop-target');
      if (!arrastando || arrastando === bloco) return;
      const todos = Array.from(container.querySelectorAll('.sidebar-section-block'));
      const posArrastando = todos.indexOf(arrastando);
      const posAlvo = todos.indexOf(bloco);
      if (posArrastando < posAlvo) bloco.after(arrastando);
      else bloco.before(arrastando);
    });
  });

  function salvarOrdemSidebar() {
    const ordem = Array.from(container.querySelectorAll('.sidebar-section-block')).map(b => b.dataset.sectionId);
    fetch('/api/sidebar-ordem', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ order: ordem }),
    });
  }
})();

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
            <div class="search-item-name">
              ${c.nome}
              <span style="font-size:9px;font-weight:700;letter-spacing:.04em;color:var(--primary);
                           background:var(--primary-light);padding:1px 6px;border-radius:10px;margin-left:6px">${c.categoria}</span>
            </div>
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
function removeDisc(i) {
  const d = disciplines[i];
  if (d && d.nome && d.nome.trim() && !confirm(`Remover a disciplina "${d.nome}"?`)) return;
  disciplines.splice(i, 1);
  renderMatrix();
}

function addDisc() {
  disciplines.unshift({ modulo:'', ordem: 1, nome:'', carga:'', professor:'', titulacao:'' });
  disciplines.forEach((d, i) => { if (i > 0) d.ordem = i + 1; });
  renderMatrix();
  document.getElementById('matrixBody')?.firstElementChild?.scrollIntoView({ behavior:'smooth', block:'nearest' });
}

function updateHidden() {
  const h = document.getElementById('disciplinas_json');
  if (h) h.value = JSON.stringify(disciplines);
}

// ── IMAGENS / LINKS DE CAPA ────────────────────────────────────────
let imagens = [];

function initImagens(existing) {
  imagens = existing && existing.length ? existing : [];
  renderImagens();
}

function renderImagens() {
  const body = document.getElementById('imagensBody');
  if (!body) return;
  body.innerHTML = imagens.map((img, i) => `
    <div class="img-row">
      <input type="text" value="${(img.descricao||'').replace(/"/g,'&quot;')}" placeholder="Ex: Capa do site, Banner Instagram..." oninput="updateImg(${i},'descricao',this.value)">
      <input type="text" value="${(img.url||'').replace(/"/g,'&quot;')}" placeholder="https://..." oninput="updateImg(${i},'url',this.value)">
      <button type="button" class="btn-del-row" onclick="removeImg(${i})" title="Remover linha">
        <svg viewBox="0 0 24 24"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14H6L5 6"/><path d="M10 11v6M14 11v6"/><path d="M9 6V4h6v2"/></svg>
      </button>
    </div>
  `).join('');
  updateImagensHidden();
}

function updateImg(i, key, val) { imagens[i][key] = val; updateImagensHidden(); }
function removeImg(i) {
  const img = imagens[i];
  const temConteudo = img && ((img.url && img.url.trim()) || (img.descricao && img.descricao.trim()));
  if (temConteudo && !confirm('Remover este link de imagem?')) return;
  imagens.splice(i, 1);
  renderImagens();
}

function addImagem() {
  imagens.push({ descricao:'', url:'' });
  renderImagens();
  document.getElementById('imagensBody')?.lastElementChild?.scrollIntoView({ behavior:'smooth', block:'nearest' });
}

function updateImagensHidden() {
  const h = document.getElementById('imagens_json');
  if (h) h.value = JSON.stringify(imagens);
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

// ── EVENTOS: NOTIFICAÇÃO DE FINALIZAÇÃO ──────────────────────────
// Avisa (notificação do navegador) 1 dia antes e no dia em que um evento
// "em andamento" finaliza, lembrando de ocultá-lo da plataforma — continua
// avisando a cada 30 min enquanto ele não for ocultado manualmente.
function _formatarDataBR(iso) {
  const [ano, mes, dia] = iso.split('-');
  return `${dia}/${mes}/${ano}`;
}

function _dispararNotificacoesEventos(eventos) {
  eventos.forEach(ev => {
    const dataFmt = _formatarDataBR(ev.data_finalizacao);
    const msg = ev.vencido
      ? `"${ev.nome}" já terminou (${dataFmt}) — oculte da plataforma.`
      : `"${ev.nome}" finaliza amanhã (${dataFmt}) — prepare para ocultar.`;
    try {
      new Notification('Evento para ocultar', { body: msg, tag: 'evento-ocultar-' + ev.id });
    } catch (e) { /* navegador sem suporte a Notification, ignora */ }
  });
}

function checarEventosPendentes() {
  fetch('/api/eventos/pendentes-ocultar')
    .then(r => r.ok ? r.json() : { eventos: [] })
    .then(data => {
      const eventos = data.eventos || [];
      if (!eventos.length || !('Notification' in window)) return;
      if (Notification.permission === 'granted') {
        _dispararNotificacoesEventos(eventos);
      } else if (Notification.permission === 'default') {
        Notification.requestPermission().then(perm => {
          if (perm === 'granted') _dispararNotificacoesEventos(eventos);
        });
      }
    })
    .catch(() => {});
}

// Só roda em páginas logadas (o sino de notificações só existe no layout logado)
if (document.getElementById('notifBtn')) {
  checarEventosPendentes();
  setInterval(checarEventosPendentes, 30 * 60 * 1000);
}
