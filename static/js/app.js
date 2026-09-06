// RoomMate Application Frontend JS

let currentUser = null;
let currentRoom = null;
let roomMembers = [];
let currentMonth = new Date().toISOString().slice(0, 7); // 'YYYY-MM'

document.addEventListener("DOMContentLoaded", () => {
  // Set default month in filters & date inputs
  const todayStr = new Date().toISOString().split("T")[0];
  const expDateInput = document.getElementById("expense-date");
  if (expDateInput) expDateInput.value = todayStr;

  const filterMonthInput = document.getElementById("filter-month");
  if (filterMonthInput) filterMonthInput.value = currentMonth;

  const currentMonthPill = document.getElementById("current-month-pill");
  if (currentMonthPill) {
    const monthNames = [
      "Jan",
      "Feb",
      "Mar",
      "Apr",
      "May",
      "Jun",
      "Jul",
      "Aug",
      "Sep",
      "Oct",
      "Nov",
      "Dec",
    ];
    const d = new Date();
    currentMonthPill.textContent = `${monthNames[d.getMonth()]} ${d.getFullYear()}`;
  }

  checkAuthStatus();
});

// Toast notification helper
function showToast(message, type = "info") {
  const container = document.getElementById("toast-container");
  if (!container) return;

  const toast = document.createElement("div");
  toast.className = `p-4 rounded-2xl shadow-2xl backdrop-blur-xl border flex items-center space-x-3 transition-all transform translate-y-2 opacity-0 text-xs font-semibold pointer-events-auto ${
    type === "error"
      ? "bg-rose-950/90 border-rose-500/40 text-rose-200"
      : type === "success"
        ? "bg-emerald-950/90 border-emerald-500/40 text-emerald-200"
        : "bg-indigo-950/90 border-indigo-500/40 text-indigo-200"
  }`;

  const icon =
    type === "error"
      ? "fa-circle-exclamation text-rose-400"
      : type === "success"
        ? "fa-circle-check text-emerald-400"
        : "fa-circle-info text-indigo-400";

  toast.innerHTML = `
        <i class="fa-solid ${icon} text-lg"></i>
        <div class="flex-1">${message}</div>
    `;

  container.appendChild(toast);
  setTimeout(() => {
    toast.classList.remove("translate-y-2", "opacity-0");
  }, 50);

  setTimeout(() => {
    toast.classList.add("opacity-0", "translate-y-2");
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

// Switch UI View (auth, onboarding, dashboard)
function showView(viewName) {
  document.getElementById("view-auth").classList.add("hidden");
  document.getElementById("view-onboarding").classList.add("hidden");
  document.getElementById("view-dashboard").classList.add("hidden");

  if (viewName === "auth") {
    document.getElementById("view-auth").classList.remove("hidden");
    document.getElementById("nav-user-controls").classList.add("hidden");
  } else if (viewName === "onboarding") {
    document.getElementById("view-onboarding").classList.remove("hidden");
    document.getElementById("nav-user-controls").classList.remove("hidden");
    document.getElementById("nav-room-badge").classList.add("hidden");
    fetchNewRandomRoomCode();
  } else if (viewName === "dashboard") {
    document.getElementById("view-dashboard").classList.remove("hidden");
    document.getElementById("nav-user-controls").classList.remove("hidden");
    document.getElementById("nav-room-badge").classList.remove("hidden");
  }
}

// Auth Tab toggle (login / register)
function toggleAuthTab(tab) {
  const loginBtn = document.getElementById("auth-tab-login");
  const regBtn = document.getElementById("auth-tab-register");
  const loginForm = document.getElementById("form-login");
  const regForm = document.getElementById("form-register");

  if (tab === "login") {
    loginBtn.className =
      "flex-1 py-2.5 rounded-xl text-xs sm:text-sm font-bold transition-all bg-indigo-600 text-white shadow-lg shadow-indigo-600/30 flex items-center justify-center space-x-2";
    regBtn.className =
      "flex-1 py-2.5 rounded-xl text-xs sm:text-sm font-bold text-slate-400 hover:text-slate-200 transition-all flex items-center justify-center space-x-2";
    loginForm.classList.remove("hidden");
    regForm.classList.add("hidden");
  } else {
    regBtn.className =
      "flex-1 py-2.5 rounded-xl text-xs sm:text-sm font-bold transition-all bg-emerald-600 text-white shadow-lg shadow-emerald-600/30 flex items-center justify-center space-x-2";
    loginBtn.className =
      "flex-1 py-2.5 rounded-xl text-xs sm:text-sm font-bold text-slate-400 hover:text-slate-200 transition-all flex items-center justify-center space-x-2";
    regForm.classList.remove("hidden");
    loginForm.classList.add("hidden");
  }
}

// Check session on load
async function checkAuthStatus() {
  try {
    const res = await fetch("/api/me");
    const data = await res.json();

    if (data.authenticated && data.user) {
      currentUser = data.user;
      updateUserNav();
      await loadRoomInfo();
    } else {
      showView("auth");
    }
  } catch (err) {
    console.error("Auth check failed:", err);
    showView("auth");
  }
}

function updateUserNav() {
  if (!currentUser) return;
  document.getElementById("nav-username").textContent = currentUser.username;
  document.getElementById("user-avatar-initials").textContent =
    currentUser.username.charAt(0).toUpperCase();
}

// AUTH HANDLERS
async function handleLogin(e) {
  e.preventDefault();
  const email = document.getElementById("login-email").value;
  const password = document.getElementById("login-password").value;

  try {
    const res = await fetch("/api/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    const data = await res.json();

    if (res.ok) {
      currentUser = data.user;
      updateUserNav();
      showToast(data.message || "Login successful!", "success");
      await loadRoomInfo();
    } else {
      showToast(data.error || "Login failed", "error");
    }
  } catch (err) {
    showToast("Network error, please try again.", "error");
  }
}

function togglePasswordVisibility(inputId, iconId) {
    const input = document.getElementById(inputId);
    const icon = document.getElementById(iconId);
    if (!input || !icon) return;

    if (input.type === 'password') {
        input.type = 'text';
        icon.classList.remove('fa-eye');
        icon.classList.add('fa-eye-slash', 'text-indigo-400');
    } else {
        input.type = 'password';
        icon.classList.remove('fa-eye-slash', 'text-indigo-400');
        icon.classList.add('fa-eye');
    }
}

function openForgotPasswordModal() {
    const modal = document.getElementById('modal-forgot-password');
    if (modal) modal.classList.remove('hidden');
}

function closeForgotPasswordModal() {
    const modal = document.getElementById('modal-forgot-password');
    if (modal) modal.classList.add('hidden');
}

async function handleResetPassword(e) {
    e.preventDefault();
    const email = document.getElementById('reset-email').value.trim();
    const new_password = document.getElementById('reset-new-password').value;

    try {
        const res = await fetch('/api/reset-password', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, new_password })
        });
        const data = await res.json();

        if (res.ok) {
            showToast(data.message, 'success');
            closeForgotPasswordModal();
            document.getElementById('login-email').value = email;
            document.getElementById('login-password').value = '';
        } else {
            showToast(data.error || 'Password reset failed', 'error');
        }
    } catch (err) {
        showToast('Server error, please try again.', 'error');
    }
}

async function handleRegister(e) {
  e.preventDefault();
  const username = document.getElementById("reg-username").value;
  const email = document.getElementById("reg-email").value;
  const password = document.getElementById("reg-password").value;

  try {
    const res = await fetch("/api/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, email, password }),
    });
    const data = await res.json();

    if (res.ok) {
      currentUser = data.user;
      updateUserNav();
      showToast(data.message || "Registration successful!", "success");
      await loadRoomInfo();
    } else {
      showToast(data.error || "Registration failed", "error");
    }
  } catch (err) {
    showToast("Network error, please try again.", "error");
  }
}

