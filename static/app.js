// Team Workflow SVV - Modern Single Page Web Application
// State Management & Real-time Operations

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

// --- Helper: Convert file to Base64 ---
function fileToBase64(file) {
  return new Promise((resolve, reject) => {
    if (!file) return resolve(null);
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = (error) => reject(error);
    reader.readAsDataURL(file);
  });
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
      
      // Determine page from URL query parameter
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

  // Handle browser back/forward buttons
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

  // Admin menu visibility
  const adminNav = document.getElementById('navAdmin');
  if (adminNav) {
    adminNav.classList.toggle('hidden', !state.user.is_admin);
    adminNav.classList.toggle('flex', state.user.is_admin);
  }

  // Commander menu visibility
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

  // Toggle active sidebar items
  document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
  const activeBtn = document.getElementById(`nav${pageId.charAt(0).toUpperCase() + pageId.slice(1)}`);
  if (activeBtn) activeBtn.classList.add('active');

  // Toggle views
  document.querySelectorAll('.view-panel').forEach(el => el.classList.add('hidden'));
  const activeView = document.getElementById(`view${pageId.charAt(0).toUpperCase() + pageId.slice(1)}`);
  if (activeView) activeView.classList.remove('hidden');

  // Update Topbar Title
  const titles = {
    commander: { icon: '🎯', title: 'โมดูลที่ 1: ระบบสั่งการและมอบหมายงาน (Commander)' },
    kanban: { icon: '📋', title: 'โมดูลที่ 2: กระดานงาน (Kanban Board)' },
    kpi: { icon: '📊', title: 'โมดูลที่ 3: แดชบอร์ดคะแนน KPI' },
    admin: { icon: '🛡️', title: 'โมดูลที่ 4: แผงควบคุมผู้ดูแลระบบ (Admin Panel)' }
  };
  const cur = titles[pageId] || titles.kanban;
  document.getElementById('pageIcon').innerText = cur.icon;
  document.getElementById('pageTitle').innerText = cur.title;

  // Render specific views
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
    state.tasks = tasks;
    state.operators = ops;

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
  const selects = ['taskAssignees', 'adjOperator', 'filterAssignee', 'histFilterEmp', 'handoverSelectUsers', 'editAssignees'];
  selects.forEach(id => {
    const el = document.getElementById(id);
    if (!el) return;
    const isFilter = id.startsWith('filter') || id.startsWith('hist');
    el.innerHTML = isFilter ? '<option value="ALL">👤 ทั้งหมด</option>' : '';
    state.operators.forEach(op => {
      const opt = document.createElement('option');
      opt.value = op.username;
      opt.innerText = op.display_name || `@${op.username}`;
      el.appendChild(opt);
    });
  });
}

// ==========================================
// MODULE 1: COMMANDER LOGIC
// ==========================================

function switchCommanderTab(tab) {
  state.commanderTab = tab;
  const tabs = ['create', 'handover', 'review', 'kpi_adj', 'manage'];
  tabs.forEach(t => {
    const btn = document.getElementById(`cmdTab${t.charAt(0).toUpperCase() + t.slice(1)}`);
    const pane = document.getElementById(`cmdPane${t.charAt(0).toUpperCase() + t.slice(1)}`);
    if (btn) {
      btn.className = t === tab ?
        'px-4 py-2 rounded-xl text-xs font-semibold bg-svv-600 text-white shadow-sm transition' :
        'px-4 py-2 rounded-xl text-xs font-semibold bg-white border border-slate-200 text-slate-700 hover:bg-slate-50 transition';
    }
    if (pane) pane.classList.toggle('hidden', t !== tab);
  });
  renderCommanderTabs();
}

