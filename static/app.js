// Team Workflow SVV - Modern Single Page Web Application (v2.1.0)
// Complete Feature Parity with Original Streamlit Workflow System

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
  multiSelectState: {
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
    // PDF handling: preserve filename in data URI like original Streamlit app
    if (fname.endsWith('.pdf') || file.type === 'application/pdf') {
      const reader = new FileReader();
      reader.onload = () => {
        const result = reader.result || '';
        const base64Part = result.includes(',') ? result.split(',')[1] : result;
        const safeName = (file.name || 'document.pdf').replace(/;/g, '_');
        resolve(`data:application/pdf;name=${safeName};base64,${base64Part}`);
      };
      reader.onerror = (err) => reject(err);
      reader.readAsDataURL(file);
      return;
    }

    // Image compression to max 1280px JPEG (quality 0.82)
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
  const str = url.trim();
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
  return url.trim();
}

function isPdfAttachment(val) {
  if (!val) return false;
  const v = val.trim().toLowerCase();
  return v.startsWith('data:application/pdf') || v.endsWith('.pdf') || v.includes('.pdf?');
}

function renderAttachmentPreviewHtml(fileVal, caption = 'ไฟล์แนบ') {
  if (!fileVal || !fileVal.trim()) return '';
  const val = fileVal.trim();

  // Case 1: PDF file (Base64 or direct URL)
  if (isPdfAttachment(val)) {
    let pdfFilename = 'attached_document.pdf';
    if (val.startsWith('data:application/pdf')) {
      const m = val.match(/name=([^;]+);/);
      if (m) pdfFilename = m[1];
    } else {
      pdfFilename = val.split('/').pop().split('?')[0] || 'document.pdf';
    }
    return `
      <div class="mt-2 p-3 rounded-xl bg-slate-50 border border-slate-200 space-y-2">
        <div class="flex items-center justify-between gap-2 flex-wrap">
          <span class="text-xs font-bold text-slate-700">📄 ${escapeHtml(caption)} (${escapeHtml(pdfFilename)})</span>
          <a href="${val}" download="${escapeHtml(pdfFilename)}" target="_blank"
            class="px-3 py-1 rounded-lg bg-brand-600 hover:bg-brand-700 text-white text-[11px] font-bold transition">
            📥 ดาวน์โหลด / เปิดไฟล์ PDF
          </a>
        </div>
        <iframe src="${val}" class="w-full h-72 rounded-lg border border-slate-200 bg-white" loading="lazy"></iframe>
      </div>
    `;
  }

  // Case 2: Google Drive Link
  const gdriveId = getGdriveFileId(val);
  if (gdriveId) {
    const previewUrl = `https://drive.google.com/file/d/${gdriveId}/preview`;
    return `
      <div class="mt-2 p-3 rounded-xl bg-slate-50 border border-slate-200 space-y-2">
        <div class="flex items-center justify-between gap-2 flex-wrap">
          <span class="text-xs font-bold text-slate-700">🖼️ ${escapeHtml(caption)} (Google Drive)</span>
          <a href="${escapeHtml(val)}" target="_blank"
            class="px-3 py-1 rounded-lg bg-slate-800 hover:bg-slate-900 text-white text-[11px] font-bold transition">
            🔗 เปิดดูไฟล์แนบจาก Google Drive (แท็บใหม่)
          </a>
        </div>
        <iframe src="${previewUrl}" class="w-full h-64 rounded-lg border border-slate-200 bg-white" allow="autoplay" loading="lazy"></iframe>
      </div>
    `;
  }

  // Case 3: Image (Base64 or Image URL)
  return `
    <div class="mt-2 p-2.5 rounded-xl bg-slate-50 border border-slate-200 space-y-1.5">
      <div class="flex items-center justify-between">
        <span class="text-[11px] font-bold text-slate-600">🖼️ ${escapeHtml(caption)}</span>
        ${val.startsWith('http') ? `<a href="${escapeHtml(val)}" target="_blank" class="text-[11px] text-brand-600 font-bold hover:underline">🔗 เปิดลิงก์รูปภาพเต็ม</a>` : ''}
      </div>
      <img src="${val}" alt="${escapeHtml(caption)}" class="max-h-64 rounded-lg border border-slate-200 object-contain bg-white mx-auto"
        onerror="this.outerHTML='<a href=\\'${escapeHtml(val)}\\' target=\\'_blank\\' class=\\'text-xs text-brand-600 underline\\'>🔗 คลิกเพื่อเปิดดูไฟล์แนบ</a>'" />
    </div>
  `;
}

// --- Interactive Multi-Select Checkboxes/Pills ---
function renderMultiSelect(containerId, groupName, selectedUsernames = null) {
  const container = document.getElementById(containerId);
  if (!container) return;

  if (selectedUsernames !== null) {
    state.multiSelectState[groupName] = [...selectedUsernames];
  }
  const currentSelected = state.multiSelectState[groupName] || [];

  if (!state.operators || state.operators.length === 0) {
    container.innerHTML = `<div class="col-span-full text-xs text-slate-400 py-2 text-center">ไม่พบรายชื่อผู้ปฏิบัติงาน</div>`;
    return;
  }

  container.innerHTML = state.operators.map(op => {
    const isChecked = currentSelected.includes(op.username);
    return `
      <div onclick="toggleMultiOption('${groupName}', '${escapeHtml(op.username)}')"
        class="multi-option-pill flex items-center gap-2 px-2.5 py-2 rounded-xl border cursor-pointer text-xs ${isChecked ? 'selected border-brand-500 bg-brand-50 text-brand-800 font-bold' : 'border-slate-200 bg-white text-slate-700'}">
        <input type="checkbox" ${isChecked ? 'checked' : ''} class="w-3.5 h-3.5 rounded text-brand-600 pointer-events-none" readonly />
        <div class="truncate">
          <span>${escapeHtml(op.display_name)}</span>
          <span class="text-[10px] text-slate-400 ml-1">(${escapeHtml(op.username)})</span>
        </div>
      </div>
    `;
  }).join('');

  if (groupName === 'createAssignees') {
    const countEl = document.getElementById('createAssigneesCount');
    if (countEl) countEl.innerText = `เลือกแล้ว ${currentSelected.length} คน`;
  }
}

function toggleMultiOption(groupName, username) {
  const list = state.multiSelectState[groupName] || [];
  const idx = list.indexOf(username);
  if (idx >= 0) {
    list.splice(idx, 1);
  } else {
    list.push(username);
  }
  state.multiSelectState[groupName] = list;

  const mapContainer = {
    createAssignees: 'createAssigneesContainer',
    editAssignees: 'editAssigneesContainer',
    handoverAssignees: 'handoverAssigneesContainer',
  };
  renderMultiSelect(mapContainer[groupName], groupName);
}

function selectAllMulti(groupName, selectAll) {
  if (selectAll) {
    state.multiSelectState[groupName] = state.operators.map(op => op.username);
  } else {
    state.multiSelectState[groupName] = [];
  }
  const mapContainer = {
    createAssignees: 'createAssigneesContainer',
    editAssignees: 'editAssigneesContainer',
    handoverAssignees: 'handoverAssigneesContainer',
  };
  renderMultiSelect(mapContainer[groupName], groupName);
}

function getSelectedMulti(groupName) {
  return state.multiSelectState[groupName] || [];
}

// --- Initialize App ---
document.addEventListener('DOMContentLoaded', async () => {
  const loader = document.getElementById('globalLoader');
  try {
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
    if (!state.user) return;
    const params = new URLSearchParams(window.location.search);
    const urlPage = params.get('page');
    if (urlPage && ['commander', 'kanban', 'kpi', 'admin'].includes(urlPage)) {
      navigateTo(urlPage, false);
    }
  });
});

// --- Authentication Views & Actions ---
function showAuth() {
  document.getElementById('authScreen').classList.remove('hidden');
  document.getElementById('appContainer').classList.add('hidden');
}

function showApp() {
  document.getElementById('authScreen').classList.add('hidden');
  document.getElementById('appContainer').classList.remove('hidden');

  const u = state.user;
  document.getElementById('sidebarDisplayName').innerText = u.display_name || u.username;
  document.getElementById('sidebarRoleBadge').innerText = u.role || 'Operator';
  document.getElementById('sidebarAvatar').innerText = (u.display_name || u.username || 'U').charAt(0).toUpperCase();

  const navAdmin = document.getElementById('nav-admin');
  if (u.is_admin) {
    navAdmin.classList.remove('hidden');
  } else {
    navAdmin.classList.add('hidden');
  }

  const today = new Date().toISOString().split('T')[0];
  const dueDateInput = document.getElementById('createDueDate');
  if (dueDateInput && !dueDateInput.value) {
    dueDateInput.value = today;
  }
  const filterDueDate = document.getElementById('filterDueDate');
  if (filterDueDate && !filterDueDate.value) {
    filterDueDate.value = today;
  }
}

function switchAuthTab(tab) {
  const loginForm = document.getElementById('loginForm');
  const regForm = document.getElementById('registerForm');
  const tabLogin = document.getElementById('tabLoginBtn');
  const tabReg = document.getElementById('tabRegisterBtn');
  document.getElementById('authAlert').classList.add('hidden');

  if (tab === 'login') {
    loginForm.classList.remove('hidden');
    regForm.classList.add('hidden');
    tabLogin.className = 'flex-1 py-2.5 text-sm font-semibold rounded-lg bg-white text-slate-900 shadow-sm transition';
    tabReg.className = 'flex-1 py-2.5 text-sm font-semibold rounded-lg text-slate-500 hover:text-slate-800 transition';
  } else {
    loginForm.classList.add('hidden');
    regForm.classList.remove('hidden');
    tabReg.className = 'flex-1 py-2.5 text-sm font-semibold rounded-lg bg-white text-slate-900 shadow-sm transition';
    tabLogin.className = 'flex-1 py-2.5 text-sm font-semibold rounded-lg text-slate-500 hover:text-slate-800 transition';
  }
}

function showAuthError(msg, isSuccess = false) {
  const el = document.getElementById('authAlert');
  el.innerText = msg;
  el.className = isSuccess
    ? 'mb-4 p-3 rounded-xl text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200'
    : 'mb-4 p-3 rounded-xl text-xs font-medium bg-rose-50 text-rose-700 border border-rose-200';
  el.classList.remove('hidden');
}

