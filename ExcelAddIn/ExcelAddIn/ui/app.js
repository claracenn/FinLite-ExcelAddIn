const web = window.chrome?.webview;
const promptEl = document.getElementById('prompt');
const sendBtn = document.getElementById('sendBtn');
const ansEl = document.getElementById('ans');
const selEl = document.getElementById('sel');
const spinner = document.getElementById('spinner');
const helpBtn = document.getElementById('helpBtn');
const selVerb = document.getElementById('verbosity');
const historyBtn = document.getElementById('historyBtn');
const historyPopover = document.getElementById('historyPopover');
const historyList = document.getElementById('historyList');
const newChatBtn = document.getElementById('newChatBtn');

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

function startNewConversation() {
  chatClear();
  web?.postMessage(JSON.stringify({ type: 'reset' }));
  toast('Started a new chat');
  promptEl?.focus();
}

function renderChatHistory() {
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
function stripSystemDirectives(s) {
    if (!s) return '';
    return s.replace(
        /^\s*please\s+answer\s+(?:concisely|detailedly)\s*:\s*/i,
        ''
    ).trim();
}

function getVerbosity() {
    const v = selVerb?.value;
    return (typeof v === 'string' && v) ? v : 'Concise';
}

function showThinking() {
    thinkingIndex = history.length;
    history.push({ role: 'assistant', text: 'Thinking...', md: false });
    renderChatHistory();
    setSpinner(true);
}

 function sendAsk() {
   const raw = (promptEl.value || '').trim();
   if (!raw) return;

   const clean = stripSystemDirectives(raw);   
   history.push({ role: 'user', text: clean });
   renderChatHistory();

   showThinking();
   web?.postMessage(JSON.stringify({
     type: 'ask',
     prompt: clean, 
     verbosity: getVerbosity()
   }));
 }

function toggleHistoryPopover() {
  if (!historyPopover) return;
  if (historyPopover.hidden) {
    web?.postMessage(JSON.stringify({ type: 'history' }));
    historyPopover.hidden = false;
  } else {
    historyPopover.hidden = true;
  }
}

function fmtShortTime(ms) {
  const d = new Date(ms);
  const now = new Date();
  return d.toDateString() === now.toDateString()
    ? d.toTimeString().slice(0,5)
    : `${d.getMonth()+1}-${String(d.getDate()).padStart(2,'0')}`;
}

function renderHistoryItems(items) {
  if (!historyList) return;
  historyList.innerHTML = '';

  if (!items || items.length === 0) {
    const empty = document.createElement('div');
    empty.className = 'history-item';
    empty.style.opacity = 0.7;
    empty.textContent = 'No history yet';
    historyList.appendChild(empty);
    return;
  }

  for (const it of items) {
    const item = document.createElement('div');
    item.className = 'history-item';

    const titleEl = document.createElement('div');
    titleEl.className = 'history-item-title';
    const rawTitle = it.prompt || it.title || 'New Chat';
    const safeTitle = stripSystemDirectives(rawTitle);
    titleEl.title = safeTitle;
    titleEl.textContent = safeTitle;

    const timeEl = document.createElement('div');
    timeEl.className = 'history-item-time';
    const ts = Date.parse(it.timestamp || '') || Date.now();
    timeEl.textContent = fmtShortTime(ts);

    item.appendChild(titleEl);
    item.appendChild(timeEl);

    item.addEventListener('click', () => {
      historyPopover.hidden = true;
      if (it.id !== undefined && it.id !== null) {
        web?.postMessage(JSON.stringify({ type: 'history-item', id: it.id }));
      }
    });

    historyList.appendChild(item);
  }
}

function chatClear() {
  if (ansEl) ansEl.innerHTML = '';
  history.length = 0;
  thinkingIndex = -1;
  setSpinner(false);
}

function pushToHistory(m) {
  history.push({
    role: m.role,
    text: m.text || '',
    md: !!m.md,
    ts: Date.now()
  });
}


// UI events
sendBtn?.addEventListener('click', sendAsk);

promptEl?.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.ctrlKey) { e.preventDefault(); sendAsk(); }
});

helpBtn?.addEventListener('click', () => {
    web?.postMessage(JSON.stringify({ type: 'help' }));
});

historyBtn?.addEventListener('click', (e) => {
  e.stopPropagation();
  toggleHistoryPopover();
});

newChatBtn?.addEventListener('click', () => {
  if (!historyPopover?.hidden) historyPopover.hidden = true;
  startNewConversation();
});

document.addEventListener('pointerdown', (e) => {
  if (!historyPopover || historyPopover.hidden) return;
  if (!historyPopover.contains(e.target) && e.target !== historyBtn) {
    historyPopover.hidden = true;
  }
});
window.addEventListener('scroll', () => { if (!historyPopover.hidden) historyPopover.hidden = true; }, { passive: true });
window.addEventListener('resize', () => { if (!historyPopover.hidden) historyPopover.hidden = true; });
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape' && !historyPopover?.hidden) historyPopover.hidden = true;
});



// Host -> Web
web?.addEventListener('message', (ev) => {
    try {
        const msg = JSON.parse(ev.data || "{}");
        switch (msg.type) {
            case 'history-data':
                renderHistoryItems(msg.items || []);
                break;
            case 'history-item-data': {
                const it = msg.item || {};
                chatClear();
                pushToHistory({ role: 'user', text: stripSystemDirectives(it.prompt || '') });
                pushToHistory({ role: 'assistant', text: it.response || '', md: true });
                renderChatHistory();
                ansEl?.scrollTo({ top: ansEl.scrollHeight, behavior: 'smooth' });
                break;
            }
            case 'history-error':
                toast(msg.message || 'History error');
                break;
            case 'selection': {
                const t = (msg.text || '').trim();
                selEl.textContent = t ? t : '(no selection)';
                break;
            }
            case 'thinking': {
                if (thinkingIndex === -1) showThinking();
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
                renderChatHistory();
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
                renderChatHistory();
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
