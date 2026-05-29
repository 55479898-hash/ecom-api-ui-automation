function showToast(msg) {
  const toast = document.getElementById('toast');
  toast.textContent = msg;
  toast.classList.remove('hidden');
  setTimeout(() => toast.classList.add('hidden'), 2500);
}

function updateNavAuth() {
  const token = localStorage.getItem('token');
  const username = localStorage.getItem('username');
  const loginLink = document.getElementById('login-link');
  const userInfo = document.getElementById('user-info');
  const logoutBtn = document.getElementById('logout-btn');

  if (token && username) {
    loginLink.classList.add('hidden');
    userInfo.textContent = `Hi, ${username}`;
    userInfo.classList.remove('hidden');
    logoutBtn.classList.remove('hidden');
  } else {
    loginLink.classList.remove('hidden');
    userInfo.classList.add('hidden');
    logoutBtn.classList.add('hidden');
  }
}

async function updateCartBadge() {
  const token = localStorage.getItem('token');
  const badge = document.getElementById('cart-badge');
  if (!token) { badge.textContent = '0'; return; }
  try {
    const res = await fetch('/api/cart', {
      headers: { 'Authorization': 'Bearer ' + token },
    });
    const data = await res.json();
    const count = (data.items || []).reduce((s, i) => s + i.quantity, 0);
    badge.textContent = count;
  } catch { badge.textContent = '0'; }
}

document.getElementById('logout-btn')?.addEventListener('click', () => {
  localStorage.removeItem('token');
  localStorage.removeItem('username');
  showToast('已退出登录');
  window.location.href = '/login';
});

updateNavAuth();
updateCartBadge();
