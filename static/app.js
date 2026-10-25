// Team Workflow SVV - Modern Single Page Web Application (v2.1.1)
// State Management, Interactive Multi-Select & Full Feature Parity

const API_BASE = '';

let state = {
  token: localStorage.getItem('svv_token') || '',
  user: null,
  tasks: [],
  operators: [],
  allUsers: [],
  kpiSummary: null,
  currentPage: 'kanban',
  commanderTab: 'create',
  kpiTab: 'leaderboard',
  kanbanView: 'board',
  draggedTaskId: null,
  activeTaskId: null,
  chartKpi: null,
  chartOntime: null,
  multiSelect: {
    createAssignees: [],
    editAssignees: [],
    handoverAssignees: [],
  },
  editingLogId: null,
};

const THAI_MONTHS = {
  1: 'มกราคม', 2: 'กุมภาพันธ์', 3: 'มีนาคม', 4: 'เมษายน',
  5: 'พฤษภาคม', 6: 'มิถุนายน', 7: 'กรกฎาคม', 8: 'สิงหาคม',
  9: 'กันยายน', 10: 'ตุลาคม', 11: 'พฤศจิกายน', 12: 'ธันวาคม',
};

// --- Toast Notifications ---
function showToast(message, type = 'info') {
  const toast = document.getElementById('toastNotification');
  if (!toast) return;
  toast.innerText = message;
  toast.className = 'fixed bottom-5 right-5 z-50 max-w-sm px-4 py-3 text-white text-xs font-semibold rounded-2xl shadow-xl border transition transform duration-200 ' +
    (type === 'success' ? 'bg-emerald-600 border-emerald-500' :
     type === 'error' ? 'bg-rose-600 border-rose-500' :
     type === 'warning' ? 'bg-amber-600 border-amber-500' : 'bg-slate-900 border-slate-800');
  toast.classList.remove('hidden', 'translate-y-2');
  setTimeout(() => {
    toast.classList.add('translate-y-2');
    setTimeout(() => toast.classList.add('hidden'), 200);
  }, 3200);
}

// --- API Request Wrapper ---
async function api(endpoint, options = {}) {
  const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) };
  if (state.token) {
    headers['Authorization'] = `Bearer ${state.token}`;
  }
  try {
    const res = await fetch(API_BASE + endpoint, { ...options, headers });
    if (res.status === 401) {
      handleLogout();
      throw new Error('Session expired. Please log in again.');
    }
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(data.detail || 'เกิดข้อผิดพลาดในการเชื่อมต่อ');
    }
    return data;
  } catch (err) {
    console.error(`API Error [${endpoint}]:`, err);
    throw err;
  }
}

// --- Helper: Image Compression & File to Base64 ---
function fileToBase64(file) {
  return new Promise((resolve, reject) => {
    if (!file) return resolve(null);
    const fname = (file.name || '').toLowerCase();

    if (fname.endsWith('.pdf') || file.type === 'application/pdf') {
      const reader = new FileReader();
      reader.onload = () => {
        const res = reader.result || '';
        const b64 = res.includes(',') ? res.split(',')[1] : res;
        const safeName = (file.name || 'document.pdf').replace(/;/g, '_');
        resolve(`data:application/pdf;name=${safeName};base64,${b64}`);
      };
      reader.onerror = (err) => reject(err);
      reader.readAsDataURL(file);
      return;
    }

    if (file.type && file.type.startsWith('image/')) {
      const reader = new FileReader();
      reader.onload = (e) => {
        const img = new Image();
        img.onload = () => {
          try {
            const maxSize = 1280;
            let width = img.width;
            let height = img.height;
            if (width > maxSize || height > maxSize) {
              if (width > height) {
                height = Math.round((height * maxSize) / width);
                width = maxSize;
              } else {
                width = Math.round((width * maxSize) / height);
                height = maxSize;
              }
            }
            const canvas = document.createElement('canvas');
            canvas.width = width;
            canvas.height = height;
            const ctx = canvas.getContext('2d');
            ctx.fillStyle = '#FFFFFF';
            ctx.fillRect(0, 0, width, height);
            ctx.drawImage(img, 0, 0, width, height);
            resolve(canvas.toDataURL('image/jpeg', 0.82));
          } catch (err) {
            resolve(e.target.result);
          }
        };
        img.onerror = () => resolve(e.target.result);
        img.src = e.target.result;
      };
      reader.onerror = (err) => reject(err);
      reader.readAsDataURL(file);
      return;
    }

    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = (error) => reject(error);
    reader.readAsDataURL(file);
  });
}

// --- Google Drive & Attachment Helpers ---
function getGdriveFileId(url) {
  if (!url) return null;
  const str = String(url).trim();
  if (!str.includes('drive.google.com') && !str.includes('docs.google.com')) return null;
  let m = str.match(/\/file\/d\/([a-zA-Z0-9_-]+)/);
  if (m) return m[1];
  m = str.match(/\/d\/([a-zA-Z0-9_-]+)/);
  if (m) return m[1];
  m = str.match(/[?&]id=([a-zA-Z0-9_-]+)/);
  if (m) return m[1];
  return null;
}

function convertGdriveUrl(url) {
  if (!url) return url;
  const fid = getGdriveFileId(url);
  if (fid) return `https://lh3.googleusercontent.com/d/${fid}=w1000`;
  return String(url).trim();
}

function isPdfAttachment(val) {
  if (!val) return false;
  const v = String(val).trim().toLowerCase();
  return v.startsWith('data:application/pdf') || v.endsWith('.pdf') || v.includes('.pdf?');
}

function renderAttachmentPreviewHtml(fileVal, caption = 'ไฟล์แนบ') {
  if (!fileVal || !String(fileVal).trim()) return '';
  const val = String(fileVal).trim();

  if (isPdfAttachment(val)) {
    let pdfFilename = 'attached_document.pdf';
    if (val.startsWith('data:application/pdf')) {
      const m = val.match(/name=([^;]+);/);
      if (m) pdfFilename = m[1];
    } else {
      pdfFilename = val.split('/').pop().split('?')[0] || 'document.pdf';
    }
    return `
      <div class="mt-2 p-3 rounded-xl bg-white border border-slate-200 space-y-2">
        <div class="flex items-center justify-between gap-2 flex-wrap">
          <span class="text-xs font-bold text-slate-700">📄 ${escapeHtml(caption)}: ${escapeHtml(pdfFilename)}</span>
          <a href="${val}" download="${escapeHtml(pdfFilename)}" target="_blank"
            class="px-3 py-1 rounded-lg bg-svv-600 hover:bg-svv-700 text-white text-[11px] font-bold transition">
            📥 ดาวน์โหลดไฟล์เอกสาร PDF
          </a>
        </div>
        <iframe src="${val}" class="w-full h-64 rounded-lg border border-slate-200 bg-slate-50" loading="lazy"></iframe>
      </div>
    `;
  }

  const gdriveId = getGdriveFileId(val);
  if (gdriveId) {
    const previewUrl = `https://drive.google.com/file/d/${gdriveId}/preview`;
    return `
      <div class="mt-2 p-3 rounded-xl bg-white border border-slate-200 space-y-2">
        <div class="flex items-center justify-between gap-2 flex-wrap">
          <span class="text-xs font-bold text-slate-700">🖼️ ${escapeHtml(caption)} (Google Drive)</span>
          <a href="${escapeHtml(val)}" target="_blank"
            class="px-3 py-1 rounded-lg bg-slate-800 hover:bg-slate-900 text-white text-[11px] font-bold transition">
            🔗 เปิดดูไฟล์แนบจาก Google Drive (แท็บใหม่)
          </a>
        </div>
        <iframe src="${previewUrl}" class="w-full h-60 rounded-lg border border-slate-200 bg-slate-50" allow="autoplay" loading="lazy"></iframe>
      </div>
    `;
  }

  return `
    <div class="mt-2 p-2.5 rounded-xl bg-white border border-slate-200 space-y-1.5">
      <div class="flex items-center justify-between">
        <span class="text-[11px] font-bold text-slate-600">🖼️ ${escapeHtml(caption)}</span>
        ${val.startsWith('http') ? `<a href="${escapeHtml(val)}" target="_blank" class="text-[11px] text-svv-600 font-bold hover:underline">🔗 เปิดลิงก์ไฟล์แนบเต็ม</a>` : ''}
      </div>
      <img src="${val}" alt="${escapeHtml(caption)}" class="max-h-60 rounded-lg border border-slate-200 object-contain bg-slate-50 mx-auto cursor-pointer"
        onclick="window.open('${val}')"
        onerror="this.outerHTML='<a href=\\'${escapeHtml(val)}\\' target=\\'_blank\\' class=\\'text-xs text-svv-600 font-bold underline\\'>🔗 คลิกเพื่อเปิดดูลิงก์ไฟล์แนบ</a>'" />
    </div>
  `;
}

// --- Interactive Multi-Select Operators (Fixes selection bug!) ---
function renderMultiSelect(containerId, groupName, selectedUsernames = null) {
  const container = document.getElementById(containerId);
  if (!container) return;

  if (selectedUsernames !== null) {
    state.multiSelect[groupName] = [...selectedUsernames];
  }
  const currentSelected = state.multiSelect[groupName] || [];

  if (!state.operators || state.operators.length === 0) {
    container.innerHTML = '<p class="text-xs text-slate-400 text-center py-3">ไม่พบรายชื่อผู้ปฏิบัติงาน</p>';
    return;
  }

  container.innerHTML = state.operators.map(op => {
    const isChecked = currentSelected.includes(op.username);
    return `
      <div onclick="toggleMultiOption('${groupName}', '${escapeHtml(op.username)}')"
        class="multi-option-pill flex items-center justify-between px-3 py-2 rounded-xl border cursor-pointer text-xs ${
          isChecked
            ? 'selected border-svv-500 bg-sky-50 text-svv-800 font-bold shadow-sm'
            : 'border-slate-200 bg-white text-slate-700 hover:bg-slate-50'
        }">
        <div class="flex items-center gap-2.5 truncate">
          <input type="checkbox" ${isChecked ? 'checked' : ''} class="w-4 h-4 rounded text-svv-600 pointer-events-none" readonly />
          <span class="truncate">${escapeHtml(op.display_name || op.fullname || op.username)}</span>
        </div>
        ${isChecked ? '<span class="text-[10px] bg-svv-600 text-white px-2 py-0.5 rounded-full font-bold shrink-0">เลือกแล้ว ✓</span>' : ''}
      </div>
    `;
  }).join('');

  if (groupName === 'createAssignees') {
    const countEl = document.getElementById('createAssigneesCount');
    if (countEl) {
      if (currentSelected.length === 0) {
        countEl.innerText = '⚠️ ยังไม่ได้เลือกผู้ปฏิบัติงาน (คลิกที่รายชื่อด้านบนเพื่อเลือกได้หลายคน)';
        countEl.className = 'text-[11px] text-amber-600 font-semibold mt-1';
      } else {
        const names = currentSelected.map(u => {
          const found = state.operators.find(o => o.username === u);
          return found ? (found.fullname || found.username) : u;
        });
        countEl.innerText = `✅ เลือกแล้ว ${currentSelected.length} คน: ${names.join(', ')}`;
        countEl.className = 'text-[11px] text-svv-700 font-bold mt-1';
      }
    }
  }
}

function toggleMultiOption(groupName, username) {
  const list = state.multiSelect[groupName] || [];
  const idx = list.indexOf(username);
  if (idx >= 0) {
    list.splice(idx, 1);
  } else {
    list.push(username);
  }
  state.multiSelect[groupName] = list;

  const containerMap = {
    createAssignees: 'createAssigneesContainer',
    editAssignees: 'editAssigneesContainer',
    handoverAssignees: 'handoverAssigneesContainer',
  };
  renderMultiSelect(containerMap[groupName], groupName);
}

function selectAllMulti(groupName, selectAll) {
  if (selectAll) {
    state.multiSelect[groupName] = state.operators.map(op => op.username);
  } else {
    state.multiSelect[groupName] = [];
  }
  const containerMap = {
    createAssignees: 'createAssigneesContainer',
    editAssignees: 'editAssigneesContainer',
    handoverAssignees: 'handoverAssigneesContainer',
  };
  renderMultiSelect(containerMap[groupName], groupName);
}

