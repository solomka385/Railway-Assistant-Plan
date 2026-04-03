import { state, saveChatMessages, loadChatMessages, clearChatMessages, saveActiveChatId, saveStreamingState, loadStreamingState, clearStreamingState, clearAllStreamingStates, saveGlobalStreamingState, loadGlobalStreamingState, clearGlobalStreamingState } from './state.js';
import { fetchChats, createChat, deleteChat as apiDeleteChat, fetchMessages, saveMessage, streamProcess } from './api.js';
import { messagesEl, userInputEl, removeTypingIndicator, hideSidebar, showDeleteModal, closeDeleteModal, setInputState } from './ui.js';
import { renderSources, addCopyButtonToMessage, addMartsDataButton, formatStructuredMessage, scrollToBottom, getWelcomeMessage } from './utils.js';
import { updateLocationIndicator, showLocationRequiredNotification } from './location.js';

// Загрузка чатов с сервера и обновление списка
export async function loadChatsFromServer() {
    console.log('[loadChatsFromServer] Начало загрузки чатов...');
    try {
        const chats = await fetchChats();
        state.chats = chats;
        console.log(`[loadChatsFromServer] Загружено ${chats.length} чатов с сервера:`, chats.map(c => ({ id: c.id, title: c.title })));
        // Восстанавливаем сообщения из localStorage для каждого чата
        state.chats.forEach(chat => {
            console.log(`[loadChatsFromServer] Обработка чата ${chat.id}...`);
            const savedMessages = loadChatMessages(chat.id);
            if (savedMessages) {
                chat.messages = savedMessages;
                console.log(`[loadChatsFromServer] Восстановлено ${savedMessages.length} сообщений из localStorage для чата ${chat.id}`);
            } else {
                chat.messages = []; // Инициализируем пустым массивом
                console.log(`[loadChatsFromServer] Сообщения для чата ${chat.id} не найдены в localStorage`);
            }
        });
        renderChatList();
        console.log('[loadChatsFromServer] Загрузка чатов завершена');
    } catch (error) {
        console.error('[loadChatsFromServer] Ошибка загрузки чатов:', error);
        throw error;
    }
}

// Создание нового чата
export async function createNewChat() {
    // Очищаем состояние стриминга и останавливаем polling при создании нового чата
    stopPollingForBotResponse();
    clearGlobalStreamingState();
    state.isStreaming = false;
    state.streamingMessageId = null;
    
    // Разблокируем ввод пользователя
    setInputState(false);
    
    try {
        const newChat = await createChat(`Чат ${state.chats.length + 1}`);
        newChat.messages = []; // Инициализируем сообщения пустым массивом
        state.chats.push(newChat);
        renderChatList();
        saveActiveChatId(newChat.id);
        renderMessages();
        hideSidebar();
        state.currentSessionId = null;
        console.log('[createNewChat] Создан новый чат:', newChat.id);
    } catch (error) {
        console.error('Ошибка создания чата:', error);
        // Fallback: создаём локально
        const chatId = Date.now().toString();
        const newChat = {
            id: chatId,
            title: `Чат ${state.chats.length + 1}`,
            messages: []
        };
        state.chats.push(newChat);
        renderChatList();
        saveActiveChatId(chatId);
        renderMessages();
        hideSidebar();
        state.currentSessionId = null;
        console.log('[createNewChat] Создан локальный чат:', chatId);
    }
}

// Удаление чата
export async function deleteChat(chatId) {
    // Очищаем состояние стриминга и останавливаем polling при удалении чата
    stopPollingForBotResponse();
    clearGlobalStreamingState();
    state.isStreaming = false;
    state.streamingMessageId = null;
    
    // Разблокируем ввод пользователя
    setInputState(false);
    
    try {
        await apiDeleteChat(chatId);
    } catch (error) {
        console.warn('Ошибка удаления чата на сервере, удаляем локально');
    }
    state.chats = state.chats.filter(chat => chat.id !== chatId);
    if (state.activeChatId === chatId) {
        const newActiveId = state.chats.length > 0 ? state.chats[0].id : null;
        saveActiveChatId(newActiveId);
    }
    // Очищаем сообщения из localStorage
    clearChatMessages(chatId);
    renderChatList();
    renderMessages();
    closeDeleteModal();
    state.currentSessionId = null;
}