async function handleLogin(e) {
  e.preventDefault();
  const username = document.getElementById('loginUsername').value.trim();
  const password = document.getElementById('loginPassword').value;
  const btn = document.getElementById('loginSubmitBtn');
  btn.disabled = true;
  btn.innerText = 'กำลังเข้าสู่ระบบ...';

  try {
    const res = await api('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    });
    state.token = res.token;
    state.user = res.user;
    localStorage.setItem('svv_token', res.token);
    showApp();
    await loadAllData();
    const defaultPage = state.user.is_commander ? 'commander' : 'kanban';
    navigateTo(defaultPage);
    showToast(`ยินดีต้อนรับ ${state.user.display_name}`, 'success');
  } catch (err) {
    showAuthError(err.message);
  } finally {
    btn.disabled = false;
    btn.innerText = 'เข้าสู่ระบบ';
  }
}

async function handleRegister(e) {
  e.preventDefault();
  const username = document.getElementById('regUsername').value.trim();
  const display_name = document.getElementById('regDisplayName').value.trim();
  const password = document.getElementById('regPassword').value;
  const confirm_password = document.getElementById('regConfirmPassword').value;
  const role = document.getElementById('regRole').value;
  const btn = document.getElementById('regSubmitBtn');

  btn.disabled = true;
  btn.innerText = 'กำลังสมัครสมาชิก...';
  try {
    const res = await api('/api/auth/register', {
      method: 'POST',
      body: JSON.stringify({ username, display_name, password, confirm_password, role }),
    });
    showAuthError(res.message || 'ลงทะเบียนสำเร็จ กรุณาเข้าสู่ระบบ', true);
    setTimeout(() => switchAuthTab('login'), 1200);
  } catch (err) {
    showAuthError(err.message);
  } finally {
    btn.disabled = false;
    btn.innerText = 'ลงทะเบียนเข้าใช้งาน';
  }
}

function handleLogout() {
  localStorage.removeItem('svv_token');
  state.token = '';
  state.user = null;
  const url = new URL(window.location.href);
  url.searchParams.delete('page');
  window.history.replaceState({}, '', url);
  showAuth();
}

// --- Navigation & Page Switching ---
function navigateTo(page, updateHistory = true) {
  if (page === 'admin' && (!state.user || !state.user.is_admin)) {
    page = 'kanban';
  }
  state.currentPage = page;

  if (updateHistory) {
    const url = new URL(window.location.href);
    url.searchParams.set('page', page);
    window.history.pushState({ page }, '', url);
  }

  document.querySelectorAll('.nav-item').forEach(btn => btn.classList.remove('active'));
  const activeNav = document.getElementById(`nav-${page}`);
  if (activeNav) activeNav.classList.add('active');

  ['commander', 'kanban', 'kpi', 'admin'].forEach(p => {
    const el = document.getElementById(`page-${p}`);
    if (el) {
      if (p === page) el.classList.remove('hidden');
      else el.classList.add('hidden');
    }
  });

  const titles = {
    commander: ['👑 หน้าผู้สั่งการ (Commander Panel)', 'มอบหมายงานใหม่ ตรวจรับงาน อนุมัติส่งต่องาน และปรับคะแนน KPI'],
    kanban: ['📌 กระดานติดตามงาน (Kanban Board)', 'ลากวางการ์ด (Drag & Drop) เพื่อเปลี่ยนสถานะงาน หรือคลิกปุ่มจัดการ'],
    kpi: ['📊 แดชบอร์ดวัดผลและรายงาน (KPI & Performance)', 'สรุปคะแนน KPI ประจำตัว กราฟเปรียบเทียบ และรายงานประวัติการทำงานรายเดือน'],
    admin: ['🛡️ จัดการผู้ใช้และระบบ (Admin Panel)', 'จัดการสิทธิ์ผู้ใช้งาน รีเซ็ตรหัสผ่าน และดูแลฐานข้อมูล'],
  };
  const [title, subtitle] = titles[page] || titles.kanban;
  document.getElementById('topbarTitle').innerText = title;
  document.getElementById('topbarSubtitle').innerText = subtitle;

  const sidebar = document.getElementById('sidebar');
  const overlay = document.getElementById('sidebarOverlay');
  if (window.innerWidth < 1024 && sidebar && !sidebar.classList.contains('-translate-x-full')) {
    sidebar.classList.add('-translate-x-full');
    overlay.classList.add('hidden');
  }

  if (page === 'commander') renderCommanderPage();
  if (page === 'kanban') renderKanbanBoard();
  if (page === 'kpi') renderKpiDashboard();
  if (page === 'admin') loadAdminUsers();
}

function toggleMobileSidebar() {
  const sidebar = document.getElementById('sidebar');
  const overlay = document.getElementById('sidebarOverlay');
  sidebar.classList.toggle('-translate-x-full');
  overlay.classList.toggle('hidden');
}

// --- Data Loading ---
async function loadAllData() {
  try {
    const [tasksRes, opsRes, kpiRes] = await Promise.all([
      api('/api/tasks'),
      api('/api/users/operators'),
      api('/api/kpi/summary'),
    ]);
    state.tasks = tasksRes.tasks || [];
    state.operators = opsRes.operators || [];
    state.allUsers = opsRes.all_users || [];
    state.kpiSummary = kpiRes;

    populateDropdowns();
    updateNotificationBadges();
    renderCurrentView();
  } catch (err) {
    showToast('ไม่สามารถโหลดข้อมูลล่าสุดได้: ' + err.message, 'error');
  }
}

async function refreshAllData() {
  showToast('กำลังรีเฟรชข้อมูล...', 'info');
  await loadAllData();
  showToast('อัปเดตข้อมูลล่าสุดเรียบร้อยแล้ว ✨', 'success');
}

function renderCurrentView() {
  if (state.currentPage === 'commander') renderCommanderPage();
  else if (state.currentPage === 'kanban') renderKanbanBoard();
  else if (state.currentPage === 'kpi') renderKpiDashboard();
  else if (state.currentPage === 'admin') loadAdminUsers();
}

function populateDropdowns() {
  // Interactive Multi-selects
  const currentCreate = state.multiSelectState.createAssignees.length > 0
    ? state.multiSelectState.createAssignees
    : (state.user ? [state.user.username] : []);
  renderMultiSelect('createAssigneesContainer', 'createAssignees', currentCreate);
  renderMultiSelect('editAssigneesContainer', 'editAssignees');
  renderMultiSelect('handoverAssigneesContainer', 'handoverAssignees');

  // Kanban Assignee filter
  const filterAssignee = document.getElementById('filterAssignee');
  if (filterAssignee) {
    const currentVal = filterAssignee.value || 'ทั้งหมด';
    const names = [...new Set(state.operators.map(o => o.display_name))];
    filterAssignee.innerHTML = `<option value="ทั้งหมด">👤 ผู้รับผิดชอบ: ทั้งหมด</option>` +
      names.map(n => `<option value="${escapeHtml(n)}">${escapeHtml(n)}</option>`).join('');
    if ([...filterAssignee.options].some(o => o.value === currentVal)) {
      filterAssignee.value = currentVal;
    }
  }

  // Commander Manage Table Creator Filter
  const manageCreatorFilter = document.getElementById('manageCreatorFilter');
  if (manageCreatorFilter) {
    const curVal = manageCreatorFilter.value || 'ทั้งหมด';
    const creators = [...new Set(state.tasks.map(t => t.created_by).filter(Boolean))].sort();
    manageCreatorFilter.innerHTML = `<option value="ทั้งหมด">👑 ผู้สั่งงาน: ทั้งหมด</option>` +
      creators.map(c => `<option value="${escapeHtml(c)}">${escapeHtml(c)}</option>`).join('');
    if ([...manageCreatorFilter.options].some(o => o.value === curVal)) {
      manageCreatorFilter.value = curVal;
    }
  }

  // KPI Adjustment user select (Commander Tab 4 & KPI Direct Adjust)
  const kpiUsersHtml = state.operators.map(op =>
    `<option value="${escapeHtml(op.username)}">${escapeHtml(op.display_name)} (${escapeHtml(op.username)})</option>`
  ).join('');
  const kpiSelect = document.getElementById('kpiTargetUser');
  if (kpiSelect) kpiSelect.innerHTML = kpiUsersHtml;
  const kpiDirectSelect = document.getElementById('kpiDirectTargetUser');
  if (kpiDirectSelect) kpiDirectSelect.innerHTML = kpiUsersHtml;

  // History Report Filters
  const histEmployee = document.getElementById('histFilterEmployee');
  if (histEmployee) {
    const curEmp = histEmployee.value || 'ทั้งหมด';
    const empNames = state.operators.map(o => o.display_name);
    histEmployee.innerHTML = `<option value="ทั้งหมด">ทั้งหมด (ทุกคน)</option>` +
      empNames.map(n => `<option value="${escapeHtml(n)}">${escapeHtml(n)}</option>`).join('');
    if ([...histEmployee.options].some(o => o.value === curEmp)) {
      histEmployee.value = curEmp;
    }
  }

  const histMonth = document.getElementById('histFilterMonth');
  if (histMonth) {
    const curMonth = histMonth.value || 'ทั้งหมด';
    const monthSet = new Set();
    state.tasks.forEach(t => {
      const ym = getTaskThaiMonthYear(t);
      if (ym) monthSet.add(ym);
    });
    const months = [...monthSet];
    histMonth.innerHTML = `<option value="ทั้งหมด">ทั้งหมด (ทุกเดือน)</option>` +
      months.map(m => `<option value="${escapeHtml(m)}">${escapeHtml(m)}</option>`).join('');
    if ([...histMonth.options].some(o => o.value === curMonth)) {
      histMonth.value = curMonth;
    }
  }
}

function getTaskThaiMonthYear(task) {
  const raw = task.created_at || task.due_date || '';
  if (!raw) return 'ไม่ระบุเดือน';
  const d = new Date(raw);
  if (isNaN(d.getTime())) return 'ไม่ระบุเดือน';
  const mName = THAI_MONTHS[d.getMonth() + 1] || '';
  const buddhistYear = d.getFullYear() + 543;
  return `${mName} ${buddhistYear}`;
}

function updateNotificationBadges() {
  const handoverTasks = state.tasks.filter(t => t.pending_assignees && t.pending_assignees.trim() !== '');
  const reviewTasks = state.tasks.filter(t => t.status === 'Waiting for Review');

  const handoverBadge = document.getElementById('cmdHandoverBadge');
  if (handoverBadge) {
    if (handoverTasks.length > 0) {
      handoverBadge.innerText = handoverTasks.length;
      handoverBadge.classList.remove('hidden');
    } else {
      handoverBadge.classList.add('hidden');
    }
  }

  const reviewBadge = document.getElementById('cmdReviewBadge');
  if (reviewBadge) {
    if (reviewTasks.length > 0) {
      reviewBadge.innerText = reviewTasks.length;
      reviewBadge.classList.remove('hidden');
    } else {
      reviewBadge.classList.add('hidden');
    }
  }

  const navCmdBadge = document.getElementById('navCommanderBadge');
  const totalActions = handoverTasks.length + reviewTasks.length;
  if (navCmdBadge) {
    if (totalActions > 0 && state.user && state.user.is_commander) {
      navCmdBadge.innerText = totalActions;
      navCmdBadge.classList.remove('hidden');
    } else {
      navCmdBadge.classList.add('hidden');
    }
  }
}

// ============================================================================
// MODULE 1: COMMANDER PANEL
// ============================================================================
function switchCommanderTab(tab) {
  state.commanderTab = tab;
  const tabs = ['create', 'handover', 'review', 'kpi-adjust'];
  const mapPane = {
    'create': 'cmdPaneCreate',
    'handover': 'cmdPaneHandover',
    'review': 'cmdPaneReview',
    'kpi-adjust': 'cmdPaneKpiAdjust',
  };
  const mapBtn = {
    'create': 'cmdTabCreate',
    'handover': 'cmdTabHandover',
    'review': 'cmdTabReview',
    'kpi-adjust': 'cmdTabKpiAdjust',
  };

  tabs.forEach(t => {
    const pane = document.getElementById(mapPane[t]);
    const btn = document.getElementById(mapBtn[t]);
    if (t === tab) {
      pane.classList.remove('hidden');
      btn.className = 'px-4 py-2.5 rounded-xl text-xs font-bold bg-brand-600 text-white shadow-sm transition flex items-center gap-1.5';
    } else {
      pane.classList.add('hidden');
      btn.className = 'px-4 py-2.5 rounded-xl text-xs font-bold bg-white text-slate-600 border border-slate-200 hover:bg-slate-50 transition flex items-center gap-1.5';
    }
  });

  renderCommanderPage();
}

function renderCommanderPage() {
  renderManageTasksTable();
  renderHandoverRequests();
  renderReviewTasks();
  renderKpiAdjustHistory();
}

async function handleCreateTask(e) {
  e.preventDefault();
  const title = document.getElementById('createTitle').value.trim();
  const description = document.getElementById('createDesc').value.trim();
  const assignees = getSelectedMulti('createAssignees');
  const priority = document.getElementById('createPriority').value;
  const task_type = document.getElementById('createType').value;
  const due_date = document.getElementById('createDueDate').value;
  const linkVal = document.getElementById('createImageLink').value.trim();
  const fileInput = document.getElementById('createImageFile');

  if (!title) return showToast('กรุณากรอกชื่องาน', 'warning');
  if (assignees.length === 0) return showToast('กรุณาคลิกเลือกผู้ปฏิบัติงานอย่างน้อย 1 คน', 'warning');

  const btn = document.getElementById('createTaskBtn');
  btn.disabled = true;
  btn.innerText = 'กำลังบันทึกงาน...';

  try {
    let task_image = linkVal ? convertGdriveUrl(linkVal) : '';
    if (fileInput && fileInput.files && fileInput.files[0]) {
      task_image = await fileToBase64(fileInput.files[0]);
    }

    await api('/api/tasks', {
      method: 'POST',
      body: JSON.stringify({ title, description, assignees, priority, task_type, due_date, task_image }),
    });

    document.getElementById('createTaskForm').reset();
    document.getElementById('createDueDate').value = new Date().toISOString().split('T')[0];
    renderMultiSelect('createAssigneesContainer', 'createAssignees', state.user ? [state.user.username] : []);
    showToast('มอบหมายงานเข้าสู่ระบบเรียบร้อยแล้ว 🚀', 'success');
    await loadAllData();
  } catch (err) {
    showToast(err.message, 'error');
  } finally {
    btn.disabled = false;
    btn.innerText = '🚀 มอบหมายงานเข้าสู่ระบบ';
  }
}

function renderManageTasksTable() {
  const container = document.getElementById('manageTasksListContainer');
  if (!container) return;

  const search = (document.getElementById('manageSearchInput')?.value || '').trim().toLowerCase();
  const creatorFilter = document.getElementById('manageCreatorFilter')?.value || 'ทั้งหมด';
  const statusFilter = document.getElementById('manageStatusFilter')?.value || 'ทั้งหมด';

  const filtered = state.tasks.filter(t => {
    if (search) {
      const hay = `${t.title} ${t.description} ${t.assigned_to}`.toLowerCase();
      if (!hay.includes(search)) return false;
    }
    if (creatorFilter !== 'ทั้งหมด' && t.created_by !== creatorFilter) return false;
    if (statusFilter !== 'ทั้งหมด' && t.status !== statusFilter) return false;
    return true;
  });

  if (filtered.length === 0) {
    container.innerHTML = `<div class="p-6 text-center text-xs text-slate-400">ยังไม่มีรายการงานที่ตรงกับเงื่อนไข</div>`;
    return;
  }

  container.innerHTML = filtered.map(t => `
    <div class="p-3.5 rounded-xl bg-slate-50 border border-slate-200/80 hover:bg-white hover:shadow-sm transition flex flex-col md:flex-row md:items-center justify-between gap-3">
      <div class="space-y-1 min-w-0 flex-1">
        <div class="flex items-center gap-2 flex-wrap">
          <span class="text-xs font-extrabold text-slate-900">#${t.id} ${escapeHtml(t.title)}</span>
          ${getPriorityBadge(t.priority)}
          ${getStatusBadge(t.status)}
          <span class="px-2 py-0.5 rounded-md bg-slate-200/70 text-slate-700 text-[10px] font-bold">🏷️ ${escapeHtml(t.task_type || 'Routine')}</span>
        </div>
        <p class="text-[11px] text-slate-500">
          👤 ผู้ปฏิบัติงาน: <strong class="text-slate-700">${escapeHtml(t.assigned_to || '-')}</strong>
          | 👑 ผู้สั่ง: <strong class="text-slate-700">${escapeHtml(t.created_by || 'System')}</strong>
          | 📅 กำหนดส่ง: <strong class="text-slate-700">${escapeHtml(t.due_date || '-')}</strong>
        </p>
      </div>
      <div class="flex items-center gap-1.5 flex-shrink-0">
        ${t.can_edit ? `<button onclick="openEditModal(${t.id})" class="px-3 py-1.5 rounded-lg bg-white border border-slate-200 hover:border-brand-400 text-slate-700 text-xs font-bold transition">✏️ แก้ไขงาน</button>` : ''}
        <button onclick="openProgressModal(${t.id})" class="px-3 py-1.5 rounded-lg bg-sky-50 hover:bg-sky-100 text-sky-700 text-xs font-bold transition">📝 คืบหน้า</button>
        ${t.can_delete ? `<button onclick="deleteTask(${t.id})" class="px-3 py-1.5 rounded-lg bg-rose-50 hover:bg-rose-100 text-rose-600 text-xs font-bold transition">🗑️ ลบงาน</button>` : ''}
      </div>
    </div>
  `).join('');
}

function renderHandoverRequests() {
  const container = document.getElementById('handoverListContainer');
  if (!container) return;
  const handovers = state.tasks.filter(t => t.pending_assignees && t.pending_assignees.trim() !== '');

  if (handovers.length === 0) {
    container.innerHTML = `<div class="bg-white rounded-2xl border border-slate-200 p-8 text-center text-slate-400 text-sm">✨ ไม่มีรายการขออนุมัติส่งต่องานในขณะนี้</div>`;
    return;
  }

  const isCmd = state.user && (state.user.is_commander || state.user.is_admin);
  container.innerHTML = handovers.map(t => `
    <div class="bg-white rounded-2xl border border-amber-200 shadow-sm p-5 flex flex-col md:flex-row md:items-center justify-between gap-4">
      <div class="space-y-1.5">
        <div class="flex items-center gap-2 flex-wrap">
          <span class="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-amber-100 text-amber-800">🔄 รออนุมัติส่งต่องาน</span>
          <span class="text-xs font-bold text-slate-400">#${t.id}</span>
          <h4 class="text-sm font-bold text-slate-900">${escapeHtml(t.title)}</h4>
        </div>
        <p class="text-xs text-slate-600">
          👤 ผู้รับผิดชอบเดิม: <strong class="text-slate-800">${escapeHtml(t.assigned_to)}</strong>
          ➔ ขอเปลี่ยนเป็น: <strong class="text-emerald-700">${escapeHtml(t.pending_assignees)}</strong>
        </p>
        <p class="text-xs text-slate-500 bg-slate-50 px-3 py-2 rounded-xl border border-slate-100">
          💬 เหตุผล/หมายเหตุ: ${escapeHtml(t.handover_Reason || '-')} (ขอโดย: ${escapeHtml(t.handover_Requested_By || '-')})
        </p>
      </div>
      <div class="flex items-center gap-2 flex-shrink-0 flex-wrap">
        ${isCmd ? `
          <button onclick="decideHandover(${t.id}, true)" class="px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold shadow-sm transition">
            ✅ อนุมัติการปรับเปลี่ยน
          </button>
          <button onclick="decideHandover(${t.id}, false)" class="px-4 py-2 rounded-xl bg-rose-50 hover:bg-rose-100 text-rose-700 border border-rose-200 text-xs font-bold transition">
            ❌ ปฏิเสธ / ยกเลิกคำขอ
          </button>
          <button onclick="openHandoverModal(${t.id})" class="px-3 py-2 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-bold transition">
            ✏️ ปรับเปลี่ยนเอง
          </button>
        ` : `<span class="text-xs text-amber-700 font-semibold">⏳ รอผู้สั่งการอนุมัติ</span>`}
      </div>
    </div>
  `).join('');
}

async function decideHandover(taskId, approve) {
  try {
    const res = await api(`/api/tasks/${taskId}/handover/decision`, {
      method: 'POST',
      body: JSON.stringify({ approve }),
    });
    showToast(res.message, 'success');
    await loadAllData();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

function renderReviewTasks() {
  const container = document.getElementById('reviewListContainer');
  if (!container) return;
  const reviews = state.tasks.filter(t => t.status === 'Waiting for Review');

  if (reviews.length === 0) {
    container.innerHTML = `<div class="bg-white rounded-2xl border border-slate-200 p-8 text-center text-slate-400 text-sm">✨ ไม่มีงานที่รอตรวจรับในขณะนี้</div>`;
    return;
  }

  container.innerHTML = reviews.map(t => {
    const onTimeBadge = t.is_on_time === 1
      ? `<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-700">⏱️ ส่งตรงเวลา (On-Time)</span>`
      : t.is_on_time === 0
      ? `<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-rose-100 text-rose-700">⚠️ ส่งล่าช้า (Late)</span>`
      : '';

    return `
      <div class="bg-white rounded-2xl border border-slate-200 shadow-sm p-5 space-y-3">
        <div class="flex flex-col md:flex-row md:items-start justify-between gap-4">
          <div class="space-y-1.5 flex-1">
            <div class="flex items-center gap-2 flex-wrap">
              <span class="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-amber-100 text-amber-800">⏳ รอตรวจรับงาน</span>
              ${onTimeBadge}
              <span class="text-xs font-bold text-slate-400">#${t.id}</span>
              <h4 class="text-sm font-bold text-slate-900">${escapeHtml(t.title)}</h4>
            </div>
            <p class="text-xs text-slate-500">
              👤 ผู้รับผิดชอบ: <strong class="text-slate-800">${escapeHtml(t.assigned_to)}</strong> |
              👑 ผู้สั่ง: <strong class="text-slate-700">${escapeHtml(t.created_by || 'System')}</strong> |
              📅 กำหนดส่ง: ${escapeHtml(t.due_date || '-')} |
              🕒 ส่งงานเมื่อ: ${escapeHtml((t.submitted_at || '-').slice(0, 16))}
            </p>
            <div class="text-xs text-slate-700 bg-slate-50 p-3 rounded-xl border border-slate-100 whitespace-pre-line">${escapeHtml(t.description || 'ไม่มีรายละเอียดเพิ่มเติม')}</div>
            ${t.task_Image ? renderAttachmentPreviewHtml(t.task_Image, 'ไฟล์แนบโจทย์งาน') : ''}
            ${t.submission_Image ? renderAttachmentPreviewHtml(t.submission_Image, 'ไฟล์ผลงานที่ส่งมอบ') : ''}
          </div>
          <div class="flex flex-wrap items-center gap-2 flex-shrink-0">
            <button onclick="openApproveModal(${t.id})" class="px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold shadow-sm transition">
              🏆 ตรวจรับงานสำเร็จ (Done)
            </button>
            <button onclick="openReturnModal(${t.id})" class="px-4 py-2 rounded-xl bg-amber-50 hover:bg-amber-100 text-amber-800 border border-amber-200 text-xs font-bold transition">
              ↩️ ส่งกลับ / ทำต่อ / ประเมินผล
            </button>
            <button onclick="openProgressModal(${t.id})" class="px-3 py-2 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-bold transition">
              📝 ความคืบหน้า
            </button>
            ${t.can_edit ? `<button onclick="openEditModal(${t.id})" class="px-3 py-2 rounded-xl bg-white border border-slate-200 hover:border-brand-400 text-slate-700 text-xs font-bold transition">✏️ แก้ไขงาน</button>` : ''}
          </div>
        </div>
      </div>
    `;
  }).join('');
}

async function handleKpiAdjustment(e) {
  e.preventDefault();
  const username = document.getElementById('kpiTargetUser').value;
  const points = parseFloat(document.getElementById('kpiPoints').value);
  const reason = document.getElementById('kpiReason').value.trim();

  if (!username || isNaN(points) || !reason) {
    return showToast('กรุณากรอกข้อมูลการปรับคะแนนให้ครบถ้วน', 'warning');
  }

  try {
    const res = await api('/api/kpi/adjust', {
      method: 'POST',
      body: JSON.stringify({ username, points, reason }),
    });
    showToast(res.message, 'success');
    document.getElementById('kpiAdjustForm').reset();
    await loadAllData();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

async function handleDirectKpiAdjust(e) {
  e.preventDefault();
  const username = document.getElementById('kpiDirectTargetUser').value;
  const typeSign = document.getElementById('kpiDirectType').value;
  const rawPts = Math.abs(parseFloat(document.getElementById('kpiDirectPoints').value || '0'));
  const reason = document.getElementById('kpiDirectReason').value.trim();

  if (!username || !rawPts || !reason) {
    return showToast('กรุณาระบุพนักงาน คะแนน และเหตุผลให้ครบถ้วน', 'warning');
  }
  const points = typeSign === 'sub' ? -rawPts : rawPts;

  try {
    const res = await api('/api/kpi/adjust', {
      method: 'POST',
      body: JSON.stringify({ username, points, reason }),
    });
    showToast(res.message, 'success');
    document.getElementById('kpiDirectReason').value = '';
    await loadAllData();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

function renderKpiAdjustHistory() {
  const container = document.getElementById('kpiAdjustHistoryList');
  if (!container || !state.kpiSummary) return;
  const list = state.kpiSummary.adjustments || [];
  if (list.length === 0) {
    container.innerHTML = `<p class="text-xs text-slate-400 text-center py-6">ยังไม่มีประวัติการปรับคะแนนพิเศษ</p>`;
    return;
  }
  container.innerHTML = list.map(a => {
    const isPlus = a.points >= 0;
    return `
      <div class="p-3 rounded-xl bg-slate-50 border border-slate-100 flex items-center justify-between gap-3">
        <div>
          <p class="text-xs font-bold text-slate-800">${escapeHtml(a.username)} <span class="text-slate-400 font-normal">• โดย ${escapeHtml(a.adjusted_by)}</span></p>
          <p class="text-[11px] text-slate-500">${escapeHtml(a.reason)}</p>
          <p class="text-[10px] text-slate-400">${escapeHtml((a.created_at || '').slice(0, 16))}</p>
        </div>
        <span class="px-2.5 py-1 rounded-lg text-xs font-extrabold ${isPlus ? 'bg-emerald-100 text-emerald-700' : 'bg-rose-100 text-rose-700'}">
          ${isPlus ? '+' : ''}${a.points}
        </span>
      </div>
    `;
  }).join('');
}

// ============================================================================
// MODULE 2: KANBAN BOARD & DRAG-AND-DROP
// ============================================================================
function setKanbanView(view) {
  state.kanbanView = view;
  const boardEl = document.getElementById('kanbanBoardView');
  const listEl = document.getElementById('kanbanListView');
  const btnBoard = document.getElementById('viewBtnBoard');
  const btnList = document.getElementById('viewBtnList');

  if (view === 'board') {
    boardEl.classList.remove('hidden');
    listEl.classList.add('hidden');
    btnBoard.className = 'px-3 py-1.5 rounded-lg text-xs font-bold bg-brand-50 text-brand-700 transition';
    btnList.className = 'px-3 py-1.5 rounded-lg text-xs font-bold text-slate-500 hover:text-slate-800 transition';
  } else {
    boardEl.classList.add('hidden');
    listEl.classList.remove('hidden');
    btnList.className = 'px-3 py-1.5 rounded-lg text-xs font-bold bg-brand-50 text-brand-700 transition';
    btnBoard.className = 'px-3 py-1.5 rounded-lg text-xs font-bold text-slate-500 hover:text-slate-800 transition';
  }
  renderKanbanBoard();
}

function toggleDateFilter() {
  const useDate = document.getElementById('filterUseDate')?.checked;
  const dateInput = document.getElementById('filterDueDate');
  if (dateInput) {
    dateInput.disabled = !useDate;
  }
  renderKanbanBoard();
}

function getFilteredTasks() {
  const search = (document.getElementById('filterSearch')?.value || '').trim().toLowerCase();
  const assignee = document.getElementById('filterAssignee')?.value || 'ทั้งหมด';
  const priority = document.getElementById('filterPriority')?.value || 'ทั้งหมด';
  const useDate = document.getElementById('filterUseDate')?.checked || false;
  const dueDateVal = document.getElementById('filterDueDate')?.value || '';

  return state.tasks.filter(t => {
    if (search) {
      const hay = `${t.title} ${t.description} ${t.assigned_to} ${t.created_by}`.toLowerCase();
      if (!hay.includes(search)) return false;
    }
    if (assignee !== 'ทั้งหมด') {
      const names = (t.assigned_to || '').split(',').map(s => s.trim());
      if (!names.includes(assignee)) return false;
    }
    if (priority !== 'ทั้งหมด' && t.priority !== priority) {
      return false;
    }
    if (useDate && dueDateVal) {
      if ((t.due_date || '') !== dueDateVal) return false;
    }
    return true;
  });
}

function getPriorityBadge(priority) {
  if (priority === 'Urgent') return `<span class="px-2 py-0.5 rounded-md bg-rose-100 text-rose-700 text-[10px] font-extrabold">🔥 Urgent</span>`;
  if (priority === 'High') return `<span class="px-2 py-0.5 rounded-md bg-amber-100 text-amber-800 text-[10px] font-bold">⚡ High</span>`;
  if (priority === 'Low') return `<span class="px-2 py-0.5 rounded-md bg-slate-100 text-slate-600 text-[10px] font-semibold">🌱 Low</span>`;
  return `<span class="px-2 py-0.5 rounded-md bg-sky-100 text-sky-700 text-[10px] font-semibold">📌 Medium</span>`;
}

function getStatusBadge(status) {
  const map = {
    'To Do': 'badge-todo',
    'In Progress': 'badge-progress',
    'Waiting for Review': 'badge-review',
    'Revision': 'badge-revision',
    'Done': 'badge-done',
  };
  return `<span class="badge-status ${map[status] || 'badge-todo'}">${escapeHtml(status)}</span>`;
}

function getDueAlertBadge(task) {
  if (!task.due_date || task.status === 'Done') return '';
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const due = new Date(task.due_date + 'T00:00:00');
  if (isNaN(due.getTime())) return '';
  const diffDays = Math.round((due - today) / (1000 * 60 * 60 * 24));
  if (diffDays < 0) {
    return `<span class="badge-status badge-overdue">🚨 เกิน ${Math.abs(diffDays)} วัน</span>`;
  } else if (diffDays <= 2) {
    return `<span class="badge-status badge-warning">⚠️ เหลือ ${diffDays} วัน</span>`;
  }
  return '';
}

function renderKanbanBoard() {
  const filtered = getFilteredTasks();
  const cols = {
    'To Do': { el: document.getElementById('col-todo'), count: document.getElementById('count-todo'), items: [] },
    'In Progress': { el: document.getElementById('col-progress'), count: document.getElementById('count-progress'), items: [] },
    'Waiting for Review': { el: document.getElementById('col-review'), count: document.getElementById('count-review'), items: [] },
    'Revision': { el: document.getElementById('col-revision'), count: document.getElementById('count-revision'), items: [] },
    'Done': { el: document.getElementById('col-done'), count: document.getElementById('count-done'), items: [] },
  };

  filtered.forEach(t => {
    const key = cols[t.status] ? t.status : 'To Do';
    cols[key].items.push(t);
  });

  Object.keys(cols).forEach(status => {
    const group = cols[status];
    if (!group.el) return;
    group.count.innerText = group.items.length;

    if (group.items.length === 0) {
      group.el.innerHTML = `<div class="h-28 rounded-xl border border-dashed border-slate-200 flex items-center justify-center text-[11px] text-slate-400">ไม่มีรายการงาน</div>`;
    } else {
      group.el.innerHTML = group.items.map(t => renderKanbanCard(t)).join('');
    }
  });

  renderKanbanListTable(filtered);
}

function renderKanbanCard(t) {
  const dueBadge = getDueAlertBadge(t);
  const hasPendingHandover = t.pending_assignees && t.pending_assignees.trim() !== '';
  const stars = t.rating ? '⭐'.repeat(t.rating) : '';
  const hasTaskAttachment = t.task_Image && t.task_Image.trim() !== '';
  const hasSubAttachment = t.submission_Image && t.submission_Image.trim() !== '';

  let primaryActionBtn = '';
  if (t.status === 'To Do') {
    primaryActionBtn = `<button onclick="quickStatusChange(${t.id}, 'In Progress')" class="flex-1 py-1.5 px-2.5 rounded-lg bg-brand-600 hover:bg-brand-700 text-white text-[11px] font-bold transition">▶️ เริ่มทำ</button>`;
  } else if (t.status === 'In Progress' || t.status === 'Revision') {
    primaryActionBtn = `<button onclick="openSubmitModal(${t.id})" class="flex-1 py-1.5 px-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-[11px] font-bold transition">📤 ส่งตรวจ</button>`;
  } else if (t.status === 'Waiting for Review' && state.user && (state.user.is_commander || state.user.is_admin)) {
    primaryActionBtn = `
      <button onclick="openApproveModal(${t.id})" class="flex-1 py-1.5 px-2 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-[11px] font-bold transition">✅ อนุมัติ</button>
      <button onclick="openReturnModal(${t.id})" class="py-1.5 px-2 rounded-lg bg-amber-100 hover:bg-amber-200 text-amber-800 text-[11px] font-bold transition">↩️ ส่งกลับ</button>
    `;
  } else if (t.status === 'Done' && state.user && (state.user.is_commander || state.user.is_admin)) {
    primaryActionBtn = `<button onclick="openReturnModal(${t.id})" class="flex-1 py-1.5 px-2 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 text-[11px] font-bold transition">🔄 ส่งกลับ/ประเมินซ้ำ</button>`;
  }

  return `
    <div class="kanban-card bg-white rounded-xl border border-slate-200/90 p-3.5 shadow-sm hover:shadow-md hover:border-brand-300 space-y-2.5"
      draggable="true"
      ondragstart="onCardDragStart(event, ${t.id})"
      ondragend="onCardDragEnd(event)">

      <div class="flex items-start justify-between gap-1.5 flex-wrap">
        <div class="flex items-center gap-1 flex-wrap">
          ${getPriorityBadge(t.priority)}
          <span class="px-1.5 py-0.5 rounded bg-slate-100 text-slate-600 text-[10px] font-bold">${escapeHtml(t.task_type || 'Routine')}</span>
          ${dueBadge}
        </div>
        <span class="text-[10px] font-bold text-slate-400">#${t.id}</span>
      </div>

      <div>
        <h4 class="text-xs font-extrabold text-slate-900 leading-snug">${escapeHtml(t.title)}</h4>
        ${t.description ? `<p class="text-[11px] text-slate-500 line-clamp-2 mt-1">${escapeHtml(t.description)}</p>` : ''}
      </div>

      ${hasPendingHandover ? `
        <div class="px-2.5 py-1.5 rounded-lg bg-amber-50 border border-amber-200 text-[10px] font-bold text-amber-800 flex items-center justify-between gap-1">
          <span>🔄 รออนุมัติส่งต่อ ➔ ${escapeHtml(t.pending_assignees)}</span>
          ${state.user && (state.user.is_commander || state.user.is_admin) ? `<button onclick="openHandoverModal(${t.id})" class="underline text-amber-900">จัดการ</button>` : ''}
        </div>
      ` : ''}

      <div class="flex items-center gap-1.5 flex-wrap">
        ${hasTaskAttachment ? `<button onclick="openProgressModal(${t.id})" class="px-2 py-0.5 rounded bg-indigo-50 text-indigo-700 text-[10px] font-bold hover:bg-indigo-100">${isPdfAttachment(t.task_Image) ? '📄 PDF โจทย์งาน' : '🖼️ รูปโจทย์งาน'}</button>` : ''}
        ${hasSubAttachment ? `<button onclick="openProgressModal(${t.id})" class="px-2 py-0.5 rounded bg-emerald-50 text-emerald-700 text-[10px] font-bold hover:bg-emerald-100">${isPdfAttachment(t.submission_Image) ? '📄 PDF ส่งมอบ' : '🖼️ รูปส่งมอบ'}</button>` : ''}
      </div>

      <div class="pt-1 border-t border-slate-100 text-[11px] text-slate-500 space-y-1">
        <div class="flex items-center justify-between">
          <span class="truncate max-w-[150px]" title="${escapeHtml(t.assigned_to)}">👤 ${escapeHtml(t.assigned_to || '-')}</span>
          <span>📅 ${escapeHtml(t.due_date || '-')}</span>
        </div>
        <div class="flex items-center justify-between text-[10px] text-slate-400">
          <span>👑 สั่งโดย: ${escapeHtml(t.created_by || 'System')}</span>
          ${stars ? `<span title="คะแนนประเมิน">${stars}</span>` : ''}
        </div>
      </div>

      <div class="pt-1 flex items-center gap-1.5 flex-wrap">
        ${primaryActionBtn}
        <button onclick="openProgressModal(${t.id})" class="py-1.5 px-2 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 text-[11px] font-bold transition" title="บันทึก/ดูความคืบหน้า">
          📝
        </button>
        ${t.status !== 'Done' ? `
          <button onclick="openHandoverModal(${t.id})" class="py-1.5 px-2 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 text-[11px] font-bold transition" title="ส่งต่องาน / ปรับทีม">
            🔄
          </button>
        ` : ''}
        ${t.can_edit ? `
          <button onclick="openEditModal(${t.id})" class="py-1.5 px-2 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 text-[11px] font-bold transition" title="แก้ไขงาน">
            ✏️
          </button>
        ` : ''}
        ${t.can_delete ? `
          <button onclick="deleteTask(${t.id})" class="py-1.5 px-2 rounded-lg bg-rose-50 hover:bg-rose-100 text-rose-600 text-[11px] font-bold transition" title="ลบงาน">
            🗑️
          </button>
        ` : ''}
      </div>
    </div>
  `;
}

function renderKanbanListTable(tasks) {
  const tbody = document.getElementById('kanbanListTableBody');
  if (!tbody) return;
  if (tasks.length === 0) {
    tbody.innerHTML = `<tr><td colspan="7" class="px-4 py-8 text-center text-slate-400">ไม่พบรายการงานที่ค้นหา</td></tr>`;
    return;
  }
  const isCmd = state.user && (state.user.is_commander || state.user.is_admin);
  tbody.innerHTML = tasks.map(t => `
    <tr class="hover:bg-slate-50 transition">
      <td class="px-4 py-3 font-bold text-slate-400">#${t.id}</td>
      <td class="px-4 py-3">
        <p class="font-bold text-slate-900">${escapeHtml(t.title)}</p>
        <p class="text-[11px] text-slate-400">👑 สั่งโดย: ${escapeHtml(t.created_by || 'System')} | 🏷️ ${escapeHtml(t.task_type || 'Routine')}</p>
      </td>
      <td class="px-4 py-3 text-slate-700 font-medium">${escapeHtml(t.assigned_to)}</td>
      <td class="px-4 py-3">${getPriorityBadge(t.priority)}</td>
      <td class="px-4 py-3 text-slate-600">${escapeHtml(t.due_date || '-')} ${getDueAlertBadge(t)}</td>
      <td class="px-4 py-3">${getStatusBadge(t.status)}</td>
      <td class="px-4 py-3 text-right space-x-1">
        ${t.status === 'To Do' ? `<button onclick="quickStatusChange(${t.id}, 'In Progress')" class="px-2.5 py-1 rounded-lg bg-brand-600 text-white font-bold">▶️ เริ่ม</button>` : ''}
        ${(t.status === 'In Progress' || t.status === 'Revision') ? `<button onclick="openSubmitModal(${t.id})" class="px-2.5 py-1 rounded-lg bg-emerald-600 text-white font-bold">📤 ส่งตรวจ</button>` : ''}
        ${(t.status === 'Waiting for Review' && isCmd) ? `<button onclick="openApproveModal(${t.id})" class="px-2.5 py-1 rounded-lg bg-emerald-600 text-white font-bold">✅ ตรวจรับ</button>` : ''}
        <button onclick="openProgressModal(${t.id})" class="px-2.5 py-1 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold">📝 คืบหน้า</button>
        ${t.status !== 'Done' ? `<button onclick="openHandoverModal(${t.id})" class="px-2.5 py-1 rounded-lg bg-amber-50 hover:bg-amber-100 text-amber-700 font-bold">🔄 ส่งต่อ</button>` : ''}
        ${t.can_edit ? `<button onclick="openEditModal(${t.id})" class="px-2.5 py-1 rounded-lg bg-sky-50 hover:bg-sky-100 text-sky-700 font-bold">✏️ แก้ไข</button>` : ''}
        ${t.can_delete ? `<button onclick="deleteTask(${t.id})" class="px-2.5 py-1 rounded-lg bg-rose-50 hover:bg-rose-100 text-rose-600 font-bold">🗑️ ลบ</button>` : ''}
      </td>
    </tr>
  `).join('');
}

// --- HTML5 Drag and Drop Handlers ---
function onCardDragStart(e, taskId) {
  state.draggedTaskId = taskId;
  e.currentTarget.classList.add('dragging');
  e.dataTransfer.effectAllowed = 'move';
  e.dataTransfer.setData('text/plain', String(taskId));
}

function onCardDragEnd(e) {
  e.currentTarget.classList.remove('dragging');
  document.querySelectorAll('.kanban-col').forEach(col => col.classList.remove('drag-over'));
}

function handleDragOver(e) {
  e.preventDefault();
  e.dataTransfer.dropEffect = 'move';
  e.currentTarget.classList.add('drag-over');
}

function handleDragLeave(e) {
  e.currentTarget.classList.remove('drag-over');
}

async function handleDrop(e, targetStatus) {
  e.preventDefault();
  e.currentTarget.classList.remove('drag-over');
  const taskId = state.draggedTaskId || parseInt(e.dataTransfer.getData('text/plain'), 10);
  if (!taskId) return;

  const task = state.tasks.find(t => t.id === taskId);
  if (!task || task.status === targetStatus) return;

  if (targetStatus === 'Done' && (!state.user || (!state.user.is_commander && !state.user.is_admin))) {
    showToast('เฉพาะผู้สั่งการ (Commander) เท่านั้นที่อนุมัติจบงาน (Done) ได้ ระบบจะเปิดหน้าส่งมอบงานให้แทน', 'warning');
    openSubmitModal(taskId);
    return;
  }

  if (targetStatus === 'Done' && state.user && (state.user.is_commander || state.user.is_admin)) {
    openApproveModal(taskId);
    return;
  }

  await quickStatusChange(taskId, targetStatus);
}

async function quickStatusChange(taskId, newStatus) {
  try {
    await api(`/api/tasks/${taskId}/status`, {
      method: 'PATCH',
      body: JSON.stringify({ status: newStatus }),
    });
    showToast(`อัปเดตสถานะงาน #${taskId} ➔ ${newStatus}`, 'success');
    await loadAllData();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

async function deleteTask(taskId) {
  if (!confirm(`ยืนยันการลบงาน #${taskId} ออกจากระบบอย่างถาวร?`)) return;
  try {
    await api(`/api/tasks/${taskId}`, { method: 'DELETE' });
    showToast(`ลบงาน #${taskId} เรียบร้อยแล้ว`, 'success');
    await loadAllData();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

// ============================================================================
// MODULE 3: MODALS (PROGRESS, SUBMIT, APPROVE, RETURN, HANDOVER, EDIT)
// ============================================================================
function closeModal(modalId) {
  const el = document.getElementById(modalId);
  if (el) el.classList.add('hidden');
}

// 1. Progress & Logs Modal (with log type, attachment, and inline edit/delete)
async function openProgressModal(taskId) {
  state.activeTaskId = taskId;
  state.editingLogId = null;
  const task = state.tasks.find(t => t.id === taskId);
  if (!task) return;

  document.getElementById('progressModalTitle').innerText = `📝 ความคืบหน้างาน #${task.id}: ${task.title}`;
  document.getElementById('progressModalSubtitle').innerText = `ผู้รับผิดชอบ: ${task.assigned_to} | ผู้สั่งงาน: ${task.created_by || 'System'} | กำหนดส่ง: ${task.due_date || '-'} | สถานะ: ${task.status}`;
  document.getElementById('newLogNote').value = '';
  document.getElementById('newLogImageLink').value = '';
  const fileEl = document.getElementById('newLogImageFile');
  if (fileEl) fileEl.value = '';

  // Render Task Reference & Submission Attachments if present
  const refBox = document.getElementById('progressTaskAttachmentBox');
  if (refBox) {
    let html = '';
    if (task.task_Image) html += renderAttachmentPreviewHtml(task.task_Image, 'ไฟล์แนบต้นฉบับ / โจทย์งาน');
    if (task.submission_Image) html += renderAttachmentPreviewHtml(task.submission_Image, 'ไฟล์ผลงานที่ส่งตรวจล่าสุด');
    if (html) {
      refBox.innerHTML = html;
      refBox.classList.remove('hidden');
    } else {
      refBox.innerHTML = '';
      refBox.classList.add('hidden');
    }
  }

  // Permission notice for adding new logs
  const addForm = document.getElementById('addProgressLogForm');
  const permNotice = document.getElementById('progressPermissionNotice');
  if (task.can_edit_progress === false) {
    addForm.classList.add('hidden');
    permNotice.classList.remove('hidden');
  } else {
    addForm.classList.remove('hidden');
    permNotice.classList.add('hidden');
  }

  document.getElementById('progressModal').classList.remove('hidden');
  await loadTaskLogs(taskId);
}

function parseLogEntry(rawNote) {
  if (!rawNote) return { text: '', attachment: null };
  let text = rawNote;
  let attachment = null;
  const match = rawNote.match(/\[ATTACHED_IMAGE:\s*(.+?)\]/s);
  if (match) {
    attachment = match[1].trim();
    text = rawNote.replace(match[0], '').trim();
  }
  return { text, attachment };
}

async function loadTaskLogs(taskId) {
  const listEl = document.getElementById('progressLogsList');
  listEl.innerHTML = `<p class="text-xs text-slate-400 text-center py-6">กำลังโหลดประวัติการอัปเดต...</p>`;
  try {
    const res = await api(`/api/tasks/${taskId}/logs`);
    const logs = res.logs || [];
    if (logs.length === 0) {
      listEl.innerHTML = `<div class="p-6 rounded-xl bg-slate-50 border border-slate-100 text-center text-xs text-slate-400">ยังไม่มีบันทึกความคืบหน้าสำหรับงานนี้</div>`;
      return;
    }

    const task = state.tasks.find(t => t.id === taskId);
    const canModify = task ? task.can_edit_progress !== false : true;

    listEl.innerHTML = logs.map(l => {
      const { text, attachment } = parseLogEntry(l.note || '');
      const isEditing = state.editingLogId === l.id;

      if (isEditing) {
        return `
          <div class="p-3.5 rounded-xl bg-amber-50/70 border border-amber-300 space-y-2">
            <div class="flex items-center justify-between">
              <span class="text-xs font-bold text-amber-900">✏️ แก้ไขบันทึกของ ${escapeHtml(l.updated_by)}</span>
              <span class="text-[11px] text-slate-400">${escapeHtml((l.created_at || '').slice(0, 16))}</span>
            </div>
            <textarea id="editLogTextarea_${l.id}" rows="3" class="w-full px-3 py-2 rounded-xl border border-amber-300 text-xs">${escapeHtml(text)}</textarea>
            <div class="flex items-center gap-2 justify-end">
              <button onclick="saveEditedLog(${l.id})" class="px-3 py-1.5 rounded-lg bg-emerald-600 text-white text-xs font-bold">💾 บันทึก</button>
              <button onclick="cancelEditLog()" class="px-3 py-1.5 rounded-lg bg-slate-200 text-slate-700 text-xs font-bold">❌ ยกเลิก</button>
            </div>
          </div>
        `;
      }

      return `
        <div class="p-3.5 rounded-xl bg-slate-50 border border-slate-200/70 space-y-1.5">
          <div class="flex items-center justify-between gap-2">
            <span class="text-xs font-bold text-brand-700">👤 ${escapeHtml(l.updated_by)}</span>
            <div class="flex items-center gap-2">
              <span class="text-[11px] text-slate-400">🕒 ${escapeHtml((l.created_at || '').slice(0, 16))}</span>
              ${canModify ? `
                <button onclick="startEditLog(${l.id})" class="text-[11px] text-slate-500 hover:text-brand-600 font-bold" title="แก้ไขบันทึกนี้">✏️</button>
                <button onclick="deleteLogEntry(${l.id})" class="text-[11px] text-slate-500 hover:text-rose-600 font-bold" title="ลบบันทึกนี้">🗑️</button>
              ` : ''}
            </div>
          </div>
          <p class="text-xs text-slate-700 whitespace-pre-line">${escapeHtml(text)}</p>
          ${attachment ? renderAttachmentPreviewHtml(attachment, 'ไฟล์แนบในความคืบหน้า') : ''}
        </div>
      `;
    }).join('');
  } catch (err) {
    listEl.innerHTML = `<p class="text-xs text-rose-500 text-center py-4">${escapeHtml(err.message)}</p>`;
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
  const textarea = document.getElementById(`editLogTextarea_${logId}`);
  if (!textarea) return;
  const note = textarea.value.trim();
  if (!note) return showToast('ข้อความบันทึกต้องไม่ว่างเปล่า', 'warning');

  try {
    await api(`/api/logs/${logId}`, {
      method: 'PUT',
      body: JSON.stringify({ note }),
    });
    state.editingLogId = null;
    showToast('แก้ไขบันทึกเรียบร้อยแล้ว ✅', 'success');
    await loadTaskLogs(state.activeTaskId);
  } catch (err) {
    showToast(err.message, 'error');
  }
}

async function deleteLogEntry(logId) {
  if (!confirm('ยืนยันการลบบันทึกความคืบหน้านี้?')) return;
  try {
    await api(`/api/logs/${logId}`, { method: 'DELETE' });
    showToast('ลบบันทึกความคืบหน้าเรียบร้อยแล้ว 🗑️', 'success');
    await loadTaskLogs(state.activeTaskId);
  } catch (err) {
    showToast(err.message, 'error');
  }
}

async function submitTaskLog(e) {
  e.preventDefault();
  const log_type = document.getElementById('newLogType')?.value || '📌 รายงานความคืบหน้า';
  const note = document.getElementById('newLogNote').value.trim();
  const linkVal = document.getElementById('newLogImageLink')?.value.trim() || '';
  const fileEl = document.getElementById('newLogImageFile');

  if (!note && !linkVal && (!fileEl || !fileEl.files || !fileEl.files[0])) {
    return showToast('กรุณากรอกรายละเอียดความคืบหน้า หรือแนบไฟล์อย่างน้อย 1 อย่าง', 'warning');
  }

  try {
    let attachment = linkVal ? convertGdriveUrl(linkVal) : '';
    if (fileEl && fileEl.files && fileEl.files[0]) {
      attachment = await fileToBase64(fileEl.files[0]);
    }

    await api(`/api/tasks/${state.activeTaskId}/logs`, {
      method: 'POST',
      body: JSON.stringify({
        note: note || 'แนบไฟล์ความคืบหน้า',
        log_type,
        attachment,
      }),
    });
    document.getElementById('newLogNote').value = '';
    if (document.getElementById('newLogImageLink')) document.getElementById('newLogImageLink').value = '';
    if (fileEl) fileEl.value = '';
    showToast('บันทึกความคืบหน้าเรียบร้อยแล้ว 📝', 'success');
    await loadTaskLogs(state.activeTaskId);
    await loadAllData();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

// 2. Submit Work Modal (Operator -> Waiting for Review)
function openSubmitModal(taskId) {
  state.activeTaskId = taskId;
  const task = state.tasks.find(t => t.id === taskId);
  if (!task) return;
  document.getElementById('submitModalSubtitle').innerText = `#${task.id}: ${task.title}`;
  document.getElementById('submitWorkNote').value = '';
  document.getElementById('submitWorkImageLink').value = '';
  document.getElementById('submitWorkImageFile').value = '';
  document.getElementById('submitWorkModal').classList.remove('hidden');
}

async function handleTaskSubmitWork(e) {
  e.preventDefault();
  const note = document.getElementById('submitWorkNote').value.trim();
  const linkVal = document.getElementById('submitWorkImageLink').value.trim();
  const fileInput = document.getElementById('submitWorkImageFile');

  try {
    let submission_image = linkVal ? convertGdriveUrl(linkVal) : '';
    if (fileInput && fileInput.files && fileInput.files[0]) {
      submission_image = await fileToBase64(fileInput.files[0]);
    }
    const res = await api(`/api/tasks/${state.activeTaskId}/submit`, {
      method: 'POST',
      body: JSON.stringify({ note, submission_image }),
    });
    closeModal('submitWorkModal');
    showToast(res.message, 'success');
    await loadAllData();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

// 3. Approve Task Modal (Commander -> Done)
function openApproveModal(taskId) {
  state.activeTaskId = taskId;
  const task = state.tasks.find(t => t.id === taskId);
  if (!task) return;
  document.getElementById('approveModalSubtitle').innerText = `#${task.id}: ${task.title} (ผู้ปฏิบัติงาน: ${task.assigned_to})`;
  document.getElementById('approveNote').value = '';

  const previewBox = document.getElementById('approveAttachmentPreview');
  if (previewBox) {
    if (task.submission_Image) {
      previewBox.innerHTML = renderAttachmentPreviewHtml(task.submission_Image, 'ไฟล์ผลงานที่ส่งมอบ');
      previewBox.classList.remove('hidden');
    } else {
      previewBox.innerHTML = '';
      previewBox.classList.add('hidden');
    }
  }

  document.getElementById('approveModal').classList.remove('hidden');
}

async function handleTaskApprove(e) {
  e.preventDefault();
  const rating = parseInt(document.querySelector('input[name="approveRating"]:checked')?.value || '5', 10);
  const note = document.getElementById('approveNote').value.trim();
  try {
    const res = await api(`/api/tasks/${state.activeTaskId}/approve`, {
      method: 'POST',
      body: JSON.stringify({ rating, note }),
    });
    closeModal('approveModal');
    showToast(res.message, 'success');
    await loadAllData();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

// 4. Return / Revision / Re-evaluate Modal
function openReturnModal(taskId) {
  state.activeTaskId = taskId;
  const task = state.tasks.find(t => t.id === taskId);
  if (!task) return;
  document.getElementById('returnModalSubtitle').innerText = `#${task.id}: ${task.title}`;
  document.getElementById('returnTargetStatus').value = 'In Progress';
  document.getElementById('returnRating').value = String(task.rating || 3);
  document.getElementById('returnNewDueDate').value = task.due_date || '';
  document.getElementById('returnReason').value = '';
  document.getElementById('returnModal').classList.remove('hidden');
}

async function handleTaskReturn(e) {
  e.preventDefault();
  const target_status = document.getElementById('returnTargetStatus').value;
  const rating = parseInt(document.getElementById('returnRating').value || '3', 10);
  const new_due_date = document.getElementById('returnNewDueDate').value;
  const reason = document.getElementById('returnReason').value.trim();

  try {
    const res = await api(`/api/tasks/${state.activeTaskId}/return`, {
      method: 'POST',
      body: JSON.stringify({ target_status, rating, new_due_date, reason }),
    });
    closeModal('returnModal');
    showToast(res.message, 'warning');
    await loadAllData();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

// 5. Handover Modal (with Pending Approval Box + Interactive Multi-Select)
function openHandoverModal(taskId) {
  state.activeTaskId = taskId;
  const task = state.tasks.find(t => t.id === taskId);
  if (!task) return;
  document.getElementById('handoverModalSubtitle').innerText = `#${task.id}: ${task.title} (ผู้รับผิดชอบปัจจุบัน: ${task.assigned_to})`;
  document.getElementById('handoverReason').value = '';

  // Check if there is a pending handover request
  const pendingBox = document.getElementById('handoverPendingBox');
  const pendingInfo = document.getElementById('handoverPendingInfo');
  const cmdBtns = document.getElementById('handoverCommanderActions');

  if (task.pending_assignees && task.pending_assignees.trim() !== '') {
    pendingBox.classList.remove('hidden');
    pendingInfo.innerText = `ขอเปลี่ยนเป็น: ${task.pending_assignees} | เหตุผล: ${task.handover_Reason || '-'} (โดย ${task.handover_Requested_By || '-'})`;
    if (state.user && (state.user.is_commander || state.user.is_admin)) {
      cmdBtns.classList.remove('hidden');
    } else {
      cmdBtns.classList.add('hidden');
    }
  } else {
    pendingBox.classList.add('hidden');
  }

  // Pre-select current assignees in multi-select
  const currentNames = (task.assigned_to || '').split(',').map(s => s.trim()).filter(Boolean);
  const currentUsernames = state.operators
    .filter(op => currentNames.includes(op.display_name) || currentNames.includes(op.username))
    .map(op => op.username);

  renderMultiSelect('handoverAssigneesContainer', 'handoverAssignees', currentUsernames);
  document.getElementById('handoverModal').classList.remove('hidden');
}

async function decideHandoverFromModal(approve) {
  if (!state.activeTaskId) return;
  await decideHandover(state.activeTaskId, approve);
  closeModal('handoverModal');
}

async function handleTaskHandover(e) {
  e.preventDefault();
  const new_assignees = getSelectedMulti('handoverAssignees');
  const reason = document.getElementById('handoverReason').value.trim();

  if (new_assignees.length === 0) {
    return showToast('กรุณาคลิกเลือกผู้ปฏิบัติงานชุดใหม่อย่างน้อย 1 คน', 'warning');
  }
  try {
    const res = await api(`/api/tasks/${state.activeTaskId}/handover`, {
      method: 'POST',
      body: JSON.stringify({ new_assignees, reason }),
    });
    closeModal('handoverModal');
    showToast(res.message, 'success');
    await loadAllData();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

// 6. Edit Task Modal (Commander / Creator)
function openEditModal(taskId) {
  state.activeTaskId = taskId;
  const task = state.tasks.find(t => t.id === taskId);
  if (!task) return;

  document.getElementById('editTitle').value = task.title || '';
  document.getElementById('editDesc').value = task.description || '';
  document.getElementById('editPriority').value = task.priority || 'Medium';
  document.getElementById('editType').value = task.task_type || 'Routine';
  document.getElementById('editStatus').value = task.status || 'To Do';
  document.getElementById('editDueDate').value = task.due_date || '';
  document.getElementById('editImageLink').value = (task.task_Image && !task.task_Image.startsWith('data:')) ? task.task_Image : '';
  const fileEl = document.getElementById('editImageFile');
  if (fileEl) fileEl.value = '';

  const previewEl = document.getElementById('editCurrentAttachmentPreview');
  if (previewEl) {
    if (task.task_Image) {
      previewEl.innerHTML = renderAttachmentPreviewHtml(task.task_Image, 'ไฟล์แนบปัจจุบัน');
      previewEl.classList.remove('hidden');
    } else {
      previewEl.innerHTML = '';
      previewEl.classList.add('hidden');
    }
  }

  const currentNames = (task.assigned_to || '').split(',').map(s => s.trim()).filter(Boolean);
  const currentUsernames = state.operators
    .filter(op => currentNames.includes(op.display_name) || currentNames.includes(op.username))
    .map(op => op.username);

  renderMultiSelect('editAssigneesContainer', 'editAssignees', currentUsernames);
  document.getElementById('editTaskModal').classList.remove('hidden');
}

async function handleEditTaskSubmit(e) {
  e.preventDefault();
  const title = document.getElementById('editTitle').value.trim();
  const description = document.getElementById('editDesc').value.trim();
  const assignees = getSelectedMulti('editAssignees');
  const priority = document.getElementById('editPriority').value;
  const task_type = document.getElementById('editType').value;
  const status = document.getElementById('editStatus').value;
  const due_date = document.getElementById('editDueDate').value;
  const linkVal = document.getElementById('editImageLink').value.trim();
  const fileEl = document.getElementById('editImageFile');

  if (!title || assignees.length === 0) {
    return showToast('กรุณาระบุชื่องานและผู้รับผิดชอบอย่างน้อย 1 คน', 'warning');
  }

  try {
    let task_image = undefined;
    if (fileEl && fileEl.files && fileEl.files[0]) {
      task_image = await fileToBase64(fileEl.files[0]);
    } else if (linkVal) {
      task_image = convertGdriveUrl(linkVal);
    }

    const payload = { title, description, assignees, priority, task_type, status, due_date };
    if (task_image !== undefined) payload.task_image = task_image;

    const res = await api(`/api/tasks/${state.activeTaskId}`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    });
    closeModal('editTaskModal');
    showToast(res.message, 'success');
    await loadAllData();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

// ============================================================================
// MODULE 4: KPI & PERFORMANCE DASHBOARD + MONTHLY HISTORICAL REPORT
// ============================================================================
function switchKpiTab(tab) {
  state.kpiTab = tab;
  const paneLeader = document.getElementById('kpiPaneLeaderboard');
  const paneHist = document.getElementById('kpiPaneHistory');
  const btnLeader = document.getElementById('kpiTabLeaderboard');
  const btnHist = document.getElementById('kpiTabHistory');

  if (tab === 'leaderboard') {
    paneLeader.classList.remove('hidden');
    paneHist.classList.add('hidden');
    btnLeader.className = 'px-4 py-2.5 rounded-xl text-xs font-bold bg-brand-600 text-white shadow-sm transition';
    btnHist.className = 'px-4 py-2.5 rounded-xl text-xs font-bold bg-white text-slate-600 border border-slate-200 hover:bg-slate-50 transition';
  } else {
    paneLeader.classList.add('hidden');
    paneHist.classList.remove('hidden');
    btnHist.className = 'px-4 py-2.5 rounded-xl text-xs font-bold bg-brand-600 text-white shadow-sm transition';
    btnLeader.className = 'px-4 py-2.5 rounded-xl text-xs font-bold bg-white text-slate-600 border border-slate-200 hover:bg-slate-50 transition';
  }
  renderKpiDashboard();
}

function renderKpiDashboard() {
  if (!state.kpiSummary) return;
  const { overview, leaderboard } = state.kpiSummary;

  const cardsEl = document.getElementById('kpiOverviewCards');
  if (cardsEl && overview) {
    cardsEl.innerHTML = `
      <div class="bg-white rounded-2xl border border-slate-200/80 p-4 shadow-sm">
        <p class="text-xs font-semibold text-slate-400">📋 งานทั้งหมดในระบบ</p>
        <p class="text-2xl font-extrabold text-slate-900 mt-1">${overview.total}</p>
      </div>
      <div class="bg-white rounded-2xl border border-emerald-200/80 p-4 shadow-sm">
        <p class="text-xs font-semibold text-emerald-600">✅ เสร็จสมบูรณ์ (Done)</p>
        <p class="text-2xl font-extrabold text-emerald-700 mt-1">${overview.done}</p>
      </div>
      <div class="bg-white rounded-2xl border border-sky-200/80 p-4 shadow-sm">
        <p class="text-xs font-semibold text-sky-600">⚡ กำลังดำเนินการ</p>
        <p class="text-2xl font-extrabold text-sky-700 mt-1">${overview.in_progress}</p>
      </div>
      <div class="bg-white rounded-2xl border border-amber-200/80 p-4 shadow-sm">
        <p class="text-xs font-semibold text-amber-600">⏳ รอตรวจรับ</p>
        <p class="text-2xl font-extrabold text-amber-700 mt-1">${overview.review}</p>
      </div>
      <div class="bg-white rounded-2xl border border-rose-200/80 p-4 shadow-sm">
        <p class="text-xs font-semibold text-rose-600">🔧 ส่งกลับแก้ไข (Revision)</p>
        <p class="text-2xl font-extrabold text-rose-700 mt-1">${overview.revision}</p>
      </div>
    `;
  }

  // Quick Task Inspect & Delete list
  const quickList = document.getElementById('kpiQuickDeleteList');
  if (quickList) {
    if (state.tasks.length === 0) {
      quickList.innerHTML = `<p class="text-xs text-slate-400 text-center py-3">ไม่มีรายการงานในระบบ</p>`;
    } else {
      quickList.innerHTML = state.tasks.map(t => `
        <div class="p-2.5 rounded-xl bg-slate-50 border border-slate-200 flex items-center justify-between gap-2 text-xs">
          <div class="truncate">
            <span class="font-bold text-slate-800">#${t.id} ${escapeHtml(t.title)}</span>
            <span class="text-slate-500 ml-2">👤 ${escapeHtml(t.assigned_to)} | 👑 ${escapeHtml(t.created_by || 'System')} | สถานะ: ${escapeHtml(t.status)}</span>
          </div>
          ${t.can_delete ? `<button onclick="deleteTask(${t.id})" class="px-2.5 py-1 rounded-lg bg-rose-600 hover:bg-rose-700 text-white text-[11px] font-bold flex-shrink-0">🗑️ ลบงาน</button>` : ''}
        </div>
      `).join('');
    }
  }

  // Show direct KPI Adjust box for Commander/Admin
  const directBox = document.getElementById('kpiDirectAdjustBox');
  if (directBox) {
    if (state.user && (state.user.is_commander || state.user.is_admin)) {
      directBox.classList.remove('hidden');
    } else {
      directBox.classList.add('hidden');
    }
  }

  // Leaderboard table
  const tbody = document.getElementById('kpiLeaderboardBody');
  if (tbody && leaderboard) {
    tbody.innerHTML = leaderboard.map((row, idx) => {
      const rankMedal = idx === 0 ? '🥇 1' : idx === 1 ? '🥈 2' : idx === 2 ? '🥉 3' : `${idx + 1}`;
      return `
        <tr class="hover:bg-slate-50 transition">
          <td class="px-4 py-3 font-bold text-slate-700">${rankMedal}</td>
          <td class="px-4 py-3">
            <p class="font-bold text-slate-900">${escapeHtml(row.display_name)}</p>
            <p class="text-[11px] text-slate-400">@${escapeHtml(row.username)}</p>
          </td>
          <td class="px-4 py-3 text-center font-semibold">${row.total_assigned}</td>
          <td class="px-4 py-3 text-center font-bold text-emerald-600">${row.done_count}</td>
          <td class="px-4 py-3 text-center">
            <span class="px-2 py-0.5 rounded-full text-[11px] font-bold bg-sky-50 text-sky-700">${row.ontime_rate}%</span>
          </td>
          <td class="px-4 py-3 text-center font-semibold text-amber-600">⭐ ${row.avg_rating} (${row.satisfaction_pts || 0} แต้ม)</td>
          <td class="px-4 py-3 text-center font-semibold ${row.manual_pts >= 0 ? 'text-emerald-600' : 'text-rose-600'}">
            ${row.manual_pts > 0 ? '+' : ''}${row.manual_pts}
          </td>
          <td class="px-4 py-3 text-right">
            <span class="px-3 py-1 rounded-xl bg-brand-50 text-brand-700 font-extrabold text-sm">${row.total_kpi}</span>
          </td>
        </tr>
      `;
    }).join('');
  }

  renderKpiCharts(leaderboard || []);
  renderHistoryReport();
}

function renderKpiCharts(leaderboard) {
  const ctxKpi = document.getElementById('chartKpiBar');
  const ctxOntime = document.getElementById('chartOntimeBar');
  if (!ctxKpi || !ctxOntime || typeof Chart === 'undefined') return;

  const labels = leaderboard.map(r => r.display_name);
  const kpiScores = leaderboard.map(r => r.total_kpi);
  const ontimeData = leaderboard.map(r => r.ontime_count);
  const lateData = leaderboard.map(r => r.late_count);

  if (state.chartKpi) state.chartKpi.destroy();
  if (state.chartOntime) state.chartOntime.destroy();

  state.chartKpi = new Chart(ctxKpi, {
    type: 'bar',
    data: {
      labels,
      datasets: [{
        label: 'คะแนน KPI รวม (Total Score)',
        data: kpiScores,
        backgroundColor: '#0284c7',
        borderRadius: 8,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: { y: { beginAtZero: true } },
    },
  });

  state.chartOntime = new Chart(ctxOntime, {
    type: 'bar',
    data: {
      labels,
      datasets: [
        { label: 'ส่งตรงเวลา (On-Time)', data: ontimeData, backgroundColor: '#10b981', borderRadius: 6 },
        { label: 'ส่งล่าช้า (Late)', data: lateData, backgroundColor: '#f43f5e', borderRadius: 6 },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: { y: { beginAtZero: true } },
    },
  });
}

function getFilteredHistoryTasks() {
  const emp = document.getElementById('histFilterEmployee')?.value || 'ทั้งหมด';
  const monthVal = document.getElementById('histFilterMonth')?.value || 'ทั้งหมด';
  const statusVal = document.getElementById('histFilterStatus')?.value || 'ทั้งหมด';

  return state.tasks.filter(t => {
    if (emp !== 'ทั้งหมด') {
      const names = (t.assigned_to || '').split(',').map(s => s.trim());
      if (!names.includes(emp)) return false;
    }
    if (monthVal !== 'ทั้งหมด') {
      if (getTaskThaiMonthYear(t) !== monthVal) return false;
    }
    if (statusVal !== 'ทั้งหมด' && t.status !== statusVal) {
      return false;
    }
    return true;
  });
}

function renderHistoryReport() {
  const tbody = document.getElementById('historyTableBody');
  const summaryEl = document.getElementById('histSummaryCards');
  if (!tbody) return;

  const filtered = getFilteredHistoryTasks();

  const totalCount = filtered.length;
  const doneCount = filtered.filter(t => t.status === 'Done').length;
  const progressCount = filtered.filter(t => ['In Progress', 'To Do', 'Revision'].includes(t.status)).length;
  const ontimeCount = filtered.filter(t => t.is_on_time === 1).length;
  const rated = filtered.filter(t => (t.rating || 0) > 0);
  const avgRating = rated.length > 0 ? (rated.reduce((acc, t) => acc + t.rating, 0) / rated.length).toFixed(2) : '0.00';

  if (summaryEl) {
    summaryEl.innerHTML = `
      <div class="bg-slate-50 rounded-xl border border-slate-200 p-3">
        <p class="text-[11px] font-semibold text-slate-500">📋 งานทั้งหมด (ตามตัวกรอง)</p>
        <p class="text-lg font-extrabold text-slate-900 mt-0.5">${totalCount} งาน</p>
      </div>
      <div class="bg-emerald-50 rounded-xl border border-emerald-200 p-3">
        <p class="text-[11px] font-semibold text-emerald-700">✅ เสร็จสมบูรณ์ (Done)</p>
        <p class="text-lg font-extrabold text-emerald-800 mt-0.5">${doneCount} งาน</p>
      </div>
      <div class="bg-sky-50 rounded-xl border border-sky-200 p-3">
        <p class="text-[11px] font-semibold text-sky-700">⏳ กำลังทำ / รอตรวจ</p>
        <p class="text-lg font-extrabold text-sky-800 mt-0.5">${progressCount} งาน</p>
      </div>
      <div class="bg-indigo-50 rounded-xl border border-indigo-200 p-3">
        <p class="text-[11px] font-semibold text-indigo-700">⏱️ ส่งตรงเวลา (On-Time)</p>
        <p class="text-lg font-extrabold text-indigo-800 mt-0.5">${ontimeCount} งาน</p>
      </div>
      <div class="bg-amber-50 rounded-xl border border-amber-200 p-3">
        <p class="text-[11px] font-semibold text-amber-700">⭐ คะแนนพึงพอใจเฉลี่ย</p>
        <p class="text-lg font-extrabold text-amber-800 mt-0.5">${avgRating} / 5.0</p>
      </div>
    `;
  }

  if (filtered.length === 0) {
    tbody.innerHTML = `<tr><td colspan="12" class="px-4 py-8 text-center text-slate-400">ไม่พบประวัติงานตามตัวกรองที่เลือก</td></tr>`;
    return;
  }

  tbody.innerHTML = filtered.map(t => {
    const ontimeText = t.is_on_time === 1 ? '✅ ตรงเวลา' : t.is_on_time === 0 ? '⚠️ ล่าช้า' : '⏳ รอส่ง';
    const stars = t.rating ? '⭐'.repeat(t.rating) + ` (${t.rating})` : '-';
    return `
      <tr class="hover:bg-slate-50 transition">
        <td class="px-3 py-2.5 font-bold text-slate-400">#${t.id}</td>
        <td class="px-3 py-2.5 text-slate-600">${escapeHtml(getTaskThaiMonthYear(t))}</td>
        <td class="px-3 py-2.5 font-bold text-slate-900">${escapeHtml(t.title)}</td>
        <td class="px-3 py-2.5 text-slate-600">${escapeHtml(t.task_type || 'Routine')}</td>
        <td class="px-3 py-2.5 text-slate-700">${escapeHtml(t.assigned_to)}</td>
        <td class="px-3 py-2.5 text-slate-500">${escapeHtml(t.created_by || 'System')}</td>
        <td class="px-3 py-2.5">${getPriorityBadge(t.priority)}</td>
        <td class="px-3 py-2.5">${getStatusBadge(t.status)}</td>
        <td class="px-3 py-2.5 text-slate-600">${escapeHtml(t.due_date || '-')}</td>
        <td class="px-3 py-2.5 text-slate-500">${escapeHtml((t.submitted_at || '-').slice(0, 16))}</td>
        <td class="px-3 py-2.5 font-semibold">${ontimeText}</td>
        <td class="px-3 py-2.5 text-amber-600 font-bold">${stars}</td>
      </tr>
    `;
  }).join('');
}

function downloadHistoryCsv() {
  const filtered = getFilteredHistoryTasks();
  if (filtered.length === 0) {
    return showToast('ไม่มีข้อมูลสำหรับดาวน์โหลด', 'warning');
  }

  const headers = [
    'รหัสงาน (ID)', 'เดือน-ปี', 'ชื่องาน', 'รายละเอียดงาน', 'ประเภทงาน',
    'ผู้รับผิดชอบ', 'ผู้สั่งงาน', 'ความสำคัญ', 'สถานะ',
    'วันที่สร้างงาน', 'กำหนดส่ง (Due Date)', 'วันที่ส่งจริง (Submitted At)',
    'การส่งตรงเวลา', 'คะแนนประเมิน (1-5)',
  ];

  const rows = filtered.map(t => {
    const ontimeText = t.is_on_time === 1 ? 'ตรงเวลา (On-Time)' : t.is_on_time === 0 ? 'ล่าช้า (Late)' : 'ยังไม่ส่ง';
    return [
      t.id,
      getTaskThaiMonthYear(t),
      t.title || '',
      (t.description || '').replace(/\r?\n/g, ' '),
      t.task_type || 'Routine',
      t.assigned_to || '',
      t.created_by || 'System',
      t.priority || 'Medium',
      t.status || 'To Do',
      (t.created_at || '').slice(0, 16),
      t.due_date || '',
      (t.submitted_at || '').slice(0, 16),
      ontimeText,
      t.rating || '',
    ].map(cell => `"${String(cell).replace(/"/g, '""')}"`).join(',');
  });

  const csvContent = '\uFEFF' + [headers.join(','), ...rows].join('\r\n');
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `SVV_Work_History_${new Date().toISOString().slice(0, 10)}.csv`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
  showToast('ดาวน์โหลดไฟล์รายงาน CSV เรียบร้อยแล้ว 📥', 'success');
}

// ============================================================================
// MODULE 5: ADMIN PANEL
// ============================================================================
async function loadAdminUsers() {
  if (!state.user || !state.user.is_admin) return;
  const tbody = document.getElementById('adminUsersTableBody');
  if (!tbody) return;

  try {
    const res = await api('/api/admin/users');
    const users = res.users || [];
    tbody.innerHTML = users.map(u => `
      <tr class="hover:bg-slate-50 transition">
        <td class="px-4 py-3 font-bold text-slate-900">${escapeHtml(u.username)}</td>
        <td class="px-4 py-3">
          <input type="text" id="adm_name_${escapeHtml(u.username)}" value="${escapeHtml(u.display_name)}"
            class="px-2.5 py-1.5 rounded-lg border border-slate-200 text-xs w-full max-w-[180px]" />
        </td>
        <td class="px-4 py-3">
          <select id="adm_role_${escapeHtml(u.username)}" class="px-2.5 py-1.5 rounded-lg border border-slate-200 text-xs bg-white">
            <option value="Operator (ผู้ปฏิบัติงาน)" ${u.role.includes('Operator') ? 'selected' : ''}>Operator (ผู้ปฏิบัติงาน)</option>
            <option value="Commander (ผู้สั่งการ)" ${u.role.includes('Commander') ? 'selected' : ''}>Commander (ผู้สั่งการ)</option>
            <option value="Admin (ผู้ดูแลระบบ)" ${u.role.includes('Admin') ? 'selected' : ''}>Admin (ผู้ดูแลระบบ)</option>
          </select>
        </td>
        <td class="px-4 py-3 text-slate-400">${escapeHtml((u.created_at || '-').slice(0, 10))}</td>
        <td class="px-4 py-3 text-right space-x-1">
          <button onclick="saveAdminUser('${escapeHtml(u.username)}')" class="px-3 py-1.5 rounded-lg bg-brand-600 hover:bg-brand-700 text-white font-bold">💾 บันทึก</button>
          <button onclick="resetAdminUserPassword('${escapeHtml(u.username)}')" class="px-3 py-1.5 rounded-lg bg-amber-50 hover:bg-amber-100 text-amber-800 font-bold">🔑 รีเซ็ตรหัส</button>
          ${u.username !== 'admin' ? `<button onclick="deleteAdminUser('${escapeHtml(u.username)}')" class="px-3 py-1.5 rounded-lg bg-rose-50 hover:bg-rose-100 text-rose-600 font-bold">🗑️ ลบ</button>` : ''}
        </td>
      </tr>
    `).join('');
  } catch (err) {
    showToast(err.message, 'error');
  }
}

async function saveAdminUser(username) {
  const display_name = document.getElementById(`adm_name_${username}`).value.trim();
  const role = document.getElementById(`adm_role_${username}`).value;
  try {
    const res = await api(`/api/admin/users/${encodeURIComponent(username)}`, {
      method: 'PUT',
      body: JSON.stringify({ display_name, role }),
    });
    showToast(res.message, 'success');
    await loadAllData();
    await loadAdminUsers();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

async function resetAdminUserPassword(username) {
  const new_password = prompt(`กำหนดรหัสผ่านใหม่สำหรับผู้ใช้ "${username}" (อย่างน้อย 4 ตัวอักษร):`);
  if (!new_password) return;
  try {
    const res = await api(`/api/admin/users/${encodeURIComponent(username)}`, {
      method: 'PUT',
      body: JSON.stringify({ new_password }),
    });
    showToast(res.message, 'success');
  } catch (err) {
    showToast(err.message, 'error');
  }
}

async function deleteAdminUser(username) {
  if (!confirm(`ยืนยันการลบบัญชีผู้ใช้ "${username}" ออกจากระบบ?`)) return;
  try {
    const res = await api(`/api/admin/users/${encodeURIComponent(username)}`, { method: 'DELETE' });
    showToast(res.message, 'success');
    await loadAllData();
    await loadAdminUsers();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

async function handleClearAllTasks() {
  if (!confirm('⚠️ คำเตือนสำคัญ: คุณต้องการล้างข้อมูลงานและประวัติทั้งหมดในระบบใช่หรือไม่? (ข้อมูลผู้ใช้ยังอยู่ครบ)')) return;
  try {
    const res = await api('/api/admin/tasks/clear-all', { method: 'DELETE' });
    showToast(res.message, 'warning');
    await loadAllData();
  } catch (err) {
    showToast(err.message, 'error');
  }
}

// --- Utility: Escape HTML ---
function escapeHtml(str) {
  if (str === null || str === undefined) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}