function renderCommanderTabs() {
  if (state.commanderTab === 'handover') renderHandoverRequests();
  if (state.commanderTab === 'review') renderReviewTasks();
  if (state.commanderTab === 'manage') renderManageTasksTable();
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

  const selectedOps = Array.from(document.getElementById('taskAssignees').selectedOptions).map(o => o.value);
  if (!selectedOps.length) {
    showToast('กรุณาระบุผู้ปฏิบัติงานอย่างน้อย 1 คน', 'warning');
    return;
  }

  let finalAttach = attachUrlInput || null;
  if (fileInput && fileInput.files[0]) {
    finalAttach = await fileToBase64(fileInput.files[0]);
  }

  const payload = {
    title,
    description: desc,
    task_type: taskType,
    priority,
    due_date: dueDate,
    assignees: selectedOps,
    attachment_url: finalAttach
  };

  try {
    await api('/api/tasks', { method: 'POST', body: JSON.stringify(payload) });
    showToast('✅ มอบหมายงานสำเร็จแล้ว!', 'success');
    e.target.reset();
    await loadAllData();
    navigateTo('kanban');
  } catch (err) {
    showToast(`เกิดข้อผิดพลาด: ${err.message}`, 'error');
  }
}

function renderHandoverRequests() {
  const container = document.getElementById('handoverList');
  if (!container) return;
  const handovers = state.tasks.filter(t => t.handover_status === 'Pending');
  if (!handovers.length) {
    container.innerHTML = '<div class="p-6 bg-white rounded-2xl border border-slate-200 text-center text-xs text-slate-500">ไม่มีคำขอส่งต่องานค้างอยู่</div>';
    return;
  }
  container.innerHTML = handovers.map(t => `
    <div class="bg-white p-4 rounded-2xl border border-slate-200 shadow-sm space-y-2">
      <div class="flex items-center justify-between">
        <h4 class="text-xs font-bold text-slate-800">${escapeHtml(t.title)}</h4>
        <span class="badge-status badge-review text-[10px]">รออนุมัติส่งต่อ</span>
      </div>
      <p class="text-xs text-slate-600">ผู้รับผิดชอบเดิม: <code class="bg-slate-100 px-1 py-0.5 rounded">${escapeHtml(t.assignee_name || '-')}</code> ➔ เปลี่ยนเป็น: <code class="bg-sky-50 text-svv-800 px-1 py-0.5 rounded font-bold">${escapeHtml(t.handover_to || '-')}</code></p>
      <p class="text-xs text-slate-500 italic">เหตุผล: "${escapeHtml(t.handover_reason || '-')}"</p>
      <div class="flex gap-2 pt-2 border-t border-slate-100">
        <button onclick="handleHandoverAction('${t.task_id}', 'approve')" class="px-3.5 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-bold transition">✅ อนุมัติ</button>
        <button onclick="handleHandoverAction('${t.task_id}', 'reject')" class="px-3.5 py-1.5 bg-rose-600 hover:bg-rose-700 text-white rounded-xl text-xs font-bold transition">❌ ปฏิเสธ</button>
        <button onclick="openHandoverModal('${t.task_id}')" class="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl text-xs font-medium transition">✏️ ปรับเปลี่ยนเอง</button>
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
    container.innerHTML = '<div class="p-6 bg-white rounded-2xl border border-slate-200 text-center text-xs text-slate-500">ไม่มีงานที่รอตรวจรับในขณะนี้</div>';
    return;
  }
  container.innerHTML = reviews.map(t => {
    const otBadge = t.is_ontime === true ? '<span class="badge-status badge-done text-[10px]">🟢 ส่งตรงเวลา</span>' :
                    t.is_ontime === false ? '<span class="badge-status badge-overdue text-[10px]">🔴 ส่งเกินกำหนด</span>' : '';
    let subImgHtml = '';
    const note = t.submission_note || '';
    if (note.includes('[ATTACHED_IMAGE:')) {
      const parts = note.split('[ATTACHED_IMAGE:');
      const imgUrl = parts[1].split(']')[0].trim();
      subImgHtml = `<div class="mt-2"><img src="${imgUrl}" class="max-h-40 rounded-xl border border-slate-200 object-cover cursor-pointer" onclick="window.open('${imgUrl}')" alt="Work Attachment"></div>`;
    }
    return `
      <div class="bg-white p-4 rounded-2xl border border-slate-200 shadow-sm space-y-2">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2">
            <h4 class="text-xs font-bold text-slate-800">${escapeHtml(t.title)}</h4>
            ${otBadge}
          </div>
          <span class="text-[11px] text-slate-400">กำหนด: ${t.due_date || '-'}</span>
        </div>
        <p class="text-xs text-slate-600">ผู้รับผิดชอบ: <strong>${escapeHtml(t.assignee_name || '-')}</strong> | ผลงานที่ส่ง: ${escapeHtml(note.split('[ATTACHED_IMAGE:')[0].trim() || '-')}</p>
        ${subImgHtml}
        <div class="flex flex-wrap gap-2 pt-2 border-t border-slate-100">
          <button onclick="openApproveModal('${t.task_id}')" class="px-3.5 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-bold transition">🏆 ตรวจรับงานสำเร็จ (Done)</button>
          <button onclick="openReturnModal('${t.task_id}')" class="px-3.5 py-1.5 bg-rose-50 hover:bg-rose-100 text-rose-700 rounded-xl text-xs font-bold transition">↩️ ส่งกลับแก้ไข</button>
          <button onclick="openProgressModal('${t.task_id}')" class="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl text-xs font-medium transition">📝 ความคืบหน้า</button>
          <button onclick="openEditModal('${t.task_id}')" class="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl text-xs font-medium transition">✏️ แก้ไข</button>
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
  } catch (err) {
    showToast(err.message, 'error');
  }
}