async function logoutUser() {
  try {
    await fetch("/api/logout", { method: "POST" });
    currentUser = null;
    currentRoom = null;
    showToast("Logged out successfully", "info");
    showView("auth");
  } catch (err) {
    console.error(err);
  }
}

// ROOM HANDLERS
async function loadRoomInfo() {
    try {
        const res = await fetch('/api/room/info');
        const data = await res.json();

        if (data.has_room && data.room) {
            currentRoom = data.room;
            roomMembers = data.members || [];

            // Update UI
            document.getElementById('nav-room-code').textContent = currentRoom.room_code;
            document.getElementById('dashboard-room-code-display').textContent = currentRoom.room_code;
            document.getElementById('dashboard-room-name').textContent = currentRoom.room_name;
            toggleHostControls();

            // Update Bills Form Inputs
            document.getElementById('bills-rent').value = currentRoom.rent || 0;
            document.getElementById('bills-gas').value = currentRoom.gas || 0;
            document.getElementById('bills-electricity').value = currentRoom.electricity || 0;
            document.getElementById('bills-water').value = currentRoom.water || 0;

            showView('dashboard');
            await refreshDashboardData();
        } else {
            currentRoom = null;
            roomMembers = [];
            toggleHostControls();
            showView('onboarding');
        }
    } catch (err) {
        console.error("Load room info failed:", err);
        showView('onboarding');
    }
}

