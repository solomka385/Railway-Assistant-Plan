import { API_BASE_URL } from './constants.js';

// Получение списка чатов
export async function fetchChats() {
    const response = await fetch(`${API_BASE_URL}/chats`, { credentials: 'include' });
    if (!response.ok) throw new Error('Failed to load chats');
    return await response.json();
}

// Создание нового чата
export async function createChat(title) {
    const response = await fetch(`${API_BASE_URL}/chats`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title }),
        credentials: 'include'
    });
    if (!response.ok) throw new Error('Failed to create chat');
    return await response.json();
}

// Удаление чата
export async function deleteChat(chatId) {
    const response = await fetch(`${API_BASE_URL}/chats/${chatId}`, {
        method: 'DELETE',
        credentials: 'include'
    });
    if (!response.ok && response.status !== 204) {
        throw new Error('Failed to delete chat on server');
    }
}

// Получение сообщений чата
export async function fetchMessages(chatId) {
    const response = await fetch(`${API_BASE_URL}/chats/${chatId}/messages`, { credentials: 'include' });
    if (!response.ok) throw new Error('Failed to load messages');
    return await response.json();
}

// Сохранение сообщения
export async function saveMessage(chatId, message) {
    const response = await fetch(`${API_BASE_URL}/chats/${chatId}/messages`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(message),
        credentials: 'include'
    });
    if (!response.ok) throw new Error('Failed to save message');
    return await response.json();
}

// Отправка запроса на stream-обработку
export async function streamProcess(chatId, data) {
    // Создаем AbortController с таймаутом 10 минут (600000 мс)
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 600000); // 10 минут
    
    try {
        const response = await fetch(`${API_BASE_URL}/chats/${chatId}/process-message-stream`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
            credentials: 'include',
            signal: controller.signal
        });
        clearTimeout(timeoutId);
        
        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`HTTP error! status: ${response.status} - ${errorText}`);
        }
        return response;
    } catch (error) {
        clearTimeout(timeoutId);
        if (error.name === 'AbortError') {
            throw new Error('Таймаут запроса. Попробуйте снова.');
        }
        throw error;
    }
}

// Получение данных из витрин по геометкам
export async function fetchMartsData(geoTags, subdivisions = null, positions = null, equipment = null) {
    const response = await fetch(`${API_BASE_URL}/marts-data`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            geo_tags: geoTags,
            subdivisions: subdivisions,
            positions: positions,
            equipment: equipment
        }),
        credentials: 'include'
    });
    if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`HTTP error! status: ${response.status} - ${errorText}`);
    }
    return await response.json();
}

// Экспорт данных по станциям в Excel
export async function exportMartsDataToExcel(geoTags, subdivisions = null, positions = null, equipment = null) {
    const response = await fetch(`${API_BASE_URL}/export-stations-excel`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            geo_tags: geoTags,
            subdivisions: subdivisions,
            positions: positions,
            equipment: equipment
        }),
        credentials: 'include'
    });
    if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`HTTP error! status: ${response.status} - ${errorText}`);
    }
    return await response.blob();
}