function renderManageTasksTable() {
  const container = document.getElementById('manageTasksTable');
  if (!container) return;
  const search = (document.getElementById('manageSearchInput')?.value || '').toLowerCase();
  const statFilter = document.getElementById('manageStatusFilter')?.value || 'ALL';

  let list = state.tasks;
  if (statFilter !== 'ALL') {
    list = list.filter(t => t.status === statFilter);
  }
  if (search) {
    list = list.filter(t => (t.title || '').toLowerCase().includes(search) || (t.description || '').toLowerCase().includes(search));
  }

  if (!list.length) {
    container.innerHTML = '<div class="p-6 bg-white rounded-2xl border border-slate-200 text-center text-xs text-slate-500">ไม่พบรายการงานที่ค้นหา</div>';
    return;
  }

  container.innerHTML = list.map(t => `
    <div class="bg-white p-3.5 rounded-2xl border border-slate-200 shadow-sm flex flex-col md:flex-row items-start md:items-center justify-between gap-3">
      <div class="space-y-1 overflow-hidden">
        <div class="flex items-center gap-2">
          <span class="font-bold text-xs text-slate-800 truncate">${escapeHtml(t.title)}</span>
          <span class="badge-status ${getBadgeClass(t.status)} text-[10px]">${t.status}</span>
          ${t.is_overdue ? '<span class="badge-status badge-overdue text-[10px]">เกินกำหนด</span>' : ''}
        </div>
        <p class="text-[11px] text-slate-500">
          ผู้รับผิดชอบ: <strong>${escapeHtml(t.assignee_name || '-')}</strong> | ผู้สั่งการ: @${escapeHtml(t.creator_username || '-')} | กำหนด: ${t.due_date || '-'}
        </p>
      </div>
      <div class="flex items-center gap-2 shrink-0">
        <button onclick="openEditModal('${t.task_id}')" class="px-2.5 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl text-xs font-medium transition">✏️ แก้ไข</button>
        <button onclick="openProgressModal('${t.task_id}')" class="px-2.5 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl text-xs font-medium transition">📝 คืบหน้า</button>
        <button onclick="handleDeleteTask('${t.task_id}', '${escapeHtml(t.title)}')" class="px-2.5 py-1.5 bg-rose-50 hover:bg-rose-100 text-rose-600 rounded-xl text-xs font-bold transition">🗑️ ลบ</button>
      </div>
    </div>
  `).join('');
}

// ==========================================
// MODULE 2: KANBAN BOARD & DRAG-AND-DROP
// ==========================================

