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

// ── SUBGRUPOS DENTRO DE FERRAMENTAS (ex: MOODLE, DRIVE) ─────────────
// Mesma lógica das seções do menu, um nível mais fundo — agrupamento é
// automático (por padrão do nome/URL), só o abrir/fechar é lembrado aqui.
function toggleFerramentasGrupo(header) {
  const bloco = header.closest('.nav-subgroup');
  if (!bloco) return;
  const items = bloco.querySelector('.nav-subgroup-items');
  const chevron = header.querySelector('.section-chevron');
  const abrir = items.classList.contains('is-collapsed');
  items.classList.toggle('is-collapsed', !abrir);
  if (chevron) chevron.classList.toggle('is-open', abrir);
  const id = bloco.dataset.subgroupId;
  if (id) localStorage.setItem('navSubgrupoAberto_' + id, abrir ? '1' : '0');
}

document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.nav-subgroup').forEach(bloco => {
    const id = bloco.dataset.subgroupId;
    const items = bloco.querySelector('.nav-subgroup-items');
    const chevron = bloco.querySelector('.section-chevron');
    if (!items || !id) return;
    const temPaginaAtual = !!items.querySelector('.nav-item.active');
    const salvo = localStorage.getItem('navSubgrupoAberto_' + id);
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
    // Seção nova, ainda não incluída na ordem salva (ex: acabou de ser lançada):
    // fica no final, na ordem em que já aparecia no HTML — nunca pula pra frente.
    Object.keys(blocos).forEach(id => { if (!ordemSalva.includes(id)) container.appendChild(blocos[id]); });
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

// ── ORDEM DOS ITENS (SUBCATEGORIAS) DENTRO DE CADA SEÇÃO ────────────
// Mesmo princípio da ordem das seções acima: global, escolhida pelo
// admin, vale pra todo mundo — só reordena, nunca decide quem vê o quê
// (isso continua vindo das permissões/visibilidade de cada item).
// Serve tanto pros módulos fixos (Cursos/Matrizes/...) quanto pras
// ferramentas externas (lista dinâmica, cadastrada pelo admin) — cada
// grupo usa seu próprio atributo de id e seu próprio endpoint de salvar,
// mas o mecanismo de arrastar é o mesmo.
function initItemDragReorder(itemSelector, ordemSalva, endpointUrl, extrairId) {
  const ehAdmin = window.SIDEBAR_IS_ADMIN === true;

  document.querySelectorAll('.sidebar-section-items').forEach(lista => {
    const itens = {};
    lista.querySelectorAll(':scope > ' + itemSelector).forEach(a => { itens[extrairId(a)] = a; });
    if (ordemSalva.length) {
      ordemSalva.forEach(id => { if (itens[id]) lista.appendChild(itens[id]); });
    }
    if (!ehAdmin) return;

    let arrastando = null;
    lista.querySelectorAll(':scope > ' + itemSelector).forEach(a => {
      a.setAttribute('draggable', 'true');
      a.addEventListener('dragstart', () => {
        arrastando = a;
        a.classList.add('item-dragging');
      });
      a.addEventListener('dragend', () => {
        a.classList.remove('item-dragging');
        lista.querySelectorAll('.item-drop-target').forEach(el => el.classList.remove('item-drop-target'));
        arrastando = null;
        salvarOrdem();
      });
      a.addEventListener('dragover', e => {
        e.preventDefault();
        if (!arrastando || arrastando === a) return;
        lista.querySelectorAll('.item-drop-target').forEach(el => el.classList.remove('item-drop-target'));
        a.classList.add('item-drop-target');
      });
      a.addEventListener('dragleave', () => a.classList.remove('item-drop-target'));
      a.addEventListener('drop', e => {
        e.preventDefault();
        a.classList.remove('item-drop-target');
        if (!arrastando || arrastando === a) return;
        const todos = Array.from(lista.querySelectorAll(':scope > ' + itemSelector));
        const posArrastando = todos.indexOf(arrastando);
        const posAlvo = todos.indexOf(a);
        if (posArrastando < posAlvo) a.after(arrastando);
        else a.before(arrastando);
      });
    });
  });

  function salvarOrdem() {
    const ordem = Array.from(document.querySelectorAll('.sidebar-section-items > ' + itemSelector)).map(extrairId);
    fetch(endpointUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ order: ordem }),
    });
  }
}

