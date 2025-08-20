const web = window.chrome?.webview;
const promptEl = document.getElementById('prompt');
const sendBtn = document.getElementById('sendBtn');
const micBtn = document.getElementById('micBtn');
const ansEl = document.getElementById('ans');
const selEl = document.getElementById('sel');
const spinner = document.getElementById('spinner');
const helpBtn = document.getElementById('helpBtn');
const selVerb = document.getElementById('verbosity');
const historyBtn = document.getElementById('historyBtn');
const historyPopover = document.getElementById('historyPopover');
const historyList = document.getElementById('historyList');
const newChatBtn = document.getElementById('newChatBtn');
const aboutBtn = document.getElementById('aboutBtn');
const aboutPopover = document.getElementById('aboutPopover');

const history = [];
let thinkingIndex = -1;
let isRecording = false;
let mediaRecorder = null;
let audioChunks = [];
let recognition = null;

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

function updatePlaceholder() {
    const verbosity = getVerbosity();
    let placeholder = 'Type a question... (Enter to send, Ctrl+Enter for newline)';
    
    if (verbosity === 'Formula') {
        placeholder = 'Ask a formula (e.g., How to calculate CAGR?)';
    } else if (verbosity === 'Detailed') {
        placeholder = 'Type a detailed question... (Enter to send, Ctrl+Enter for newline)';
    } else {
        placeholder = 'Type a question... (Enter to send, Ctrl+Enter for newline)';
    }
    
    if (promptEl) {
        promptEl.placeholder = placeholder;
    }
}

function showThinking() {
    thinkingIndex = history.length;
    history.push({ role: 'assistant', text: 'Thinking...', md: false });
    renderChatHistory();
    setSpinner(true);
}

async function handleFormulaRequest(prompt) {
    try {
        const response = await fetch('http://127.0.0.1:8000/formula-helper', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                prompt: prompt,
                user_selection: '',
                active_cell: '',
                occupied_ranges: []
            })
        });

        if (response.ok) {
            const result = await response.json();
            
            let formattedResponse;
            
            // Check if this is a fallback response (LLM generated)
            if (result.formula === "See explanation above") {
                // For fallback, just show the explanation without template formatting
                formattedResponse = result.explanation;
            } else {
                // For predefined templates, use the structured format
                formattedResponse = `**Formula Explanation:**
${result.explanation}

**Formula:**
\`${result.formula}\``;
            }
            
            // Replace thinking message with the result
            if (thinkingIndex >= 0 && thinkingIndex < history.length) {
                history[thinkingIndex] = { role: 'assistant', text: formattedResponse, md: true };
            } else {
                history.push({ role: 'assistant', text: formattedResponse, md: true });
            }
            renderChatHistory();
            setSpinner(false);
        } else {
            throw new Error(`HTTP ${response.status}`);
        }
    } catch (error) {
        console.error('Formula request failed:', error);
        const errorMsg = 'Sorry, I encountered an error while generating the formula explanation. Please try again.';
        
        if (thinkingIndex >= 0 && thinkingIndex < history.length) {
            history[thinkingIndex] = { role: 'assistant', text: errorMsg, md: false };
        } else {
            history.push({ role: 'assistant', text: errorMsg, md: false });
        }
        renderChatHistory();
        setSpinner(false);
    }
}

 function sendAsk() {
   const raw = (promptEl.value || '').trim();
   if (!raw) return;

   const clean = stripSystemDirectives(raw);   
   history.push({ role: 'user', text: clean });
   renderChatHistory();
   
   // Clear the prompt input
   promptEl.value = '';

   showThinking();
   
   const verbosity = getVerbosity();
   
   // If Formula mode is selected, call the formula helper endpoint directly
   if (verbosity === 'Formula') {
     handleFormulaRequest(clean);
   } else {
     // Regular chat mode - send to C# backend as before
     web?.postMessage(JSON.stringify({
       type: 'ask',
       prompt: clean, 
       verbosity: verbosity
     }));
   }
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

function toggleAboutPopover() {
  if (!aboutPopover) return;
  // Hide history popover if open
  if (!historyPopover?.hidden) historyPopover.hidden = true;
  // Toggle about popover
  aboutPopover.hidden = !aboutPopover.hidden;
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

// Voice recognition functions
function initializeVoiceRecognition() {
  // Try to use Web Speech API first
  if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = true; // Show interim results
    recognition.lang = 'en-US';
    
    recognition.onstart = function() {
      isRecording = true;
      updateMicButton();
    };
    
    recognition.onresult = function(event) {
      const lastResultIndex = event.results.length - 1;
      const result = event.results[lastResultIndex];
      
      if (result.isFinal) {
        const transcript = result[0].transcript.trim();
        if (transcript) {
          // Append to existing text instead of replacing
          const currentText = promptEl.value.trim();
          if (currentText) {
            promptEl.value = currentText + ' ' + transcript;
          } else {
            promptEl.value = transcript;
          }
          // Auto-stop after getting final result
          recognition.stop();
        }
      }
    };
    
    recognition.onerror = function(event) {
      console.error('Speech recognition error:', event.error);
      // Silent error handling - no toast messages
      isRecording = false;
      updateMicButton();
    };
    
    recognition.onend = function() {
      isRecording = false;
      updateMicButton();
    };
  }
}

function startVoiceRecording() {
  if (recognition) {
    // Use Web Speech API
    try {
      recognition.start();
    } catch (error) {
      console.error('Failed to start speech recognition:', error);
      // Silent error handling
    }
  } else {
    // Fallback to MediaRecorder for file upload
    startMediaRecording();
  }
}

function stopVoiceRecording() {
  if (recognition && isRecording) {
    recognition.stop();
  } else if (mediaRecorder && isRecording) {
    stopMediaRecording();
  }
}

async function startMediaRecording() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorder = new MediaRecorder(stream);
    audioChunks = [];
    
    mediaRecorder.ondataavailable = function(event) {
      audioChunks.push(event.data);
    };
    
    mediaRecorder.onstop = async function() {
      const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
      await uploadAudioForTranscription(audioBlob);
      
      // Stop all tracks to release microphone
      stream.getTracks().forEach(track => track.stop());
    };
    
    mediaRecorder.start();
    isRecording = true;
    updateMicButton();
    
  } catch (error) {
    console.error('Failed to access microphone:', error);
    // Silent error handling
  }
}