function getSelectedMulti(groupName) {
  return state.multiSelect[groupName] || [];
}

// --- Initialize App ---
document.addEventListener('DOMContentLoaded', async () => {
  const loader = document.getElementById('globalLoader');
  try {
    const today = new Date().toISOString().split('T')[0];
    const dueEl = document.getElementById('taskDueDate');
    if (dueEl && !dueEl.value) dueEl.value = today;
    const filterDateEl = document.getElementById('filterDueDate');
    if (filterDateEl && !filterDateEl.value) filterDateEl.value = today;

    if (state.token) {
      const res = await api('/api/auth/me');
      state.user = res.user;
      showApp();
      await loadAllData();

      const params = new URLSearchParams(window.location.search);
      const urlPage = params.get('page');
      if (urlPage && ['commander', 'kanban', 'kpi', 'admin'].includes(urlPage)) {
        navigateTo(urlPage, false);
      } else {
        const defaultPage = state.user.is_commander ? 'commander' : 'kanban';
        navigateTo(defaultPage, false);
      }
    } else {
      showAuth();
    }
  } catch (err) {
    showAuth();
  } finally {
    if (loader) loader.classList.add('hidden');
  }

  window.addEventListener('popstate', () => {
    const params = new URLSearchParams(window.location.search);
    const p = params.get('page') || 'kanban';
    navigateTo(p, false);
  });
});

// --- Auth Controls ---
function switchAuthTab(tab) {
  document.getElementById('loginForm').classList.toggle('hidden', tab !== 'login');
  document.getElementById('registerForm').classList.toggle('hidden', tab !== 'register');
  document.getElementById('resetForm').classList.toggle('hidden', tab !== 'reset');

  const bL = document.getElementById('tabBtnLogin');
  const bR = document.getElementById('tabBtnRegister');
  const bS = document.getElementById('tabBtnReset');

  bL.className = tab === 'login' ? 'pb-3 border-b-2 border-svv-600 text-svv-700' : 'pb-3 border-b-2 border-transparent hover:text-slate-700';
  bR.className = tab === 'register' ? 'pb-3 border-b-2 border-svv-600 text-svv-700' : 'pb-3 border-b-2 border-transparent hover:text-slate-700';
  bS.className = tab === 'reset' ? 'pb-3 border-b-2 border-svv-600 text-svv-700' : 'pb-3 border-b-2 border-transparent hover:text-slate-700';
}

function showAuth() {
  document.getElementById('authScreen').classList.remove('hidden');
  document.getElementById('appScreen').classList.add('hidden');
}

function showApp() {
  document.getElementById('authScreen').classList.add('hidden');
  document.getElementById('appScreen').classList.remove('hidden');
  renderUserProfile();
}

function handleLogout() {
  localStorage.removeItem('svv_token');
  state.token = '';
  state.user = null;
  window.location.href = window.location.pathname;
}

async function handleLogin(e) {
  e.preventDefault();
  const alertEl = document.getElementById('loginAlert');
  alertEl.classList.add('hidden');
  const username = document.getElementById('loginUsername').value.trim();
  const password = document.getElementById('loginPassword').value.trim();

  try {
    const res = await api('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password })
    });
    state.token = res.token;
    state.user = res.user;
    localStorage.setItem('svv_token', res.token);
    showApp();
    await loadAllData();
    const defaultPage = state.user.is_commander ? 'commander' : 'kanban';
    navigateTo(defaultPage);
    showToast(`ยินดีต้อนรับคุณ ${state.user.fullname || state.user.username}`, 'success');
  } catch (err) {
    alertEl.innerText = err.message;
    alertEl.classList.remove('hidden');
  }
}

async function handleRegister(e) {
  e.preventDefault();
  const alertEl = document.getElementById('registerAlert');
  alertEl.classList.add('hidden');
  const p1 = document.getElementById('regPassword').value;
  const p2 = document.getElementById('regPassword2').value;
  if (p1 !== p2) {
    alertEl.className = 'text-xs p-2.5 rounded-lg bg-red-50 text-red-600 border border-red-200';
    alertEl.innerText = 'รหัสผ่านไม่ตรงกัน';
    alertEl.classList.remove('hidden');
    return;
  }
  const payload = {
    username: document.getElementById('regUsername').value.trim(),
    fullname: document.getElementById('regFullname').value.trim(),
    email: document.getElementById('regEmail').value.trim(),
    phone: document.getElementById('regPhone').value.trim(),
    password: p1
  };
  try {
    const res = await api('/api/auth/register', { method: 'POST', body: JSON.stringify(payload) });
    alertEl.className = 'text-xs p-2.5 rounded-lg bg-emerald-50 text-emerald-700 border border-emerald-200';
    alertEl.innerText = res.message || 'สมัครสมาชิกสำเร็จ! กรุณารอ Admin อนุมัติ';
    alertEl.classList.remove('hidden');
    e.target.reset();
  } catch (err) {
    alertEl.className = 'text-xs p-2.5 rounded-lg bg-red-50 text-red-600 border border-red-200';
    alertEl.innerText = err.message;
    alertEl.classList.remove('hidden');
  }
}

async function handleResetPassword(e) {
  e.preventDefault();
  const alertEl = document.getElementById('resetAlert');
  alertEl.classList.add('hidden');
  const p1 = document.getElementById('resetNewPass').value;
  const p2 = document.getElementById('resetNewPass2').value;
  if (p1 !== p2) {
    alertEl.className = 'text-xs p-2.5 rounded-lg bg-red-50 text-red-600 border border-red-200';
    alertEl.innerText = 'รหัสผ่านไม่ตรงกัน';
    alertEl.classList.remove('hidden');
    return;
  }
  const payload = {
    username: document.getElementById('resetUsername').value.trim(),
    contact: document.getElementById('resetContact').value.trim(),
    new_password: p1
  };
  try {
    const res = await api('/api/auth/reset-password', { method: 'POST', body: JSON.stringify(payload) });
    alertEl.className = 'text-xs p-2.5 rounded-lg bg-emerald-50 text-emerald-700 border border-emerald-200';
    alertEl.innerText = res.message || 'บันทึกรหัสผ่านใหม่เรียบร้อยแล้ว';
    alertEl.classList.remove('hidden');
    e.target.reset();
  } catch (err) {
    alertEl.className = 'text-xs p-2.5 rounded-lg bg-red-50 text-red-600 border border-red-200';
    alertEl.innerText = err.message;
    alertEl.classList.remove('hidden');
  }
}

// --- Render User Profile in Sidebar ---
function renderUserProfile() {
  if (!state.user) return;
  document.getElementById('userFullName').innerText = state.user.fullname || state.user.username;
  document.getElementById('userHandle').innerText = `@${state.user.username}`;

  const badgesContainer = document.getElementById('userRoleBadges');
  badgesContainer.innerHTML = '';
  if (state.user.is_admin) {
    badgesContainer.innerHTML += '<span class="badge-status badge-overdue text-[10px]">🛡️ Admin</span>';
  }
  const roles = state.user.parsed_roles || [];
  roles.forEach(r => {
    if (r === 'ระดับสั่งการ') {
      badgesContainer.innerHTML += '<span class="badge-status badge-review text-[10px]">👑 สั่งการ</span>';
    } else if (r === 'ปฏิบัติงาน') {
      badgesContainer.innerHTML += '<span class="badge-status badge-done text-[10px]">🛠️ ปฏิบัติงาน</span>';
    }
  });

  const adminNav = document.getElementById('navAdmin');
  if (adminNav) {
    adminNav.classList.toggle('hidden', !state.user.is_admin);
    adminNav.classList.toggle('flex', state.user.is_admin);
  }

  const cmdNav = document.getElementById('navCommander');
  if (cmdNav) {
    cmdNav.classList.toggle('hidden', !state.user.is_commander);
    cmdNav.classList.toggle('flex', state.user.is_commander);
  }
}

// --- Navigation between Modules ---
function navigateTo(pageId, updateHistory = true) {
  state.currentPage = pageId;
  if (updateHistory) {
    const url = new URL(window.location);
    url.searchParams.set('page', pageId);
    window.history.pushState({}, '', url);
  }

  document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
  const activeBtn = document.getElementById(`nav${pageId.charAt(0).toUpperCase() + pageId.slice(1)}`);
  if (activeBtn) activeBtn.classList.add('active');

  document.querySelectorAll('.view-panel').forEach(el => el.classList.add('hidden'));
  const activeView = document.getElementById(`view${pageId.charAt(0).toUpperCase() + pageId.slice(1)}`);
  if (activeView) activeView.classList.remove('hidden');

  const titles = {
    commander: { icon: '🎯', title: 'โมดูลที่ 1: ระบบสั่งการและมอบหมายงาน (Commander)' },
    kanban: { icon: '📋', title: 'โมดูลที่ 2: กระดานงาน (Kanban Board)' },
    kpi: { icon: '📊', title: 'โมดูลที่ 3: แดชบอร์ดคะแนน KPI' },
    admin: { icon: '🛡️', title: 'โมดูลที่ 4: แผงควบคุมผู้ดูแลระบบ (Admin Panel)' }
  };
  const cur = titles[pageId] || titles.kanban;
  document.getElementById('pageIcon').innerText = cur.icon;
  document.getElementById('pageTitle').innerText = cur.title;

  if (pageId === 'kanban') renderKanbanBoard();
  if (pageId === 'commander') renderCommanderTabs();
  if (pageId === 'kpi') renderKpiDashboard();
  if (pageId === 'admin') renderAdminPanel();
}

// --- Load All Data ---
async function loadAllData() {
  try {
    const [tasks, ops] = await Promise.all([
      api('/api/tasks'),
      api('/api/users/operators')
    ]);
    state.tasks = tasks || [];
    state.operators = ops || [];

    populateOperatorDropdowns();
    renderKanbanBoard();
    updatePendingBadgeCounts();
    if (state.currentPage === 'commander') renderCommanderTabs();
    if (state.currentPage === 'kpi') renderKpiDashboard();
  } catch (err) {
    console.error('Failed to load data:', err);
  }
}

async function refreshData() {
  const syncStatus = document.getElementById('syncStatus');
  if (syncStatus) syncStatus.innerText = '🔄 กำลังซิงค์...';
  await loadAllData();
  if (syncStatus) syncStatus.innerText = '● ซิงค์เรียบร้อย';
  showToast('ซิงค์ข้อมูลกับเซิร์ฟเวอร์เรียบร้อยแล้ว', 'success');
}

function updatePendingBadgeCounts() {
  const handovers = state.tasks.filter(t => t.handover_status === 'Pending').length;
  const reviews = state.tasks.filter(t => t.status === 'In Review').length;
  const hEl = document.getElementById('pendingHandoverCount');
  const rEl = document.getElementById('pendingReviewCount');
  if (hEl) hEl.innerText = handovers;
  if (rEl) rEl.innerText = reviews;
}

function populateOperatorDropdowns() {
  // Interactive multi-select containers
  renderMultiSelect('createAssigneesContainer', 'createAssignees', state.multiSelect.createAssignees);
  renderMultiSelect('editAssigneesContainer', 'editAssignees', state.multiSelect.editAssignees);
  renderMultiSelect('handoverAssigneesContainer', 'handoverAssignees', state.multiSelect.handoverAssignees);

  // Standard <select> dropdowns
  const selects = ['adjOperator', 'directAdjUser', 'filterAssignee', 'histFilterEmp'];
  selects.forEach(id => {
    const el = document.getElementById(id);
    if (!el) return;
    const prevVal = el.value;
    const isFilter = id.startsWith('filter') || id.startsWith('hist');
    el.innerHTML = isFilter ? '<option value="ALL">ทุกคน (ทั้งหมด)</option>' : '';
    state.operators.forEach(op => {
      const opt = document.createElement('option');
      opt.value = op.username;
      opt.innerText = op.display_name || `@${op.username}`;
      el.appendChild(opt);
    });
    if (prevVal && Array.from(el.options).some(o => o.value === prevVal)) {
      el.value = prevVal;
    }
  });

  // Creator filter in Commander Manage Table
  const creatorFilter = document.getElementById('manageCreatorFilter');
  if (creatorFilter) {
    const prevCreator = creatorFilter.value || 'ALL';
    const creators = [...new Set(state.tasks.map(t => t.creator_username).filter(Boolean))].sort();
    creatorFilter.innerHTML = '<option value="ALL">ทั้งหมด (งานของทุกคน)</option>' +
      creators.map(c => `<option value="${escapeHtml(c)}">👑 @${escapeHtml(c)}</option>`).join('');
    if (Array.from(creatorFilter.options).some(o => o.value === prevCreator)) {
      creatorFilter.value = prevCreator;
    }
  }
}

