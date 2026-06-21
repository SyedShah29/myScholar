/* global state */
let sessionId = localStorage.getItem('myscholar_session') || generateId();
let currentMadhab = localStorage.getItem('myscholar_madhab') || 'general';
let currentTheme = localStorage.getItem('myscholar_theme') || 'dark';
let isStreaming = false;
let selectedImageStyle = 'geometric';
let currentAudio = null;
let currentLat = 21.3891;
let currentLon = 39.8579;

/* ─── INIT ──────────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  applyTheme(currentTheme);
  applyMadhab(currentMadhab);
  checkHealth();

  // Event listeners
  document.getElementById('sendBtn').addEventListener('click', sendMessage);
  document.getElementById('chatInput').addEventListener('keydown', onKeyDown);
  document.getElementById('chatInput').addEventListener('input', autoResizeTextarea);
  document.getElementById('newChatBtn').addEventListener('click', newChat);
  document.getElementById('themeToggle').addEventListener('click', toggleTheme);
  document.getElementById('sidebarToggle').addEventListener('click', toggleSidebar);
  document.getElementById('locationBtn').addEventListener('click', requestLocation);
  document.getElementById('imageBtn').addEventListener('click', () => showModal('imageModal'));
  document.getElementById('modalClose').addEventListener('click', () => hideModal('imageModal'));
  document.getElementById('generateImageBtn').addEventListener('click', generateImage);
  
  // Source Modal Close
  document.getElementById('sourceModalClose').addEventListener('click', () => hideModal('sourceModal'));
  document.getElementById('sourceModal').addEventListener('click', (e) => {
    if (e.target === document.getElementById('sourceModal')) hideModal('sourceModal');
  });

  // Madhab pills
  document.querySelectorAll('.madhab-pill').forEach(pill => {
    pill.addEventListener('click', () => applyMadhab(pill.dataset.madhab));
  });

  // Panel tabs
  document.querySelectorAll('.panel-tab').forEach(tab => {
    tab.addEventListener('click', () => switchPanelTab(tab.dataset.tab));
  });

  // Style buttons
  document.querySelectorAll('.style-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.style-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      selectedImageStyle = btn.dataset.style;
    });
  });

  // Starter questions
  document.querySelectorAll('.starter-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const q = btn.dataset.q;
      if (q.toLowerCase().includes('generate') || q.toLowerCase().includes('art')) {
        showModal('imageModal');
      } else {
        document.getElementById('chatInput').value = q;
        sendMessage();
      }
    });
  });

  // Modal backdrop close
  document.getElementById('imageModal').addEventListener('click', (e) => {
    if (e.target === document.getElementById('imageModal')) hideModal('imageModal');
  });

  // Initialize calendar (Mecca default)
  loadCalendar(currentLat, currentLon);
  updateSessionInfo();
});

/* ─── THEME ─────────────────────────────────────────────── */
function applyTheme(theme) {
  currentTheme = theme;
  document.documentElement.setAttribute('data-theme', theme);
  document.getElementById('themeToggle').querySelector('.theme-icon').textContent =
    theme === 'dark' ? '☀️' : '🌙';
  localStorage.setItem('myscholar_theme', theme);
}

function toggleTheme() {
  applyTheme(currentTheme === 'dark' ? 'light' : 'dark');
}

/* ─── MADHAB ─────────────────────────────────────────────── */
function applyMadhab(madhab) {
  currentMadhab = madhab;
  localStorage.setItem('myscholar_madhab', madhab);
  document.querySelectorAll('.madhab-pill').forEach(p => {
    p.classList.toggle('active', p.dataset.madhab === madhab);
  });
  const labels = {
    general: 'General', hanafi: 'Hanafi', maliki: 'Maliki',
    shafii: "Shafi'i", hanbali: 'Hanbali', jafari: "Ja'fari"
  };
  document.getElementById('madhabBadge').textContent = labels[madhab] || madhab;
  
  // Reload calendar times to reflect madhab differences
  if (typeof loadCalendar === 'function') {
    loadCalendar(currentLat, currentLon);
  }
}

/* ─── SIDEBAR ─────────────────────────────────────────────── */
function toggleSidebar() {
  document.getElementById('sidebar').classList.toggle('collapsed');
}