function switchKanbanView(view) {
  state.kanbanView = view;
  const boardEl = document.getElementById('kanbanBoardWrapper');
  const listEl = document.getElementById('compactListView');
  const btnB = document.getElementById('viewBtnBoard');
  const btnL = document.getElementById('viewBtnList');

  if (view === 'board') {
    boardEl.classList.remove('hidden');
    listEl.classList.add('hidden');
    btnB.className = 'px-3 py-1 rounded-lg bg-white shadow-sm text-svv-700';
    btnL.className = 'px-3 py-1 rounded-lg text-slate-500 hover:text-slate-700';
    renderKanbanBoard();
  } else {
    boardEl.classList.add('hidden');
    listEl.classList.remove('hidden');
    btnL.className = 'px-3 py-1 rounded-lg bg-white shadow-sm text-svv-700';
    btnB.className = 'px-3 py-1 rounded-lg text-slate-500 hover:text-slate-700';
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

  return state.tasks.filter(t => {
    if (fAssignee !== 'ALL' && !(t.assignee_name || '').includes(fAssignee)) return false;
    if (fStatus !== 'ALL' && t.status !== fStatus) return false;
    if (fType !== 'ALL' && t.task_type !== fType) return false;
    return true;
  });
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
      listEl.innerHTML = colTasks.map(t => renderKanbanCard(t)).join('');
    }
  });
}