async function fetchNewRandomRoomCode() {
    try {
        const res = await fetch('/api/room/generate-code');
        const data = await res.json();
        if (data.room_code) {
            const input = document.getElementById('create-room-code');
            if (input) input.value = data.room_code;
        }
    } catch (err) {
        console.error("Failed to generate random room code:", err);
    }
}

async function handleCreateRoom(e) {
    e.preventDefault();
    const room_name = document.getElementById('create-room-name').value.trim();
    const room_code = document.getElementById('create-room-code').value.trim();

    try {
        const res = await fetch('/api/room/create', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ room_name, room_code })
        });
        const data = await res.json();

        if (res.ok) {
            showToast(data.message, 'success');
            await loadRoomInfo();
        } else {
            showToast(data.error || 'Room creation failed', 'error');
        }
    } catch (err) {
        showToast('Server error', 'error');
    }
}

async function handleJoinRoom(e) {
    e.preventDefault();
    const room_code = document.getElementById('join-room-code').value.trim().toUpperCase();

    try {
        const res = await fetch('/api/room/join', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ room_code })
        });
        const data = await res.json();

        if (res.ok) {
            showToast(data.message, 'success');
            await loadRoomInfo();
        } else {
            showToast(data.error || 'Failed to join room', 'error');
        }
    } catch (err) {
        showToast('Server error', 'error');
    }
}

function copyRoomCode() {
    if (!currentRoom) return;
    navigator.clipboard.writeText(currentRoom.room_code).then(() => {
        showToast(`Room Code '${currentRoom.room_code}' copied to clipboard!`, 'success');
    }).catch(() => {
        showToast(`Room Code: ${currentRoom.room_code}`, 'info');
    });
}

function toggleHostControls() {
    const deleteBtn = document.getElementById('delete-room-btn');
    if (!deleteBtn || !currentUser || !currentRoom) {
        if (deleteBtn) deleteBtn.classList.add('hidden');
        return;
    }

    const isHost = Number(currentUser.id) === Number(currentRoom.created_by);
    deleteBtn.classList.toggle('hidden', !isHost);
}

async function handleDeleteRoom() {
    if (!currentRoom) return;

    const confirmed = confirm(`Are you sure you want to delete room "${currentRoom.room_name}"? This action will remove the room for all members.`);
    if (!confirmed) return;

    try {
        const res = await fetch('/api/room/delete', { method: 'DELETE' });
        const data = await res.json();

        if (res.ok) {
            showToast(data.message, 'success');
            currentRoom = null;
            roomMembers = [];
            await loadRoomInfo();
        } else {
            showToast(data.error || 'You are not allowed to delete this room.', 'error');
        }
    } catch (err) {
        showToast('Server error', 'error');
    }
}

