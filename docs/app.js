// Inițializare Telegram Web App
const tg = window.Telegram.WebApp;
tg.ready();
tg.expand();

// URL-ul API-ului tău local (îl schimbi când deployezi)
const API_URL = "http://localhost:8000";

// Telegram ID-ul utilizatorului curent
const telegramId = tg.initDataUnsafe?.user?.id || null;

// ── Navigare între pagini ────────────────────────────────────────────────────
function arataPagina(numePagina) {
    // Ascunde toate paginile
    document.querySelectorAll('.pagina').forEach(p => p.classList.remove('activa'));
    document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));

    // Arată pagina selectată
    document.getElementById(`pagina-${numePagina}`).classList.add('activa');
    event.currentTarget.classList.add('active');

    // Încarcă datele pentru pagina respectivă
    if (numePagina === 'dashboard') incarcaDashboard();
    if (numePagina === 'lista')     incarcaLista();
    if (numePagina === 'stoc')      incarcaStoc();
    if (numePagina === 'buget')     incarcaBuget();
}

// ── Apel API helper ──────────────────────────────────────────────────────────
async function apelAPI(endpoint) {
    try {
        const raspuns = await fetch(`${API_URL}${endpoint}?telegram_id=${telegramId}`);
        if (!raspuns.ok) throw new Error('Eroare API');
        return await raspuns.json();
    } catch (err) {
        console.error('Eroare API:', err);
        return null;
    }
}

// ── Dashboard ────────────────────────────────────────────────────────────────
async function incarcaDashboard() {
    const date = await apelAPI('/api/dashboard');
    if (!date) return;

    // Salut personalizat
    const ora = new Date().getHours();
    const salut = ora < 12 ? "Bună dimineața" : ora < 18 ? "Bună ziua" : "Bună seara";
    document.getElementById('salut-user').textContent = `${salut}, ${date.nume}!`;

    // Bara buget
    const procent = date.buget_total > 0
        ? Math.min((date.cheltuit / date.buget_total) * 100, 100)
        : 0;
    const bara = document.getElementById('bara-buget');
    bara.style.width = procent + '%';
    bara.className = 'bara-progres' +
        (procent > 85 ? ' danger' : procent > 60 ? ' warning' : '');

    document.getElementById('cheltuit-sum').textContent = `${Math.round(date.cheltuit)} lei`;
    document.getElementById('ramas-sum').textContent =
        `${Math.round(date.buget_total - date.cheltuit)} lei`;

    // Produse critice
    const criticeDiv = document.getElementById('produse-critice');
    if (date.produse_critice.length === 0) {
        criticeDiv.innerHTML = '<p class="gol">✅ Niciun produs pe terminate</p>';
    } else {
        criticeDiv.innerHTML = date.produse_critice.map(p => `
            <div class="produs-item">
                <span class="produs-nume">${p.name}</span>
                <span class="badge-critic">⚠️ ${p.procent}%</span>
            </div>
        `).join('');
    }

    // De cumpărat
    const cumparatDiv = document.getElementById('de-cumparat-azi');
    if (date.de_cumparat.length === 0) {
        cumparatDiv.innerHTML = '<p class="gol">✅ Nimic de cumpărat!</p>';
    } else {
        cumparatDiv.innerHTML = date.de_cumparat.slice(0, 5).map(p => `
            <div class="produs-item">
                <span class="produs-nume">${p.name}</span>
                <span class="produs-qty">${p.cantitate} ${p.unit}</span>
            </div>
        `).join('');
        if (date.de_cumparat.length > 5) {
            cumparatDiv.innerHTML +=
                `<p style="text-align:center;color:#888;font-size:13px;margin-top:8px">
                    și alte ${date.de_cumparat.length - 5} produse...
                </p>`;
        }
    }
}