// ==========================================
// MODULE 1: COMMANDER LOGIC
// ==========================================

function switchCommanderTab(tab) {
  state.commanderTab = tab;
  const tabs = ['create', 'handover', 'review', 'kpi_adj'];
  tabs.forEach(t => {
    const btn = document.getElementById(`cmdTab${t.charAt(0).toUpperCase() + t.slice(1)}`);
    const pane = document.getElementById(`cmdPane${t.charAt(0).toUpperCase() + t.slice(1)}`);
    if (btn) {
      btn.className = t === tab ?
        'px-4 py-2 rounded-xl text-xs font-bold bg-svv-600 text-white shadow-sm transition' :
        'px-4 py-2 rounded-xl text-xs font-bold bg-white border border-slate-200 text-slate-700 hover:bg-slate-50 transition';
    }
    if (pane) pane.classList.toggle('hidden', t !== tab);
  });
  renderCommanderTabs();
}

function renderCommanderTabs() {
  renderManageTasksTable();
  if (state.commanderTab === 'handover') renderHandoverRequests();
  if (state.commanderTab === 'review') renderReviewTasks();
}

async function handleCreateTask(e) {
  e.preventDefault();
  const title = document.getElementById('taskTitle').value.trim();
  const dueDate = document.getElementById('taskDueDate').value;
  const taskType = document.getElementById('taskType').value;
  const priority = document.getElementById('taskPriority').value;
  const desc = document.getElementById('taskDesc').value.trim();
  const attachUrlInput = document.getElementById('taskAttachUrl').value.trim();
  const fileInput = document.getElementById('taskAttachFile');

  const selectedOps = getSelectedMulti('createAssignees');
  if (!selectedOps.length) {
    showToast('⚠️ กรุณาคลิกเลือกผู้ปฏิบัติงานอย่างน้อย 1 คน', 'warning');
    return;
  }

  let finalAttach = attachUrlInput ? convertGdriveUrl(attachUrlInput) : null;
  if (fileInput && fileInput.files[0]) {
    finalAttach = await fileToBase64(fileInput.files[0]);
  }

  const btn = document.getElementById('btnCreateTaskSubmit');
  if (btn) {
    btn.disabled = true;
    btn.innerText = 'กำลังบันทึกและส่งงาน...';
  }

  try {
    await api('/api/tasks', {
      method: 'POST',
      body: JSON.stringify({
        title,
        description: desc,
        task_type: taskType,
        priority,
        due_date: dueDate,
        assignees: selectedOps,
        attachment_url: finalAttach
      })
    });
    showToast('✅ มอบหมายงานสำเร็จแล้ว!', 'success');
    e.target.reset();
    document.getElementById('taskDueDate').value = new Date().toISOString().split('T')[0];
    selectAllMulti('createAssignees', false);
    await loadAllData();
  } catch (err) {
    showToast(`เกิดข้อผิดพลาด: ${err.message}`, 'error');
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerText = 'บันทึกและส่งงานไปยังกระดาน';
    }
  }
}

function renderManageTasksTable() {
  const container = document.getElementById('manageTasksTable');
  const countLabel = document.getElementById('manageTasksCount');
  if (!container) return;

  const search = (document.getElementById('manageSearchInput')?.value || '').trim().toLowerCase();
  const creatorFilter = document.getElementById('manageCreatorFilter')?.value || 'ALL';
  const statFilter = document.getElementById('manageStatusFilter')?.value || 'ALL';

  let list = state.tasks;
  if (creatorFilter !== 'ALL') {
    list = list.filter(t => t.creator_username === creatorFilter);
  }
  if (statFilter !== 'ALL') {
    list = list.filter(t => t.status === statFilter);
  }
  if (search) {
    list = list.filter(t =>
      (t.title || '').toLowerCase().includes(search) ||
      (t.description || '').toLowerCase().includes(search) ||
      (t.assignee_name || '').toLowerCase().includes(search)
    );
  }

  if (countLabel) {
    countLabel.innerText = `พบงานทั้งหมด ${list.length} รายการ (จากทั้งหมด ${state.tasks.length} งานในระบบ)`;
  }

  if (!list.length) {
    container.innerHTML = '<div class="p-6 bg-slate-50 rounded-2xl border border-slate-200 text-center text-xs text-slate-500">ไม่พบรายการงานตามเงื่อนไขที่เลือก</div>';
    return;
  }

  container.innerHTML = list.map(t => `
    <div class="bg-slate-50/70 hover:bg-white p-3.5 rounded-2xl border border-slate-200 shadow-sm flex flex-col md:flex-row items-start md:items-center justify-between gap-3 transition">
      <div class="space-y-1 overflow-hidden">
        <div class="flex flex-wrap items-center gap-2">
          <span class="font-bold text-xs text-slate-800">${escapeHtml(t.title)}</span>
          <span class="badge-status ${getBadgeClass(t.status)} text-[10px]">${t.status}</span>
          <span class="px-2 py-0.5 bg-slate-200/70 text-slate-700 rounded text-[10px] font-bold">${escapeHtml(t.task_type || 'Project')}</span>
          ${getDueAlertBadgeHtml(t)}
        </div>
        <p class="text-[11px] text-slate-500">
          👤 ผู้ปฏิบัติงาน: <strong class="text-slate-700">${escapeHtml(t.assignee_name || '-')}</strong> |
          👑 ผู้สั่งการ: <strong class="text-slate-700">@${escapeHtml(t.creator_username || '-')}</strong> |
          📅 กำหนดส่ง: <strong>${t.due_date || '-'}</strong>
        </p>
      </div>
      <div class="flex items-center gap-2 shrink-0">
        <button onclick="openEditModal('${t.task_id}')" class="px-3 py-1.5 bg-white hover:bg-svv-50 text-svv-700 border border-slate-200 rounded-xl text-xs font-bold transition">✏️ แก้ไขงาน</button>
        <button onclick="openProgressModal('${t.task_id}')" class="px-3 py-1.5 bg-white hover:bg-slate-100 text-slate-700 border border-slate-200 rounded-xl text-xs font-bold transition">📝 คืบหน้า</button>
        <button onclick="handleDeleteTask('${t.task_id}', '${escapeHtml(t.title)}')" class="px-3 py-1.5 bg-rose-50 hover:bg-rose-100 text-rose-600 rounded-xl text-xs font-bold transition">🗑️ ลบงาน</button>
      </div>
    </div>
  `).join('');
}

function renderHandoverRequests() {
  const container = document.getElementById('handoverList');
  if (!container) return;
  const handovers = state.tasks.filter(t => t.handover_status === 'Pending');
  if (!handovers.length) {
    container.innerHTML = '<div class="p-6 bg-white rounded-2xl border border-slate-200 text-center text-xs text-slate-500">✨ ไม่มีคำขอส่งต่องานค้างอยู่ในขณะนี้</div>';
    return;
  }
  container.innerHTML = handovers.map(t => `
    <div class="bg-white p-4 rounded-2xl border border-amber-200 shadow-sm space-y-2.5">
      <div class="flex items-center justify-between">
        <h4 class="text-xs font-extrabold text-slate-800">📌 ${escapeHtml(t.title)}</h4>
        <span class="badge-status badge-review text-[10px]">🔄 รออนุมัติส่งต่อ</span>
      </div>
      <p class="text-xs text-slate-600">
        ผู้รับผิดชอบเดิม: <code class="bg-slate-100 px-1.5 py-0.5 rounded font-semibold">${escapeHtml(t.assignee_name || '-')}</code>
        ➔ ขอเปลี่ยนเป็น: <code class="bg-sky-50 text-svv-800 px-1.5 py-0.5 rounded font-bold">${escapeHtml(t.handover_to || '-')}</code>
      </p>
      <p class="text-xs text-slate-500 bg-slate-50 p-2.5 rounded-xl border border-slate-100">💬 เหตุผล: "${escapeHtml(t.handover_reason || '-')}"</p>
      <div class="flex flex-wrap gap-2 pt-2 border-t border-slate-100">
        <button onclick="handleHandoverAction('${t.task_id}', 'approve')" class="px-3.5 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-bold transition">✅ อนุมัติการปรับเปลี่ยน</button>
        <button onclick="handleHandoverAction('${t.task_id}', 'reject')" class="px-3.5 py-1.5 bg-rose-600 hover:bg-rose-700 text-white rounded-xl text-xs font-bold transition">❌ ปฏิเสธ</button>
        <button onclick="openHandoverModal('${t.task_id}')" class="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl text-xs font-bold transition">✏️ ปรับเปลี่ยนเอง</button>
      </div>
    </div>
  `).join('');
}