async function handleRemoveMember(memberId, memberName) {
    if (!memberId || !currentRoom) return;

    const confirmed = confirm(`Remove ${memberName} from room "${currentRoom.room_name}"?`);
    if (!confirmed) return;

    try {
        const res = await fetch('/api/room/member/remove', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ member_id: memberId })
        });
        const data = await res.json();

        if (res.ok) {
            showToast(data.message, 'success');
            await loadRoomInfo();
        } else {
            showToast(data.error || 'Unable to remove member.', 'error');
        }
    } catch (err) {
        showToast('Server error', 'error');
    }
}

async function handleUpdateBills(e) {
    e.preventDefault();
    const rent = parseFloat(document.getElementById('bills-rent').value || 0);
    const gas = parseFloat(document.getElementById('bills-gas').value || 0);
    const electricity = parseFloat(document.getElementById('bills-electricity').value || 0);
    const water = parseFloat(document.getElementById('bills-water').value || 0);

    try {
        const res = await fetch('/api/room/update-bills', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ rent, gas, electricity, water })
        });
        const data = await res.json();

        if (res.ok) {
            showToast(data.message, 'success');
            await loadRoomInfo();
        } else {
            showToast(data.error, 'error');
        }
    } catch (err) {
        showToast('Server error', 'error');
    }
}

// DASHBOARD REFRESH & TABS
async function refreshDashboardData() {
    const selectedMonth = document.getElementById('filter-month').value || currentMonth;
    await Promise.all([
        loadExpenses(selectedMonth),
        loadSettlement(selectedMonth),
        loadMessages(),
        renderMembersList()
    ]);
}

function switchTab(tabName) {
    // Hide all panes
    document.querySelectorAll('.tab-pane').forEach(el => el.classList.add('hidden'));
    document.querySelectorAll('.tab-btn').forEach(el => {
        el.classList.remove('bg-indigo-600', 'text-white', 'shadow-md');
        el.classList.add('text-slate-400', 'hover:text-slate-200');
    });

    const activeBtn = document.getElementById(`tab-btn-${tabName}`);
    const activePane = document.getElementById(`tab-content-${tabName}`);

    if (activeBtn) {
        activeBtn.classList.add('bg-indigo-600', 'text-white', 'shadow-md');
        activeBtn.classList.remove('text-slate-400');
    }
    if (activePane) {
        activePane.classList.remove('hidden');
    }
}

// EXPENSES HANDLERS
async function handleAddExpense(e) {
    e.preventDefault();
    const item_name = document.getElementById('expense-item-name').value;
    const amount = parseFloat(document.getElementById('expense-amount').value || 0);
    const category = document.getElementById('expense-category').value;
    const expense_date = document.getElementById('expense-date').value;

    try {
        const res = await fetch('/api/expenses', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ item_name, amount, category, expense_date })
        });
        const data = await res.json();

        if (res.ok) {
            showToast(data.message, 'success');
            document.getElementById('expense-item-name').value = '';
            document.getElementById('expense-amount').value = '';
            const m = expense_date.slice(0, 7);
            await refreshDashboardData();
        } else {
            showToast(data.error, 'error');
        }
    } catch (err) {
        showToast('Server error', 'error');
    }
}