/* ─── HEALTH CHECK ───────────────────────────────────────── */
async function checkHealth() {
  try {
    const resp = await fetch('/api/health');
    const data = await resp.json();
    const dot = document.getElementById('statusDot');
    const text = document.getElementById('statusText');
    if (data.status === 'ok') {
      dot.className = 'status-dot online';
      text.textContent = data.seed_complete ? 'Ready' : 'Seeding corpus...';
    } else {
      dot.className = 'status-dot error';
      text.textContent = 'Error';
    }
  } catch {
    document.getElementById('statusDot').className = 'status-dot error';
    document.getElementById('statusText').textContent = 'Offline';
  }
}

/* ─── SESSION ────────────────────────────────────────────── */
function generateId() {
  return 'session-' + Math.random().toString(36).slice(2, 14);
}

function updateSessionInfo() {
  document.getElementById('sessionInfo').textContent = `Session: ${sessionId.slice(0, 16)}...`;
  localStorage.setItem('myscholar_session', sessionId);
}

async function newChat() {
  try {
    await fetch(`/api/sessions/${sessionId}/clear`, { method: 'POST' });
  } catch {}
  sessionId = generateId();
  updateSessionInfo();
  document.getElementById('chatWindow').innerHTML = `
    <div class="welcome-screen" id="welcomeScreen">
      <div class="welcome-bismillah">بِسْمِ اللّٰهِ الرَّحْمٰنِ الرَّحِيْمِ</div>
      <h1 class="welcome-title">myScholar</h1>
      <p class="welcome-subtitle">Your Islamic AI companion — grounded in Quran, Hadith, and authentic scholarship</p>
      <div class="starter-questions" id="starterQuestions">
        <button class="starter-btn" data-q="What are the five pillars of Islam?">🕌 Five Pillars of Islam</button>
        <button class="starter-btn" data-q="Explain the concept of Tawhid">☝️ Concept of Tawhid</button>
        <button class="starter-btn" data-q="What does Islam say about seeking knowledge?">📚 Seeking Knowledge</button>
        <button class="starter-btn" data-q="Teach me a dua for anxiety and grief">🤲 Dua for Anxiety</button>
        <button class="starter-btn" data-q="What is the importance of Salah in Islam?">🙏 Importance of Salah</button>
        <button class="starter-btn" data-q="Generate an Islamic geometric art image">🎨 Islamic Art</button>
      </div>
    </div>`;
  document.querySelectorAll('.starter-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const q = btn.dataset.q;
      if (q.toLowerCase().includes('generate') || q.toLowerCase().includes('art')) {
        showModal('imageModal');
      } else {
        document.getElementById('chatInput').value = q;
        sendMessage();
      }
    });
  });
  document.getElementById('citationPanel').style.display = 'none';
}

/* ─── SEND MESSAGE ───────────────────────────────────────── */
function onKeyDown(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
}

function autoResizeTextarea() {
  const ta = document.getElementById('chatInput');
  ta.style.height = 'auto';
  ta.style.height = Math.min(ta.scrollHeight, 120) + 'px';
}

async function sendMessage() {
  if (isStreaming) return;
  const input = document.getElementById('chatInput');
  const message = input.value.trim();
  if (!message) return;

  const lowerMsg = message.toLowerCase();
  if ((lowerMsg.includes('generate') || lowerMsg.includes('draw') || lowerMsg.includes('create')) && 
      (lowerMsg.includes('image') || lowerMsg.includes('art') || lowerMsg.includes('picture'))) {
    showModal('imageModal');
    document.getElementById('imagePromptInput').value = message;
    input.value = '';
    return;
  }

  input.value = '';
  input.style.height = 'auto';
  hideWelcome();

  appendUserMessage(message);
  const assistantMsgId = appendAssistantPlaceholder();

  isStreaming = true;
  document.getElementById('sendBtn').disabled = true;
  setStatus('loading', 'Thinking...');

  try {
    await streamResponse(message, assistantMsgId);
  } catch (err) {
    updateAssistantMessage(assistantMsgId, `⚠️ Error: ${err.message}. Please try again.`);
    finalizeMessage(assistantMsgId);
  }

  isStreaming = false;
  document.getElementById('sendBtn').disabled = false;
  setStatus('online', 'Ready');
}

