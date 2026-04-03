import { state, saveChatMessages } from './state.js';
import { checkAuth, logout } from './auth.js';
import { loadChatsFromServer, createNewChat, deleteChat, setActiveChat, sendUserMessage } from './chat.js';
import { renderMessages } from './chat.js';
import {
    messagesEl, userInputEl, sendBtn, newChatBtn, profileBtn, closeProfileBtn,
    toggleSidebarBtn, sidebar, confirmDeleteBtn, cancelDeleteBtn, logoutBtn,
    closeSpans, addModeSwitch, openProfile, closeProfile, showDeleteModal,
    closeDeleteModal, hideSidebar, removeTypingIndicator
} from './ui.js';
import { updateLocationIndicator, openLocationModal, initYandexMap, useDeviceGPS, confirmMapSelection, closeLocationModal, showLocationRequiredNotification } from './location.js';
import { getWelcomeMessage } from './utils.js';
import { fetchAndDisplayMartsData } from './marts.js';

document.addEventListener('DOMContentLoaded', async () => {
    // 1. Проверка аутентификации
    const authed = await checkAuth();
    if (!authed) return;

    // 2. Инициализация интерфейса
    addModeSwitch();        // добавляет переключатель режимов
    updateLocationIndicator();

    // 3. Загрузка чатов
    try {
        await loadChatsFromServer();
        if (state.chats.length === 0) {
            await createNewChat();
        } else {
            // Проверяем, существует ли сохраненный активный чат
            const savedActiveChatId = state.activeChatId;
            const chatExists = state.chats.find(chat => chat.id === savedActiveChatId);
            if (chatExists) {
                setActiveChat(savedActiveChatId);
            } else {
                // Если сохраненный чат не найден, выбираем первый
                setActiveChat(state.chats[0].id);
            }
        }
    } catch (error) {
        console.error('Ошибка загрузки чатов:', error);
        // fallback: создаём локальный чат
        const chatId = Date.now().toString();
        state.chats = [{ id: chatId, title: 'Чат 1', messages: [] }];
        setActiveChat(chatId);
    }

    // 4. Привязка обработчиков событий
    sendBtn.addEventListener('click', (e) => {
        // Если кнопка заблокирована (геолокация не установлена в режиме плана)
        if (sendBtn.disabled) {
            e.preventDefault();
            showLocationRequiredNotification();
            return;
        }
        sendUserMessage();
    });
    userInputEl.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !sendBtn.disabled) sendUserMessage();
    });
    newChatBtn.addEventListener('click', createNewChat);
    profileBtn.addEventListener('click', openProfile);
    closeProfileBtn.addEventListener('click', closeProfile);
    toggleSidebarBtn.addEventListener('click', () => {
        sidebar.classList.toggle('active');
        // Сохраняем состояние сайдбара
        localStorage.setItem('sidebarOpen', sidebar.classList.contains('active'));
    });
    confirmDeleteBtn.addEventListener('click', () => {
        if (state.chatToDelete) deleteChat(state.chatToDelete);
    });
    cancelDeleteBtn.addEventListener('click', closeDeleteModal);
    if (logoutBtn) {
        logoutBtn.addEventListener('click', async () => {
            await logout();
        });
    }

    // Закрытие модалок по крестику
    Array.from(closeSpans).forEach(span => span.addEventListener('click', () => {
        closeProfile();
        closeDeleteModal();
        closeLocationModal();
    }));

    // Клик вне сайдбара
    document.addEventListener('click', (event) => {
        if (sidebar.classList.contains('active') &&
            !sidebar.contains(event.target) &&
            event.target !== toggleSidebarBtn) {
            hideSidebar();
            // Сохраняем состояние сайдбара
            localStorage.setItem('sidebarOpen', 'false');
        }
    });

    // Закрытие модалок по клику на фон
    window.onclick = (event) => {
        const profileModal = document.getElementById('profileModal');
        const deleteConfirmModal = document.getElementById('deleteConfirmModal');
        const locationModal = document.getElementById('locationModal');
        if (event.target === profileModal) closeProfile();
        if (event.target === deleteConfirmModal) closeDeleteModal();
        if (event.target === locationModal) closeLocationModal();
    };

    // Инициализация геолокации (обработчики кнопок)
    const useDeviceLocationBtn = document.getElementById('useDeviceLocation');
    const useMapLocationBtn = document.getElementById('useMapLocation');
    const confirmMapLocationBtn = document.getElementById('confirmMapLocation');
    if (useDeviceLocationBtn) useDeviceLocationBtn.addEventListener('click', useDeviceGPS);
    if (useMapLocationBtn) useMapLocationBtn.addEventListener('click', initYandexMap);
    if (confirmMapLocationBtn) confirmMapLocationBtn.addEventListener('click', confirmMapSelection);

    // Если Telegram WebApp, расширяем и задаём цвет
    const tg = window.Telegram?.WebApp;
    if (tg) {
        tg.expand();
        tg.setHeaderColor('#E31E24');
    }

    // Восстанавливаем состояние сайдбара из localStorage
    const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
    const isTelegramWebApp = !!window.Telegram?.WebApp;
    const savedSidebarOpen = localStorage.getItem('sidebarOpen');
    
    // Сайдбар всегда закрыт по умолчанию, открывается только если был сохранен как открытый
    if (sidebar && savedSidebarOpen === 'true' && !isMobile && !isTelegramWebApp) {
        sidebar.classList.add('active');
    }
});