async function loadExpenses(month = null) {
    const selectedMonth = month || document.getElementById('filter-month').value || currentMonth;
    try {
        const res = await fetch(`/api/expenses?month=${selectedMonth}`);
        const data = await res.json();

        const tbody = document.getElementById('expense-table-body');
        const badge = document.getElementById('expense-count-badge');

        if (!data.expenses || data.expenses.length === 0) {
            tbody.innerHTML = `<tr><td colspan="5" class="text-center py-8 text-slate-500">No expenses added for this month (${selectedMonth}).</td></tr>`;
            if (badge) badge.textContent = '0 items';
            return;
        }

        if (badge) badge.textContent = `${data.expenses.length} items`;

        tbody.innerHTML = data.expenses.map(e => `
            <tr class="hover:bg-slate-800/40 transition-colors">
                <td class="py-3.5 px-4 font-bold text-slate-100 flex items-center space-x-2">
                    <span class="w-2 h-2 rounded-full bg-indigo-400"></span>
                    <span>${escapeHtml(e.item_name)}</span>
                    <span class="text-[10px] px-2 py-0.5 rounded-md bg-slate-800 text-slate-400 font-normal">${e.category}</span>
                </td>
                <td class="py-3.5 px-4 text-slate-300 font-semibold">${escapeHtml(e.user_name)}</td>
                <td class="py-3.5 px-4 font-extrabold text-emerald-400">₹${e.amount}</td>
                <td class="py-3.5 px-4 text-slate-400">${e.expense_date}</td>
                <td class="py-3.5 px-4 text-right">
                    ${e.user_id === currentUser.id ? `
                        <button onclick="deleteExpense(${e.id})" title="Delete" class="p-1.5 text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 rounded-lg transition-all">
                            <i class="fa-regular fa-trash-can"></i>
                        </button>
                    ` : ''}
                </td>
            </tr>
        `).join('');
    } catch (err) {
        console.error("Load expenses failed:", err);
    }
}

async function deleteExpense(id) {
    if (!confirm('Are you sure you want to delete this expense?')) return;

    try {
        const res = await fetch(`/api/expenses/${id}`, { method: 'DELETE' });
        const data = await res.json();

        if (res.ok) {
            showToast(data.message, 'success');
            await refreshDashboardData();
        } else {
            showToast(data.error, 'error');
        }
    } catch (err) {
        showToast('Server error', 'error');
    }
}

function filterExpenseList() {
    const filter = document.getElementById('search-expense-input').value.toLowerCase();
    const rows = document.querySelectorAll('#expense-table-body tr');

    rows.forEach(row => {
        const text = row.textContent.toLowerCase();
        row.style.display = text.includes(filter) ? '' : 'none';
    });
}


