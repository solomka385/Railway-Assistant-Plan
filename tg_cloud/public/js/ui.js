import { state, saveMode } from './state.js';
import { updateLocationIndicator } from './location.js';
import { renderSources, formatStructuredMessage, scrollToBottom, addMartsDataButton } from './utils.js';

// DOM элементы
export const messagesEl = document.getElementById('messages');
export const userInputEl = document.getElementById('userInput');
export const sendBtn = document.getElementById('sendBtn');

// Глобальная функция для добавления сообщений из других модулей
export function addMessage(text, type = 'system', options = {}) {
    const messageEl = document.createElement('div');
    messageEl.className = `message ${type}`;
    messageEl.setAttribute('data-mode', state.currentMode);
    
    if (type === 'bot' && state.currentMode === 'plan') {
        messageEl.innerHTML = formatStructuredMessage(text);
    } else if (options.isHtml || type === 'system') {
        messageEl.innerHTML = text;
    } else {
        messageEl.textContent = text;
    }
    
    if (type === 'bot' || type === 'system') {
        // Создаем контейнер для кнопок
        const actionsContainer = document.createElement('div');
        actionsContainer.className = 'message-actions';
        
        // Добавляем кнопку копирования для системных сообщений
        const copyBtn = document.createElement('button');
        copyBtn.className = 'copy-btn';
        copyBtn.textContent = '📋 Копировать';
        copyBtn.onclick = () => {
            navigator.clipboard.writeText(text).then(() => {
                copyBtn.textContent = '✅ Скопировано!';
                setTimeout(() => { copyBtn.textContent = '📋 Копировать'; }, 2000);
            });
        };
        actionsContainer.appendChild(copyBtn);
        
        // Добавляем кнопку получения данных по станциям (если не запрещено)
        addMartsDataButton(actionsContainer, options.skipMartsButton);
        
        messageEl.appendChild(actionsContainer);
    }
    
    messagesEl.appendChild(messageEl);
    scrollToBottom(messagesEl);
}

// Блокировка/разблокировка кнопки отправки (поле ввода всегда доступно)
export function setInputState(locked) {
    if (sendBtn) sendBtn.disabled = locked;
    if (locked) {
        sendBtn.classList.add('disabled');
    } else {
        sendBtn.classList.remove('disabled');
    }
}
export const newChatBtn = document.getElementById('newChatBtn');
export const profileBtn = document.getElementById('profileBtn');
export const profileModal = document.getElementById('profileModal');
export const closeProfileBtn = document.getElementById('closeProfileBtn');
export const toggleSidebarBtn = document.getElementById('toggleSidebarBtn');
export const sidebar = document.getElementById('sidebar');
export const deleteConfirmModal = document.getElementById('deleteConfirmModal');
export const confirmDeleteBtn = document.getElementById('confirmDeleteBtn');
export const cancelDeleteBtn = document.getElementById('cancelDeleteBtn');
export const logoutBtn = document.getElementById('logoutBtn');
export const closeSpans = document.getElementsByClassName('close');

// Добавление переключателя режимов в DOM
export function addModeSwitch() {
    const modeSwitchHtml = `
        <div class="mode-switch">
            <label class="mode-label">
                <input type="radio" name="mode" value="plan" ${state.currentMode === 'plan' ? 'checked' : ''}>
                <span>📋 Режим плана</span>
            </label>
            <label class="mode-label">
                <input type="radio" name="mode" value="chat" ${state.currentMode === 'chat' ? 'checked' : ''}>
                <span>💬 Чат-режим</span>
            </label>
        </div>
        <div id="locationIndicator" class="location-indicator inactive">
            <span id="locationText">📍 Геолокация не установлена</span>
            <button id="setLocationBtn">Указать</button>
        </div>
    `;
    const appHeader = document.querySelector('.app-header');
    appHeader.insertAdjacentHTML('afterend', modeSwitchHtml);

    // Обработчики переключения режима
    document.querySelectorAll('input[name="mode"]').forEach(radio => {
        radio.addEventListener('change', (e) => {
            saveMode(e.target.value);
            console.log(`Режим изменен на: ${state.currentMode}`);
            updateLocationIndicator();
            // Если идет стриминг, фильтруем DOM элементы, иначе перерисовываем сообщения
            if (state.isStreaming) {
                import('./chat.js').then(module => module.filterDomMessagesByMode());
            } else {
                import('./chat.js').then(module => module.renderMessages());
            }
        });
    });

    // Кнопка указания локации
    const setLocationBtn = document.getElementById('setLocationBtn');
    if (setLocationBtn) {
        setLocationBtn.addEventListener('click', () => {
            import('./location.js').then(module => module.openLocationModal());
        });
    }
    
    updateLocationIndicator();
}

// Управление сайдбаром
export function toggleSidebar() {
    sidebar.classList.toggle('active');
    localStorage.setItem('sidebarOpen', sidebar.classList.contains('active'));
}
export function hideSidebar() {
    sidebar.classList.remove('active');
    localStorage.setItem('sidebarOpen', 'false');
}

// Модалка профиля
export function openProfile() {
    profileModal.style.display = 'block';
}
export function closeProfile() {
    profileModal.style.display = 'none';
}

// Модалка удаления чата
export function showDeleteModal(chatId) {
    state.chatToDelete = chatId;
    deleteConfirmModal.style.display = 'block';
}
export function closeDeleteModal() {
    state.chatToDelete = null;
    deleteConfirmModal.style.display = 'none';
}

// Модалка локации – импортируется из location.js

// Удаление индикатора печати
export function removeTypingIndicator() {
    if (state.typingIndicator && state.typingIndicator.parentNode) {
        state.typingIndicator.remove();
        state.typingIndicator = null;
    }
}

// Показ уведомления (всплывающее)
export function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    document.body.appendChild(notification);
    setTimeout(() => notification.remove(), 3000);
}