(function () {
    const btn = document.querySelector('#start-btn');
    if (!btn) return;
    const statusText = document.querySelector('#status-text');
    const panel = document.querySelector('#results-panel');
    const container = document.querySelector('#topics-container');
    const closedBar = document.querySelector('#closed-bar');
    const totalRounds = parseInt(btn.dataset.totalRounds, 10);
    let source = null;
    let selectedTopicId = null;

    function typewrite(el, text, speed, done) {
        el.textContent = '';
        let i = 0;
        (function tick() {
            if (i < text.length) {
                el.textContent += text[i++];
                setTimeout(tick, speed);
            } else if (done) {
                done();
            }
        })();
    }

    const WINDOWS = {
        'window-generator': 'ГЕНЕРАТОР',
        'window-critic': 'КРИТИК',
        'window-judge': 'СУДДЯ'
    };
    const STORE_KEY = 'debate-windows-state';

    function loadState() {
        try { return JSON.parse(localStorage.getItem(STORE_KEY)) || {}; }
        catch (e) { return {}; }
    }
    function saveState(s) {
        try { localStorage.setItem(STORE_KEY, JSON.stringify(s)); }
        catch (e) {}
    }
    const state = loadState();

    function renderClosedBar() {
        if (!closedBar) return;
        closedBar.textContent = '';
        Object.keys(WINDOWS).forEach(function (id) {
            if (!(state[id] && state[id].closed)) return;
            const b = document.createElement('button');
            b.type = 'button';
            b.className = 'win-btn me-2';
            b.textContent = '[+ ' + WINDOWS[id] + ']';
            b.addEventListener('click', function () {
                state[id] = { collapsed: false, closed: false };
                saveState(state);
                applyWindow(id);
            });
            closedBar.appendChild(b);
        });
    }

    function applyWindow(id) {
        const win = document.querySelector('#' + id);
        if (!win) return;
        const col = win.closest('[class*="col-"]');
        const s = state[id] || {};
        win.classList.toggle('collapsed', !!s.collapsed);
        if (col) col.classList.toggle('d-none', !!s.closed);
        const c = win.querySelector('[data-action="collapse"]');
        if (c) c.textContent = s.collapsed ? '[+]' : '[–]';
        renderClosedBar();
    }

    document.querySelectorAll('.win-btn[data-target]').forEach(function (b) {
        b.addEventListener('click', function () {
            const id = b.dataset.target;
            const win = document.querySelector('#' + id);
            const s = state[id] || { collapsed: false, closed: false };
            if (b.dataset.action === 'collapse') {
                s.collapsed = !s.collapsed;
            } else if (b.dataset.action === 'close') {
                s.closed = true;
            } else if (b.dataset.action === 'expand') {
                const open = win.classList.toggle('expanded');
                b.textContent = open ? '[⤡]' : '[⤢]';
                return;
            }
            state[id] = s;
            saveState(state);
            applyWindow(id);
        });
    });
    Object.keys(WINDOWS).forEach(applyWindow);

    function bodyOf(agent) {
        return document.querySelector('.agent-window-body[data-agent="' + agent + '"]');
    }
    function setStep(agent, text) {
        const el = document.querySelector('#window-' + agent + ' .step-status');
        if (el) el.textContent = text;
    }
    function addMessage(agent, text) {
        const body = bodyOf(agent);
        if (!body) return;
        const div = document.createElement('div');
        div.className = 'agent-msg';
        div.style.whiteSpace = 'pre-wrap';
        body.appendChild(div);
        typewrite(div, text, 6, function () { body.scrollTop = body.scrollHeight; });
    }

    function renderTopic(t) {
        const col = document.createElement('div');
        col.className = 'col-md-6';
        const card = document.createElement('div');
        card.className = 'agent-window p-3';

        const h = document.createElement('h5');
        h.className = 'fw-bold';
        h.textContent = t.title;
        const meta = document.createElement('div');
        meta.className = 'small font-monospace mb-2';
        meta.textContent = 'КОЛО ' + (t.round || '') + ' · ' + t.difficulty +
            ' · ОЦІНКА: ' + (t.score !== null && t.score !== undefined ? t.score + '/10' : '—');
        const why = document.createElement('p');
        why.textContent = t.why;
        const crit = document.createElement('p');
        crit.className = 'small text-muted';
        crit.textContent = 'Критик: ' + (t.critic_comment || '—');

        const pin = document.createElement('button');
        pin.className = 'btn-brutal';
        pin.textContent = t.is_pinned ? 'ЗАКРІПЛЕНО' : 'ЗАКРІПИТИ';
        pin.disabled = !!t.is_pinned;
        pin.addEventListener('click', function () { pinTopic(t.db_id, pin, col); });

        const sel = document.createElement('button');
        sel.className = 'btn-brutal ms-2';
        sel.style.marginTop = '0.5rem';
        sel.textContent = t.db_id === selectedTopicId ? '[✓ ОБРАНО]' : '[ ОБРАТИ ]';
        if (t.db_id === selectedTopicId) {
            card.style.outline = '3px solid #000';
        }
        sel.addEventListener('click', function () {
            document.querySelectorAll('.topic-sel-btn').forEach(function (b) {
                b.textContent = '[ ОБРАТИ ]';
                const parentCard = b.closest('.agent-window');
                if (parentCard) parentCard.style.outline = '';
            });
            selectedTopicId = t.db_id;
            sel.textContent = '[✓ ОБРАНО]';
            card.style.outline = '3px solid #000';
        });
        sel.classList.add('topic-sel-btn');

        card.append(h, meta, why, crit, pin, sel);
        col.appendChild(card);
        container.appendChild(col);
    }

    function pinTopic(id, button, col) {
        const url = btn.dataset.pinUrlTemplate.replace('/0/', '/' + id + '/');
        fetch(url, { method: 'POST', headers: { 'X-CSRFToken': btn.dataset.csrf } })
            .then(function (r) {
                if (!r.ok || r.redirected) throw new Error(r.status);
                button.textContent = 'ЗАКРІПЛЕНО';
                button.disabled = true;
                container.prepend(col);
            })
            .catch(function () { button.textContent = 'ПОМИЛКА, СПРОБУЙ ЩЕ'; });
    }

    function showPanel() { panel.classList.add('active'); }

    function finishRound(round) {
        if (round >= totalRounds) {
            btn.disabled = true;
            btn.textContent = 'ДЕБАТИ ЗАВЕРШЕНО';
            statusText.textContent = 'ЗАВЕРШЕНО';
        } else {
            btn.disabled = false;
            btn.dataset.nextRound = round + 1;
            btn.textContent = 'ПОЧАТИ КОЛО ' + (round + 1);
            statusText.textContent = 'КОЛО ' + round + ' ГОТОВЕ';
        }
    }

    function start() {
        const round = parseInt(btn.dataset.nextRound, 10);
        if (Number.isNaN(round)) {
            statusText.textContent = 'ПОМИЛКА: НЕ ВИЗНАЧЕНО НОМЕР КОЛА. ОНОВІТЬ СТОРІНКУ';
            return;
        }
        btn.disabled = true;
        Object.keys(WINDOWS).forEach(function (id) {
            setStep(id.replace('window-', ''), 'ОЧІКУВАННЯ');
        });

        let url = btn.dataset.streamUrl + '?round=' + round;
        if (selectedTopicId) url += '&selected_topic=' + selectedTopicId;
        source = new EventSource(url);

        source.onmessage = function (e) {
            const d = JSON.parse(e.data);
            if (d.type === 'status') {
                statusText.textContent = d.text;
            } else if (d.type === 'agent') {
                addMessage(d.agent, d.text);
                setStep(d.agent, 'ГОТОВО (' + d.provider + ')');
            } else if (d.type === 'round_done') {
                source.close();
                d.topics.forEach(function (t) { t.round = d.round; renderTopic(t); });
                showPanel();
                finishRound(d.round);
            } else if (d.type === 'error') {
                source.close();
                statusText.textContent = 'ПОМИЛКА: ' + d.text;
                btn.disabled = false;
            }
        };
        source.onerror = function () {
            source.close();
            statusText.textContent = 'З’ЄДНАННЯ ПЕРЕРВАНО. ОНОВІТЬ СТОРІНКУ';
            btn.disabled = false;
        };
    }

    btn.addEventListener('click', start);

    const dataEl = document.querySelector('#topics-data');
    const saved = dataEl ? JSON.parse(dataEl.textContent) : [];
    if (saved.length) { saved.forEach(renderTopic); showPanel(); }
})();