/* ─── STREAMING ──────────────────────────────────────────── */
async function streamResponse(message, msgId) {
  const resp = await fetch('/api/chat/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      session_id: sessionId,
      message,
      madhab: currentMadhab,
      stream: true,
    }),
  });

  if (!resp.ok) {
    throw new Error(`Server error ${resp.status}`);
  }

  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let fullText = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    const lines = buffer.split('\n');
    buffer = lines.pop();

    for (const line of lines) {
      if (!line.startsWith('data:')) continue;
      const data = line.slice(5).trim();
      if (!data || data === '[DONE]') continue;

      try {
        const chunk = JSON.parse(data);
        if (chunk.token && !chunk.done) {
          fullText += chunk.token;
          updateStreamingMessage(msgId, fullText);
        }
        if (chunk.done) {
          const finalText = chunk.full_text || fullText;
          updateAssistantMessage(msgId, renderMarkdown(finalText));
          finalizeMessage(msgId);
          const c = chunk.citations || [];
          const cr = chunk.cross_references || [];
          const d = chunk.dua || null;
          if (c.length > 0 || cr.length > 0 || d) {
            renderCitations(c, cr, d);
            showCitationPanel();
          } else {
            hideCitationPanel();
          }
        }
      } catch {}
    }
  }
}

/* ─── DOM HELPERS ────────────────────────────────────────── */
function hideWelcome() {
  const ws = document.getElementById('welcomeScreen');
  if (ws) ws.remove();
}

function appendUserMessage(text) {
  const chatWindow = document.getElementById('chatWindow');
  const div = document.createElement('div');
  div.className = 'message user';
  div.innerHTML = `
    <div class="message-avatar">🧑</div>
    <div class="message-body">
      <div class="message-bubble">${escapeHtml(text)}</div>
      <div class="message-meta">${formatTime()}</div>
    </div>`;
  chatWindow.appendChild(div);
  scrollToBottom();
}

function appendAssistantPlaceholder() {
  const id = 'msg-' + Date.now();
  const chatWindow = document.getElementById('chatWindow');
  const div = document.createElement('div');
  div.className = 'message assistant message-loading';
  div.id = id;
  div.innerHTML = `
    <div class="message-avatar">🕌</div>
    <div class="message-body">
      <div class="message-bubble">
        <div class="spinner"></div>
        <span>Searching Islamic sources...</span>
      </div>
    </div>`;
  chatWindow.appendChild(div);
  scrollToBottom();
  return id;
}

function updateStreamingMessage(msgId, text) {
  const el = document.getElementById(msgId);
  if (!el) return;
  el.className = 'message assistant';
  el.querySelector('.message-body').innerHTML = `
    <div class="message-bubble">${renderMarkdown(text)}<span class="streaming-cursor"></span></div>
    <div class="message-meta">Streaming...</div>`;
  scrollToBottom();
}

function updateAssistantMessage(msgId, htmlContent) {
  const el = document.getElementById(msgId);
  if (!el) return;
  el.className = 'message assistant';
  el.querySelector('.message-body').innerHTML = `
    <div class="message-bubble">${htmlContent}</div>
    <div class="message-meta">${formatTime()} · myScholar</div>`;
}

function finalizeMessage(msgId) {
  const el = document.getElementById(msgId);
  if (!el) return;
  const cursor = el.querySelector('.streaming-cursor');
  if (cursor) cursor.remove();
  scrollToBottom();
}

function scrollToBottom() {
  const cw = document.getElementById('chatWindow');
  cw.scrollTop = cw.scrollHeight;
}

/* ─── CITATION PANEL ─────────────────────────────────────── */
function showCitationPanel() {
  document.getElementById('citationPanel').style.display = 'flex';
}

function hideCitationPanel() {
  document.getElementById('citationPanel').style.display = 'none';
}

function switchPanelTab(tab) {
  document.querySelectorAll('.panel-tab').forEach(t => t.classList.toggle('active', t.dataset.tab === tab));
  renderActiveTab(tab);
}

let _lastCitations = [];
let _lastCrossRefs = [];
let _lastDua = null;

function renderCitations(citations, crossRefs, dua) {
  _lastCitations = citations || [];
  _lastCrossRefs = crossRefs || [];
  _lastDua = dua;
  
  const hasQuran = _lastCitations.some(c => c.source === 'quran') || _lastCrossRefs.some(c => c.source === 'quran');
  const hasHadith = _lastCitations.some(c => c.source !== 'quran') || _lastCrossRefs.some(c => c.source !== 'quran');
  const hasDua = !!dua;

  document.getElementById('tab-quran').style.display = hasQuran ? 'flex' : 'none';
  document.getElementById('tab-hadith').style.display = hasHadith ? 'flex' : 'none';
  document.getElementById('tab-dua').style.display = hasDua ? 'flex' : 'none';

  let targetTab = hasQuran ? 'quran' : (hasHadith ? 'hadith' : 'dua');
  
  renderActiveTab(targetTab);
  document.querySelectorAll('.panel-tab').forEach(t => t.classList.toggle('active', t.dataset.tab === targetTab));

  if (hasDua && !hasQuran && !hasHadith) {
    targetTab = 'dua';
    switchPanelTab(targetTab);
  }
}