// SETTLEMENT HANDLERS
async function loadSettlement(month = null) {
    const selectedMonth = month || document.getElementById('filter-month').value || currentMonth;
    try {
        const res = await fetch(`/api/settlements/calculate?month=${selectedMonth}`);
        const data = await res.json();

        if (!res.ok) return;

        // Update KPI Stats
        document.getElementById('stat-total-expense').textContent = `₹${data.grand_total}`;
        document.getElementById('stat-per-head').textContent = `₹${data.per_head_share}`;
        document.getElementById('stat-fixed-bills').textContent = `₹${data.bills_breakdown.total_bills}`;
        document.getElementById('stat-members-count').textContent = `${data.num_members} Members`;

        // Render Individual Member Summary Cards
        const grid = document.getElementById('settlement-members-grid');
        grid.innerHTML = data.members_summary.map(m => {
            const isSelf = m.user_id === currentUser.id;
            const statusBg = m.net_balance > 0 ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400' :
                             m.net_balance < 0 ? 'bg-rose-500/10 border-rose-500/30 text-rose-400' :
                             'bg-slate-800 border-slate-700 text-slate-300';

            const statusText = m.net_balance > 0 ? `+ ₹${m.net_balance} (To Receive)` :
                               m.net_balance < 0 ? `- ₹${Math.abs(m.net_balance)} (To Pay)` :
                               '₹0 (Settled)';

            return `
                <div class="bg-slate-950 border border-slate-800 rounded-2xl p-4 flex flex-col justify-between relative overflow-hidden ${isSelf ? 'ring-2 ring-indigo-500/50' : ''}">
                    ${isSelf ? '<span class="absolute top-2 right-2 text-[10px] font-extrabold px-2 py-0.5 rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">YOU</span>' : ''}
                    <div>
                        <div class="flex items-center space-x-3 mb-3">
                            <div class="w-9 h-9 rounded-xl bg-gradient-to-tr from-indigo-500 to-purple-600 flex items-center justify-center font-bold text-white text-sm shadow-md">
                                ${m.username.charAt(0).toUpperCase()}
                            </div>
                            <div>
                                <h5 class="font-bold text-white text-sm">${escapeHtml(m.username)}</h5>
                                <p class="text-[11px] text-slate-400">Paid: ₹${m.paid} | Share: ₹${m.share}</p>
                            </div>
                        </div>
                    </div>

                    <div class="mt-2 pt-3 border-t border-slate-800/80 flex items-center justify-between">
                        <span class="text-xs text-slate-400 font-medium">Net Status:</span>
                        <span class="text-xs font-extrabold px-2.5 py-1 rounded-xl border ${statusBg}">
                            ${statusText}
                        </span>
                    </div>
                </div>
            `;
        }).join('');

        // Render Debt Settlement Instructions (Who pays whom)
        const txList = document.getElementById('transactions-list');
        if (!data.transactions || data.transactions.length === 0) {
            txList.innerHTML = `<p class="text-xs text-slate-400 italic">All balances are settled or no expenses recorded yet.</p>`;
        } else {
            txList.innerHTML = data.transactions.map(t => `
                <div class="bg-slate-900 border border-slate-800/90 rounded-xl p-3 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                    <div class="flex items-center space-x-2 text-xs font-medium text-slate-200">
                        <span class="font-bold text-rose-400">${escapeHtml(t.from_name)}</span>
                        <span class="text-slate-500">needs to pay</span>
                        <i class="fa-solid fa-arrow-right text-indigo-400 text-xs"></i>
                        <span class="font-bold text-emerald-400">${escapeHtml(t.to_name)}</span>
                    </div>
                    <div class="text-sm font-extrabold text-amber-300 bg-amber-400/10 px-3 py-1 rounded-lg border border-amber-400/20 w-fit">
                        Amount: ₹${t.amount}
                    </div>
                </div>
            `).join('');
        }

    } catch (err) {
        console.error("Load settlement failed:", err);
    }
}

async function finalizeMonthSettlement() {
    const selectedMonth = document.getElementById('filter-month').value || currentMonth;
    if (!confirm(`Are you sure you want to finalize the settlement for ${selectedMonth} and send notification messages to all room members?`)) {
        return;
    }

    try {
        const res = await fetch('/api/settlements/finalize', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ month: selectedMonth })
        });
        const data = await res.json();

        if (res.ok) {
            showToast(data.message, 'success');
            await refreshDashboardData();
            switchTab('messages');
        } else {
            showToast(data.error, 'error');
        }
    } catch (err) {
        showToast('Server error', 'error');
    }
}

// MESSAGES HANDLERS
async function loadMessages() {
    try {
        const res = await fetch('/api/messages');
        const data = await res.json();

        if (!res.ok) return;

        // Update Unread Badge
        const unreadBadge = document.getElementById('unread-count-badge');
        const unreadDot = document.getElementById('tab-unread-dot');

        if (data.unread_count > 0) {
            if (unreadBadge) {
                unreadBadge.textContent = data.unread_count;
                unreadBadge.classList.remove('hidden');
            }
            if (unreadDot) unreadDot.classList.remove('hidden');
        } else {
            if (unreadBadge) unreadBadge.classList.add('hidden');
            if (unreadDot) unreadDot.classList.add('hidden');
        }

        const container = document.getElementById('messages-container');
        if (!data.messages || data.messages.length === 0) {
            container.innerHTML = `<p class="text-xs text-slate-500 text-center py-6">No messages or notifications yet.</p>`;
            return;
        }

        container.innerHTML = data.messages.map(m => {
            const isBill = m.msg_type === 'month_end_bill';
            const cardBg = isBill ? 'bg-indigo-950/40 border-indigo-500/40' : 'bg-slate-950 border-slate-800';

            return `
                <div class="${cardBg} border rounded-2xl p-4 shadow-sm transition-all hover:border-slate-700">
                    <div class="flex items-center justify-between mb-2">
                        <div class="flex items-center space-x-2">
                            <span class="px-2 py-0.5 rounded-md text-[10px] font-bold ${isBill ? 'bg-indigo-500/20 text-indigo-300' : 'bg-slate-800 text-slate-400'}">
                                ${escapeHtml(m.sender_name)}
                            </span>
                            <h5 class="text-xs font-bold text-white">${escapeHtml(m.title)}</h5>
                        </div>
                        <span class="text-[10px] text-slate-500">${m.created_at}</span>
                    </div>
                    <p class="text-xs text-slate-300 whitespace-pre-line leading-relaxed font-medium">${escapeHtml(m.message)}</p>
                </div>
            `;
        }).join('');

    } catch (err) {
        console.error("Load messages failed:", err);
    }
}