async function handleHandoverAction(taskId, action) {
  try {
    const res = await api(`/api/tasks/${taskId}/handover-action`, {
      method: 'POST',
      body: JSON.stringify({ action })
    });
    showToast(res.message || 'บันทึกสำเร็จ', 'success');
    closeModal('modalHandover');
    await loadAllData();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

function renderReviewTasks() {
  const container = document.getElementById('reviewList');
  if (!container) return;
  const reviews = state.tasks.filter(t => t.status === 'In Review');
  if (!reviews.length) {
    container.innerHTML = '<div class="p-6 bg-white rounded-2xl border border-slate-200 text-center text-xs text-slate-500">✨ ไม่มีงานที่รอตรวจรับในขณะนี้</div>';
    return;
  }
  container.innerHTML = reviews.map(t => {
    const otBadge = t.is_ontime === true ? '<span class="badge-status badge-done text-[10px]">🟢 ส่งตรงเวลา (+10 แต้ม)</span>' :
                    t.is_ontime === false ? '<span class="badge-status badge-overdue text-[10px]">🔴 ส่งเกินกำหนด (-5 แต้ม)</span>' : '';
    const noteRaw = t.submission_note || '';
    const cleanNote = noteRaw.split('[ATTACHED_IMAGE:')[0].trim();
    let subAttach = null;
    if (noteRaw.includes('[ATTACHED_IMAGE:')) {
      subAttach = noteRaw.split('[ATTACHED_IMAGE:')[1].split(']')[0].trim();
    }

    return `
      <div class="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm space-y-3">
        <div class="flex flex-wrap items-center justify-between gap-2">
          <div class="flex items-center gap-2 flex-wrap">
            <h4 class="text-sm font-extrabold text-slate-800">⭐ ${escapeHtml(t.title)}</h4>
            ${otBadge}
            <span class="px-2 py-0.5 bg-slate-100 text-slate-600 rounded text-[10px] font-bold">${escapeHtml(t.task_type || 'Project')}</span>
          </div>
          <span class="text-xs text-slate-500 font-semibold">📅 กำหนดส่ง: ${t.due_date || '-'}</span>
        </div>
        <p class="text-xs text-slate-600">
          👤 ผู้ปฏิบัติงาน: <strong>${escapeHtml(t.assignee_name || '-')}</strong> |
          👑 ผู้สั่งการ: <strong>@${escapeHtml(t.creator_username || '-')}</strong>
        </p>
        <div class="p-3 bg-slate-50 rounded-xl border border-slate-200 text-xs text-slate-700 space-y-1">
          <p class="font-bold text-slate-800">📝 รายงานสรุปผลงานที่ส่งมอบ:</p>
          <p class="whitespace-pre-line">${escapeHtml(cleanNote || '-')}</p>
        </div>
        ${t.attachment_url ? renderAttachmentPreviewHtml(t.attachment_url, 'ไฟล์แนบโจทย์งาน') : ''}
        ${subAttach ? renderAttachmentPreviewHtml(subAttach, 'ไฟล์ผลงานที่ส่งมอบ') : ''}
        <div class="flex flex-wrap gap-2 pt-2 border-t border-slate-100">
          <button onclick="openApproveModal('${t.task_id}')" class="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-bold shadow-sm transition">🏆 ตรวจรับงานสำเร็จ (Done)</button>
          <button onclick="openReturnModal('${t.task_id}')" class="px-4 py-2 bg-amber-50 hover:bg-amber-100 text-amber-800 border border-amber-200 rounded-xl text-xs font-bold transition">🔄 ส่งกลับ / ทำต่อ / ประเมินผล</button>
          <button onclick="openProgressModal('${t.task_id}')" class="px-3 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl text-xs font-bold transition">📝 ความคืบหน้า</button>
          <button onclick="openEditModal('${t.task_id}')" class="px-3 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl text-xs font-bold transition">✏️ แก้ไขงาน</button>
        </div>
      </div>
    `;
  }).join('');
}

async function handleKpiAdjustment(e) {
  e.preventDefault();
  const uname = document.getElementById('adjOperator').value;
  const reasonType = document.getElementById('adjType').value;
  const pts = parseFloat(document.getElementById('adjPoints').value);
  const desc = document.getElementById('adjReason').value.trim();

  try {
    const res = await api('/api/kpi/adjustments', {
      method: 'POST',
      body: JSON.stringify({ username: uname, reason_type: reasonType, points: pts, description: desc })
    });
    showToast(res.message || 'บันทึกคะแนนเรียบร้อยแล้ว', 'success');
    e.target.reset();
    await loadAllData();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

async function handleDirectKpiAdjust(e) {
  e.preventDefault();
  const uname = document.getElementById('directAdjUser').value;
  const pts = parseFloat(document.getElementById('directAdjPoints').value);
  const desc = document.getElementById('directAdjReason').value.trim();
  const reasonType = pts < 0 ? 'ความผิดพลาด' : 'ความดีความชอบ';

  try {
    const res = await api('/api/kpi/adjustments', {
      method: 'POST',
      body: JSON.stringify({ username: uname, reason_type: reasonType, points: pts, description: desc })
    });
    showToast(res.message || 'บันทึกการปรับคะแนนเรียบร้อยแล้ว', 'success');
    document.getElementById('directAdjReason').value = '';
    await renderKpiDashboard();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

// ==========================================
// MODULE 2: KANBAN BOARD & DRAG-AND-DROP
// ==========================================

function toggleDateFilter() {
  const checked = document.getElementById('filterUseDate')?.checked;
  const dateInput = document.getElementById('filterDueDate');
  if (dateInput) {
    dateInput.disabled = !checked;
  }
  applyKanbanFilters();
}

function switchKanbanView(view) {
  state.kanbanView = view;
  const boardEl = document.getElementById('kanbanBoardWrapper');
  const listEl = document.getElementById('compactListView');
  const btnB = document.getElementById('viewBtnBoard');
  const btnL = document.getElementById('viewBtnList');

  if (view === 'board') {
    boardEl.classList.remove('hidden');
    listEl.classList.add('hidden');
    btnB.className = 'px-3 py-1.5 rounded-lg bg-white shadow-sm text-svv-700';
    btnL.className = 'px-3 py-1.5 rounded-lg text-slate-500 hover:text-slate-700';
    renderKanbanBoard();
  } else {
    boardEl.classList.add('hidden');
    listEl.classList.remove('hidden');
    btnL.className = 'px-3 py-1.5 rounded-lg bg-white shadow-sm text-svv-700';
    btnB.className = 'px-3 py-1.5 rounded-lg text-slate-500 hover:text-slate-700';
    renderCompactList();
  }
}

function applyKanbanFilters() {
  if (state.kanbanView === 'board') renderKanbanBoard();
  else renderCompactList();
}

function getFilteredTasks() {
  const fAssignee = document.getElementById('filterAssignee')?.value || 'ALL';
  const fStatus = document.getElementById('filterStatus')?.value || 'ALL';
  const fType = document.getElementById('filterType')?.value || 'ALL';
  const useDate = document.getElementById('filterUseDate')?.checked || false;
  const fDate = document.getElementById('filterDueDate')?.value || '';

  return state.tasks.filter(t => {
    if (fAssignee !== 'ALL') {
      const assignees = (t.assignee_name || '').split(',').map(s => s.trim());
      if (!assignees.includes(fAssignee)) return false;
    }
    if (fStatus !== 'ALL' && t.status !== fStatus) return false;
    if (fType !== 'ALL' && t.task_type !== fType) return false;
    if (useDate && fDate && (t.due_date || '').slice(0, 10) !== fDate) return false;
    return true;
  });
}

function getDueAlertBadgeHtml(t) {
  if (t.status === 'Done' || t.days_diff === null || t.days_diff === undefined) return '';
  if (t.days_diff < 0) {
    return `<span class="badge-status badge-overdue text-[9px] shrink-0">🚨 เกิน ${Math.abs(t.days_diff)} วัน</span>`;
  }
  if (t.days_diff <= 2) {
    return `<span class="badge-status badge-warning text-[9px] shrink-0">⚠️ เหลือ ${t.days_diff} วัน</span>`;
  }
  return '';
}

function getPriorityBadgeHtml(priority) {
  if (priority === 'Urgent') return '<span class="px-1.5 py-0.5 bg-rose-100 text-rose-700 rounded text-[9px] font-extrabold">🔥 Urgent</span>';
  if (priority === 'High') return '<span class="px-1.5 py-0.5 bg-amber-100 text-amber-800 rounded text-[9px] font-bold">⚡ High</span>';
  return '<span class="px-1.5 py-0.5 bg-slate-100 text-slate-600 rounded text-[9px] font-semibold">📌 Normal</span>';
}

function renderKanbanBoard() {
  const tasks = getFilteredTasks();
  const cols = ['ToDo', 'InProgress', 'InReview', 'Revision', 'Done'];
  const mapping = {
    ToDo: 'To Do',
    InProgress: 'In Progress',
    InReview: 'In Review',
    Revision: 'Revision',
    Done: 'Done'
  };

  cols.forEach(colKey => {
    const statusVal = mapping[colKey];
    const colTasks = tasks.filter(t => t.status === statusVal);
    const countEl = document.getElementById(`colCount${colKey}`);
    const listEl = document.getElementById(`colList${colKey}`);
    if (countEl) countEl.innerText = colTasks.length;
    if (listEl) {
      if (!colTasks.length) {
        listEl.innerHTML = '<div class="h-24 rounded-xl border border-dashed border-slate-200/80 flex items-center justify-center text-[11px] text-slate-400">ไม่มีรายการงาน</div>';
      } else {
        listEl.innerHTML = colTasks.map(t => renderKanbanCard(t)).join('');
      }
    }
  });
}

function renderKanbanCard(t) {
  const isComm = state.user?.is_commander || state.user?.is_admin;
  const dueBadge = getDueAlertBadgeHtml(t);
  const prioBadge = getPriorityBadgeHtml(t.priority);
  const hasAttach = Boolean(t.attachment_url && String(t.attachment_url).trim());
  const isPendingHandover = t.handover_status === 'Pending';

  return `
    <div id="card_${t.task_id}" draggable="true" ondragstart="handleDragStart(event, '${t.task_id}')" ondragend="handleDragEnd(event)" class="kanban-card bg-white p-3 rounded-xl border border-slate-200/90 shadow-sm hover:shadow-md space-y-2">
      <div class="flex items-start justify-between gap-1 flex-wrap">
        <div class="flex items-center gap-1 flex-wrap">
          ${prioBadge}
          <span class="px-1.5 py-0.5 bg-sky-50 text-svv-700 rounded text-[9px] font-bold">${escapeHtml(t.task_type || 'Project')}</span>
        </div>
        ${dueBadge}
      </div>

      <h4 class="text-xs font-extrabold text-slate-800 leading-snug break-words">${escapeHtml(t.title)}</h4>

      <p class="text-[11px] text-slate-600 line-clamp-2">${escapeHtml(t.description || '')}</p>

      ${isPendingHandover ? `
        <div class="px-2 py-1 bg-amber-50 border border-amber-200 rounded-lg text-[10px] text-amber-800 font-bold flex items-center justify-between">
          <span>🔄 รออนุมัติส่งต่อ ➔ @${escapeHtml(t.handover_to || '')}</span>
          <button onclick="openHandoverModal('${t.task_id}')" class="underline">ดู</button>
        </div>
      ` : ''}

      ${hasAttach ? `
        <div>
          <button onclick="openProgressModal('${t.task_id}')" class="px-2 py-0.5 bg-indigo-50 hover:bg-indigo-100 text-indigo-700 rounded text-[10px] font-bold transition">
            ${isPdfAttachment(t.attachment_url) ? '📄 เปิดดูไฟล์ PDF แนบ' : '🖼️ ดูรูปภาพแนบ'}
          </button>
        </div>
      ` : ''}

      <div class="space-y-1 pt-1 border-t border-slate-100 text-[10px] text-slate-500">
        <div class="flex items-center justify-between gap-1">
          <span class="truncate font-semibold text-slate-700" title="${escapeHtml(t.assignee_name || '-')}">👤 ${escapeHtml(t.assignee_name || '-')}</span>
          <span class="shrink-0">📅 ${t.due_date || '-'}</span>
        </div>
        <div class="flex items-center justify-between text-slate-400">
          <span>👑 สั่งโดย: @${escapeHtml(t.creator_username || t.requester_name || '-')}</span>
          ${t.satisfaction_rating ? `<span class="text-amber-500 font-bold">⭐ ${t.satisfaction_rating}</span>` : ''}
        </div>
      </div>

      <div class="flex items-center justify-between pt-2 border-t border-slate-100 text-[11px] gap-1 flex-wrap">
        <div class="flex gap-1">
          <button onclick="openProgressModal('${t.task_id}')" title="บันทึก/ดูความคืบหน้า" class="p-1.5 bg-slate-100 hover:bg-slate-200 rounded-lg text-slate-700 font-bold">📝</button>
          ${t.status !== 'Done' ? `<button onclick="openHandoverModal('${t.task_id}')" title="ส่งต่องาน / ปรับทีม" class="p-1.5 bg-slate-100 hover:bg-slate-200 rounded-lg text-slate-700 font-bold">🤝</button>` : ''}
          ${t.can_edit ? `<button onclick="openEditModal('${t.task_id}')" title="แก้ไขงาน" class="p-1.5 bg-slate-100 hover:bg-slate-200 rounded-lg text-slate-700 font-bold">✏️</button>` : ''}
          ${t.can_delete ? `<button onclick="handleDeleteTask('${t.task_id}', '${escapeHtml(t.title)}')" title="ลบงาน" class="p-1.5 bg-rose-50 hover:bg-rose-100 text-rose-600 rounded-lg font-bold">🗑️</button>` : ''}
        </div>
        <div class="flex gap-1">
          ${(t.status === 'To Do' || t.status === 'Revision') ? `<button onclick="quickMoveTask('${t.task_id}', 'In Progress')" class="px-2 py-1 bg-svv-600 hover:bg-svv-700 text-white font-bold rounded-lg text-[10px] transition">▶️ เริ่มทำ</button>` : ''}
          ${t.status === 'In Progress' ? `<button onclick="openSubmitModal('${t.task_id}')" class="px-2 py-1 bg-svv-50 hover:bg-svv-100 text-svv-700 font-bold rounded-lg text-[10px] border border-svv-200 transition">📤 ส่งงาน</button>` : ''}
          ${t.status === 'In Review' && isComm ? `
            <button onclick="openApproveModal('${t.task_id}')" class="px-2 py-1 bg-emerald-600 hover:bg-emerald-700 text-white font-bold rounded-lg text-[10px] transition">🏆 ตรวจรับ</button>
            <button onclick="openReturnModal('${t.task_id}')" class="px-2 py-1 bg-amber-100 hover:bg-amber-200 text-amber-800 font-bold rounded-lg text-[10px] transition">↩️</button>
          ` : ''}
          ${t.status === 'Done' && isComm ? `<button onclick="openReturnModal('${t.task_id}')" class="px-2 py-1 bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold rounded-lg text-[10px] transition">🔄 ส่งกลับ</button>` : ''}
        </div>
      </div>
    </div>
  `;
}

function renderCompactList() {
  const container = document.getElementById('compactListView');
  if (!container) return;
  const tasks = getFilteredTasks();
  if (!tasks.length) {
    container.innerHTML = '<div class="p-6 bg-white rounded-2xl border border-slate-200 text-center text-xs text-slate-500">ไม่พบรายการงาน</div>';
    return;
  }
  const isComm = state.user?.is_commander || state.user?.is_admin;
  container.innerHTML = tasks.map(t => `
    <div class="bg-white p-3.5 rounded-2xl border border-slate-200 shadow-sm flex flex-col md:flex-row items-start md:items-center justify-between gap-3">
      <div class="space-y-1">
        <div class="flex flex-wrap items-center gap-2">
          <span class="font-extrabold text-xs text-slate-800">${escapeHtml(t.title)}</span>
          <span class="badge-status ${getBadgeClass(t.status)} text-[10px]">${t.status}</span>
          ${getPriorityBadgeHtml(t.priority)}
          <span class="px-1.5 py-0.5 bg-sky-50 text-svv-700 rounded text-[10px] font-bold">${escapeHtml(t.task_type || 'Project')}</span>
          ${getDueAlertBadgeHtml(t)}
        </div>
        <p class="text-[11px] text-slate-500">
          👤 ผู้รับผิดชอบ: <strong>${escapeHtml(t.assignee_name || '-')}</strong> |
          👑 สั่งโดย: <strong>@${escapeHtml(t.creator_username || '-')}</strong> |
          📅 กำหนดส่ง: ${t.due_date || '-'}
        </p>
      </div>
      <div class="flex flex-wrap items-center gap-1.5 shrink-0">
        ${(t.status === 'To Do' || t.status === 'Revision') ? `<button onclick="quickMoveTask('${t.task_id}', 'In Progress')" class="px-2.5 py-1.5 bg-svv-600 text-white rounded-xl text-xs font-bold">▶️ เริ่มทำ</button>` : ''}
        ${t.status === 'In Progress' ? `<button onclick="openSubmitModal('${t.task_id}')" class="px-2.5 py-1.5 bg-emerald-600 text-white rounded-xl text-xs font-bold">📤 ส่งงาน</button>` : ''}
        ${t.status === 'In Review' && isComm ? `<button onclick="openApproveModal('${t.task_id}')" class="px-2.5 py-1.5 bg-emerald-600 text-white rounded-xl text-xs font-bold">🏆 ตรวจรับ</button>` : ''}
        <button onclick="openProgressModal('${t.task_id}')" class="px-2.5 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl text-xs font-bold transition">📝 ความคืบหน้า</button>
        ${t.status !== 'Done' ? `<button onclick="openHandoverModal('${t.task_id}')" class="px-2.5 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl text-xs font-bold transition">🤝 ส่งต่อ</button>` : ''}
        ${t.can_edit ? `<button onclick="openEditModal('${t.task_id}')" class="px-2.5 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl text-xs font-bold transition">✏️ แก้ไข</button>` : ''}
        ${t.can_delete ? `<button onclick="handleDeleteTask('${t.task_id}', '${escapeHtml(t.title)}')" class="px-2.5 py-1.5 bg-rose-50 hover:bg-rose-100 text-rose-600 rounded-xl text-xs font-bold transition">🗑️ ลบ</button>` : ''}
      </div>
    </div>
  `).join('');
}

async function quickMoveTask(taskId, targetStatus) {
  try {
    await api(`/api/tasks/${taskId}/move`, {
      method: 'POST',
      body: JSON.stringify({ target_status: targetStatus })
    });
    showToast(`ย้ายงานไปยัง ${targetStatus} เรียบร้อย`, 'success');
    await loadAllData();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

// Drag and Drop Event Handlers
function handleDragStart(e, taskId) {
  state.draggedTaskId = taskId;
  e.dataTransfer.setData('text/plain', taskId);
  e.target.classList.add('dragging');
}

function handleDragEnd(e) {
  e.target.classList.remove('dragging');
  document.querySelectorAll('.drag-over').forEach(el => el.classList.remove('drag-over'));
}

function handleDragOver(e) {
  e.preventDefault();
  const col = e.currentTarget;
  if (!col.classList.contains('drag-over')) {
    col.classList.add('drag-over');
  }
}

function handleDragLeave(e) {
  e.currentTarget.classList.remove('drag-over');
}

async function handleDrop(e, targetStatus) {
  e.preventDefault();
  e.currentTarget.classList.remove('drag-over');
  const taskId = state.draggedTaskId || e.dataTransfer.getData('text/plain');
  if (!taskId) return;

  const task = state.tasks.find(t => String(t.task_id) === String(taskId));
  if (!task || task.status === targetStatus) return;

  if (targetStatus === 'In Review') {
    openSubmitModal(task.task_id);
    return;
  }
  if (targetStatus === 'Done') {
    if (state.user?.is_commander || state.user?.is_admin) {
      openApproveModal(task.task_id);
    } else {
      showToast('⚠️ เฉพาะผู้มียศระดับสั่งการเท่านั้นที่สามารถตรวจรับงานไป Done ได้', 'warning');
    }
    return;
  }
  if ((targetStatus === 'In Progress' || targetStatus === 'Revision' || targetStatus === 'To Do') && (task.status === 'In Review' || task.status === 'Done')) {
    if (state.user?.is_commander || state.user?.is_admin) {
      openReturnModal(task.task_id, targetStatus);
    } else {
      showToast('⚠️ เฉพาะผู้สั่งการเท่านั้นที่สามารถประเมินผลและย้ายสถานะนี้ได้', 'warning');
    }
    return;
  }

  await quickMoveTask(task.task_id, targetStatus);
}

// ==========================================
// MODULE 3: KPI DASHBOARD & HISTORICAL REPORT
// ==========================================

function switchKpiTab(tab) {
  state.kpiTab = tab;
  document.getElementById('kpiPaneLeaderboard').classList.toggle('hidden', tab !== 'leaderboard');
  document.getElementById('kpiPaneHistory').classList.toggle('hidden', tab !== 'history');

  const btnB = document.getElementById('kpiTabBtnBoard');
  const btnH = document.getElementById('kpiTabBtnHistory');
  btnB.className = tab === 'leaderboard' ? 'text-svv-700 border-b-2 border-svv-600 pb-2 font-bold' : 'text-slate-500 hover:text-slate-800 border-b-2 border-transparent pb-2 font-semibold';
  btnH.className = tab === 'history' ? 'text-svv-700 border-b-2 border-svv-600 pb-2 font-bold' : 'text-slate-500 hover:text-slate-800 border-b-2 border-transparent pb-2 font-semibold';

  if (tab === 'history') renderHistoryReport();
}

async function renderKpiDashboard() {
  try {
    const res = await api('/api/kpi/summary');
    state.kpiSummary = res;

    document.getElementById('kpiCardTotal').innerText = res.overview.total_tasks;
    document.getElementById('kpiCardProg').innerText = res.overview.in_progress;
    document.getElementById('kpiCardRev').innerText = res.overview.in_review;
    document.getElementById('kpiCardDone').innerText = res.overview.done;

    // Collapsible Quick Delete List
    const quickList = document.getElementById('kpiQuickDeleteList');
    if (quickList) {
      if (!state.tasks.length) {
        quickList.innerHTML = '<p class="text-xs text-slate-400 text-center py-3">ไม่มีงานในระบบ</p>';
      } else {
        quickList.innerHTML = state.tasks.map(t => `
          <div class="p-2.5 bg-slate-50 rounded-xl border border-slate-200 flex items-center justify-between gap-2 text-xs">
            <div class="truncate">
              <span class="font-bold text-slate-800">${escapeHtml(t.title)}</span>
              <span class="text-slate-500 ml-2">👤 ${escapeHtml(t.assignee_name || '-')} | สถานะ: <strong>${t.status}</strong></span>
            </div>
            ${t.can_delete ? `<button onclick="handleDeleteTask('${t.task_id}', '${escapeHtml(t.title)}')" class="px-3 py-1 bg-rose-600 hover:bg-rose-700 text-white rounded-lg text-[11px] font-bold shrink-0">🗑️ ลบงาน</button>` : ''}
          </div>
        `).join('');
      }
    }

    // Commander direct KPI adjust box
    const directBox = document.getElementById('kpiDirectAdjustBox');
    if (directBox) {
      const isComm = state.user?.is_commander || state.user?.is_admin;
      directBox.classList.toggle('hidden', !isComm);
    }

    // Render 9-column KPI Leaderboard Table
    const tbody = document.getElementById('kpiTableBody');
    tbody.innerHTML = res.leaderboard.map((item, idx) => `
      <tr class="hover:bg-slate-50 transition">
        <td class="py-3 px-4 font-bold text-slate-800 flex items-center gap-2">
          <span class="text-xs px-2 py-0.5 rounded-full ${idx === 0 ? 'bg-amber-100 text-amber-700 font-extrabold' : 'bg-slate-100 text-slate-600'}">#${idx + 1}</span>
          ${escapeHtml(item.fullname || item.username)}
        </td>
        <td class="py-3 px-3 text-slate-500">@${escapeHtml(item.username)}</td>
        <td class="py-3 px-3 text-center">${item.total_tasks}</td>
        <td class="py-3 px-3 text-center font-bold text-slate-800">${item.done_tasks}</td>
        <td class="py-3 px-3 text-center font-bold text-emerald-600">${item.ontime_count}</td>
        <td class="py-3 px-3 text-center font-bold text-rose-600">${item.late_count}</td>
        <td class="py-3 px-3 text-center text-amber-600 font-bold">⭐ ${item.avg_rating}</td>
        <td class="py-3 px-3 text-center font-bold ${item.manual_points >= 0 ? 'text-emerald-600' : 'text-rose-600'}">${item.manual_points > 0 ? '+' : ''}${item.manual_points}</td>
        <td class="py-3 px-4 text-right font-extrabold text-sm text-svv-700">${item.total_kpi}</td>
      </tr>
    `).join('');

    renderKpiCharts(res.leaderboard);
    renderHistoryReport();
  } catch (err) {
    console.error('Failed to load KPI:', err);
  }
}

function renderKpiCharts(data) {
  const labels = data.map(d => d.fullname || d.username);
  const totalScores = data.map(d => d.total_kpi);
  const ontimes = data.map(d => d.ontime_count);
  const lates = data.map(d => d.late_count);

  const ctx1 = document.getElementById('chartKpiTotal')?.getContext('2d');
  if (ctx1) {
    if (state.chartKpi) state.chartKpi.destroy();
    state.chartKpi = new Chart(ctx1, {
      type: 'bar',
      data: {
        labels,
        datasets: [{
          label: 'คะแนน KPI รวม',
          data: totalScores,
          backgroundColor: '#0284c7',
          borderRadius: 8
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: { y: { beginAtZero: true } }
      }
    });
  }

  const ctx2 = document.getElementById('chartOntimeLate')?.getContext('2d');
  if (ctx2) {
    if (state.chartOntime) state.chartOntime.destroy();
    state.chartOntime = new Chart(ctx2, {
      type: 'bar',
      data: {
        labels,
        datasets: [
          { label: 'ส่งทันเวลา', data: ontimes, backgroundColor: '#10b981', borderRadius: 6 },
          { label: 'ส่งล่าช้า', data: lates, backgroundColor: '#f87171', borderRadius: 6 }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: { y: { beginAtZero: true } }
      }
    });
  }
}

function getTaskThaiMonthYear(t) {
  const raw = t.completed_at || t.due_date || t.created_at || '';
  if (!raw) return 'ไม่ระบุเดือน';
  const d = new Date(raw);
  if (isNaN(d.getTime())) return 'ไม่ระบุเดือน';
  return `${THAI_MONTHS[d.getMonth() + 1]} ${d.getFullYear() + 543}`;
}

function calcTaskKpiScore(t) {
  if (t.status !== 'Done') return 0;
  let score = 5;
  if (t.is_ontime === true) score += 10;
  else if (t.is_ontime === false) score -= 5;
  const r = parseFloat(t.satisfaction_rating || 0);
  if (r > 0) score += r * 4;
  return score;
}

function getFilteredHistoryTasks() {
  const fEmp = document.getElementById('histFilterEmp')?.value || 'ALL';
  const fMonth = document.getElementById('histFilterMonth')?.value || 'ALL';
  const fStat = document.getElementById('histFilterStat')?.value || 'DONE';

  // Populate Thai Month dropdown dynamically
  const monthSelect = document.getElementById('histFilterMonth');
  if (monthSelect) {
    const curVal = monthSelect.value || 'ALL';
    const months = [...new Set(state.tasks.map(t => getTaskThaiMonthYear(t)).filter(Boolean))];
    monthSelect.innerHTML = '<option value="ALL">ทุกเดือน</option>' +
      months.map(m => `<option value="${escapeHtml(m)}">${escapeHtml(m)}</option>`).join('');
    if (Array.from(monthSelect.options).some(o => o.value === curVal)) {
      monthSelect.value = curVal;
    }
  }

  return state.tasks.filter(t => {
    if (fStat === 'DONE' && t.status !== 'Done') return false;
    if (fEmp !== 'ALL') {
      const assignees = (t.assignee_name || '').split(',').map(s => s.trim());
      if (!assignees.includes(fEmp)) return false;
    }
    if (fMonth !== 'ALL' && getTaskThaiMonthYear(t) !== fMonth) return false;
    return true;
  });
}

function renderHistoryReport() {
  const tbody = document.getElementById('historyTableBody');
  const cardsEl = document.getElementById('histSummaryCards');
  const countEl = document.getElementById('histCountLabel');
  if (!tbody) return;

  const filtered = getFilteredHistoryTasks();
  if (countEl) countEl.innerText = `พบรายการงานทั้งหมด: ${filtered.length} งาน`;

  const doneList = filtered.filter(t => t.status === 'Done');
  const ontimeCount = doneList.filter(t => t.is_ontime === true).length;
  const lateCount = doneList.filter(t => t.is_ontime === false).length;
  const rated = doneList.filter(t => parseFloat(t.satisfaction_rating || 0) > 0);
  const avgStar = rated.length ? (rated.reduce((s, t) => s + parseFloat(t.satisfaction_rating), 0) / rated.length).toFixed(1) : '0.0';
  const totalPts = filtered.reduce((s, t) => s + calcTaskKpiScore(t), 0);

  if (cardsEl) {
    cardsEl.innerHTML = `
      <div class="bg-white p-3.5 rounded-2xl border border-slate-200 shadow-sm">
        <span class="text-[11px] font-bold text-slate-500">📋 จำนวนงานที่พบ</span>
        <p class="text-lg font-extrabold text-slate-800 mt-0.5">${filtered.length} งาน</p>
      </div>
      <div class="bg-white p-3.5 rounded-2xl border border-emerald-200 shadow-sm">
        <span class="text-[11px] font-bold text-emerald-600">🟢 ส่งตรงเวลา</span>
        <p class="text-lg font-extrabold text-emerald-700 mt-0.5">${ontimeCount} งาน</p>
      </div>
      <div class="bg-white p-3.5 rounded-2xl border border-rose-200 shadow-sm">
        <span class="text-[11px] font-bold text-rose-600">🔴 ส่งล่าช้า</span>
        <p class="text-lg font-extrabold text-rose-700 mt-0.5">${lateCount} งาน</p>
      </div>
      <div class="bg-white p-3.5 rounded-2xl border border-amber-200 shadow-sm">
        <span class="text-[11px] font-bold text-amber-600">⭐ ความพึงพอใจเฉลี่ย</span>
        <p class="text-lg font-extrabold text-amber-600 mt-0.5">${avgStar} ดาว</p>
      </div>
      <div class="bg-white p-3.5 rounded-2xl border border-svv-200 shadow-sm">
        <span class="text-[11px] font-bold text-svv-700">🏆 แต้ม KPI จากผลงาน</span>
        <p class="text-lg font-extrabold text-svv-700 mt-0.5">+${totalPts} แต้ม</p>
      </div>
    `;
  }

  if (!filtered.length) {
    tbody.innerHTML = '<tr><td colspan="12" class="py-8 text-center text-slate-400">ไม่มีประวัติผลงานตามเงื่อนไขที่เลือก</td></tr>';
    return;
  }

  tbody.innerHTML = filtered.map(t => {
    const ontimeTxt = t.status !== 'Done' ? '⏳ กำลังทำ' : (t.is_ontime === true ? '🟢 ทันเวลา' : '🔴 ล่าช้า');
    const starTxt = t.satisfaction_rating ? `⭐ ${t.satisfaction_rating}` : '-';
    const pts = calcTaskKpiScore(t);
    return `
      <tr class="hover:bg-slate-50 transition">
        <td class="py-2.5 px-3 font-bold text-slate-800">${escapeHtml(t.title)}</td>
        <td class="py-2.5 px-3">${escapeHtml(t.assignee_name || '-')}</td>
        <td class="py-2.5 px-3 text-slate-500">@${escapeHtml(t.creator_username || '-')}</td>
        <td class="py-2.5 px-2">${escapeHtml(t.task_type || 'Project')}</td>
        <td class="py-2.5 px-2">${t.due_date || '-'}</td>
        <td class="py-2.5 px-2">${t.completed_at ? t.completed_at.slice(0, 10) : '-'}</td>
        <td class="py-2.5 px-2">${escapeHtml(getTaskThaiMonthYear(t))}</td>
        <td class="py-2.5 px-2 font-semibold">${ontimeTxt}</td>
        <td class="py-2.5 px-2 font-bold text-amber-600">${starTxt}</td>
        <td class="py-2.5 px-2 text-right font-extrabold text-svv-700">${pts > 0 ? '+' + pts : '0'}</td>
        <td class="py-2.5 px-2"><span class="badge-status ${getBadgeClass(t.status)} text-[10px]">${t.status}</span></td>
        <td class="py-2.5 px-3">
          <button onclick="openProgressModal('${t.task_id}')" class="px-2.5 py-1 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-[11px] font-bold">📝 ดูประวัติ</button>
        </td>
      </tr>
    `;
  }).join('');
}

function downloadHistoryCsv() {
  const filtered = getFilteredHistoryTasks();
  if (!filtered.length) {
    showToast('ไม่มีข้อมูลสำหรับดาวน์โหลด', 'warning');
    return;
  }
  const headers = [
    'ชื่องาน', 'รายละเอียด', 'ผู้รับผิดชอบงาน', 'ผู้สั่งการ', 'ประเภท',
    'กำหนดส่ง', 'วันที่ส่งจริง', 'ประจำเดือน', 'ผลการส่ง', 'คะแนนดาว', 'แต้ม KPI', 'สถานะ'
  ];
  const rows = filtered.map(t => {
    const ontimeTxt = t.status !== 'Done' ? 'กำลังดำเนินการ' : (t.is_ontime === true ? 'ส่งทันเวลา' : 'ส่งล่าช้า');
    return [
      t.title || '',
      (t.description || '').replace(/\r?\n/g, ' '),
      t.assignee_name || '',
      t.creator_username || '',
      t.task_type || 'Project',
      t.due_date || '',
      t.completed_at ? t.completed_at.slice(0, 16) : '',
      getTaskThaiMonthYear(t),
      ontimeTxt,
      t.satisfaction_rating || '',
      calcTaskKpiScore(t),
      t.status || ''
    ].map(v => `"${String(v).replace(/"/g, '""')}"`).join(',');
  });

  const csv = '\uFEFF' + [headers.join(','), ...rows].join('\r\n');
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `SVV_KPI_History_${new Date().toISOString().slice(0, 10)}.csv`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
  showToast('📥 ดาวน์โหลดไฟล์รายงาน Excel (CSV) เรียบร้อยแล้ว', 'success');
}

// ==========================================
// MODULE 4: ADMIN PANEL
// ==========================================

async function renderAdminPanel() {
  if (!state.user?.is_admin) return;
  try {
    const users = await api('/api/admin/users');
    state.allUsers = users;

    const pending = users.filter(u => u.is_approved === false && u.role !== 'Admin');
    const pContainer = document.getElementById('adminPendingUsers');
    if (!pending.length) {
      pContainer.innerHTML = '<div class="p-4 bg-emerald-50 text-emerald-700 rounded-xl text-xs font-semibold">ไม่มีคำขอค้างอยู่ ทุกคนได้รับการอนุมัติแล้ว</div>';
    } else {
      pContainer.innerHTML = pending.map(u => `
        <div class="p-4 bg-slate-50 border border-slate-200 rounded-xl flex flex-col md:flex-row items-start md:items-center justify-between gap-3 text-xs">
          <div>
            <p class="font-bold text-slate-800">${escapeHtml(u.fullname || u.username)} (@${escapeHtml(u.username)})</p>
            <p class="text-slate-500">Email: ${escapeHtml(u.email || '-')} | โทร: ${escapeHtml(u.phone || '-')}</p>
          </div>
          <div class="flex items-center gap-2">
            <select id="sel_role_${u.user_id}" class="px-2.5 py-1.5 bg-white border border-slate-200 rounded-xl text-xs">
              <option value="ปฏิบัติงาน">ปฏิบัติงาน</option>
              <option value="ระดับสั่งการ">ระดับสั่งการ</option>
              <option value="ระดับสั่งการ, ปฏิบัติงาน">ทั้งสองยศ</option>
            </select>
            <button onclick="handleApproveUser('${u.user_id}')" class="px-3.5 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl font-bold transition">อนุมัติ</button>
            <button onclick="handleDeleteUser('${u.user_id}')" class="px-3 py-1.5 bg-rose-50 text-rose-600 hover:bg-rose-100 rounded-xl font-bold transition">ลบ</button>
          </div>
        </div>
      `).join('');
    }

    const uContainer = document.getElementById('adminAllUsers');
    uContainer.innerHTML = users.map(u => {
      const roles = u.parsed_roles || [];
      const isComm = roles.includes('ระดับสั่งการ');
      const isOp = roles.includes('ปฏิบัติงาน');
      return `
        <div class="p-3.5 bg-slate-50 border border-slate-200 rounded-xl flex flex-col md:flex-row items-start md:items-center justify-between gap-3 text-xs">
          <div>
            <p class="font-bold text-slate-800">${escapeHtml(u.fullname || u.username)} <span class="text-slate-500 font-normal">(@${escapeHtml(u.username)})</span></p>
            <p class="text-slate-400 text-[11px]">${escapeHtml(u.email || '-')} | ${escapeHtml(u.phone || '-')}</p>
          </div>
          <div class="flex items-center gap-3">
            <label class="flex items-center gap-1.5 cursor-pointer">
              <input type="checkbox" id="chk_comm_${u.user_id}" ${isComm ? 'checked' : ''} class="rounded text-svv-600">
              <span>ระดับสั่งการ</span>
            </label>
            <label class="flex items-center gap-1.5 cursor-pointer">
              <input type="checkbox" id="chk_op_${u.user_id}" ${isOp ? 'checked' : ''} class="rounded text-svv-600">
              <span>ปฏิบัติงาน</span>
            </label>
            <button onclick="handleSaveRoles('${u.user_id}')" class="px-3 py-1 bg-svv-600 hover:bg-svv-700 text-white font-semibold rounded-xl transition">บันทึกยศ</button>
            ${u.username !== 'admin' ? `<button onclick="handleDeleteUser('${u.user_id}')" class="p-1 text-rose-500 hover:text-rose-700">🗑️</button>` : ''}
          </div>
        </div>
      `;
    }).join('');
  } catch (err) {
    console.error('Failed to load admin panel:', err);
  }
}

async function handleApproveUser(userId) {
  const roleSelect = document.getElementById(`sel_role_${userId}`).value;
  const roles = roleSelect.split(',').map(r => r.trim());
  try {
    const res = await api(`/api/admin/users/${userId}/approve`, {
      method: 'PUT',
      body: JSON.stringify({ roles })
    });
    showToast(res.message || 'อนุมัติเรียบร้อย', 'success');
    renderAdminPanel();
    await loadAllData();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

async function handleSaveRoles(userId) {
  const isComm = document.getElementById(`chk_comm_${userId}`)?.checked;
  const isOp = document.getElementById(`chk_op_${userId}`)?.checked;
  const roles = [];
  if (isComm) roles.push('ระดับสั่งการ');
  if (isOp) roles.push('ปฏิบัติงาน');
  if (!roles.length) roles.push('ปฏิบัติงาน');

  try {
    const res = await api(`/api/admin/users/${userId}/roles`, {
      method: 'PUT',
      body: JSON.stringify({ roles })
    });
    showToast(res.message || 'บันทึกยศสำเร็จ', 'success');
    renderAdminPanel();
    await loadAllData();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

async function handleDeleteUser(userId) {
  if (!confirm('ยืนยันลบผู้ใช้งานนี้ออกจากระบบ?')) return;
  try {
    const res = await api(`/api/admin/users/${userId}`, { method: 'DELETE' });
    showToast(res.message || 'ลบผู้ใช้แล้ว', 'success');
    renderAdminPanel();
    await loadAllData();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

// ==========================================
// MODAL CONTROLLERS & ACTIONS
// ==========================================

function openModal(id) {
  document.getElementById(id)?.classList.remove('hidden');
}

function closeModal(id) {
  document.getElementById(id)?.classList.add('hidden');
}

// 1. Progress Modal
async function openProgressModal(taskId) {
  state.activeTaskId = taskId;
  state.editingLogId = null;
  const task = state.tasks.find(t => String(t.task_id) === String(taskId));
  if (!task) return;

  const subRaw = task.submission_note || '';
  const subClean = subRaw.split('[ATTACHED_IMAGE:')[0].trim();
  let subAttach = null;
  if (subRaw.includes('[ATTACHED_IMAGE:')) {
    subAttach = subRaw.split('[ATTACHED_IMAGE:')[1].split(']')[0].trim();
  }

  const infoEl = document.getElementById('modalProgTaskInfo');
  infoEl.innerHTML = `
    <div class="flex flex-wrap items-center justify-between gap-2">
      <h4 class="font-extrabold text-sm text-slate-800">📌 ${escapeHtml(task.title)}</h4>
      <span class="badge-status ${getBadgeClass(task.status)} text-[10px]">${task.status}</span>
    </div>
    <p class="text-slate-600">
      👤 ผู้รับผิดชอบ: <strong>${escapeHtml(task.assignee_name || '-')}</strong> |
      👑 ผู้สั่งการ: <strong>@${escapeHtml(task.creator_username || task.requester_name || '-')}</strong> |
      📅 กำหนดส่ง: <strong>${task.due_date || '-'}</strong>
    </p>
    <div class="p-2.5 bg-white rounded-xl border border-slate-200/80 text-slate-700 whitespace-pre-line">
      <strong>รายละเอียดขอบเขตงาน:</strong> ${escapeHtml(task.description || '-')}
    </div>
    ${subClean ? `<div class="p-2.5 bg-emerald-50 rounded-xl border border-emerald-200 text-emerald-900"><strong>ข้อความส่งมอบงานล่าสุด:</strong> ${escapeHtml(subClean)}</div>` : ''}
    ${task.attachment_url ? renderAttachmentPreviewHtml(task.attachment_url, 'ไฟล์แนบต้นฉบับ / โจทย์งาน') : ''}
    ${subAttach ? renderAttachmentPreviewHtml(subAttach, 'ไฟล์แนบจากการส่งมอบงาน') : ''}
  `;

  const authorEl = document.getElementById('progAuthorLabel');
  if (authorEl && state.user) {
    authorEl.innerText = `${state.user.fullname || state.user.username} (@${state.user.username})`;
  }

  const formBox = document.getElementById('modalProgFormBox');
  const lockedNotice = document.getElementById('modalProgLockedNotice');
  if (task.can_edit_progress === false) {
    formBox?.classList.add('hidden');
    lockedNotice?.classList.remove('hidden');
  } else {
    formBox?.classList.remove('hidden');
    lockedNotice?.classList.add('hidden');
  }

  document.getElementById('modalProgNoteInput').value = '';
  if (document.getElementById('progAttachLink')) document.getElementById('progAttachLink').value = '';
  if (document.getElementById('progAttachFile')) document.getElementById('progAttachFile').value = '';

  await loadTaskLogs(taskId);
  openModal('modalProgress');
}

async function loadTaskLogs(taskId) {
  const container = document.getElementById('modalProgLogsList');
  const task = state.tasks.find(t => String(t.task_id) === String(taskId));
  const canEditProg = task ? task.can_edit_progress !== false : true;

  try {
    const logs = await api(`/api/tasks/${taskId}/logs`);
    if (!logs.length) {
      container.innerHTML = '<p class="text-slate-400 italic text-center py-4">ยังไม่มีประวัติการดำเนินงาน</p>';
      return;
    }
    container.innerHTML = logs.map(l => {
      const rawDetails = l.details || '';
      const cleanText = rawDetails.split('[ATTACHED_IMAGE:')[0].trim();
      let logAttach = null;
      if (rawDetails.includes('[ATTACHED_IMAGE:')) {
        logAttach = rawDetails.split('[ATTACHED_IMAGE:')[1].split(']')[0].trim();
      }
      const canModifyThis = canEditProg && (state.user?.is_commander || state.user?.is_admin || l.performed_by === state.user?.username);

      if (String(state.editingLogId) === String(l.log_id)) {
        return `
          <div class="p-3 bg-amber-50 rounded-xl border border-amber-300 space-y-2">
            <div class="flex items-center justify-between text-[11px]">
              <span class="font-bold text-amber-900">✏️ แก้ไขบันทึก: ${escapeHtml(l.action)}</span>
              <span class="text-slate-400">${formatDate(l.created_at)}</span>
            </div>
            <textarea id="editLogInput_${l.log_id}" rows="3" class="w-full px-3 py-2 text-xs bg-white border border-amber-300 rounded-xl">${escapeHtml(cleanText)}</textarea>
            <div class="flex gap-2 justify-end">
              <button onclick="saveEditedLog('${l.log_id}')" class="px-3 py-1 bg-emerald-600 text-white rounded-lg text-xs font-bold">💾 บันทึก</button>
              <button onclick="cancelEditLog()" class="px-3 py-1 bg-slate-200 text-slate-700 rounded-lg text-xs font-bold">ยกเลิก</button>
            </div>
          </div>
        `;
      }

      return `
        <div class="p-3 bg-slate-50 rounded-xl border border-slate-200 space-y-1.5">
          <div class="flex items-center justify-between text-[11px]">
            <span class="font-bold text-svv-800">${escapeHtml(l.action)} <span class="text-slate-500 font-normal">โดย @${escapeHtml(l.performed_by || '-')}</span></span>
            <div class="flex items-center gap-2">
              <span class="text-slate-400">${formatDate(l.created_at)}</span>
              ${canModifyThis ? `
                <button onclick="startEditLog('${l.log_id}')" title="แก้ไขบันทึก" class="text-slate-400 hover:text-svv-600 font-bold">✏️</button>
                <button onclick="deleteTaskLogEntry('${l.log_id}')" title="ลบบันทึก" class="text-slate-400 hover:text-rose-600 font-bold">🗑️</button>
              ` : ''}
            </div>
          </div>
          <p class="text-slate-700 whitespace-pre-line">${escapeHtml(cleanText || '-')}</p>
          ${logAttach ? renderAttachmentPreviewHtml(logAttach, 'ไฟล์แนบในความคืบหน้า') : ''}
        </div>
      `;
    }).join('');
  } catch (err) {
    container.innerHTML = '<p class="text-rose-500">เกิดข้อผิดพลาดในการโหลดประวัติ</p>';
  }
}

function startEditLog(logId) {
  state.editingLogId = logId;
  loadTaskLogs(state.activeTaskId);
}

function cancelEditLog() {
  state.editingLogId = null;
  loadTaskLogs(state.activeTaskId);
}

async function saveEditedLog(logId) {
  const val = document.getElementById(`editLogInput_${logId}`)?.value.trim() || '';
  if (!val) {
    showToast('กรุณาระบุข้อความบันทึก', 'warning');
    return;
  }
  try {
    await api(`/api/logs/${logId}`, {
      method: 'PUT',
      body: JSON.stringify({ details: val })
    });
    state.editingLogId = null;
    await loadTaskLogs(state.activeTaskId);
    showToast('แก้ไขบันทึกเรียบร้อยแล้ว', 'success');
  } catch (err) {
    showToast(err.message, 'error');
  }
}

async function deleteTaskLogEntry(logId) {
  if (!confirm('ยืนยันการลบบันทึกความคืบหน้านี้?')) return;
  try {
    await api(`/api/logs/${logId}`, { method: 'DELETE' });
    await loadTaskLogs(state.activeTaskId);
    showToast('ลบบันทึกความคืบหน้าเรียบร้อยแล้ว', 'success');
  } catch (err) {
    showToast(err.message, 'error');
  }
}

async function handleAddProgressLog(e) {
  if (e) e.preventDefault();
  if (!state.activeTaskId) return;
  const action = document.getElementById('progLogType')?.value || '📌 รายงานความคืบหน้า';
  const note = document.getElementById('modalProgNoteInput').value.trim();
  const linkInput = document.getElementById('progAttachLink')?.value.trim() || '';
  const fileInput = document.getElementById('progAttachFile');

  let attach = linkInput ? convertGdriveUrl(linkInput) : null;
  if (fileInput && fileInput.files && fileInput.files[0]) {
    attach = await fileToBase64(fileInput.files[0]);
  }

  if (!note && !attach) {
    showToast('กรุณาระบุรายละเอียดความคืบหน้าหรือแนบไฟล์อย่างน้อย 1 อย่าง', 'warning');
    return;
  }

  try {
    await api(`/api/tasks/${state.activeTaskId}/logs`, {
      method: 'POST',
      body: JSON.stringify({ action, note: note || 'แนบไฟล์ความคืบหน้า', attachment_url: attach })
    });
    document.getElementById('modalProgNoteInput').value = '';
    if (document.getElementById('progAttachLink')) document.getElementById('progAttachLink').value = '';
    if (fileInput) fileInput.value = '';
    await loadTaskLogs(state.activeTaskId);
    showToast('บันทึกรายงานความคืบหน้าสำเร็จ', 'success');
  } catch (err) {
    showToast(err.message, 'error');
  }
}

// 2. Submit Work Modal
function openSubmitModal(taskId) {
  state.activeTaskId = taskId;
  const task = state.tasks.find(t => String(t.task_id) === String(taskId));
  if (!task) return;
  const headerEl = document.getElementById('submitTaskHeader');
  if (headerEl) {
    headerEl.innerHTML = `
      <p class="font-bold text-slate-800">📌 งาน: ${escapeHtml(task.title)}</p>
      <p class="text-slate-500 mt-0.5">ผู้รับผิดชอบ: ${escapeHtml(task.assignee_name || '-')} | กำหนดส่ง: ${task.due_date || '-'}</p>
    `;
  }
  document.getElementById('submitNote').value = '';
  document.getElementById('submitLink').value = '';
  document.getElementById('submitFile').value = '';
  openModal('modalSubmit');
}

async function handleConfirmSubmitWork(e) {
  e.preventDefault();
  if (!state.activeTaskId) return;
  const note = document.getElementById('submitNote').value.trim();
  const link = document.getElementById('submitLink').value.trim();
  const fileInput = document.getElementById('submitFile');

  let attach = link ? convertGdriveUrl(link) : null;
  if (fileInput && fileInput.files[0]) {
    attach = await fileToBase64(fileInput.files[0]);
  }

  if (!note && !attach) {
    showToast('กรุณาระบุสรุปผลงานหรือแนบไฟล์ส่งมอบงาน', 'warning');
    return;
  }

  try {
    const res = await api(`/api/tasks/${state.activeTaskId}/submit`, {
      method: 'POST',
      body: JSON.stringify({ submission_note: note || 'ส่งมอบงานพร้อมไฟล์แนบ', attachment_url: attach })
    });
    closeModal('modalSubmit');
    showToast(res.message || 'ส่งงานสำเร็จ', 'success');
    await loadAllData();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

// 3. Approve Modal
function openApproveModal(taskId) {
  state.activeTaskId = taskId;
  const task = state.tasks.find(t => String(t.task_id) === String(taskId));
  if (!task) return;
  const otBadge = task.is_ontime === true ? '🟢 ส่งตรงเวลา (+10 แต้ม)' : '🔴 ส่งเกินกำหนด (-5 แต้ม)';
  const subRaw = task.submission_note || '';
  const subClean = subRaw.split('[ATTACHED_IMAGE:')[0].trim();
  let subAttach = null;
  if (subRaw.includes('[ATTACHED_IMAGE:')) {
    subAttach = subRaw.split('[ATTACHED_IMAGE:')[1].split(']')[0].trim();
  }

  document.getElementById('approveTaskDetails').innerHTML = `
    <p class="font-bold text-slate-800">📌 ${escapeHtml(task.title)}</p>
    <p class="text-slate-500">ผู้รับผิดชอบ: <strong>${escapeHtml(task.assignee_name || '-')}</strong> | ประเภท: <strong>${escapeHtml(task.task_type || 'Project')}</strong></p>
    <p class="text-slate-700 font-bold">${otBadge}</p>
    ${subClean ? `<div class="p-2.5 bg-white rounded-xl border border-slate-200 text-slate-700"><strong>สรุปงานที่ส่ง:</strong> ${escapeHtml(subClean)}</div>` : ''}
    ${subAttach ? renderAttachmentPreviewHtml(subAttach, 'ไฟล์ผลงานที่ส่งมอบ') : ''}
  `;
  document.getElementById('approveRating').value = 5;
  document.getElementById('ratingValLabel').innerText = '5 ดาว (20 แต้ม KPI)';
  document.getElementById('approveFeedback').value = '';
  openModal('modalApprove');
}

async function handleConfirmApprove(e) {
  e.preventDefault();
  if (!state.activeTaskId) return;
  const rating = parseInt(document.getElementById('approveRating').value, 10);
  const feedback = document.getElementById('approveFeedback').value.trim();

  try {
    const res = await api(`/api/tasks/${state.activeTaskId}/approve`, {
      method: 'POST',
      body: JSON.stringify({ satisfaction_rating: rating, feedback })
    });
    closeModal('modalApprove');
    showToast(res.message || 'ตรวจรับสำเร็จ', 'success');
    await loadAllData();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

// 4. Return Modal
function openReturnModal(taskId, defaultTargetStatus = 'In Progress') {
  state.activeTaskId = taskId;
  const task = state.tasks.find(t => String(t.task_id) === String(taskId));
  if (!task) return;
  document.getElementById('returnTaskTitle').innerText = `📌 งาน: ${task.title} (ผู้รับผิดชอบ: ${task.assignee_name || '-'})`;
  document.getElementById('returnStatus').value = defaultTargetStatus;
  document.getElementById('returnRating').value = task.satisfaction_rating || 5;
  document.getElementById('returnRatingLabel').innerText = `${task.satisfaction_rating || 5} ดาว (${(task.satisfaction_rating || 5) * 4} แต้ม)`;
  document.getElementById('returnFeedback').value = '';
  document.getElementById('returnNewDue').value = (task.due_date || '').slice(0, 10);
  openModal('modalReturn');
}

async function handleConfirmReturn(e) {
  e.preventDefault();
  if (!state.activeTaskId) return;
  const targetStatus = document.getElementById('returnStatus').value;
  const rating = parseInt(document.getElementById('returnRating').value || '5', 10);
  const newDue = document.getElementById('returnNewDue').value || null;
  const feedback = document.getElementById('returnFeedback').value.trim();

  try {
    const res = await api(`/api/tasks/${state.activeTaskId}/return`, {
      method: 'POST',
      body: JSON.stringify({ target_status: targetStatus, rating, new_due_date: newDue, feedback })
    });
    closeModal('modalReturn');
    showToast(res.message || 'ส่งกลับงานเรียบร้อย', 'success');
    await loadAllData();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

// 5. Handover Modal
function openHandoverModal(taskId) {
  state.activeTaskId = taskId;
  const task = state.tasks.find(t => String(t.task_id) === String(taskId));
  if (!task) return;

  const isComm = state.user?.is_commander || state.user?.is_admin;
  const infoEl = document.getElementById('handoverTaskInfo');
  infoEl.innerHTML = `
    <p class="font-bold text-slate-800">📌 ${escapeHtml(task.title)}</p>
    <p class="text-slate-500 mt-1">ผู้รับผิดชอบปัจจุบัน: <strong>${escapeHtml(task.assignee_name || '-')}</strong> | ผู้สั่งการ: <strong>@${escapeHtml(task.creator_username || '-')}</strong></p>
  `;

  const pendingBox = document.getElementById('handoverPendingBox');
  if (task.handover_status === 'Pending') {
    pendingBox.classList.remove('hidden');
    pendingBox.innerHTML = `
      <div class="p-3 bg-amber-50 border border-amber-200 rounded-xl text-xs space-y-2">
        <p class="font-bold text-amber-900">⏳ มีคำขอปรับเปลี่ยนผู้รับผิดชอบรออนุมัติ</p>
        <p class="text-amber-800">ขอเปลี่ยนเป็น: <strong>${escapeHtml(task.handover_to || '-')}</strong></p>
        <p class="text-amber-700">เหตุผล: "${escapeHtml(task.handover_reason || '-')}"</p>
        <div class="flex flex-wrap gap-2 pt-1">
          ${isComm ? `
            <button type="button" onclick="handleHandoverAction('${task.task_id}', 'approve')" class="px-3 py-1.5 bg-emerald-600 text-white rounded-lg font-bold">✅ อนุมัติคำขอนี้</button>
            <button type="button" onclick="handleHandoverAction('${task.task_id}', 'reject')" class="px-3 py-1.5 bg-rose-600 text-white rounded-lg font-bold">❌ ปฏิเสธ</button>
          ` : `
            <button type="button" onclick="handleHandoverAction('${task.task_id}', 'cancel')" class="px-3 py-1.5 bg-slate-200 text-slate-700 rounded-lg font-bold">✖️ ยกเลิกคำขอส่งต่อ</button>
          `}
        </div>
      </div>
    `;
  } else {
    pendingBox.classList.add('hidden');
    pendingBox.innerHTML = '';
  }

  const currAssignees = (task.assignee_name || '').split(',').map(s => s.trim()).filter(Boolean);
  renderMultiSelect('handoverAssigneesContainer', 'handoverAssignees', currAssignees);

  document.getElementById('handoverSubmitBtn').innerText = isComm ? '💾 บันทึกปรับเปลี่ยนผู้รับผิดชอบทันที' : '📤 ส่งคำขอปรับเปลี่ยนให้ผู้สั่งการอนุมัติ';
  document.getElementById('handoverReason').value = '';
  openModal('modalHandover');
}

async function handleConfirmHandover(e) {
  e.preventDefault();
  if (!state.activeTaskId) return;
  const selectedOps = getSelectedMulti('handoverAssignees');
  const reason = document.getElementById('handoverReason').value.trim();
  if (!selectedOps.length) {
    showToast('⚠️ กรุณาคลิกเลือกผู้รับผิดชอบอย่างน้อย 1 คน', 'warning');
    return;
  }

  try {
    const res = await api(`/api/tasks/${state.activeTaskId}/handover`, {
      method: 'POST',
      body: JSON.stringify({ handover_to: selectedOps, reason })
    });
    closeModal('modalHandover');
    showToast(res.message || 'บันทึกเรียบร้อย', 'success');
    await loadAllData();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

// 6. Edit Task Modal
function openEditModal(taskId) {
  state.activeTaskId = taskId;
  const task = state.tasks.find(t => String(t.task_id) === String(taskId));
  if (!task) return;

  document.getElementById('editTaskId').value = task.task_id;
  document.getElementById('editTitle').value = task.title || '';
  document.getElementById('editType').value = task.task_type || 'Project';
  document.getElementById('editDueDate').value = (task.due_date || '').slice(0, 10);
  document.getElementById('editPriority').value = task.priority || 'Normal';
  document.getElementById('editDesc').value = task.description || '';
  document.getElementById('editAttachLink').value = (task.attachment_url && !String(task.attachment_url).startsWith('data:')) ? task.attachment_url : '';
  if (document.getElementById('editAttachFile')) document.getElementById('editAttachFile').value = '';

  const previewEl = document.getElementById('editCurrentAttachmentPreview');
  if (previewEl) {
    previewEl.innerHTML = task.attachment_url ? renderAttachmentPreviewHtml(task.attachment_url, 'ไฟล์แนบปัจจุบัน') : '';
  }

  const currAssignees = (task.assignee_name || '').split(',').map(s => s.trim()).filter(Boolean);
  renderMultiSelect('editAssigneesContainer', 'editAssignees', currAssignees);

  openModal('modalEdit');
}

async function handleConfirmEditTask(e) {
  e.preventDefault();
  const taskId = document.getElementById('editTaskId').value;
  const title = document.getElementById('editTitle').value.trim();
  const taskType = document.getElementById('editType').value;
  const dueDate = document.getElementById('editDueDate').value;
  const priority = document.getElementById('editPriority').value;
  const desc = document.getElementById('editDesc').value.trim();
  const linkInput = document.getElementById('editAttachLink').value.trim();
  const fileInput = document.getElementById('editAttachFile');
  const selectedOps = getSelectedMulti('editAssignees');

  if (!selectedOps.length) {
    showToast('⚠️ กรุณาคลิกเลือกผู้ปฏิบัติงานอย่างน้อย 1 คน', 'warning');
    return;
  }

  let attach = linkInput ? convertGdriveUrl(linkInput) : undefined;
  if (fileInput && fileInput.files && fileInput.files[0]) {
    attach = await fileToBase64(fileInput.files[0]);
  }

  const payload = {
    title,
    task_type: taskType,
    due_date: dueDate,
    priority,
    description: desc,
    assignees: selectedOps,
  };
  if (attach !== undefined) payload.attachment_url = attach;

  try {
    const res = await api(`/api/tasks/${taskId}`, { method: 'PUT', body: JSON.stringify(payload) });
    closeModal('modalEdit');
    showToast(res.message || 'แก้ไขงานสำเร็จ', 'success');
    await loadAllData();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

// 7. Delete Task
async function handleDeleteTask(taskId, title) {
  if (!confirm(`คุณต้องการลบงาน "${title}" หรือไม่?\n(ระบบจะตัดยอดงานและลบออกจากสถิติ KPI ทันที)`)) return;
  try {
    const res = await api(`/api/tasks/${taskId}`, { method: 'DELETE' });
    showToast(res.message || 'ลบงานสำเร็จ', 'success');
    await loadAllData();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

// --- Utility Functions ---
function escapeHtml(str) {
  if (!str) return '';
  return String(str).replace(/[&<>"']/g, m => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  }[m]));
}

function formatDate(dateStr) {
  if (!dateStr) return '-';
  try {
    const d = new Date(dateStr);
    return d.toLocaleString('th-TH', { dateStyle: 'short', timeStyle: 'short' });
  } catch {
    return dateStr;
  }
}

function getBadgeClass(status) {
  switch (status) {
    case 'To Do': return 'badge-todo';
    case 'In Progress': return 'badge-progress';
    case 'In Review': return 'badge-review';
    case 'Revision': return 'badge-revision';
    case 'Done': return 'badge-done';
    default: return 'badge-todo';
  }
}