// Отрисовка списка чатов
export function renderChatList() {
    const chatListEl = document.getElementById('chatList');
    chatListEl.innerHTML = '';
    state.chats.forEach(chat => {
        const chatItem = document.createElement('div');
        chatItem.className = `chat-item ${chat.id === state.activeChatId ? 'active' : ''}`;
        chatItem.innerHTML = `
            <div class="chat-content">${chat.title}</div>
            <button class="delete-chat-btn" data-chat-id="${chat.id}">×</button>
        `;
        chatItem.querySelector('.chat-content').addEventListener('click', () => {
            setActiveChat(chat.id);
            hideSidebar();
        });
        chatItem.querySelector('.delete-chat-btn').addEventListener('click', (e) => {
            e.stopPropagation();
            showDeleteModal(chat.id);
        });
        chatListEl.appendChild(chatItem);
    });
}

// Установка активного чата
export function setActiveChat(chatId) {
    // Останавливаем polling при переключении чата
    stopPollingForBotResponse();
    
    // Проверяем, есть ли активный стриминг для этого чата
    const globalStreamingState = loadGlobalStreamingState();
    const hasActiveStreaming = globalStreamingState && globalStreamingState.isStreaming;
    
    // Очищаем состояние стриминга только если нет активного стриминга
    if (!hasActiveStreaming) {
        clearGlobalStreamingState();
        state.isStreaming = false;
        state.streamingMessageId = null;
        
        // Разблокируем ввод пользователя
        setInputState(false);
    }
    
    saveActiveChatId(chatId);
    renderChatList();
    renderMessages();
    state.currentSessionId = null;
}

// Фильтрация сообщений по режиму
// Сообщения фильтруются по полю mode - показываем только сообщения текущего режима
function filterMessagesByMode(messages) {
    if (!messages) return [];
    return messages.filter(msg => msg.mode === state.currentMode);
}

// Фильтрация DOM элементов сообщений по режиму (используется во время стриминга)
export function filterDomMessagesByMode() {
    const allMessages = messagesEl.querySelectorAll('.message');
    let hasVisibleMessages = false;
    
    allMessages.forEach(msgEl => {
        const msgMode = msgEl.getAttribute('data-mode');
        if (msgMode && msgMode !== state.currentMode) {
            msgEl.style.display = 'none';
        } else {
            msgEl.style.display = '';
            hasVisibleMessages = true;
        }
    });

    // Показываем приветственное сообщение, если нет видимых сообщений
    if (!hasVisibleMessages) {
        const welcomeMsg = getWelcomeMessage(document.getElementById('userDisplay')?.textContent || '');
        if (!messagesEl.querySelector('.welcome-message')) {
            messagesEl.insertAdjacentHTML('afterbegin', welcomeMsg);
        }
    } else {
        // Удаляем приветственное сообщение, если есть видимые сообщения
        const welcomeEl = messagesEl.querySelector('.welcome-message');
        if (welcomeEl) {
            welcomeEl.remove();
        }
    }
}

// Переменная для хранения интервала polling
let pollingInterval = null;
let lastMessageCount = 0;