function stopMediaRecording() {
  if (mediaRecorder && isRecording) {
    mediaRecorder.stop();
    isRecording = false;
    updateMicButton();
  }
}

async function uploadAudioForTranscription(audioBlob) {
  try {
    const formData = new FormData();
    formData.append('audio_file', audioBlob, 'recording.wav');
    
    const response = await fetch('http://127.0.0.1:8000/speech-to-text', {
      method: 'POST',
      body: formData
    });
    
    if (response.ok) {
      const result = await response.json();
      if (result.text && result.text.trim()) {
        // Append to existing text instead of replacing
        const currentText = promptEl.value.trim();
        if (currentText) {
          promptEl.value = currentText + ' ' + result.text.trim();
        } else {
          promptEl.value = result.text.trim();
        }
      }
    } else {
      console.error('Transcription failed');
    }
  } catch (error) {
    console.error('Failed to upload audio:', error);
    // Silent error handling
  }
}

function updateMicButton() {
  if (!micBtn) return;
  
  if (isRecording) {
    micBtn.classList.add('recording');
    micBtn.title = 'Click to stop recording (or will auto-stop)';
  } else {
    micBtn.classList.remove('recording');
    micBtn.title = 'Click to start voice recording';
  }
}

function handleMicClick() {
  if (isRecording) {
    stopVoiceRecording();
  } else {
    startVoiceRecording();
  }
}


// UI events
sendBtn?.addEventListener('click', sendAsk);

promptEl?.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.ctrlKey) { e.preventDefault(); sendAsk(); }
});

// Update placeholder when verbosity changes
selVerb?.addEventListener('change', updatePlaceholder);

helpBtn?.addEventListener('click', () => {
    web?.postMessage(JSON.stringify({ type: 'help' }));
});

historyBtn?.addEventListener('click', (e) => {
  e.stopPropagation();
  toggleHistoryPopover();
});

aboutBtn?.addEventListener('click', (e) => {
  e.stopPropagation();
  toggleAboutPopover();
});

newChatBtn?.addEventListener('click', () => {
  if (!historyPopover?.hidden) historyPopover.hidden = true;
  if (!aboutPopover?.hidden) aboutPopover.hidden = true;
  startNewConversation();
});

// Microphone button event listener
micBtn?.addEventListener('click', handleMicClick);

// Initialize voice recognition on page load
document.addEventListener('DOMContentLoaded', initializeVoiceRecognition);
// Also initialize immediately in case DOMContentLoaded already fired
initializeVoiceRecognition();

// Initialize placeholder
updatePlaceholder();

document.addEventListener('pointerdown', (e) => {
  if (!historyPopover?.hidden && !historyPopover.contains(e.target) && e.target !== historyBtn) {
    historyPopover.hidden = true;
  }
  if (!aboutPopover?.hidden && !aboutPopover.contains(e.target) && e.target !== aboutBtn) {
    aboutPopover.hidden = true;
  }
});
window.addEventListener('scroll', () => { 
  if (!historyPopover?.hidden) historyPopover.hidden = true; 
  if (!aboutPopover?.hidden) aboutPopover.hidden = true; 
}, { passive: true });
window.addEventListener('resize', () => { 
  if (!historyPopover?.hidden) historyPopover.hidden = true; 
  if (!aboutPopover?.hidden) aboutPopover.hidden = true; 
});
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') {
    if (!historyPopover?.hidden) historyPopover.hidden = true;
    if (!aboutPopover?.hidden) aboutPopover.hidden = true;
  }
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
                if (t) {
                    selEl.textContent = t;
                    selEl.classList.remove('no-selection');
                } else {
                    selEl.textContent = '(no selection)';
                    selEl.classList.add('no-selection');
                }
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
                selEl.classList.add('no-selection');
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
