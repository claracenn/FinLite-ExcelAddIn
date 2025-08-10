const web = window.chrome?.webview;
const promptEl = document.getElementById('prompt');
const sendBtn = document.getElementById('sendBtn');
const ansEl = document.getElementById('ans');
const selEl = document.getElementById('sel');
const spinner = document.getElementById('spinner');
const helpBtn = document.getElementById('helpBtn');
const selVerb = document.getElementById('verbosity');

const history = [];
let thinkingIndex = -1;

function setSpinner(on) {
    if (!spinner || !sendBtn) return;
    if (on) { spinner.classList.remove('hidden'); sendBtn.disabled = true; }
    else { spinner.classList.add('hidden'); sendBtn.disabled = false; }
}
function toast(msg) {
    const t = document.getElementById('toast');
    if (!t) return;
    t.textContent = msg || '';
    t.classList.remove('hidden');
    setTimeout(() => t.classList.add('hidden'), 2500);
}
function escapeHtml(s) {
    return (s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;')
        .replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}
function renderHistory() {
    let html = '';
    for (const item of history) {
        if (item.role === 'user') {
            html += `<div><strong>Q:</strong> ${escapeHtml(item.text)}</div>`;
        } else {
            if (item.md && window.marked) {
                let md = marked.parse(item.text || '');
                md = md.replace(/^<p>/i, '').replace(/<\/p>\s*$/i, '').trim();
                html += `<div><strong>A:</strong> ${md}</div>`;
            } else {
                html += `<div><strong>A:</strong> ${escapeHtml(item.text)}</div>`;
            }
        }
        html += `<div style="opacity:.4;border-bottom:1px dashed #ddd;margin:6px 0;"></div>`;
    }
    ansEl.innerHTML = html || '';
}
function getVerbosity() {
    const v = selVerb?.value;
    return (typeof v === 'string' && v) ? v : 'Concise';
}
function showThinking() {
    thinkingIndex = history.length;
    history.push({ role: 'assistant', text: 'Thinking...', md: false });
    renderHistory();
    setSpinner(true);
}
function sendAsk() {
    const text = (promptEl.value || '').trim();
    if (!text) return;

    history.push({ role: 'user', text });
    renderHistory();

    showThinking();

    web?.postMessage(JSON.stringify({
        type: 'ask',
        prompt: text,
        verbosity: getVerbosity()
    }));
}

// UI events
sendBtn?.addEventListener('click', sendAsk);
promptEl?.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.ctrlKey) { e.preventDefault(); sendAsk(); }
});
helpBtn?.addEventListener('click', () => {
    web?.postMessage(JSON.stringify({ type: 'help' }));
});

// Host -> Web
web?.addEventListener('message', (ev) => {
    try {
        const msg = JSON.parse(ev.data || "{}");
        switch (msg.type) {
            case 'selection': {
                const t = (msg.text || '').trim();
                selEl.textContent = t ? t : '(no selection)';
                break;
            }
            case 'thinking': {
                if (thinkingIndex === -1) showThinking(); // ȥ��
                break;
            }
            case 'answer': {
                const text = msg.text || '';
                if (thinkingIndex >= 0 && thinkingIndex < history.length && history[thinkingIndex]?.role === 'assistant') {
                    history[thinkingIndex] = { role: 'assistant', text, md: true };
                    thinkingIndex = -1;
                } else {
                    history.push({ role: 'assistant', text, md: true });
                }
                renderHistory();
                promptEl.value = '';
                setSpinner(false);
                break;
            }
            case 'error': {
                const text = `Error: ${msg.message || 'unknown'}`;
                if (thinkingIndex >= 0 && thinkingIndex < history.length) {
                    history[thinkingIndex] = { role: 'assistant', text, md: false };
                    thinkingIndex = -1;
                } else {
                    history.push({ role: 'assistant', text, md: false });
                }
                renderHistory();
                setSpinner(false);
                break;
            }
            case 'reset': {
                history.length = 0;
                thinkingIndex = -1;
                ansEl.innerHTML = '';
                selEl.textContent = '(no selection)';
                setSpinner(false);
                break;
            }
            case 'toast': {
                toast(msg.message || '');
                break;
            }
            default: break;
        }
    } catch {
        setSpinner(false);
    }
});