// Функция для запуска polling для проверки ответа бота
function startPollingForBotResponse() {
    console.log('[startPollingForBotResponse] Запуск polling для проверки ответа бота...');
    
    // Сохраняем текущее количество сообщений
    const activeChat = state.chats.find(chat => chat.id === state.activeChatId);
    lastMessageCount = activeChat ? activeChat.messages.length : 0;
    console.log('[startPollingForBotResponse] Текущее количество сообщений:', lastMessageCount);
    
    // Запускаем polling каждые 2 секунды
    pollingInterval = setInterval(async () => {
        try {
            console.log('[polling] Проверка новых сообщений...');
            const messages = await fetchMessages(state.activeChatId);
            const activeChat = state.chats.find(chat => chat.id === state.activeChatId);
            
            console.log('[polling] Получено сообщений с сервера:', messages.length, 'Ожидали:', lastMessageCount);
            
            // Сначала проверяем, есть ли сообщение от бота в текущем режиме
            // Это нужно для случая, когда сообщение от бота уже было сохранено до перезагрузки
            const botMessages = messages.filter(msg => msg.type === 'bot' && msg.mode === state.currentMode);
            
            if (botMessages.length > 0) {
                // Проверяем, есть ли уже это сообщение в DOM
                const existingBotMessages = messagesEl.querySelectorAll('.message.bot[data-mode="' + state.currentMode + '"]');
                const lastBotMessage = botMessages[botMessages.length - 1];
                
                // Проверяем, нужно ли добавить это сообщение (сравниваем по тексту или id)
                let needsToAdd = true;
                existingBotMessages.forEach(el => {
                    const elText = el.textContent.trim();
                    if (elText === lastBotMessage.text.trim()) {
                        needsToAdd = false;
                    }
                });
                
                if (needsToAdd) {
                    console.log('[polling] Найден новый ответ от бота:', lastBotMessage);
                    
                    // Останавливаем polling
                    stopPollingForBotResponse();
                    
                    // Обновляем сообщения в чате
                    activeChat.messages = messages;
                    saveChatMessages(state.activeChatId, messages);
                    
                    // Удаляем индикатор печати
                    const indicator = messagesEl.querySelector('.message.bot.streaming');
                    if (indicator) indicator.remove();
                    
                    // Добавляем новое сообщение бота в DOM
                    const botMessageEl = document.createElement('div');
                    botMessageEl.className = `message ${lastBotMessage.type}`;
                    botMessageEl.setAttribute('data-mode', lastBotMessage.mode);
                    if (lastBotMessage.type === 'bot' && state.currentMode === 'plan') {
                        botMessageEl.innerHTML = formatStructuredMessage(lastBotMessage.text);
                    } else {
                        botMessageEl.textContent = lastBotMessage.text;
                    }
                    if (lastBotMessage.type === 'bot') {
                        addCopyButtonToMessage(botMessageEl, lastBotMessage.text);
                        addMartsDataButton(botMessageEl);
                    }
                    if (lastBotMessage.type === 'bot' && lastBotMessage.sources && lastBotMessage.sources.length > 0) {
                        const sourcesHtml = renderSources(lastBotMessage.sources);
                        botMessageEl.insertAdjacentHTML('beforeend', sourcesHtml);
                    }
                    messagesEl.appendChild(botMessageEl);
                    scrollToBottom(messagesEl);
                    
                    // Очищаем состояние стриминга
                    clearGlobalStreamingState();
                    clearStreamingState(state.streamingMessageId);
                    state.isStreaming = false;
                    state.streamingMessageId = null;
                    
                    // Разблокируем ввод пользователя
                    setInputState(false);
                } else {
                    console.log('[polling] Сообщение от бота уже отображено в DOM');
                    stopPollingForBotResponse();
                    clearGlobalStreamingState();
                    clearStreamingState(state.streamingMessageId);
                    state.isStreaming = false;
                    state.streamingMessageId = null;
                    setInputState(false);
                }
            } else if (messages.length > lastMessageCount) {
                // Если есть новые сообщения, но нет сообщения от бота в текущем режиме,
                // обновляем lastMessageCount, чтобы не проверять те же сообщения снова
                console.log('[polling] Новые сообщения есть, но нет ответа от бота в текущем режиме');
                lastMessageCount = messages.length;
            }
        } catch (error) {
            // Игнорируем ошибки сети при polling - просто продолжаем проверку
            console.log('[polling] Ошибка при проверке сообщений (игнорируем):', error.message);
        }
    }, 2000); // Проверяем каждые 2 секунды
}

// Функция для остановки polling
function stopPollingForBotResponse() {
    if (pollingInterval) {
        clearInterval(pollingInterval);
        pollingInterval = null;
        console.log('[stopPollingForBotResponse] Polling остановлен');
    }
}

