// Глобальное состояние приложения
export const state = {
    chats: [],                // список чатов
    activeChatId: localStorage.getItem('activeChatId'),  // ID текущего активного чата - восстанавливаем из localStorage
    currentMode: localStorage.getItem('currentMode') || 'plan',  // 'plan' или 'chat' - восстанавливаем из localStorage
    userLocation: loadUserLocation(),  // { latitude, longitude, source } - загружаем из localStorage
    currentSessionId: null,  // session_id для RAG
    chatToDelete: null,      // ID чата, который хотят удалить
    typingIndicator: null,   // DOM-элемент индикатора печати
    yandexMap: null,         // объект Яндекс.Карты
    mapPlacemark: null,      // метка на карте
    isStreaming: false,       // флаг: идет ли сейчас стриминг ответа от LLM
    streamingMessageId: null, // ID сообщения, которое сейчас стримится
    accumulatedText: '',      // накопленный текст ответа
    streamingSources: [],     // источники во время стриминга
    streamingEmployees: []    // сотрудники во время стриминга
};

// Функция для сохранения режима в localStorage
export function saveMode(mode) {
    state.currentMode = mode;
    localStorage.setItem('currentMode', mode);
}

// Функция для сохранения активного чата в localStorage
export function saveActiveChatId(chatId) {
    state.activeChatId = chatId;
    localStorage.setItem('activeChatId', chatId);
}

// Функция для загрузки геолокации из localStorage
function loadUserLocation() {
    const saved = localStorage.getItem('userLocation');
    if (saved) {
        try {
            return JSON.parse(saved);
        } catch (e) {
            console.error('Ошибка загрузки геолокации из localStorage:', e);
            return null;
        }
    }
    return null;
}

// Функция для сохранения геолокации в localStorage
export function saveUserLocation(location) {
    state.userLocation = location;
    if (location) {
        localStorage.setItem('userLocation', JSON.stringify(location));
    } else {
        localStorage.removeItem('userLocation');
    }
}

// Функция для сохранения сообщений чата в localStorage
export function saveChatMessages(chatId, messages) {
    const key = `chat_messages_${chatId}`;
    try {
        localStorage.setItem(key, JSON.stringify(messages));
        console.log(`[localStorage] Сохранено ${messages.length} сообщений для чата ${chatId}`);
        console.log(`[localStorage] Ключ: ${key}, Размер: ${JSON.stringify(messages).length} байт`);
    } catch (e) {
        console.error('[localStorage] Ошибка сохранения сообщений:', e);
        console.error('[localStorage] ChatId:', chatId, 'Messages count:', messages?.length);
    }
}

// Функция для загрузки сообщений чата из localStorage
export function loadChatMessages(chatId) {
    const key = `chat_messages_${chatId}`;
    const saved = localStorage.getItem(key);
    console.log(`[localStorage] Попытка загрузки сообщений для чата ${chatId}, ключ: ${key}`);
    if (saved) {
        try {
            const messages = JSON.parse(saved);
            console.log(`[localStorage] Загружено ${messages.length} сообщений для чата ${chatId}`);
            console.log(`[localStorage] Первые 3 сообщения:`, messages.slice(0, 3).map(m => ({ type: m.type, mode: m.mode, text: m.text?.substring(0, 50) })));
            return messages;
        } catch (e) {
            console.error('[localStorage] Ошибка загрузки сообщений:', e);
            console.error('[localStorage] Сохраненное значение:', saved.substring(0, 200));
            return null;
        }
    }
    console.log(`[localStorage] Сообщения для чата ${chatId} не найдены в localStorage`);
    // Выводим все ключи localStorage для отладки
    console.log('[localStorage] Все ключи в localStorage:', Object.keys(localStorage));
    return null;
}

// Функция для очистки сообщений чата из localStorage
export function clearChatMessages(chatId) {
    const key = `chat_messages_${chatId}`;
    localStorage.removeItem(key);
    console.log(`[localStorage] Очищены сообщения для чата ${chatId}`);
}

// Функция для сохранения состояния стриминга в localStorage
export function saveStreamingState(messageId, accumulatedText, sources, employees) {
    const key = `streaming_state_${messageId}`;
    try {
        const stateToSave = {
            messageId,
            accumulatedText,
            sources,
            employees,
            timestamp: Date.now()
        };
        localStorage.setItem(key, JSON.stringify(stateToSave));
        console.log(`[localStorage] Сохранено состояние стриминга для сообщения ${messageId}`);
    } catch (e) {
        console.error('[localStorage] Ошибка сохранения состояния стриминга:', e);
    }
}