function renderActiveTab(tab) {
  const content = document.getElementById('panelContent');
  content.innerHTML = '';

  if (tab === 'quran') {
    const quranCites = _lastCitations.filter(c => c.source === 'quran');
    const quranRefs = _lastCrossRefs.filter(c => c.source === 'quran');
    if (!quranCites.length && !quranRefs.length) {
      content.innerHTML = '<div style="color:var(--text-muted);font-size:0.8rem;padding:16px">No Quranic verses found for this response.</div>';
      return;
    }
    quranCites.forEach(c => content.appendChild(buildCitationCard(c, false)));
    quranRefs.forEach(c => content.appendChild(buildCitationCard(c, true)));
  } else if (tab === 'hadith') {
    const hadithCites = _lastCitations.filter(c => c.source !== 'quran');
    const hadithRefs = _lastCrossRefs.filter(c => c.source !== 'quran');
    if (!hadithCites.length && !hadithRefs.length) {
      content.innerHTML = '<div style="color:var(--text-muted);font-size:0.8rem;padding:16px">No Hadiths found for this response.</div>';
      return;
    }
    hadithCites.forEach(c => content.appendChild(buildCitationCard(c, false)));
    hadithRefs.forEach(c => content.appendChild(buildCitationCard(c, true)));
  } else if (tab === 'dua') {
    if (!_lastDua) {
      content.innerHTML = '<div style="color:var(--text-muted);font-size:0.8rem;padding:16px">No dua for this response. Ask for a specific dua!</div>';
      return;
    }
    content.appendChild(buildDuaCard(_lastDua));
  }
}

function buildCitationCard(c, isCrossRef = false) {
  const card = document.createElement('div');
  card.className = `citation-card ${c.source}`;
  const sourceLabel = { quran: '📖 Quran', hadith: '📜 Hadith', scholar: '🎓 Scholar' }[c.source] || c.source;
  const keyClass = c.source;

  card.innerHTML = `
    <div class="citation-key ${keyClass}">${isCrossRef ? '🔗 ' : ''}${sourceLabel}</div>
    <div class="citation-ref">${escapeHtml(c.reference)}</div>
    ${c.collection ? `<div class="citation-collection">${escapeHtml(c.collection)}</div>` : ''}
    <div class="citation-text">${escapeHtml(c.text)}</div>
    ${c.arabic ? `<div class="citation-arabic">${escapeHtml(c.arabic)}</div>` : ''}
    ${c.audio_url ? `<button class="citation-audio-btn" data-url="${escapeHtml(c.audio_url)}">▶ Play Recitation</button>` : ''}
  `;

  if (c.audio_url) {
    card.querySelector('.citation-audio-btn').addEventListener('click', (e) => {
      e.stopPropagation(); // prevent modal opening
      playAudio(c.audio_url, e.target);
    });
  }

  // Click to open Modal
  card.addEventListener('click', () => {
    showSourceModal({
      title: `${isCrossRef ? '🔗 ' : ''}${sourceLabel}`,
      text: c.text,
      arabic: c.arabic,
      collection: c.collection,
      reference: c.reference,
      audio_url: c.audio_url
    });
  });

  return card;
}

function buildDuaCard(dua) {
  const card = document.createElement('div');
  card.className = 'dua-card';
  card.innerHTML = `
    <div class="dua-title">🤲 Dua — ${escapeHtml(dua.context.replace(/_/g, ' '))}</div>
    ${dua.arabic ? `<div class="dua-arabic">${escapeHtml(dua.arabic)}</div>` : ''}
    ${dua.transliteration ? `<div class="dua-transliteration">${escapeHtml(dua.transliteration)}</div>` : ''}
    <div class="dua-text">${escapeHtml(dua.text)}</div>
    ${dua.source ? `<div class="dua-source">Source: ${escapeHtml(dua.source)}</div>` : ''}
  `;

  card.addEventListener('click', () => {
    showSourceModal({
      title: `🤲 Dua — ${dua.context.replace(/_/g, ' ')}`,
      text: dua.text,
      arabic: dua.arabic,
      transliteration: dua.transliteration,
      collection: dua.source
    });
  });

  return card;
}