// Отрисовка сообщений активного чата
export async function renderMessages(skipStreamingCheck = false) {
    console.log('[renderMessages] Начало отрисовки сообщений...');
    
    // Проверяем, есть ли незавершенный стриминг из предыдущей сессии
    const globalStreamingState = loadGlobalStreamingState();
    let hasPendingStreaming = false;
    
    if (globalStreamingState && globalStreamingState.isStreaming && globalStreamingState.streamingMessageId) {
        console.log('[renderMessages] Обнаружен незавершенный стриминг из localStorage');
        hasPendingStreaming = true;
        state.isStreaming = true;
        state.streamingMessageId = globalStreamingState.streamingMessageId;
    }
    
    // Не перерисовывать сообщения во время активного стриминга (если не пропущена проверка и нет pending стриминга)
    if (state.isStreaming && !skipStreamingCheck && !hasPendingStreaming) {
        console.log('[renderMessages] Стриминг в процессе, пропускаем перерисовку сообщений');
        return;
    }

    if (!state.activeChatId) {
        console.log('[renderMessages] Нет активного чата, показываем приветствие');
        messagesEl.innerHTML = getWelcomeMessage(document.getElementById('userDisplay')?.textContent || '');
        return;
    }

    const activeChat = state.chats.find(chat => chat.id === state.activeChatId);
    if (!activeChat) {
        console.error('[renderMessages] Активный чат не найден:', state.activeChatId);
        return;
    }

    console.log('[renderMessages] activeChatId =', state.activeChatId, 'activeChat.messages =', activeChat.messages?.length);

    // Если сообщения уже загружены в чате, используем их
    let messages = activeChat.messages;
    
    // Если сообщений нет в чате, пробуем загрузить из localStorage
    if (!messages || messages.length === 0) {
        console.log('[renderMessages] Сообщений нет в чате, пробуем загрузить из localStorage...');
        messages = loadChatMessages(state.activeChatId);
        if (messages) {
            console.log('[renderMessages] Загружено сообщений из localStorage:', messages.length, 'для чата:', state.activeChatId);
        }
    }
    
    // Если в localStorage нет сообщений, загружаем с сервера
    if (!messages || messages.length === 0) {
        console.log('[renderMessages] Сообщений нет в localStorage, загружаем с сервера...');
        try {
            messages = await fetchMessages(state.activeChatId);
            console.log('[renderMessages] Загружено сообщений с сервера:', messages.length, 'для чата:', state.activeChatId, 'режим:', state.currentMode);
            // Сохраняем в localStorage для будущего использования
            saveChatMessages(state.activeChatId, messages);
        } catch (error) {
            console.error('[renderMessages] Ошибка загрузки сообщений с сервера:', error);
            messages = [];
        }
    }
    
    activeChat.messages = messages;
    console.log('[renderMessages] Итого сообщений для отрисовки:', messages.length);

    messagesEl.innerHTML = '';
    const filteredMessages = filterMessagesByMode(activeChat.messages);

    if (filteredMessages.length > 0) {
        filteredMessages.forEach(msg => {
            const messageEl = document.createElement('div');
            messageEl.className = `message ${msg.type}`;
            messageEl.setAttribute('data-mode', msg.mode);
            
            if (msg.type === 'bot' && state.currentMode === 'plan') {
                messageEl.innerHTML = formatStructuredMessage(msg.text);
            } else {
                messageEl.textContent = msg.text;
            }
            if (msg.type === 'bot' && msg.sources && msg.sources.length > 0) {
                console.log('[renderMessages] Отображение источников для сообщения:', msg.id, msg.sources);
                const sourcesHtml = renderSources(msg.sources);
                messageEl.insertAdjacentHTML('beforeend', sourcesHtml);
            } else if (msg.type === 'bot') {
                console.log('[renderMessages] Нет источников для сообщения:', msg.id, 'sources:', msg.sources);
            }
            if (msg.type === 'bot') {
                addCopyButtonToMessage(messageEl, msg.text);
                addMartsDataButton(messageEl);
            }
            messagesEl.appendChild(messageEl);
        });
    } else {
        messagesEl.innerHTML = getWelcomeMessage(document.getElementById('userDisplay')?.textContent || '');
    }
    if (state.activeChatId) {
        if (filteredMessages.length > 0) {
            scrollToBottom(messagesEl);
        }
    }
    
    // Если есть незавершенный стриминг, добавляем индикатор печати после отрисовки сообщений
    if (hasPendingStreaming) {
        console.log('[renderMessages] Добавляем индикатор печати для незавершенного стриминга');
        const typingIndicatorEl = document.createElement('div');
        typingIndicatorEl.className = 'message bot streaming';
        typingIndicatorEl.setAttribute('data-mode', state.currentMode);
        typingIndicatorEl.id = `streaming_msg_${state.streamingMessageId}`;
        typingIndicatorEl.innerHTML = '<div class="typing-indicator">...</div>';
        messagesEl.appendChild(typingIndicatorEl);
        scrollToBottom(messagesEl);
        
        // Блокируем ввод пользователя
        setInputState(true);
        
        // Запускаем polling для проверки новых сообщений
        startPollingForBotResponse();
    } else {
        // Разблокируем ввод пользователя, если нет стриминга
        setInputState(false);
    }
}