async function handleSendRoomChat(e) {
    e.preventDefault();
    const input = document.getElementById('chat-input-text');
    const message = input.value.trim();

    if (!message) return;

    try {
        const res = await fetch('/api/messages', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message })
        });
        const data = await res.json();

        if (res.ok) {
            input.value = '';
            await loadMessages();
        } else {
            showToast(data.error, 'error');
        }
    } catch (err) {
        showToast('Server error', 'error');
    }
}

// MEMBERS LIST
function renderMembersList() {
    const grid = document.getElementById('members-list-grid');
    if (!grid || !roomMembers) return;

    const isHost = currentUser && currentRoom && Number(currentUser.id) === Number(currentRoom.created_by);

    grid.innerHTML = roomMembers.map(m => {
        const isCurrentUser = Number(m.id) === Number(currentUser?.id);
        const isRoomHost = Number(m.id) === Number(currentRoom?.created_by);

        return `
            <div class="bg-slate-950 border border-slate-800 rounded-2xl p-4 flex items-center justify-between gap-3 shadow-md">
                <div class="flex items-center space-x-4 min-w-0">
                    <div class="w-12 h-12 rounded-2xl bg-gradient-to-tr from-indigo-500 via-purple-500 to-pink-500 flex items-center justify-center font-extrabold text-white text-lg shadow-lg shadow-indigo-500/20 flex-shrink-0">
                        ${escapeHtml(m.username ? m.username.charAt(0).toUpperCase() : '?')}
                    </div>
                    <div class="min-w-0">
                        <h4 class="font-bold text-white text-sm flex items-center flex-wrap gap-1.5">
                            <span>${escapeHtml(m.username)}</span>
                            ${isCurrentUser ? '<span class="text-[10px] bg-indigo-500/20 text-indigo-300 px-2 py-0.5 rounded-full font-bold">You</span>' : ''}
                            ${isRoomHost ? '<span class="text-[10px] bg-emerald-500/20 text-emerald-300 px-2 py-0.5 rounded-full font-bold">Host</span>' : ''}
                        </h4>
                        <p class="text-xs text-slate-400 mt-0.5 truncate">${escapeHtml(m.email)}</p>
                        <div class="flex items-center space-x-1 text-[10px] text-emerald-400 mt-1 font-semibold">
                            <span class="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
                            <span>Connected on Room Dashboard</span>
                        </div>
                    </div>
                </div>
                ${isHost && !isCurrentUser && !isRoomHost ? `
                    <button
                        type="button"
                        onclick="handleRemoveMember(${m.id}, '${escapeHtml(m.username).replace(/'/g, "\\'")}')"
                        class="px-2.5 py-2 bg-rose-600/20 hover:bg-rose-600 text-rose-200 hover:text-white rounded-xl text-[10px] font-bold border border-rose-500/30 transition-all"
                        title="Remove member"
                    >
                        <i class="fa-solid fa-user-minus mr-1"></i>
                        Remove
                    </button>
                ` : ''}
            </div>
        `;
    }).join('');
}

// Helper XSS prevention
function escapeHtml(str) {
    if (!str) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}
