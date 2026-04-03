import { API_BASE_URL } from './constants.js';

export async function checkAuth() {
    try {
        const res = await fetch(`${API_BASE_URL}/me`, { credentials: 'include' });
        if (res.ok) {
            const data = await res.json();
            // Обновляем отображение имени пользователя в DOM
            const userDisplaySpan = document.getElementById('userDisplay');
            const userNameSpan = document.getElementById('userName');
            if (userDisplaySpan) userDisplaySpan.textContent = data.user;
            if (userNameSpan) userNameSpan.textContent = data.user;
            return true;
        } else {
            window.location.href = '/login.html';
            return false;
        }
    } catch (error) {
        console.error('Auth check failed:', error);
        window.location.href = '/login.html';
        return false;
    }
}

export async function logout() {
    await fetch(`${API_BASE_URL}/logout`, { method: 'POST', credentials: 'include' });
    window.location.href = '/login.html';
}