function renderKanbanCard(t) {
  const isOverdue = t.is_overdue;
  const isComm = state.user?.is_commander || state.user?.is_admin;
  return `
    <div id="card_${t.task_id}" draggable="true" ondragstart="handleDragStart(event, '${t.task_id}')" ondragend="handleDragEnd(event)" class="kanban-card bg-white p-3 rounded-xl border border-slate-200/90 shadow-sm hover:shadow-md space-y-2">
      <div class="flex items-start justify-between gap-1.5">
        <h4 class="text-xs font-bold text-slate-800 leading-snug break-words">${escapeHtml(t.title)}</h4>
        ${isOverdue ? '<span class="badge-status badge-overdue text-[9px] shrink-0">เกินส่ง</span>' : ''}
      </div>

      <p class="text-[11px] text-slate-600 line-clamp-2">${escapeHtml(t.description || '')}</p>

      <div class="flex flex-wrap items-center gap-1.5 text-[10px] text-slate-500">
        <span class="bg-slate-100 px-1.5 py-0.5 rounded font-medium">👤 ${escapeHtml(t.assignee_name || '-')}</span>
        <span class="bg-slate-100 px-1.5 py-0.5 rounded font-medium">📅 ${t.due_date || '-'}</span>
      </div>

      <div class="flex items-center justify-between pt-2 border-t border-slate-100 text-[11px]">
        <div class="flex gap-1">
          <button onclick="openProgressModal('${t.task_id}')" title="ความคืบหน้า" class="p-1 hover:bg-slate-100 rounded text-slate-600 font-medium">📝</button>
          <button onclick="openHandoverModal('${t.task_id}')" title="ส่งต่องาน" class="p-1 hover:bg-slate-100 rounded text-slate-600 font-medium">🤝</button>
          ${isComm ? `<button onclick="openEditModal('${t.task_id}')" title="แก้ไข" class="p-1 hover:bg-slate-100 rounded text-slate-600 font-medium">✏️</button>` : ''}
          ${isComm ? `<button onclick="handleDeleteTask('${t.task_id}', '${escapeHtml(t.title)}')" title="ลบ" class="p-1 hover:bg-rose-50 text-rose-500 rounded font-medium">🗑️</button>` : ''}
        </div>
        ${t.status === 'In Progress' ? `<button onclick="openSubmitModal('${t.task_id}')" class="px-2 py-0.5 bg-svv-50 hover:bg-svv-100 text-svv-700 font-bold rounded-lg text-[10px] transition">ส่งงาน ➔</button>` : ''}
        ${t.status === 'In Review' && isComm ? `<button onclick="openApproveModal('${t.task_id}')" class="px-2 py-0.5 bg-emerald-50 hover:bg-emerald-100 text-emerald-700 font-bold rounded-lg text-[10px] transition">ตรวจรับ ⭐</button>` : ''}
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
  container.innerHTML = tasks.map(t => `
    <div class="bg-white p-3 rounded-2xl border border-slate-200 shadow-sm flex flex-col md:flex-row items-start md:items-center justify-between gap-3">
      <div class="space-y-0.5">
        <div class="flex items-center gap-2">
          <span class="font-bold text-xs text-slate-800">${escapeHtml(t.title)}</span>
          <span class="badge-status ${getBadgeClass(t.status)} text-[10px]">${t.status}</span>
          ${t.is_overdue ? '<span class="badge-status badge-overdue text-[9px]">เกินกำหนด</span>' : ''}
        </div>
        <p class="text-[11px] text-slate-500">
          ผู้รับผิดชอบ: <strong>${escapeHtml(t.assignee_name || '-')}</strong> | กำหนด: ${t.due_date || '-'} | ประเภท: ${t.task_type || 'Project'}
        </p>
      </div>
      <div class="flex items-center gap-2">
        <button onclick="openProgressModal('${t.task_id}')" class="px-2.5 py-1 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl text-xs font-medium transition">📝 ความคืบหน้า</button>
        <button onclick="openHandoverModal('${t.task_id}')" class="px-2.5 py-1 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl text-xs font-medium transition">🤝 ส่งต่อ</button>
      </div>
    </div>
  `).join('');
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

async function handleDrop(e, targetStatus) {
  e.preventDefault();
  e.currentTarget.classList.remove('drag-over');
  const taskId = state.draggedTaskId || e.dataTransfer.getData('text/plain');
  if (!taskId) return;

  const task = state.tasks.find(t => t.task_id === taskId);
  if (!task || task.status === targetStatus) return;

  // Intercept special transitions
  if (targetStatus === 'In Review') {
    openSubmitModal(taskId);
    return;
  }
  if (targetStatus === 'Done') {
    if (state.user?.is_commander || state.user?.is_admin) {
      openApproveModal(taskId);
    } else {
      showToast('⚠️ เฉพาะผู้มียศระดับสั่งการเท่านั้นที่สามารถตรวจรับงานไป Done ได้', 'warning');
    }
    return;
  }
  if ((targetStatus === 'In Progress' || targetStatus === 'Revision') && task.status === 'In Review') {
    if (state.user?.is_commander || state.user?.is_admin) {
      openReturnModal(taskId);
    } else {
      showToast('⚠️ เฉพาะผู้สั่งการเท่านั้นที่สามารถประเมินผลและย้ายสถานะนี้ได้', 'warning');
    }
    return;
  }

  // Normal Move
  try {
    await api(`/api/tasks/${taskId}/move`, {
      method: 'POST',
      body: JSON.stringify({ target_status: targetStatus })
    });
    task.status = targetStatus;
    renderKanbanBoard();
    updatePendingBadgeCounts();
    showToast(`ย้ายงานไปยัง ${targetStatus} เรียบร้อย`, 'success');
  } catch (err) {
    showToast(err.message, 'error');
    renderKanbanBoard();
  }
}

// ==========================================
// MODULE 3: KPI DASHBOARD & CHARTS
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

    // Overview Cards
    document.getElementById('kpiCardTotal').innerText = res.overview.total_tasks;
    document.getElementById('kpiCardProg').innerText = res.overview.in_progress;
    document.getElementById('kpiCardRev').innerText = res.overview.in_review;
    document.getElementById('kpiCardDone').innerText = res.overview.done;

    // Render Table
    const tbody = document.getElementById('kpiTableBody');
    tbody.innerHTML = res.leaderboard.map((item, idx) => `
      <tr class="hover:bg-slate-50 transition">
        <td class="py-3 px-4 font-bold text-slate-800 flex items-center gap-2">
          <span class="text-xs px-2 py-0.5 rounded-full ${idx === 0 ? 'bg-amber-100 text-amber-700 font-extrabold' : 'bg-slate-100 text-slate-600'}">#${idx + 1}</span>
          ${escapeHtml(item.fullname || item.username)}
          <span class="text-[10px] text-slate-400 font-normal">(@${escapeHtml(item.username)})</span>
        </td>
        <td class="py-3 px-3 text-center">${item.total_tasks}</td>
        <td class="py-3 px-3 text-center font-bold text-slate-800">${item.done_tasks}</td>
        <td class="py-3 px-3 text-center font-bold text-emerald-600">${item.ontime_count}</td>
        <td class="py-3 px-3 text-center font-bold text-rose-600">${item.late_count}</td>
        <td class="py-3 px-3 text-center text-amber-600 font-bold">⭐ ${item.avg_rating}</td>
        <td class="py-3 px-3 text-center ${item.manual_points >= 0 ? 'text-emerald-600' : 'text-rose-600'}">${item.manual_points > 0 ? '+' : ''}${item.manual_points}</td>
        <td class="py-3 px-4 text-right font-extrabold text-sm text-svv-700">${item.total_kpi}</td>
      </tr>
    `).join('');

    renderKpiCharts(res.leaderboard);
  } catch (err) {
    console.error('Failed to load KPI:', err);
  }
}

function renderKpiCharts(data) {
  const labels = data.map(d => d.fullname || d.username);
  const totalScores = data.map(d => d.total_kpi);
  const ontimes = data.map(d => d.ontime_count);
  const lates = data.map(d => d.late_count);

  // Chart 1: Total KPI
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

  // Chart 2: Ontime vs Late
  const ctx2 = document.getElementById('chartOntimeLate')?.getContext('2d');
  if (ctx2) {
    if (state.chartOntime) state.chartOntime.destroy();
    state.chartOntime = new Chart(ctx2, {
      type: 'bar',
      data: {
        labels,
        datasets: [
          { label: 'ส่งทันเวลา', data: ontimes, backgroundColor: '#0284c7', borderRadius: 6 },
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

function renderHistoryReport() {
  const container = document.getElementById('historyReportList');
  if (!container) return;

  const fEmp = document.getElementById('histFilterEmp')?.value || 'ALL';
  const fMonth = document.getElementById('histFilterMonth')?.value || 'ALL';

  const doneTasks = state.tasks.filter(t => t.status === 'Done');

  // Populate Month options if empty
  const monthSelect = document.getElementById('histFilterMonth');
  if (monthSelect && monthSelect.options.length <= 1) {
    const months = new Set();
    doneTasks.forEach(t => {
      const dt = t.completed_at || t.due_date;
      if (dt) months.add(dt.substring(0, 7)); // 'YYYY-MM'
    });
    months.forEach(m => {
      const opt = document.createElement('option');
      opt.value = m;
      opt.innerText = m;
      monthSelect.appendChild(opt);
    });
  }

  let filtered = doneTasks;
  if (fEmp !== 'ALL') {
    filtered = filtered.filter(t => (t.assignee_name || '').includes(fEmp));
  }
  if (fMonth !== 'ALL') {
    filtered = filtered.filter(t => (t.completed_at || t.due_date || '').startsWith(fMonth));
  }

  if (!filtered.length) {
    container.innerHTML = '<div class="p-6 bg-white rounded-2xl border border-slate-200 text-center text-xs text-slate-500">ไม่มีประวัติผลงานตามเงื่อนไขที่เลือก</div>';
    return;
  }

  container.innerHTML = filtered.map(t => `
    <div class="bg-white p-4 rounded-2xl border border-slate-200 shadow-sm space-y-1">
      <div class="flex items-center justify-between">
        <h4 class="text-xs font-bold text-slate-800">${escapeHtml(t.title)}</h4>
        <span class="badge-status badge-done text-[10px]">⭐ ${t.satisfaction_rating || 5} ดาว</span>
      </div>
      <p class="text-xs text-slate-600">ผู้ปฏิบัติงาน: <strong>${escapeHtml(t.assignee_name || '-')}</strong> | สำเร็จเมื่อ: ${formatDate(t.completed_at || t.due_date)}</p>
      ${t.submission_note ? `<p class="text-xs text-slate-500 italic bg-slate-50 p-2 rounded-xl mt-1">"${escapeHtml(t.submission_note)}"</p>` : ''}
    </div>
  `).join('');
}

// ==========================================
// MODULE 4: ADMIN PANEL
// ==========================================

async function renderAdminPanel() {
  if (!state.user?.is_admin) return;
  try {
    const users = await api('/api/admin/users');
    state.allUsers = users;

    // 1. Pending Users
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

    // 2. All Users Management
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
  const task = state.tasks.find(t => t.task_id === taskId);
  if (!task) return;

  const infoEl = document.getElementById('modalProgTaskInfo');
  infoEl.innerHTML = `
    <p class="font-bold text-slate-800">${escapeHtml(task.title)}</p>
    <p class="text-slate-500 mt-1">ผู้รับผิดชอบ: <strong>${escapeHtml(task.assignee_name || '-')}</strong> | สถานะ: <span class="badge-status ${getBadgeClass(task.status)} text-[10px]">${task.status}</span></p>
  `;

  document.getElementById('modalProgNoteInput').value = '';
  await loadTaskLogs(taskId);
  openModal('modalProgress');
}

async function loadTaskLogs(taskId) {
  const container = document.getElementById('modalProgLogsList');
  try {
    const logs = await api(`/api/tasks/${taskId}/logs`);
    if (!logs.length) {
      container.innerHTML = '<p class="text-slate-400 italic">ยังไม่มีประวัติการดำเนินงาน</p>';
      return;
    }
    container.innerHTML = logs.map(l => `
      <div class="p-2.5 bg-slate-50 rounded-xl border border-slate-200">
        <div class="flex items-center justify-between text-[11px] mb-1">
          <span class="font-bold text-svv-800">${escapeHtml(l.action)}</span>
          <span class="text-slate-400">${formatDate(l.created_at)}</span>
        </div>
        <p class="text-slate-700">${escapeHtml(l.details || '-')}</p>
        <span class="text-[10px] text-slate-400">โดย: @${escapeHtml(l.performed_by || '-')}</span>
      </div>
    `).join('');
  } catch (err) {
    container.innerHTML = '<p class="text-rose-500">เกิดข้อผิดพลาดในการโหลดประวัติ</p>';
  }
}

async function handleAddProgressLog() {
  const note = document.getElementById('modalProgNoteInput').value.trim();
  if (!note || !state.activeTaskId) return;

  try {
    await api(`/api/tasks/${state.activeTaskId}/logs`, {
      method: 'POST',
      body: JSON.stringify({ note })
    });
    document.getElementById('modalProgNoteInput').value = '';
    await loadTaskLogs(state.activeTaskId);
    showToast('บันทึกความคืบหน้าสำเร็จ', 'success');
  } catch (err) {
    showToast(err.message, 'error');
  }
}

// 2. Submit Work Modal
function openSubmitModal(taskId) {
  state.activeTaskId = taskId;
  const task = state.tasks.find(t => t.task_id === taskId);
  if (!task) return;
  document.getElementById('submitTaskTitle').innerText = `งาน: ${task.title}`;
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

  let attach = link || null;
  if (fileInput && fileInput.files[0]) {
    attach = await fileToBase64(fileInput.files[0]);
  }

  try {
    const res = await api(`/api/tasks/${state.activeTaskId}/submit`, {
      method: 'POST',
      body: JSON.stringify({ submission_note: note, attachment_url: attach })
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
  const task = state.tasks.find(t => t.task_id === taskId);
  if (!task) return;
  const otBadge = task.is_ontime === true ? '🟢 ส่งตรงเวลา (+10 แต้ม)' : '🔴 ส่งเกินกำหนด (-5 แต้ม)';
  document.getElementById('approveTaskDetails').innerHTML = `
    <p class="font-bold text-slate-800">${escapeHtml(task.title)}</p>
    <p class="text-slate-500">ผู้รับผิดชอบ: <strong>${escapeHtml(task.assignee_name || '-')}</strong></p>
    <p class="text-slate-600 font-medium">${otBadge}</p>
  `;
  document.getElementById('approveRating').value = 5;
  document.getElementById('ratingValLabel').innerText = '5 ดาว (20 แต้ม KPI)';
  document.getElementById('approveFeedback').value = '';
  openModal('modalApprove');
}

async function handleConfirmApprove(e) {
  e.preventDefault();
  if (!state.activeTaskId) return;
  const rating = parseInt(document.getElementById('approveRating').value);
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
function openReturnModal(taskId) {
  state.activeTaskId = taskId;
  const task = state.tasks.find(t => t.task_id === taskId);
  if (!task) return;
  document.getElementById('returnTaskTitle').innerText = `งาน: ${task.title}`;
  document.getElementById('returnFeedback').value = '';
  document.getElementById('returnNewDue').value = task.due_date || '';
  openModal('modalReturn');
}

async function handleConfirmReturn(e) {
  e.preventDefault();
  if (!state.activeTaskId) return;
  const targetStatus = document.getElementById('returnStatus').value;
  const newDue = document.getElementById('returnNewDue').value || null;
  const feedback = document.getElementById('returnFeedback').value.trim();

  try {
    const res = await api(`/api/tasks/${state.activeTaskId}/return`, {
      method: 'POST',
      body: JSON.stringify({ target_status: targetStatus, new_due_date: newDue, feedback })
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
  const task = state.tasks.find(t => t.task_id === taskId);
  if (!task) return;

  const infoEl = document.getElementById('handoverTaskInfo');
  infoEl.innerHTML = `
    <p class="font-bold text-slate-800">${escapeHtml(task.title)}</p>
    <p class="text-slate-500 mt-1">ผู้รับผิดชอบปัจจุบัน: <strong>${escapeHtml(task.assignee_name || '-')}</strong></p>
  `;

  const isComm = state.user?.is_commander || state.user?.is_admin;
  document.getElementById('handoverSubmitBtn').innerText = isComm ? '💾 บันทึกเปลี่ยนตัวทันที' : '📤 ส่งคำขอส่งต่องาน';
  document.getElementById('handoverReason').value = '';
  openModal('modalHandover');
}

async function handleConfirmHandover(e) {
  e.preventDefault();
  if (!state.activeTaskId) return;
  const selectedOps = Array.from(document.getElementById('handoverSelectUsers').selectedOptions).map(o => o.value);
  const reason = document.getElementById('handoverReason').value.trim();
  if (!selectedOps.length) {
    showToast('กรุณาเลือกผู้รับผิดชอบอย่างน้อย 1 คน', 'warning');
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
  const task = state.tasks.find(t => t.task_id === taskId);
  if (!task) return;

  document.getElementById('editTaskId').value = taskId;
  document.getElementById('editTitle').value = task.title || '';
  document.getElementById('editDueDate').value = task.due_date || '';
  document.getElementById('editPriority').value = task.priority || 'Normal';
  document.getElementById('editDesc').value = task.description || '';

  // Select current assignees
  const select = document.getElementById('editAssignees');
  const currAssignees = (task.assignee_name || '').split(',').map(s => s.trim());
  Array.from(select.options).forEach(opt => {
    opt.selected = currAssignees.includes(opt.value);
  });

  openModal('modalEdit');
}

async function handleConfirmEditTask(e) {
  e.preventDefault();
  const taskId = document.getElementById('editTaskId').value;
  const title = document.getElementById('editTitle').value.trim();
  const dueDate = document.getElementById('editDueDate').value;
  const priority = document.getElementById('editPriority').value;
  const desc = document.getElementById('editDesc').value.trim();
  const selectedOps = Array.from(document.getElementById('editAssignees').selectedOptions).map(o => o.value);

  const payload = {
    title,
    due_date: dueDate,
    priority,
    description: desc,
    assignees: selectedOps.length ? selectedOps : undefined
  };

  try {
    await api(`/api/tasks/${taskId}`, { method: 'PUT', body: JSON.stringify(payload) });
    closeModal('modalEdit');
    showToast('แก้ไขงานสำเร็จ', 'success');
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