// ── Listă cumpărături ────────────────────────────────────────────────────────
async function incarcaLista() {
    const date = await apelAPI('/api/lista');
    const div = document.getElementById('lista-continut');
    if (!date || date.produse.length === 0) {
        div.innerHTML = '<p class="gol">✅ Nu ai niciun produs de cumpărat!</p>';
        return;
    }

    // Grupează pe categorii
    const categorii = {};
    date.produse.forEach(p => {
        if (!categorii[p.category]) categorii[p.category] = [];
        categorii[p.category].push(p);
    });

    let html = '';
    for (const [cat, produse] of Object.entries(categorii)) {
        html += `<div class="categorie-titlu">📦 ${cat}</div>
                 <div class="card" style="margin-top:0">`;
        produse.forEach(p => {
            html += `
                <div class="produs-item">
                    <div>
                        <div class="produs-nume">${p.name}</div>
                        <div class="produs-qty">Necesar: ${p.cantitate} ${p.unit}</div>
                    </div>
                    <span style="color:#2E75B6;font-weight:600">
                        ~${Math.round(p.pret_estimat)} lei
                    </span>
                </div>`;
        });
        html += '</div>';
    }

    const total = date.produse.reduce((s, p) => s + p.pret_estimat, 0);
    html += `<div class="card" style="background:#E8F5E9">
                <div style="display:flex;justify-content:space-between;font-weight:700">
                    <span>💰 Total estimat:</span>
                    <span style="color:#2E7D32">${Math.round(total)} lei</span>
                </div>
             </div>`;

    div.innerHTML = html;
}

// ── Stoc ─────────────────────────────────────────────────────────────────────
async function incarcaStoc() {
    const date = await apelAPI('/api/stoc');
    const div = document.getElementById('stoc-continut');
    if (!date) return;

    const categorii = {};
    date.produse.forEach(p => {
        if (!categorii[p.category]) categorii[p.category] = [];
        categorii[p.category].push(p);
    });

    let html = '';
    for (const [cat, produse] of Object.entries(categorii)) {
        html += `<div class="categorie-titlu">📦 ${cat}</div>
                 <div class="card" style="margin-top:0">`;
        produse.forEach(p => {
            const procent = p.desired > 0 ? Math.round((p.stoc / p.desired) * 100) : 100;
            const culoare = procent < 30 ? '#F44336' : procent < 60 ? '#FF9800' : '#4CAF50';
            html += `
                <div class="produs-item">
                    <div>
                        <div class="produs-nume">${p.name}</div>
                        <div class="produs-qty">${p.stoc} / ${p.desired} ${p.unit}</div>
                    </div>
                    <span style="color:${culoare};font-weight:700">${procent}%</span>
                </div>`;
        });
        html += '</div>';
    }

    div.innerHTML = html || '<p class="gol">Nu ai produse înregistrate.</p>';
}

// ── Buget ────────────────────────────────────────────────────────────────────
async function incarcaBuget() {
    const date = await apelAPI('/api/buget');
    const div = document.getElementById('buget-continut');
    if (!date) return;

    const procent = date.buget_total > 0
        ? Math.min(Math.round((date.cheltuit / date.buget_total) * 100), 100)
        : 0;
    const ramas = date.buget_total - date.cheltuit;

    let html = `
        <div class="card">
            <h3>📊 Luna curentă</h3>
            <div class="bara-progres-container">
                <div class="bara-progres ${procent > 85 ? 'danger' : procent > 60 ? 'warning' : ''}"
                     style="width:${procent}%"></div>
            </div>
            <div class="buget-info" style="margin-top:8px">
                <span>Buget: <b>${date.buget_total} lei</b></span>
                <span>Cheltuit: <b>${Math.round(date.cheltuit)} lei</b></span>
            </div>
            <div style="text-align:center;margin-top:12px;font-size:16px;font-weight:700;
                        color:${ramas >= 0 ? '#2E7D32' : '#C62828'}">
                ${ramas >= 0 ? '✅ Rămas: ' + Math.round(ramas) + ' lei'
                             : '🔴 Depășit cu ' + Math.round(Math.abs(ramas)) + ' lei'}
            </div>
        </div>`;

    if (date.produse_frecvente && date.produse_frecvente.length > 0) {
        html += `<div class="card"><h3>⭐ Produse cumpărate des</h3>`;
        const medalii = ['🥇','🥈','🥉','4️⃣','5️⃣'];
        date.produse_frecvente.forEach((p, i) => {
            html += `<div class="produs-item">
                        <span class="produs-nume">${medalii[i]} ${p.name}</span>
                        <span class="produs-qty">${p.frecventa}x</span>
                     </div>`;
        });
        html += '</div>';
    }

    div.innerHTML = html;
}

// ── Pornire automată ─────────────────────────────────────────────────────────
incarcaDashboard();