/* ─── AUDIO ──────────────────────────────────────────────── */
function playAudio(url, btn) {
  if (currentAudio) {
    currentAudio.pause();
    currentAudio = null;
    document.querySelectorAll('.citation-audio-btn').forEach(b => { b.textContent = '▶ Play Recitation'; });
    if (btn.dataset.playing === 'true') {
      btn.dataset.playing = 'false';
      return;
    }
  }
  currentAudio = new Audio(url);
  currentAudio.play();
  btn.textContent = '⏸ Playing...';
  btn.dataset.playing = 'true';
  currentAudio.addEventListener('ended', () => {
    btn.textContent = '▶ Play Recitation';
    btn.dataset.playing = 'false';
    currentAudio = null;
  });
}

/* ─── CALENDAR ───────────────────────────────────────────── */
async function loadCalendar(lat, lon) {
  try {
    const resp = await fetch(`/api/calendar?lat=${lat}&lon=${lon}&madhab=${currentMadhab}`);
    const data = await resp.json();

    document.getElementById('hijriValue').textContent = data.hijri_date || 'N/A';
    document.getElementById('gregorianDate').textContent = data.gregorian_date || '';

    const prayerDiv = document.getElementById('prayerTimes');
    const prayers = ['Fajr', 'Dhuhr', 'Asr', 'Maghrib', 'Isha'];
    if (data.prayer_times && Object.keys(data.prayer_times).length > 0) {
      prayerDiv.innerHTML = prayers.map(p =>
        `<div class="prayer-row">
          <span class="prayer-name">${p}</span>
          <span class="prayer-time">${data.prayer_times[p] || '--:--'}</span>
        </div>`
      ).join('');
    }

    // Qibla
    if (data.qibla_direction !== undefined && lat !== 21.3891) {
      document.getElementById('qiblaDisplay').style.display = 'flex';
      document.getElementById('compassArrow').style.transform = `rotate(${data.qibla_direction}deg)`;
      document.getElementById('qiblaDegrees').textContent = `${Math.round(data.qibla_direction)}° from North`;
    }

    if (data.upcoming_events && data.upcoming_events.length) {
      const section = document.getElementById('upcomingSection');
      section.style.display = 'block';
      document.getElementById('eventsList').innerHTML = data.upcoming_events.slice(0, 4).map(e =>
        `<div class="event-item">
          <div style="font-weight:600;margin-bottom:2px;">📅 ${escapeHtml(e.name)}</div>
          <div style="font-size:0.65rem;color:var(--text-muted);display:flex;justify-content:space-between;">
            <span>${escapeHtml(e.hijri)}</span>
            <span>${escapeHtml(e.gregorian)}</span>
          </div>
        </div>`
      ).join('');
    }
  } catch (err) {
    document.getElementById('hijriValue').textContent = 'Unavailable';
  }
}

function requestLocation() {
  if (!navigator.geolocation) {
    alert('Geolocation not supported by your browser.');
    return;
  }
  document.getElementById('locationBtn').textContent = '📍 Getting location...';
  navigator.geolocation.getCurrentPosition(
    pos => {
      currentLat = pos.coords.latitude;
      currentLon = pos.coords.longitude;
      loadCalendar(currentLat, currentLon);
      document.getElementById('locationBtn').textContent = '✅ Location set';
      document.getElementById('locationNote').textContent = 'Using your location';
    },
    () => {
      document.getElementById('locationBtn').textContent = '📍 Get Prayer Times';
      alert('Location access denied. Using Mecca as default.');
    }
  );
}

/* ─── IMAGE GENERATION ───────────────────────────────────── */
async function generateImage() {
  const prompt = document.getElementById('imagePromptInput').value.trim();
  if (!prompt) {
    alert('Please describe the art you want to generate.');
    return;
  }

  document.getElementById('imageResult').style.display = 'none';
  document.getElementById('imageLoading').style.display = 'flex';
  document.getElementById('generateImageBtn').disabled = true;

  try {
    const resp = await fetch('/api/images', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sessionId,
        prompt,
        style: selectedImageStyle,
      }),
    });
    const data = await resp.json();

    if (data.image_url) {
      const img = document.getElementById('generatedImage');
      img.src = data.image_url;
      img.onload = () => {
        document.getElementById('imageLoading').style.display = 'none';
        document.getElementById('imageResult').style.display = 'flex';
        document.getElementById('downloadLink').href = data.image_url;
      };
      img.onerror = () => {
        document.getElementById('imageLoading').style.display = 'none';
        alert('Image generation failed. The service may be temporarily unavailable.');
      };
    } else if (data.moderation && !data.moderation.allowed) {
      document.getElementById('imageLoading').style.display = 'none';
      alert(`⚠️ ${data.moderation.reason}\n\n${data.moderation.safe_alternative}`);
    }
  } catch (err) {
    document.getElementById('imageLoading').style.display = 'none';
    alert('Failed to generate image: ' + err.message);
  } finally {
    document.getElementById('generateImageBtn').disabled = false;
  }
}

