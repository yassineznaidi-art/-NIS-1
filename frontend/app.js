// NIS App v0.1 — frontend, no competing intelligence layer
const api = {
  async getSessions(){ const r=await fetch('/api/sessions'); if(!r.ok) throw new Error('sessions failed'); return r.json(); },
  async newSession(title){ const r=await fetch('/api/sessions',{method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({title})}); return r.json(); },
  async getSession(id){ const r=await fetch(`/api/sessions/${id}`); if(!r.ok) throw new Error('not found'); return r.json(); },
  async chat(message, session_id, attachments){
    const r=await fetch('/api/chat',{method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({message, session_id, attachments})});
    const j=await r.json();
    if(!r.ok) throw Object.assign(new Error(j.message||'chat failed'), {data:j});
    return j;
  },
  async config(){ const r=await fetch('/api/config'); return r.json(); },
  async health(){ const r=await fetch('/api/health'); return r.json(); },
};

let state = {
  sessionId: null,
  sessions: [],
  sending: false,
};

// DOM
const conversation = document.getElementById('conversation');
const emptyState = document.getElementById('emptyState');
const input = document.getElementById('input');
const btnSend = document.getElementById('btnSend');
const btnNew = document.getElementById('btnNew');
const btnSessions = document.getElementById('btnSessions');
const sessionsDrawer = document.getElementById('sessionsDrawer');
const drawerOverlay = document.getElementById('drawerOverlay');
const btnCloseDrawer = document.getElementById('btnCloseDrawer');
const sessionsList = document.getElementById('sessionsList');
const statusEl = document.getElementById('status');
const toast = document.getElementById('toast');
const suggestions = document.getElementById('suggestions');
const btnSettings = document.getElementById('btnSettings');
const settingsDialog = document.getElementById('settingsDialog');
const providerNote = document.getElementById('providerNote');
const healthOut = document.getElementById('healthOut');

function showToast(msg, ms=2200){
  toast.textContent = msg;
  toast.classList.remove('hidden');
  setTimeout(()=>toast.classList.add('hidden'), ms);
}