// Функция для сохранения глобального состояния стриминга (флаг и ID)
export function saveGlobalStreamingState(isStreaming, streamingMessageId) {
    try {
        const stateToSave = {
            isStreaming,
            streamingMessageId,
            timestamp: Date.now()
        };
        localStorage.setItem('global_streaming_state', JSON.stringify(stateToSave));
        console.log(`[localStorage] Сохранено глобальное состояние стриминга: isStreaming=${isStreaming}, messageId=${streamingMessageId}`);
    } catch (e) {
        console.error('[localStorage] Ошибка сохранения глобального состояния стриминга:', e);
    }
}

// Функция для загрузки глобального состояния стриминга с проверкой на устаревание
export function loadGlobalStreamingState() {
    const saved = localStorage.getItem('global_streaming_state');
    if (saved) {
        try {
            const state = JSON.parse(saved);
            // Проверяем, не устарело ли состояние (более 5 минут)
            const MAX_AGE = 5 * 60 * 1000; // 5 минут
            const age = Date.now() - state.timestamp;
            
            if (age > MAX_AGE) {
                console.log(`[localStorage] Состояние стриминга устарело (${Math.round(age / 1000)} сек), очищаем`);
                clearGlobalStreamingState();
                return null;
            }
            
            console.log(`[localStorage] Загружено глобальное состояние стриминга:`, state);
            return state;
        } catch (e) {
            console.error('[localStorage] Ошибка загрузки глобального состояния стриминга:', e);
            return null;
        }
    }
    return null;
}

// Функция для очистки глобального состояния стриминга
export function clearGlobalStreamingState() {
    localStorage.removeItem('global_streaming_state');
    console.log('[localStorage] Очищено глобальное состояние стриминга');
}

// Функция для сохранения вопроса пользователя при стриминге
export function saveStreamingQuestion(chatId, question, mode) {
    try {
        const data = {
            chatId,
            question,
            mode,
            timestamp: Date.now()
        };
        localStorage.setItem('streaming_question', JSON.stringify(data));
        console.log(`[localStorage] Сохранен вопрос для стриминга:`, question);
    } catch (e) {
        console.error('[localStorage] Ошибка сохранения вопроса для стриминга:', e);
    }
}

// Функция для загрузки вопроса пользователя при стриминге
export function loadStreamingQuestion() {
    const saved = localStorage.getItem('streaming_question');
    if (saved) {
        try {
            const data = JSON.parse(saved);
            // Проверяем, не устарел ли вопрос (более 5 минут)
            const MAX_AGE = 5 * 60 * 1000; // 5 минут
            const age = Date.now() - data.timestamp;
            
            if (age > MAX_AGE) {
                console.log(`[localStorage] Вопрос для стриминга устарел (${Math.round(age / 1000)} сек), очищаем`);
                clearStreamingQuestion();
                return null;
            }
            
            console.log(`[localStorage] Загружен вопрос для стриминга:`, data);
            return data;
        } catch (e) {
            console.error('[localStorage] Ошибка загрузки вопроса для стриминга:', e);
            return null;
        }
    }
    return null;
}

// Функция для очистки вопроса пользователя при стриминге
export function clearStreamingQuestion() {
    localStorage.removeItem('streaming_question');
    console.log('[localStorage] Очищен вопрос для стриминга');
}

// Функция для загрузки состояния стриминга из localStorage
export function loadStreamingState(messageId) {
    const key = `streaming_state_${messageId}`;
    const saved = localStorage.getItem(key);
    if (saved) {
        try {
            const state = JSON.parse(saved);
            console.log(`[localStorage] Загружено состояние стриминга для сообщения ${messageId}`);
            return state;
        } catch (e) {
            console.error('[localStorage] Ошибка загрузки состояния стриминга:', e);
            return null;
        }
    }
    return null;
}

// Функция для удаления состояния стриминга из localStorage
export function clearStreamingState(messageId) {
    const key = `streaming_state_${messageId}`;
    localStorage.removeItem(key);
    console.log(`[localStorage] Удалено состояние стриминга для сообщения ${messageId}`);
}

// Функция для очистки всех состояний стриминга
export function clearAllStreamingStates() {
    const keys = Object.keys(localStorage).filter(key => key.startsWith('streaming_state_'));
    keys.forEach(key => localStorage.removeItem(key));
    console.log(`[localStorage] Очищено ${keys.length} состояний стриминга`);
}