// Отправка сообщения
export async function sendUserMessage() {
    const userMessage = userInputEl.value.trim();
    if (!userMessage || !state.activeChatId) return;

    // Проверка: не идет ли стриминг в текущем чате и режиме
    if (state.isStreaming) {
        console.log('[sendUserMessage] Стриминг в процессе, отправка сообщения заблокирована');
        return;
    }

    // Проверка геолокации для режима плана
    if (state.currentMode === 'plan' && !state.userLocation) {
        showLocationRequiredNotification();
        return;
    }

    // Останавливаем polling перед отправкой нового сообщения
    stopPollingForBotResponse();

    // Устанавливаем флаг стриминга
    state.isStreaming = true;
    // Сохраняем глобальное состояние стриминга
    saveGlobalStreamingState(true, null); // messageId будет установлен позже
    
    // Блокируем ввод пользователя
    setInputState(true);

    const requestMode = state.currentMode;

    const activeChat = state.chats.find(chat => chat.id === state.activeChatId);
    if (!activeChat.messages) activeChat.messages = [];

    // Удаляем приветствие, если оно есть
    const welcomeElements = messagesEl.querySelectorAll('.welcome-message');
    welcomeElements.forEach(el => el.remove());

    // Добавляем сообщение пользователя в DOM
    const userMsgDiv = document.createElement('div');
    userMsgDiv.className = 'message user';
    userMsgDiv.setAttribute('data-mode', requestMode);
    userMsgDiv.textContent = userMessage;
    messagesEl.appendChild(userMsgDiv);
    userInputEl.value = '';
    scrollToBottom(messagesEl);

    // Сохраняем сообщение пользователя на сервер
    try {
        const saved = await saveMessage(state.activeChatId, {
            type: 'user',
            text: userMessage,
            mode: requestMode,
            sources: [],
            employees: []
        });
        console.log('[sendUserMessage] Сообщение пользователя сохранено на сервере:', saved);
        activeChat.messages.push(saved);
        // Сохраняем в localStorage
        saveChatMessages(state.activeChatId, activeChat.messages);
        console.log('[sendUserMessage] Всего сообщений в чате после сохранения:', activeChat.messages.length);
    } catch (error) {
        console.error('[sendUserMessage] Ошибка сохранения сообщения пользователя:', error);
        const localMsg = { type: 'user', text: userMessage, mode: requestMode };
        activeChat.messages.push(localMsg);
        // Сохраняем в localStorage даже при ошибке сервера
        saveChatMessages(state.activeChatId, activeChat.messages);
        console.log('[sendUserMessage] Сообщение сохранено локально. Всего сообщений:', activeChat.messages.length);
    }

    // Индикатор печати
    state.typingIndicator = document.createElement('div');
    state.typingIndicator.className = 'message bot';
    state.typingIndicator.setAttribute('data-mode', requestMode);
    state.typingIndicator.innerHTML = '<div class="typing-indicator">...</div>';
    messagesEl.appendChild(state.typingIndicator);
    scrollToBottom(messagesEl);

    // Генерируем ID для сообщения бота
    const botMessageId = Date.now().toString();
    state.streamingMessageId = botMessageId;
    state.accumulatedText = '';
    state.streamingSources = [];
    state.streamingEmployees = [];
    // Обновляем глобальное состояние стриминга с messageId
    saveGlobalStreamingState(true, botMessageId);

    try {
        const response = await streamProcess(state.activeChatId, {
            question: userMessage,
            session_id: state.currentSessionId,
            mode: requestMode
        });

        removeTypingIndicator();

        const botMessageEl = document.createElement('div');
        botMessageEl.className = 'message bot streaming';
        botMessageEl.setAttribute('data-mode', requestMode);
        botMessageEl.id = `streaming_msg_${botMessageId}`;
        messagesEl.appendChild(botMessageEl);
        let accumulatedText = '';

        const reader = response.body.getReader();
        const decoder = new TextDecoder();

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value, { stream: true });
            const lines = chunk.split('\n');

            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    try {
                        // Безопасный парсинг JSON с обработкой некорректных escape-последовательностей
                        const jsonStr = line.slice(6);
                        let data;
                        try {
                            data = JSON.parse(jsonStr);
                        } catch (e) {
                            // Если стандартный парсинг не сработал, пробуем исправить escape-последовательности
                            console.warn('Ошибка парсинга JSON, пробуем исправить:', e.message);
                            const fixedJson = jsonStr.replace(/\\([^"\\\/bfnrt])/g, '\\\\$1');
                            data = JSON.parse(fixedJson);
                        }
                        if (data.type === 'content') {
                            accumulatedText += data.chunk;
                            state.accumulatedText = accumulatedText;
                            if (requestMode === 'plan') {
                                botMessageEl.innerHTML = formatStructuredMessage(accumulatedText);
                            } else {
                                botMessageEl.textContent = accumulatedText;
                            }
                            scrollToBottom(messagesEl);
                            // Сохраняем состояние стриминга в localStorage
                            saveStreamingState(botMessageId, accumulatedText, state.streamingSources, state.streamingEmployees);
                        } else if (data.type === 'complete') {
                            if (data.session_id) {
                                state.currentSessionId = data.session_id;
                                console.log('Новый session_id:', state.currentSessionId);
                            }
                            botMessageEl.classList.remove('streaming');

                            // Сбор источников
                            let sourcesList = [];
                            if (data.subdivisions && data.subdivisions.sources) sourcesList = sourcesList.concat(data.subdivisions.sources);
                            if (data.technics && data.technics.sources) sourcesList = sourcesList.concat(data.technics.sources);
                            if (data.employees && data.employees.sources) sourcesList = sourcesList.concat(data.employees.sources);
                            if (data.work_plan && data.work_plan.sources) sourcesList = sourcesList.concat(data.work_plan.sources);
                            // Если есть новый формат с data.sources, используем его
                            if (data.sources) {
                                if (data.sources.subdivisions) sourcesList = sourcesList.concat(data.sources.subdivisions);
                                if (data.sources.technics) sourcesList = sourcesList.concat(data.sources.technics);
                                if (data.sources.employees) sourcesList = sourcesList.concat(data.sources.employees);
                                if (data.sources.work_plan) sourcesList = sourcesList.concat(data.sources.work_plan);
                            }
                            sourcesList = sourcesList.filter((src, index, self) =>
                                index === self.findIndex(s => s.source_file === src.source_file)
                            );
                            console.log('[sendUserMessage] Собрано источников:', sourcesList.length, sourcesList);
                            state.streamingSources = sourcesList;

                            // Финальный текст
                            let finalText = accumulatedText;
                            if (requestMode === 'plan') {
                                if (!accumulatedText.includes('Необходимая техника') && data.technics && data.technics.list && data.technics.list.length > 0) {
                                    const techList = data.technics.list.map(t => `- ${t}`).join('\n');
                                    finalText = `Необходимая техника:\n${techList}\n\n` + finalText;
                                }
                                if (!accumulatedText.includes('Необходимые сотрудники') && data.employees && data.employees.list && data.employees.list.length > 0) {
                                    const empList = data.employees.list.map(e => `- ${e}`).join('\n');
                                    finalText = `Необходимые сотрудники:\n${empList}\n\n` + finalText;
                                }
                            }
                            state.streamingEmployees = data.employees ? data.employees.list : [];

                            // Сохраняем ответ бота
                            console.log('[sendUserMessage] Начало сохранения ответа бота...');
                            try {
                                const savedBot = await saveMessage(state.activeChatId, {
                                    type: 'bot',
                                    text: finalText,
                                    mode: requestMode,
                                    sources: sourcesList,
                                    employees: data.employees ? data.employees.list : []
                                });
                                console.log('[sendUserMessage] Ответ бота сохранен на сервере:', savedBot);
                                activeChat.messages.push(savedBot);
                            } catch (e) {
                                console.error('[sendUserMessage] Ошибка сохранения ответа бота:', e);
                                activeChat.messages.push({
                                    type: 'bot',
                                    text: finalText,
                                    mode: requestMode,
                                    sources: sourcesList,
                                    employees: data.employees ? data.employees.list : []
                                });
                            }
                            // Сохраняем в localStorage
                            console.log('[sendUserMessage] Сохранение в localStorage...');
                            saveChatMessages(state.activeChatId, activeChat.messages);
                            console.log('[sendUserMessage] Всего сообщений в чате после сохранения ответа бота:', activeChat.messages.length);

                            // Отображаем финальный текст
                            if (requestMode === 'plan') {
                                botMessageEl.innerHTML = formatStructuredMessage(finalText);
                            } else {
                                botMessageEl.textContent = finalText;
                            }

                            if (sourcesList.length > 0) {
                                const sourcesHtml = renderSources(sourcesList);
                                botMessageEl.insertAdjacentHTML('beforeend', sourcesHtml);
                            }
                            addCopyButtonToMessage(botMessageEl, finalText);
                            addMartsDataButton(botMessageEl);
                            scrollToBottom(messagesEl);
                            
                            // Очищаем состояние стриминга
                            clearStreamingState(botMessageId);
                            clearGlobalStreamingState();
                            stopPollingForBotResponse();
                            state.streamingMessageId = null;
                            state.accumulatedText = '';
                            state.streamingSources = [];
                            state.streamingEmployees = [];
                            
                            state.isStreaming = false;
                            
                            // Разблокируем ввод пользователя
                            setInputState(false);
                            
                            return;
                        } else if (data.type === 'error') {
                            throw new Error(data.chunk);
                        }
                    } catch (e) {
                        console.error('Ошибка парсинга JSON из потока:', e);
                    }
                }
            }
        }
    } catch (error) {
        console.error('Ошибка при отправке запроса к RAG:', error);
        removeTypingIndicator();
        const errorMsg = `⚠️ Не удалось получить ответ. ${error.message}`;
        const errorDiv = document.createElement('div');
        errorDiv.className = 'message bot';
        errorDiv.setAttribute('data-mode', requestMode);
        errorDiv.textContent = errorMsg;
        messagesEl.appendChild(errorDiv);
        addCopyButtonToMessage(errorDiv, errorMsg);
        scrollToBottom(messagesEl);

        try {
            await saveMessage(state.activeChatId, {
                type: 'bot',
                text: errorMsg,
                mode: requestMode,
                sources: [],
                employees: []
            });
            // Сохраняем в localStorage
            saveChatMessages(state.activeChatId, activeChat.messages);
        } catch (e) {}
    } finally {
        state.isStreaming = false;
        clearGlobalStreamingState();
        stopPollingForBotResponse();
        
        // Разблокируем ввод пользователя
        setInputState(false);
    }
}