/* ─── MODAL ──────────────────────────────────────────────── */
function showModal(id) {
  document.getElementById(id).style.display = 'flex';
  document.body.style.overflow = 'hidden';
}

function hideModal(id) {
  document.getElementById(id).style.display = 'none';
  document.body.style.overflow = '';
  if (id === 'imageModal') {
    document.getElementById('imageResult').style.display = 'none';
    document.getElementById('imageLoading').style.display = 'none';
  }
}

function showSourceModal(data) {
  document.getElementById('sourceModalTitle').innerHTML = escapeHtml(data.title) + (data.reference ? ` <span style="font-size: 0.9rem; font-weight:normal; margin-left:8px; opacity:0.8;">${escapeHtml(data.reference)}</span>` : '');
  
  const textEl = document.getElementById('sourceModalText');
  textEl.textContent = data.text || '';
  
  const arabicEl = document.getElementById('sourceModalArabic');
  if (data.arabic) {
    arabicEl.textContent = data.arabic;
    arabicEl.style.display = 'block';
  } else {
    arabicEl.style.display = 'none';
  }
  
  const transEl = document.getElementById('sourceModalTransliteration');
  if (data.transliteration) {
    transEl.textContent = data.transliteration;
    transEl.style.display = 'block';
  } else {
    transEl.style.display = 'none';
  }
  
  const collEl = document.getElementById('sourceModalCollection');
  if (data.collection) {
    collEl.textContent = data.collection;
    collEl.style.display = 'block';
  } else {
    collEl.style.display = 'none';
  }
  
  const audioContainer = document.getElementById('sourceModalAudioContainer');
  const audioBtn = document.getElementById('sourceModalAudioBtn');
  // Remove old listeners to avoid multiple fires
  const newAudioBtn = audioBtn.cloneNode(true);
  audioBtn.parentNode.replaceChild(newAudioBtn, audioBtn);
  
  if (data.audio_url) {
    newAudioBtn.textContent = '▶ Play Recitation';
    newAudioBtn.dataset.playing = 'false';
    newAudioBtn.addEventListener('click', (e) => {
      playAudio(data.audio_url, e.target);
    });
    audioContainer.style.display = 'block';
  } else {
    audioContainer.style.display = 'none';
  }
  
  showModal('sourceModal');
}

/* ─── STATUS ─────────────────────────────────────────────── */
function setStatus(type, text) {
  document.getElementById('statusDot').className = `status-dot ${type}`;
  document.getElementById('statusText').textContent = text;
}

/* ─── MARKDOWN RENDERER ──────────────────────────────────── */
function renderMarkdown(text) {
  if (!text) return '';
  return text
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    // Bold
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    // Italic
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    // Code
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    // Inline citations [Quran 2:255] → styled span
    .replace(/\[([^\]]+)\]/g, '<span class="inline-cite">$1</span>')
    // Headings
    .replace(/^### (.*$)/gm, '<h3>$1</h3>')
    .replace(/^## (.*$)/gm, '<h3>$1</h3>')
    .replace(/^# (.*$)/gm, '<h3>$1</h3>')
    // Bullet lists
    .replace(/^\- (.*)/gm, '<li>$1</li>')
    .replace(/^• (.*)/gm, '<li>$1</li>')
    // Numbered lists
    .replace(/^\d+\. (.*)/gm, '<li>$1</li>')
    // Wrap consecutive <li> in <ul>
    .replace(/(<li>.*<\/li>\n?)+/g, m => `<ul>${m}</ul>`)
    // Paragraphs
    .replace(/\n\n/g, '</p><p>')
    .replace(/\n/g, '<br>');
}

function escapeHtml(str) {
  if (typeof str !== 'string') return '';
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function formatTime() {
  return new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}