function escapeHtml(s){
  return s.replace(/[&<>"']/g, c=>({ '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}

function linkify(text){
  // Minimal linkify for provenance URLs, without exposing internals
  const urlRe = /(https?:\/\/[^\s)]+)\)?/g;
  return escapeHtml(text).replace(urlRe, '<a href="$1" target="_blank" rel="noopener">$1</a>').replace(/\n/g,'<br>');
}

function addMessage(role, content, meta){
  if(emptyState) emptyState.style.display='none';
  const div = document.createElement('div');
  div.className = `msg ${role}` + (meta?.mock ? ' mock' : '');
  const contentDiv = document.createElement('div');
  contentDiv.className = 'content';
  contentDiv.innerHTML = linkify(content);
  div.appendChild(contentDiv);
  if(meta && (meta.deliberation_level || meta.verification || meta.trace_id)){
    const m = document.createElement('div');
    m.className = 'meta';
    if(meta.deliberation_level) { const s=document.createElement('span'); s.textContent=meta.deliberation_level; m.appendChild(s); }
    if(meta.verification) { const s=document.createElement('span'); s.textContent=meta.verification; m.appendChild(s); }
    if(meta.mock) { const s=document.createElement('span'); s.textContent='MOCK'; m.appendChild(s); }
    // Trace shown only in debug
    if(localStorage.getItem('nis_debug')==='true' && meta.trace_id){
      const s=document.createElement('span'); s.textContent=meta.trace_id.slice(0,16); m.appendChild(s);
    }
    div.appendChild(m);
  }
  conversation.appendChild(div);
  conversation.scrollTop = conversation.scrollHeight;
  window.scrollTo(0, document.body.scrollHeight);
  return div;
}

function showTyping(){
  const t = document.createElement('div');
  t.className='typing';
  t.id='typing';
  t.innerHTML='<div class="dot"></div><div class="dot"></div><div class="dot"></div>';
  conversation.appendChild(t);
  t.scrollIntoView({behavior:'smooth'});
  return t;
}
function hideTyping(){
  const t=document.getElementById('typing');
  if(t) t.remove();
}

async function loadSessions(){
  try{
    const {sessions} = await api.getSessions();
    state.sessions = sessions;
    renderSessions();
  }catch(e){ console.warn(e); }
}
function renderSessions(){
  sessionsList.innerHTML='';
  if(state.sessions.length===0){
    sessionsList.innerHTML='<div style="color:var(--muted);font-size:13px;text-align:center;padding:20px">No conversations yet</div>';
    return;
  }
  state.sessions.forEach(s=>{
    const div=document.createElement('div');
    div.className='session-item' + (s.id===state.sessionId ? ' active' : '');
    div.innerHTML=`<div class="title">${escapeHtml(s.title||'New conversation')}</div><div class="preview">${escapeHtml(s.preview||'')}</div><div class="meta"><span>${new Date(s.updated_at*1000).toLocaleDateString()}</span><span>${s.message_count} messages</span></div>`;
    div.onclick=()=> openSession(s.id);
    sessionsList.appendChild(div);
  });
}

async function openSession(id){
  try{
    const {session} = await api.getSession(id);
    state.sessionId = id;
    conversation.innerHTML='';
    if(session.messages.length===0){
      // show empty but keep session
      if(emptyState) emptyState.style.display='none';
    }
    session.messages.forEach(m=>{
      addMessage(m.role, m.content, m.meta);
    });
    closeDrawer();
    input.focus();
    renderSessions();
  }catch(e){ showToast('Could not open conversation'); }
}

async function newConversation(){
  try{
    const {session} = await api.newSession();
    state.sessionId = session.id;
    conversation.innerHTML='';
    if(emptyState){
      // recreate emptyState content structure
      emptyState.style.display='block';
      conversation.appendChild(emptyState);
    }
    showToast('New conversation');
    await loadSessions();
    input.focus();
  }catch(e){ showToast('Could not create conversation'); }
}

function openDrawer(){ sessionsDrawer.classList.remove('hidden'); drawerOverlay.classList.remove('hidden'); loadSessions(); }
function closeDrawer(){ sessionsDrawer.classList.add('hidden'); drawerOverlay.classList.add('hidden'); }

async function send(){
  const text = input.value.trim();
  if(!text || state.sending) return;
  state.sending = true;
  btnSend.disabled = true;
  statusEl.textContent = 'Sending…';
  addMessage('user', text);
  input.value = '';
  input.style.height='auto';
  const typing = showTyping();
  try{
    const res = await api.chat(text, state.sessionId);
    state.sessionId = res.session_id;
    hideTyping();
    addMessage('assistant', res.message, {deliberation_level: res.deliberation_level, verification: res.verification, trace_id: res.trace_id, mock: res.mock});
    statusEl.textContent = res.mock ? 'Mock response' : '';
    await loadSessions();
  }catch(e){
    hideTyping();
    const data = e.data || {};
    const msg = data.message || e.message || 'Failed to send';
    addMessage('assistant', `⚠️ ${msg}\n\n${data.details ? '('+data.details.slice(0,120)+')' : 'Please try again. The request was logged for review and no internal reasoning was exposed.'}`);
    statusEl.textContent = 'Error';
    console.warn('chat error', e, data);
  }finally{
    state.sending=false;
    btnSend.disabled=false;
    statusEl.textContent='';
    input.focus();
  }
}

// Events
btnSend.onclick = send;
input.addEventListener('keydown', (e)=>{
  if(e.key==='Enter' && !e.shiftKey){ e.preventDefault(); send(); }
});
input.addEventListener('input', ()=>{
  input.style.height='auto';
  input.style.height = Math.min(input.scrollHeight, 120) + 'px';
});
btnNew.onclick = newConversation;
btnSessions.onclick = openDrawer;
btnCloseDrawer.onclick = closeDrawer;
drawerOverlay.onclick = closeDrawer;
suggestions?.addEventListener('click', (e)=>{
  const b=e.target.closest('.chip');
  if(b && b.dataset.prompt){ input.value=b.dataset.prompt; input.focus(); }
});
btnSettings.onclick = async ()=>{
  const cfg = await api.config().catch(()=>({}));
  document.getElementById('settingProvider').value = cfg.model_provider || 'nis_core';
  providerNote.textContent = cfg.model_provider==='mock' ? 'Mock is development fallback — not a real AI model.' : 'NIS Core is the authority (N3/N6/N7/N14 remain active).';
  settingsDialog.showModal();
};
document.getElementById('btnHealth').onclick = async ()=>{
  healthOut.textContent='Checking…';
  try{
    const h=await api.health();
    healthOut.textContent = JSON.stringify(h,null,2);
  }catch(e){ healthOut.textContent=String(e); }
};

// Init
(async()=>{
  await loadSessions();
  // If no session, create one lazily on first send; keep empty state visible
  // Preload config for debug flag
  try{
    const cfg=await api.config();
    if(cfg.features?.debug_mode) localStorage.setItem('nis_debug','true');
  }catch{}
  // Check health quietly
  api.health().then(h=>{
    if(h.status!=='ok') showToast('NIS Core degraded — using fallback');
  }).catch(()=>{});
  input.focus();
})();

// Voice stub — disabled, interface prepared
document.getElementById('btnMic').addEventListener('click', ()=> showToast('Voice input — future capability (interface prepared, disabled in v0.1)'));

// Register service worker if needed? No for v0.1
