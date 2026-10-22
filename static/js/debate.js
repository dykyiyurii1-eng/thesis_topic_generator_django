document.addEventListener("DOMContentLoaded", function() {
    const btn = document.querySelector('#start-btn');
    if (!btn) return;

    const statusEl = document.querySelector('#status-text');
    const resultsPanel = document.querySelector('#results-panel');
    const topicsContainer = document.querySelector('#topics-container');
    
    const STREAM_URL = btn.dataset.streamUrl;
    const TOTAL_ROUNDS = parseInt(btn.dataset.totalRounds, 10);

    window.toggleExpand = function(windowId) {
        const win = document.querySelector('#' + windowId);
        win.classList.toggle('expanded');
        const isExpanded = win.classList.contains('expanded');
        const btnSpan = win.querySelector('.expand-btn');
        btnSpan.textContent = isExpanded ? '[Згорнути]' : '[Розгорнути]';
    };

    function updateStepper(activeAgent) {
        document.querySelectorAll('.agent-window').forEach(win => {
            const agent = win.querySelector('.agent-window-body').dataset.agent;
            const statusSpan = win.querySelector('.step-status');
            
            if (agent === activeAgent) {
                statusSpan.textContent = 'В ПРОЦЕСІ...';
                statusSpan.classList.add('step-active');
                statusSpan.classList.remove('text-muted');
            } else {
                statusSpan.classList.remove('step-active');
                statusSpan.classList.add('text-muted');
                if (statusSpan.textContent === 'В ПРОЦЕСІ...') {
                    statusSpan.textContent = 'ГОТОВО';
                }
            }
        });
    }

    function appendMsg(agent, provider, text) {
        const box = document.querySelector(`.agent-window-body[data-agent="${agent}"]`);
        if (!box) return;
        
        const empty = box.querySelector('.empty-placeholder');
        if (empty) empty.remove();

        const div = document.createElement('div');
        div.className = 'msg-line';
        div.innerHTML = `<div class="fw-bold text-muted mb-1">> ${provider.toUpperCase()}</div>
                         <div style="white-space: pre-wrap;">${text}</div>`;
        box.appendChild(div);
        box.scrollTop = box.scrollHeight;
    }

    function renderResults(topics) {
        resultsPanel.classList.add('active');
        topicsContainer.innerHTML = '';
        
        const sorted = topics.sort((a, b) => (b.score ?? 0) - (a.score ?? 0));
        sorted.forEach(t => {
            const div = document.createElement('div');
            div.className = 'col-md-6';
            div.innerHTML = `
                <div class="p-3 border border-dark bg-white d-flex align-items-center">
                    <div class="me-3 text-center border-end border-dark pe-3">
                        <div class="score-badge">${t.score !== null ? t.score : '-'}</div>
                        <small class="text-muted">/10</small>
                    </div>
                    <div>
                        <h5 class="fw-bold mb-1">${t.title}</h5>
                        <div class="text-muted small mb-2">${t.why || ''}</div>
                        ${t.critic_comment ? `<div class="text-danger small font-monospace border-top border-danger pt-1">КРИТИК: ${t.critic_comment}</div>` : ''}
                    </div>
                </div>
            `;
            topicsContainer.appendChild(div);
        });
    }

    function startDebate(roundNo) {
        btn.disabled = true;
        btn.textContent = 'З\u2019ЄДНАННЯ...';
        statusEl.textContent = 'З\u2019ЄДНАННЯ...';
        statusEl.className = 'mt-2 fw-bold font-monospace text-uppercase text-primary';
        
        document.querySelectorAll('.agent-window-body').forEach(box => {
            box.innerHTML = '<div class="empty-placeholder text-muted text-center mt-5">ОЧІКУВАННЯ...</div>';
        });
        document.querySelectorAll('.step-status').forEach(span => {
            span.textContent = 'ОЧІКУВАННЯ';
            span.classList.remove('step-active');
            span.classList.add('text-muted');
        });
        resultsPanel.classList.remove('active');

        const source = new EventSource(STREAM_URL + '?round=' + roundNo);
        let finished = false;

        source.onmessage = (event) => {
            let data;
            try { data = JSON.parse(event.data); } catch (e) { return; }

            if (data.type === 'status') {
                statusEl.textContent = data.text.toUpperCase();
                if (data.text.includes('Генератор')) updateStepper('generator');
                else if (data.text.includes('Критик')) updateStepper('critic');
                else if (data.text.includes('Суддя')) updateStepper('judge');

            } else if (data.type === 'agent') {
                appendMsg(data.agent, data.provider, data.text);

            } else if (data.type === 'round_done') {
                finished = true;
                source.close();
                statusEl.textContent = 'КОЛО ' + data.round + ' ЗАВЕРШЕНО';
                statusEl.className = 'mt-2 fw-bold font-monospace text-uppercase text-success';
                renderResults(data.topics);

                if (data.round < TOTAL_ROUNDS) {
                    btn.disabled = false;
                    btn.textContent = 'ПОЧАТИ КОЛО ' + (data.round + 1);
                    btn.onclick = () => startDebate(data.round + 1);
                } else {
                    btn.disabled = false;
                    btn.textContent = 'ПОВТОРИТИ КОЛО ' + data.round;
                    btn.onclick = () => startDebate(data.round);
                }

            } else if (data.type === 'error') {
                finished = true;
                source.close();
                statusEl.textContent = 'ПОМИЛКА: ' + data.text;
                statusEl.className = 'mt-2 fw-bold font-monospace text-uppercase text-danger';
                updateStepper(null);
                btn.disabled = false;
                btn.textContent = 'СПРОБУВАТИ ЩЕ РАЗ';
                btn.onclick = () => startDebate(roundNo);
            }
        };

        source.onerror = () => {
            source.close();
            if (finished) return;
            statusEl.textContent = 'ПОМИЛКА З\u2019ЄДНАННЯ';
            statusEl.className = 'mt-2 fw-bold font-monospace text-uppercase text-danger';
            updateStepper(null);
            btn.disabled = false;
            btn.textContent = 'СПРОБУВАТИ ЩЕ РАЗ';
            btn.onclick = () => startDebate(roundNo);
        };
    }

    btn.onclick = () => startDebate(parseInt(btn.dataset.currentRound));
});