initItemDragReorder('.nav-item[data-item-id]', window.MODULOS_ORDEM || [], '/api/modulos-ordem', a => a.dataset.itemId);
// ferramentas já chegam do servidor na ordem certa (ORDER BY ExternalTool.ordem)
// — não precisa reordenar de novo no carregamento, só habilitar o arrastar.
initItemDragReorder('.nav-item[data-tool-id]', [], '/api/ferramentas-ordem', a => a.dataset.toolId);

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

function blankDisc() { return { modulo:'', nome:'', carga:'', professor:'', titulacao:'' }; }

// Sempre mantém pelo menos 1 linha em branco — é nela que o onpaste do
// campo escuta o Ctrl+V; sem nenhuma linha não tem input nenhum pra colar,
// e a matriz colada não tinha onde cair.
function initMatrix(existing) {
  disciplines = existing && existing.length ? existing : [blankDisc()];
  renderMatrix();
}

function escAttr(v) {
  return String(v == null ? '' : v).replace(/&/g,'&amp;').replace(/"/g,'&quot;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

// Ordem real de gravação é sempre a posição no array (o back-end ignora
// o campo "ordem" antigo e recalcula por índice), então a coluna "#" aqui
// é só leitura — quem reordena de verdade é o arraste pelo ⠿.
function renderMatrix() {
  const tbody = document.getElementById('matrixBody');
  if (!tbody) return;
  tbody.innerHTML = disciplines.map((d, i) => `
    <div class="matrix-row matrix-editable" draggable="true" data-idx="${i}">
      <span class="row-drag-handle" title="Arraste para reordenar">⠿</span>
      <input type="text" value="${escAttr(d.modulo)}" placeholder="Mód. 01" oninput="updateDisc(${i},'modulo',this.value)" onpaste="handleMatrixPaste(event,${i},'modulo')">
      <span class="row-ordem">${i+1}</span>
      <input type="text" value="${escAttr(d.nome)}" placeholder="Nome da disciplina" oninput="updateDisc(${i},'nome',this.value)" onpaste="handleMatrixPaste(event,${i},'nome')">
      <input type="text" value="${escAttr(d.carga)}" placeholder="30h" oninput="updateDisc(${i},'carga',this.value)" onpaste="handleMatrixPaste(event,${i},'carga')">
      <input type="text" value="${escAttr(d.professor)}" placeholder="Professor" oninput="updateDisc(${i},'professor',this.value)" onpaste="handleMatrixPaste(event,${i},'professor')">
      <input type="text" value="${escAttr(d.titulacao)}" placeholder="MSc" oninput="updateDisc(${i},'titulacao',this.value)" onpaste="handleMatrixPaste(event,${i},'titulacao')">
      <button type="button" class="btn-del-row" onclick="removeDisc(${i})" title="Remover linha">
        <svg viewBox="0 0 24 24"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14H6L5 6"/><path d="M10 11v6M14 11v6"/><path d="M9 6V4h6v2"/></svg>
      </button>
    </div>
  `).join('');
  updateHidden();
  initMatrixDrag();
}

function updateDisc(i, key, val) { disciplines[i][key] = val; updateHidden(); }
function removeDisc(i) {
  const d = disciplines[i];
  if (d && d.nome && d.nome.trim() && !confirm(`Remover a disciplina "${d.nome}"?`)) return;
  disciplines.splice(i, 1);
  if (disciplines.length === 0) disciplines.push(blankDisc());
  renderMatrix();
}

function addDisc() {
  disciplines.unshift(blankDisc());
  renderMatrix();
  document.getElementById('matrixBody')?.firstElementChild?.scrollIntoView({ behavior:'smooth', block:'nearest' });
}

function limparMatriz() {
  const qtd = disciplines.filter(discPreenchida).length;
  if (!qtd) return;
  if (!confirm(`Excluir ${qtd === 1 ? 'a disciplina' : `as ${qtd} disciplinas`} da matriz? Isso só é gravado de fato quando você salvar o curso.`)) return;
  disciplines = [blankDisc()];
  renderMatrix();
}

// A linha em branco que sempre existe (pra sempre ter onde colar) não pode
// virar disciplina fantasma no banco se o curso for salvo sem preenchê-la.
function discPreenchida(d) {
  return Object.values(d).some(v => (v || '').toString().trim());
}

function updateHidden() {
  const h = document.getElementById('disciplinas_json');
  if (h) h.value = JSON.stringify(disciplines.filter(discPreenchida));
}

// Arraste das linhas (pelo ⠿) para reordenar — reordena o array de
// verdade, não só o DOM, já que renderMatrix() redesenha tudo a partir dele.
function initMatrixDrag() {
  const tbody = document.getElementById('matrixBody');
  if (!tbody) return;
  let arrastando = null;
  tbody.querySelectorAll('.matrix-row').forEach(row => {
    row.addEventListener('dragstart', () => {
      arrastando = row;
      row.classList.add('row-dragging');
    });
    row.addEventListener('dragend', () => {
      row.classList.remove('row-dragging');
      tbody.querySelectorAll('.row-drop-target').forEach(r => r.classList.remove('row-drop-target'));
      arrastando = null;
    });
    row.addEventListener('dragover', e => {
      e.preventDefault();
      if (!arrastando || arrastando === row) return;
      tbody.querySelectorAll('.row-drop-target').forEach(r => r.classList.remove('row-drop-target'));
      row.classList.add('row-drop-target');
    });
    row.addEventListener('dragleave', () => row.classList.remove('row-drop-target'));
    row.addEventListener('drop', e => {
      e.preventDefault();
      row.classList.remove('row-drop-target');
      if (!arrastando || arrastando === row) return;
      const from = Number(arrastando.dataset.idx);
      const to = Number(row.dataset.idx);
      const [movida] = disciplines.splice(from, 1);
      disciplines.splice(to, 0, movida);
      renderMatrix();
    });
  });
}

// Colar tipo planilha: cola numa célula (ex: Módulo) uma tabela copiada do
// Excel/Sheets ou só uma lista de linhas, e preenche/expande a matriz a
// partir dali — mesma lógica de "colar" de uma planilha de verdade. Se for
// só um valor simples (sem tab/quebra de linha), deixa o paste normal do
// campo acontecer.
const MATRIX_PASTE_COLS = ['modulo', 'nome', 'carga', 'professor', 'titulacao'];

function handleMatrixPaste(e, rowIndex, colKey) {
  const html = e.clipboardData && e.clipboardData.getData('text/html');
  const texto = e.clipboardData && e.clipboardData.getData('text/plain');
  let linhas = null;

  if (html && /<table/i.test(html)) {
    const doc = new DOMParser().parseFromString(html, 'text/html');
    const tabela = doc.querySelector('table');
    if (tabela) {
      linhas = Array.from(tabela.querySelectorAll('tr'))
        .map(tr => Array.from(tr.querySelectorAll('td,th')).map(cel => cel.textContent.replace(/\r?\n+/g, ' ').trim()))
        .filter(linha => linha.some(c => c.length));
    }
  }
  if (!linhas && texto) {
    linhas = texto.replace(/\r/g, '').split('\n').filter(l => l.length).map(l => l.split('\t'));
  }
  if (!linhas || linhas.length === 0 || (linhas.length === 1 && linhas[0].length <= 1)) return;

  e.preventDefault();
  const colStart = MATRIX_PASTE_COLS.indexOf(colKey);
  linhas.forEach((celulas, ri) => {
    const idx = rowIndex + ri;
    while (disciplines.length <= idx) disciplines.push(blankDisc());
    celulas.forEach((val, ci) => {
      const key = MATRIX_PASTE_COLS[colStart + ci];
      if (key) disciplines[idx][key] = val.trim();
    });
  });
  renderMatrix();
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

// ── MOSTRAR/OCULTAR SENHA ─────────────────────────────────────────
const EYE_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>';
const EYE_OFF_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17.94 17.94A10.94 10.94 0 0 1 12 20c-7 0-11-8-11-8a20.6 20.6 0 0 1 5.06-6.06M9.9 4.24A10.94 10.94 0 0 1 12 4c7 0 11 8 11 8a20.6 20.6 0 0 1-2.16 3.19M14.12 14.12a3 3 0 1 1-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/></svg>';

document.querySelectorAll('input[type=password]').forEach(input => {
  const wrap = document.createElement('div');
  wrap.className = 'pw-wrap';
  input.parentNode.insertBefore(wrap, input);
  wrap.appendChild(input);
  const btn = document.createElement('button');
  btn.type = 'button';
  btn.className = 'pw-toggle';
  btn.setAttribute('aria-label', 'Mostrar senha');
  btn.innerHTML = EYE_ICON;
  wrap.appendChild(btn);
  btn.addEventListener('click', () => {
    const show = input.type === 'password';
    input.type = show ? 'text' : 'password';
    btn.innerHTML = show ? EYE_OFF_ICON : EYE_ICON;
    btn.setAttribute('aria-label', show ? 'Ocultar senha' : 'Mostrar senha');
  });
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
