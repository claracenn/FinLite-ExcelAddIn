(() => {
  const q = (id) => document.getElementById(id);
  const prompt = q('prompt');
  const sendBtn = q('sendBtn');
  const spinner = q('spinner');
  const ans = q('ans');
  const sel = q('sel');
  const counter = q('counter');
  const verbosityCtl = q('verbosity');
  const helpBtn = q('helpBtn');
  const themeBtn = q('themeBtn');
  const toast = q('toast');

  // Character counter + keyboard behavior
  const updateCount = () => counter.textContent = `${prompt.value.length} chars`;
  prompt.addEventListener('input', updateCount); updateCount();
  prompt.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.ctrlKey && !e.shiftKey) { e.preventDefault(); send(); }
    if (e.key === 'Enter' && e.ctrlKey) { /* allow newline */ }
  });

  // Theme
  function setTheme(t){ document.documentElement.setAttribute('data-theme', t); localStorage.setItem('theme', t); }
  const current = localStorage.getItem('theme') || 'light'; setTheme(current);
  themeBtn.addEventListener('click', ()=> setTheme(document.documentElement.getAttribute('data-theme')==='light'?'dark':'light'));

  // Send ask
  async function send(){
    const promptText = prompt.value.trim(); if(!promptText) return;
    spinner.classList.remove('hidden');
    window.chrome.webview.postMessage({ type: 'ask', payload: { prompt: promptText, verbosity: verbosityCtl.value } });
  }
  sendBtn.addEventListener('click', send);
  helpBtn.addEventListener('click', ()=> window.chrome.webview.postMessage({ type:'help' }));

  // Receive messages from .NET
  window.chrome.webview.addEventListener('message', ev => {
    const msg = ev.data || {}; const t = msg.type;
    if (t === 'selection') {
      sel.textContent = msg.text || '';
    } else if (t === 'answer') {
      ans.innerHTML = marked.parse(msg.text || '');
      spinner.classList.add('hidden');
    } else if (t === 'error') {
      spinner.classList.add('hidden');
      showToast(msg.message || 'Unknown error');
    }
  });

  function showToast(text){
    toast.textContent = text; toast.classList.remove('hidden');
    setTimeout(()=> toast.classList.add('hidden'), 3000);
  }
})();