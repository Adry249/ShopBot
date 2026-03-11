/* ═══════════════════════════════════════════════
   CONFIG & STATE
═══════════════════════════════════════════════ */
const tg = window.Telegram?.WebApp;
if (tg) { tg.ready(); tg.expand(); }

const API = "https://sarmentose-dawn-prebronchial.ngrok-free.dev"; // ← înlocuiește cu URL-ul ngrok
const TG_ID = tg?.initDataUnsafe?.user?.id || null;

// State local
let state = {
  user: null,
  dashboard: null,
  lista: null,
  stoc: null,
  raport: null,
  cosul: {},          // product_id -> {in_cart: bool, up_id}
  stocEditat: {},     // product_id -> cantitate
  listaCatActiva: null,
  stocCatActiva: null,
};

/* ═══════════════════════════════════════════════
   UTILITAR
═══════════════════════════════════════════════ */
async function api(endpoint) {
  if (!TG_ID) return null;
  try {
    const r = await fetch(`${API}${endpoint}?telegram_id=${TG_ID}`, {
      headers: { "ngrok-skip-browser-warning": "true" }
    });
    if (!r.ok) return null;
    return await r.json();
  } catch { return null; }
}

async function apiPost(endpoint, body) {
  if (!TG_ID) return null;
  try {
    const r = await fetch(`${API}${endpoint}?telegram_id=${TG_ID}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "ngrok-skip-browser-warning": "true"
      },
      body: JSON.stringify(body)
    });
    if (!r.ok) return null;
    return await r.json();
  } catch { return null; }
}

function toast(msg, type="") {
  const el = document.getElementById("toast");
  el.textContent = msg;
  el.className = `toast show ${type}`;
  clearTimeout(el._t);
  el._t = setTimeout(() => el.className = "toast", 2200);
}

function lei(n) { return `${Math.round(n)} lei`; }

function dataCurenta() {
  const d = new Date();
  return d.toLocaleDateString('ro-RO', {day:'numeric', month:'long'});
}

function categIcon(cat) {
  const m = {
    'Lactate':'🥛','Paine':'🍞','Carne':'🥩','Legume':'🥦',
    'Fructe':'🍎','Cereale':'🌾','Altele':'🏪','Bauturi':'🥤','Igiena':'🧴'
  };
  return m[cat] || '📦';
}

/* ═══════════════════════════════════════════════
   NAVIGARE
═══════════════════════════════════════════════ */
function navTo(page) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
  document.getElementById(`page-${page}`).classList.add('active');
  document.getElementById(`nav-${page}`).classList.add('active');

  if (page === 'home')   incarcaDashboard();
  if (page === 'lista')  incarcaLista();
  if (page === 'stoc')   incarcaStoc();
  if (page === 'raport') incarcaRaport();
}

/* ═══════════════════════════════════════════════
   SHEET
═══════════════════════════════════════════════ */
function openSheet(html) {
  document.getElementById("sheet-content").innerHTML = html;
  document.getElementById("overlay").classList.add("open");
  document.getElementById("sheet").classList.add("open");
}
function closeSheet() {
  document.getElementById("overlay").classList.remove("open");
  document.getElementById("sheet").classList.remove("open");
}

/* ═══════════════════════════════════════════════
   DASHBOARD
═══════════════════════════════════════════════ */
async function incarcaDashboard() {
  document.getElementById("date-pill").textContent = dataCurenta();

  const data = await api("/api/dashboard");
  if (!data) { toast("Eroare la încărcare", "error"); return; }
  state.dashboard = data;

  // Salut
  const ora = new Date().getHours();
  const salut = ora < 12 ? "Bună dimineața" : ora < 18 ? "Bună ziua" : "Bună seara";
  document.getElementById("hero-name").innerHTML =
    `${salut},<br><span style="color:var(--accent)">${data.nume}</span> 👋`;

  // Hero stats
  const ramas = (data.buget_total || 0) - (data.cheltuit || 0);
  const ramasEl = document.getElementById("hero-ramas");
  if (data.buget_total > 0) {
    ramasEl.textContent = lei(ramas);
    ramasEl.className = "hero-stat-val " + (ramas < 0 ? "bad" : ramas < data.buget_total * .2 ? "warn" : "ok");
  } else {
    ramasEl.textContent = "Nesetat";
    ramasEl.className = "hero-stat-val warn";
  }
  document.getElementById("hero-nr-prod").textContent =
    data.de_cumparat.length > 0 ? `${data.de_cumparat.length} produse` : "Totul OK ✓";

  // Buget bar
  if (data.buget_total > 0) {
    const pct = Math.min(100, Math.round((data.cheltuit / data.buget_total) * 100));
    const bar = document.getElementById("dash-prog");
    bar.style.width = pct + "%";
    bar.className = "prog-bar" + (pct > 85 ? " bad" : pct > 60 ? " warn" : "");
    document.getElementById("dash-cheltuit").textContent = `${lei(data.cheltuit)} cheltuiți`;
    document.getElementById("dash-total").textContent = `din ${lei(data.buget_total)}`;
    document.getElementById("buget-card").style.display = "block";
  }

  // Alerte produse critice
  if (data.produse_critice.length > 0) {
    const s = document.getElementById("alerte-section");
    const l = document.getElementById("alerte-list");
    l.innerHTML = data.produse_critice.slice(0,4).map(p => `
      <div class="list-item">
        <div class="item-left">
          <div class="item-icon">⚠️</div>
          <div><div class="item-name">${p.name}</div>
               <div class="item-sub">Stoc critic</div></div>
        </div>
        <span class="badge badge-danger">${p.procent}%</span>
      </div>`).join('');
    s.style.display = "block";
  }

  // Top produse de cumpărat
  if (data.de_cumparat.length > 0) {
    const top = document.getElementById("top-cumparaturi");
    document.getElementById("top-list").innerHTML =
      data.de_cumparat.slice(0,5).map(p => `
        <div class="list-item">
          <div class="item-left">
            <div class="item-icon">🛒</div>
            <div><div class="item-name">${p.name}</div>
                 <div class="item-sub">${p.cantitate} ${p.unit}</div></div>
          </div>
        </div>`).join('');
    top.style.display = "block";
  }
}

/* ═══════════════════════════════════════════════
   LISTĂ CUMPĂRĂTURI
═══════════════════════════════════════════════ */
async function incarcaLista() {
  document.getElementById("lista-content").innerHTML =
    '<div class="skel skel-card"></div><div class="skel skel-card"></div>';
  document.getElementById("lista-footer").style.display = "none";

  const data = await api("/api/lista");
  if (!data) { toast("Eroare la încărcare", "error"); return; }
  state.lista = data;

  // Inițializează cosul din state
  data.produse.forEach(p => {
    if (!state.cosul[p.up_id]) state.cosul[p.up_id] = false;
  });

  const pill = document.getElementById("lista-count-pill");
  pill.textContent = `${data.produse.length} produse`;

  if (data.produse.length === 0) {
    document.getElementById("lista-content").innerHTML = `
      <div class="empty">
        <div class="empty-icon">🎉</div>
        <p>Totul e în stoc!<br>Nu ai nevoie să cumperi nimic.</p>
      </div>`;
    return;
  }

  // Categorii tabs
  const cats = [...new Set(data.produse.map(p => p.category))];
  if (!state.listaCatActiva || !cats.includes(state.listaCatActiva))
    state.listaCatActiva = cats[0];

  renderListaTabs(cats);
  renderListaProduse();
}

function renderListaTabs(cats) {
  document.getElementById("lista-tabs").innerHTML = cats.map(c => `
    <button class="tab-btn ${c === state.listaCatActiva ? 'active' : ''}"
            onclick="selectListaCat('${c}')">
      ${categIcon(c)} ${c}
    </button>`).join('');
}

function selectListaCat(cat) {
  state.listaCatActiva = cat;
  const cats = [...new Set(state.lista.produse.map(p => p.category))];
  renderListaTabs(cats);
  renderListaProduse();
}

function renderListaProduse() {
  const produse = state.lista.produse.filter(p => p.category === state.listaCatActiva);
  let total = 0;
  state.lista.produse.forEach(p => {
    if (state.cosul[p.up_id]) total += p.pret_estimat;
  });

  document.getElementById("lista-content").innerHTML = `
    <div class="card">
      ${produse.map(p => {
        const inCos = state.cosul[p.up_id];
        return `
        <div class="list-item" id="li-${p.up_id}">
          <div class="item-left">
            <div class="item-icon">${categIcon(p.category)}</div>
            <div>
              <div class="item-name" style="${inCos ? 'text-decoration:line-through;opacity:.5' : ''}">${p.name}</div>
              <div class="item-sub">${p.cantitate} ${p.unit} · ~${lei(p.pret_estimat)}</div>
            </div>
          </div>
          <div class="item-right">
            <button class="btn btn-sm ${inCos ? 'btn-danger' : 'btn-primary'}"
                    onclick="toggleCos(${p.up_id}, ${p.pret_estimat})">
              ${inCos ? '↩️' : '🛒'}
            </button>
            <button class="btn btn-secondary btn-sm" onclick="deschideEditDorita(${p.product_id}, '${p.name}', ${p.desired_quantity}, '${p.unit}', '${p.category}')">✏️</button>
          </div>
        </div>`;
      }).join('')}
    </div>`;

  // Footer cu total și buton finalizare
  const inCosCount = Object.values(state.cosul).filter(Boolean).length;
  if (inCosCount > 0) {
    document.getElementById("lista-footer").style.display = "block";
    document.getElementById("lista-total").textContent = lei(total);
    document.getElementById("btn-finalizeaza").textContent =
      `🏁 Finalizează (${inCosCount} produse)`;
  } else {
    document.getElementById("lista-footer").style.display = "none";
  }
}

function toggleCos(upId, pret) {
  state.cosul[upId] = !state.cosul[upId];
  renderListaProduse();
  const inCos = state.cosul[upId];
  toast(inCos ? "Adăugat în coș 🛒" : "Scos din coș", inCos ? "success" : "");
}

async function finalizeazaCumparaturi() {
  const ids = Object.entries(state.cosul)
    .filter(([,v]) => v).map(([k]) => parseInt(k));
  if (ids.length === 0) return;

  const btn = document.getElementById("btn-finalizeaza");
  btn.textContent = "Se procesează...";
  btn.disabled = true;

  const res = await apiPost("/api/finalizeaza", { up_ids: ids });
  if (res && res.ok) {
    state.cosul = {};
    toast("Cumpărături finalizate! 🎉", "success");
    await incarcaLista();
    incarcaDashboard();
  } else {
    toast("Eroare la finalizare", "error");
    btn.textContent = "🏁 Finalizează cumpărăturile";
    btn.disabled = false;
  }
}

/* Sheet: editare cantitate dorită */
function deschideEditDorita(productId, name, currentVal, unit, category) {
  openSheet(`
    <div class="sheet-title">✏️ ${name}</div>
    <p class="text-muted">Câte ${unit} dorești să ai acasă?</p>
    <div style="margin:20px 0">
      <div class="stepper" style="justify-content:center">
        <button class="stepper-btn" onclick="stepVal('dorita-val',-1,0,999,'${unit}')">−</button>
        <div class="stepper-val"><input id="dorita-val" type="number" min="0" step="0.5"
          value="${currentVal || 0}"
          style="width:70px;text-align:center;background:transparent;border:none;color:var(--text);font-family:Syne,sans-serif;font-size:22px;font-weight:700;outline:none"></div>
        <button class="stepper-btn" onclick="stepVal('dorita-val',1,0,999,'${unit}')">+</button>
      </div>
      <div class="text-muted text-center mt8">${unit}</div>
    </div>
    <button class="btn btn-primary" onclick="salveazaDorita(${productId},'${category}')">✅ Salvează</button>
    <button class="btn btn-secondary mt8" onclick="closeSheet()">Anulează</button>
  `);
}

function stepVal(id, delta, min, max) {
  const inp = document.getElementById(id);
  const v = Math.max(min, Math.min(max, parseFloat(inp.value || 0) + delta));
  inp.value = Math.round(v * 10) / 10;
}

async function salveazaDorita(productId, category) {
  const val = parseFloat(document.getElementById("dorita-val").value) || 0;
  const res = await apiPost("/api/dorita", { product_id: productId, quantity: val });
  if (res && res.ok) {
    toast("Cantitate salvată ✅", "success");
    closeSheet();
    incarcaLista();
  } else {
    toast("Eroare la salvare", "error");
  }
}

/* ═══════════════════════════════════════════════
   STOC
═══════════════════════════════════════════════ */
async function incarcaStoc() {
  document.getElementById("stoc-content").innerHTML =
    '<div class="skel skel-card"></div><div class="skel skel-card"></div>';

  const data = await api("/api/stoc");
  if (!data) { toast("Eroare la încărcare", "error"); return; }
  state.stoc = data;

  const cats = [...new Set(data.produse.map(p => p.category))];
  if (!state.stocCatActiva || !cats.includes(state.stocCatActiva))
    state.stocCatActiva = cats[0];

  renderStocTabs(cats);
  renderStocProduse();
}

function renderStocTabs(cats) {
  document.getElementById("stoc-tabs").innerHTML = cats.map(c => `
    <button class="tab-btn ${c === state.stocCatActiva ? 'active' : ''}"
            onclick="selectStocCat('${c}')">
      ${categIcon(c)} ${c}
    </button>`).join('');
}

function selectStocCat(cat) {
  state.stocCatActiva = cat;
  const cats = [...new Set(state.stoc.produse.map(p => p.category))];
  renderStocTabs(cats);
  renderStocProduse();
}

function renderStocProduse() {
  const produse = state.stoc.produse.filter(p => p.category === state.stocCatActiva);

  document.getElementById("stoc-content").innerHTML = `
    <div class="card">
      ${produse.length === 0
        ? '<div class="empty"><p>Niciun produs în această categorie</p></div>'
        : produse.map(p => {
            const pct = p.desired > 0 ? Math.min(100, Math.round((p.stoc / p.desired) * 100)) : 100;
            const col = pct < 30 ? '#ff4b6e' : pct < 60 ? '#ffb347' : '#43e97b';
            const r = 16; const circ = 2 * Math.PI * r;
            const offset = circ - (pct / 100) * circ;
            return `
            <div class="list-item">
              <div class="item-left">
                <svg class="circle-prog" viewBox="0 0 38 38">
                  <circle class="circle-bg" cx="19" cy="19" r="${r}"/>
                  <circle class="circle-fg" cx="19" cy="19" r="${r}"
                    stroke="${col}"
                    stroke-dasharray="${circ}"
                    stroke-dashoffset="${offset}"/>
                </svg>
                <div>
                  <div class="item-name">${p.name}</div>
                  <div class="item-sub">${p.stoc} / ${p.desired} ${p.unit}</div>
                </div>
              </div>
              <button class="btn btn-sm btn-secondary"
                      onclick="deschideEditStoc(${p.product_id},'${p.name}',${p.stoc},'${p.unit}')">
                ✏️
              </button>
            </div>`;
          }).join('')}
    </div>`;
}

function deschideEditStoc(productId, name, currentVal, unit) {
  openSheet(`
    <div class="sheet-title">📦 ${name}</div>
    <p class="text-muted">Câte ${unit} ai acasă acum?</p>
    <div style="margin:20px 0">
      <div class="stepper" style="justify-content:center">
        <button class="stepper-btn" onclick="stepVal('stoc-val',-0.5,0,9999)">−</button>
        <div class="stepper-val">
          <input id="stoc-val" type="number" min="0" step="0.5" value="${currentVal}"
            style="width:70px;text-align:center;background:transparent;border:none;color:var(--text);font-family:Syne,sans-serif;font-size:22px;font-weight:700;outline:none">
        </div>
        <button class="stepper-btn" onclick="stepVal('stoc-val',0.5,0,9999)">+</button>
      </div>
      <div class="text-muted text-center mt8">${unit}</div>
    </div>
    <button class="btn btn-primary" onclick="salveazaStoc(${productId})">✅ Salvează stocul</button>
    <button class="btn btn-danger mt8" onclick="golesteProdus(${productId},'${name}')">🗑️ Golește (pune pe 0)</button>
    <button class="btn btn-secondary mt8" onclick="closeSheet()">Anulează</button>
  `);
}

async function salveazaStoc(productId) {
  const val = parseFloat(document.getElementById("stoc-val").value) || 0;
  const res = await apiPost("/api/stoc/update", { product_id: productId, quantity: val });
  if (res && res.ok) {
    toast("Stoc actualizat ✅", "success");
    closeSheet();
    incarcaStoc();
    incarcaDashboard();
  } else {
    toast("Eroare la salvare", "error");
  }
}

async function golesteProdus(productId, name) {
  const res = await apiPost("/api/stoc/update", { product_id: productId, quantity: 0 });
  if (res && res.ok) {
    toast(`${name} golit ✅`);
    closeSheet();
    incarcaStoc();
  } else {
    toast("Eroare", "error");
  }
}

function deschideAdaugaStoc() {
  openSheet(`
    <div class="sheet-title">+ Actualizare rapidă stoc</div>
    <p class="text-muted" style="margin-bottom:16px">Mergi în tab-ul produsului și apasă ✏️ pentru a edita cantitatea.</p>
    <button class="btn btn-primary" onclick="closeSheet()">OK</button>
  `);
}

/* ═══════════════════════════════════════════════
   RAPORT
═══════════════════════════════════════════════ */
async function incarcaRaport() {
  document.getElementById("raport-content").innerHTML =
    '<div class="skel skel-card"></div><div class="skel skel-card"></div>';

  const data = await api("/api/raport");
  if (!data) { toast("Eroare la încărcare", "error"); return; }

  const luna = new Date().toLocaleDateString('ro-RO', {month:'long', year:'numeric'});
  document.getElementById("raport-luna-pill").textContent = luna;

  const ramas = (data.buget_total || 0) - (data.cheltuit || 0);
  const pct = data.buget_total > 0
    ? Math.min(100, Math.round((data.cheltuit / data.buget_total) * 100)) : 0;
  const barClass = pct > 85 ? "bad" : pct > 60 ? "warn" : "";

  let html = `
    <!-- Card rezumat buget -->
    <div class="card">
      <div class="card-title">💰 Buget lunar</div>
      <div class="stat-row">
        <span class="stat-label">Buget total</span>
        <span class="stat-val">${lei(data.buget_total)}</span>
      </div>
      <div class="stat-row">
        <span class="stat-label">Cheltuit</span>
        <span class="stat-val">${lei(data.cheltuit)}</span>
      </div>
      <div class="stat-row">
        <span class="stat-label">${ramas >= 0 ? 'Economii' : 'Depășire'}</span>
        <span class="stat-val ${ramas >= 0 ? 'text-success' : 'text-danger'}">${lei(Math.abs(ramas))}</span>
      </div>
      <div class="prog-wrap" style="margin-top:12px">
        <div class="prog-bar ${barClass}" style="width:${pct}%"></div>
      </div>
      <div class="prog-labels">
        <span>${pct}% utilizat</span>
        <span>${lei(ramas >= 0 ? ramas : 0)} rămas</span>
      </div>
    </div>`;

  // Față de luna trecută
  if (data.cheltuit_luna_trecuta !== undefined) {
    const diff = data.cheltuit_luna_trecuta - data.cheltuit;
    html += `
    <div class="card">
      <div class="card-title">📈 Față de luna trecută</div>
      <div class="stat-row">
        <span class="stat-label">Luna trecută</span>
        <span class="stat-val">${lei(data.cheltuit_luna_trecuta)}</span>
      </div>
      <div class="stat-row">
        <span class="stat-label">Luna aceasta</span>
        <span class="stat-val">${lei(data.cheltuit)}</span>
      </div>
      <div class="stat-row" style="border:none">
        <span class="stat-label">${diff >= 0 ? '✅ Economii' : '📈 Creștere'}</span>
        <span class="stat-val ${diff >= 0 ? 'text-success' : 'text-warn'}">${lei(Math.abs(diff))}</span>
      </div>
    </div>`;
  }

  // Produse cumpărate luna asta
  if (data.produse_luna && data.produse_luna.length > 0) {
    html += `
    <div class="card">
      <div class="card-title">🛒 Cumpărate luna aceasta</div>
      ${data.produse_luna.map(p => `
        <div class="list-item">
          <div class="item-left">
            <div class="item-icon">${categIcon('')}</div>
            <div>
              <div class="item-name">${p.name}</div>
              <div class="item-sub">${p.qty} ${p.unit}</div>
            </div>
          </div>
          <span class="stat-val">${lei(p.pret)}</span>
        </div>`).join('')}
    </div>`;
  }

  // Top produse frecvente
  if (data.produse_frecvente && data.produse_frecvente.length > 0) {
    const medalii = ['🥇','🥈','🥉','4️⃣','5️⃣'];
    html += `
    <div class="card">
      <div class="card-title">⭐ Cumpărate cel mai des (3 luni)</div>
      ${data.produse_frecvente.map((p,i) => `
        <div class="list-item">
          <div class="item-left">
            <div class="item-icon">${medalii[i]}</div>
            <div class="item-name">${p.name}</div>
          </div>
          <span class="badge badge-purple">${p.frecventa}x</span>
        </div>`).join('')}
    </div>`;
  }

  // Buton schimbare buget
  html += `
    <div style="padding:0 14px">
      <button class="btn btn-secondary" onclick="deschideSchimbaBuget()">
        ✏️ Schimbă bugetul lunar
      </button>
    </div>`;

  document.getElementById("raport-content").innerHTML = html;
}

/* ═══════════════════════════════════════════════
   SETĂRI
═══════════════════════════════════════════════ */
function deschideSetari() {
  const user = state.dashboard;
  openSheet(`
    <div class="sheet-title">⚙️ Setări cont</div>
    <div class="card" style="margin:0 0 12px">
      <div class="stat-row">
        <span class="stat-label">Utilizator</span>
        <span class="stat-val">${user?.nume || '—'}</span>
      </div>
      <div class="stat-row" style="border:none">
        <span class="stat-label">Ziua salariului</span>
        <span class="stat-val" id="salary-day-display">${user?.salary_day || '—'}</span>
      </div>
    </div>

    <div class="input-wrap">
      <label class="input-label">Buget lunar (lei)</label>
      <input class="input" id="set-buget" type="number" placeholder="ex: 3000"
             value="${state.dashboard?.buget_total || ''}">
    </div>
    <div class="input-wrap">
      <label class="input-label">Ziua salariului (1-31)</label>
      <input class="input" id="set-salary" type="number" min="1" max="31"
             placeholder="ex: 15" value="${user?.salary_day || ''}">
    </div>
    <button class="btn btn-primary" onclick="salveazaSetari()">💾 Salvează</button>
    <button class="btn btn-secondary mt8" onclick="closeSheet()">Anulează</button>
  `);
}

async function salveazaSetari() {
  const buget = parseInt(document.getElementById("set-buget").value) || 0;
  const salary = parseInt(document.getElementById("set-salary").value) || 0;

  if (salary < 1 || salary > 31) {
    toast("Ziua salariului trebuie să fie între 1 și 31", "error"); return;
  }

  const res = await apiPost("/api/setari", { monthly_budget: buget, salary_day: salary });
  if (res && res.ok) {
    toast("Setări salvate ✅", "success");
    closeSheet();
    incarcaDashboard();
  } else {
    toast("Eroare la salvare", "error");
  }
}

function deschideSchimbaBuget() {
  openSheet(`
    <div class="sheet-title">💰 Schimbă bugetul</div>
    <div class="input-wrap" style="margin-top:8px">
      <label class="input-label">Buget lunar (lei)</label>
      <input class="input" id="new-buget" type="number" placeholder="ex: 3000"
             value="${state.dashboard?.buget_total || ''}">
    </div>
    <button class="btn btn-primary" onclick="salveazaBuget()">💾 Salvează</button>
    <button class="btn btn-secondary mt8" onclick="closeSheet()">Anulează</button>
  `);
}

async function salveazaBuget() {
  const buget = parseInt(document.getElementById("new-buget").value) || 0;
  const res = await apiPost("/api/setari", {
    monthly_budget: buget,
    salary_day: state.dashboard?.salary_day || 1
  });
  if (res && res.ok) {
    toast("Buget actualizat ✅", "success");
    closeSheet();
    incarcaDashboard();
    incarcaRaport();
  } else {
    toast("Eroare la salvare", "error");
  }
}

/* ═══════════════════════════════════════════════
   INIT
═══════════════════════════════════════════════ */
document.addEventListener("DOMContentLoaded", () => {
  incarcaDashboard();
});