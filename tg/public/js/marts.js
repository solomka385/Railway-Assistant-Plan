import { fetchMartsData, exportMartsDataToExcel } from './api.js';
import { showNotification, addMessage } from './ui.js';
import { state } from './state.js';

/**
 * Извлекает список необходимой техники из текста сообщения
 * Ищет секцию "Необходимая техника:" и парсит список техники
 * @param {string} messageText - Текст сообщения
 * @returns {string[]} - Список названий техники
 */
function extractRequiredEquipment(messageText) {
    if (!messageText) return [];
    
    const requiredEquipment = [];
    
    // Ищем секцию "Необходимая техника:"
    const equipmentSectionMatch = messageText.match(/Необходимая техника:\s*\n([\s\S]*?)(?=\n\n|\nНеобходимые|План работ|$)/i);
    if (equipmentSectionMatch) {
        const equipmentSection = equipmentSectionMatch[1];
        // Парсим список техники (каждая строка начинается с "- ")
        const lines = equipmentSection.split('\n');
        for (const line of lines) {
            const trimmed = line.trim();
            if (trimmed.startsWith('- ')) {
                const equipmentName = trimmed.substring(2).trim();
                if (equipmentName) {
                    requiredEquipment.push(equipmentName);
                }
            }
        }
    }
    
    return requiredEquipment;
}

/**
 * Фильтрует список техники по необходимому списку
 * @param {Array} equipmentList - Полный список техники из витрин
 * @param {string[]} requiredEquipment - Список необходимой техники
 * @returns {Array} - Отфильтрованный список техники
 */
function filterEquipmentByRequired(equipmentList, requiredEquipment) {
    if (!requiredEquipment || requiredEquipment.length === 0) {
        return equipmentList;
    }
    
    // Создаём карту необходимых названий для быстрого поиска
    const requiredMap = new Set(requiredEquipment.map(e => e.toLowerCase()));
    
    return equipmentList.filter(item => {
        const itemName = item.equipment_name.toLowerCase();
        // Проверяем, есть ли название техники в списке необходимой
        // Ищем точное совпадение или частичное совпадение
        for (const required of requiredMap) {
            if (itemName === required || itemName.includes(required) || required.includes(itemName)) {
                return true;
            }
        }
        return false;
    });
}

/**
 * Функция для получения и отображения данных из витрин (Marts)
 * Получает данные о сотрудниках, технике и подразделениях с привязкой к геометкам
 */
export async function fetchAndDisplayMartsData() {
    try {
        // Показываем индикатор загрузки
        showNotification('Получаем данные по геолокации...', 'info');
        
        // Получаем текущую геолокацию из состояния
        const userLocation = state.userLocation;
        
        if (!userLocation || !userLocation.latitude || !userLocation.longitude) {
            showNotification('Сначала укажите геолокацию', 'error');
            return;
        }
        
        // Запрос к API для получения данных из витрин
        const geoTags = [{
            latitude: userLocation.latitude,
            longitude: userLocation.longitude
        }];
        const data = await fetchMartsData(geoTags);
        
        // Обработка и отображение полученных данных
        displayMartsData(data);
        
        showNotification('Данные по геолокации успешно получены', 'success');
        
    } catch (error) {
        console.error('Ошибка при получении данных из витрин:', error);
        
        // Детальная обработка ошибок
        let errorMessage = 'Неизвестная ошибка';
        if (error.message.includes('Failed to fetch')) {
            errorMessage = 'Нет соединения с сервером';
        } else if (error.message.includes('401')) {
            errorMessage = 'Требуется авторизация';
        } else if (error.message.includes('500')) {
            errorMessage = 'Ошибка сервера';
        } else if (error.message.includes('404')) {
            errorMessage = 'Данные не найдены';
        }
        
        showNotification(`Ошибка при получении данных: ${errorMessage}`, 'error');
    }
}

/**
 * Экспортирует данные по станциям в Excel файл
 */
export async function exportMartsDataToExcelFile() {
    try {
        showNotification('Подготовка данных для экспорта...', 'info');
        
        // Получаем текущую геолокацию из состояния
        const userLocation = state.userLocation;
        
        if (!userLocation || !userLocation.latitude || !userLocation.longitude) {
            showNotification('Сначала укажите геолокацию', 'error');
            return;
        }
        
        // Запрос к API для получения данных из витрин
        const geoTags = [{
            latitude: userLocation.latitude,
            longitude: userLocation.longitude
        }];
        
        const blob = await exportMartsDataToExcel(geoTags);
        
        // Создаем ссылку для скачивания файла
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `stations_data_${new Date().toISOString().split('T')[0].replace(/\./g, '-')}.xlsx`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);
        
        showNotification('Данные успешно экспортированы в Excel', 'success');
        
    } catch (error) {
        console.error('Ошибка при экспорте данных в Excel:', error);
        showNotification('Ошибка при экспорте данных', 'error');
    }
}

/**
 * Функция для отображения данных из витрин
 * @param {Object} data - Данные, полученные из витрин
 */
function displayMartsData(data) {
    // Проверяем наличие данных
    if (!data) {
        showNotification('Нет данных для отображения', 'info');
        return;
    }
    
    // Формируем HTML сообщение с красивым форматированием
    let message = '<div class="marts-data-container">';
    
    // Техника по станциям
    if (data.equipment && Object.keys(data.equipment).length > 0) {
        message += '<div class="marts-section"><h3>🔧 Техника по станциям</h3>';
        for (const [stationName, equipmentList] of Object.entries(data.equipment)) {
            message += `<div class="station-block"><h4>📍 ${stationName}: ${equipmentList.length} единиц</h4><ul class="equipment-list">`;
            for (const eq of equipmentList) {
                message += `<li>${eq.equipment_name} — ${eq.quantity} шт.</li>`;
            }
            message += '</ul></div>';
        }
        message += '</div>';
    }
    
    // Сотрудники по станциям
    if (data.staff && Object.keys(data.staff).length > 0) {
        message += '<div class="marts-section"><h3>👥 Сотрудники по станциям</h3>';
        for (const [stationName, staffList] of Object.entries(data.staff)) {
            message += `<div class="station-block"><h4>📍 ${stationName}: ${staffList.length} позиций</h4><ul class="staff-list">`;
            for (const s of staffList) {
                message += `<li>${s.position_name} — ${s.quantity} шт.</li>`;
            }
            message += '</ul></div>';
        }
        message += '</div>';
    }
    
    // Ответственные по станциям (только 1 контакт с телефоном)
    if (data.responsibles && Object.keys(data.responsibles).length > 0) {
        message += '<div class="marts-section"><h3>👔 Ответственные по станциям</h3>';
        for (const [stationName, responsible] of Object.entries(data.responsibles)) {
            message += `<div class="station-block"><h4>📍 ${stationName}</h4>`;
            if (responsible.full_name) {
                message += `<p><strong>${responsible.full_name}</strong> — ${responsible.position_name}</p>`;
                message += `<p>📞 ${responsible.phone_number}</p>`;
            } else {
                message += `<p>Ответственный не указан</p>`;
            }
            message += '</div>';
        }
        message += '</div>';
    }
    
    message += '</div>';
    
    // Добавляем сообщение в чат с флагом, чтобы не добавлять кнопку
    addMessage(message, 'system', { isHtml: true, skipMartsButton: true });
}

/**
 * Функция для отображения данных из витрин в том же блоке, где кнопка
 * @param {HTMLElement} container - Контейнер, где находится кнопка (обычно .message-actions или .message)
 */
export function fetchAndDisplayMartsDataInPlace(container) {
    try {
        showNotification('Получаем данные по геолокации...', 'info');
        
        // Получаем текущую геолокацию из состояния
        const userLocation = state.userLocation;
        
        if (!userLocation || !userLocation.latitude || !userLocation.longitude) {
            showNotification('Сначала укажите геолокацию', 'error');
            return;
        }
        
        // Находим родительский элемент сообщения
        const messageEl = container.closest('.message');
        if (!messageEl) {
            console.error('[fetchAndDisplayMartsDataInPlace] Не найден родительский элемент сообщения');
            return;
        }
        
        // Извлекаем текст сообщения для поиска необходимой техники
        const messageText = messageEl.textContent || messageEl.innerText || '';
        const requiredEquipment = extractRequiredEquipment(messageText);
        
        // Запрос к API для получения данных из витрин
        const geoTags = [{
            latitude: userLocation.latitude,
            longitude: userLocation.longitude
        }];
        fetchMartsData(geoTags).then(data => {
            // Проверяем, есть ли уже блок с данными внутри сообщения
            let martsDataBlock = messageEl.querySelector('.marts-data-block');
            
            // Если блок уже существует, просто переключаем его видимость и не создаем новый
            if (martsDataBlock) {
                const details = martsDataBlock.querySelector('details');
                if (details) {
                    details.toggleAttribute('open');
                }
                return;
            }
            
            // Формируем HTML с красивым форматированием
            // summary не нужен, так как кнопка уже существует в .message-actions
            let html = '<details><div class="marts-data-container">';
            
            // Техника по станциям (с фильтрацией по необходимой технике)
            if (data.equipment && Object.keys(data.equipment).length > 0) {
                html += '<div class="marts-section"><h3>🔧 Техника по станциям</h3>';
                for (const [stationName, equipmentList] of Object.entries(data.equipment)) {
                    // Фильтруем технику по необходимому списку
                    const filteredEquipment = filterEquipmentByRequired(equipmentList, requiredEquipment);
                    if (filteredEquipment.length > 0) {
                        html += `<div class="station-block"><h4>📍 ${stationName}: ${filteredEquipment.length} единиц</h4><ul class="equipment-list">`;
                        for (const eq of filteredEquipment) {
                            html += `<li>${eq.equipment_name} — ${eq.quantity} шт.</li>`;
                        }
                        html += '</ul></div>';
                    }
                }
                html += '</div>';
            }
            
            // Сотрудники по станциям
            if (data.staff && Object.keys(data.staff).length > 0) {
                html += '<div class="marts-section"><h3>👥 Сотрудники по станциям</h3>';
                for (const [stationName, staffList] of Object.entries(data.staff)) {
                    html += `<div class="station-block"><h4>📍 ${stationName}: ${staffList.length} позиций</h4><ul class="staff-list">`;
                    for (const s of staffList) {
                        html += `<li>${s.position_name} — ${s.quantity} шт.</li>`;
                    }
                    html += '</ul></div>';
                }
                html += '</div>';
            }
            
            // Ответственные по станциям (только 1 контакт с телефоном)
            if (data.responsibles && Object.keys(data.responsibles).length > 0) {
                html += '<div class="marts-section"><h3>👔 Ответственные по станциям</h3>';
                for (const [stationName, responsible] of Object.entries(data.responsibles)) {
                    html += `<div class="station-block"><h4>📍 ${stationName}</h4>`;
                    if (responsible.full_name) {
                        html += `<p><strong>${responsible.full_name}</strong> — ${responsible.position_name}</p>`;
                        html += `<p>📞 ${responsible.phone_number}</p>`;
                    } else {
                        html += `<p>Ответственный не указан</p>`;
                    }
                    html += '</div>';
                }
                html += '</div>';
            }
            
            html += '</div></details>';
            
            // Создаем новый блок и вставляем внутрь сообщения после контейнера кнопок
            martsDataBlock = document.createElement('div');
            martsDataBlock.className = 'marts-data-block';
            martsDataBlock.innerHTML = html;
            
            // Ищем контейнер кнопок и вставляем после него
            const actionsContainer = messageEl.querySelector('.message-actions');
            if (actionsContainer) {
                actionsContainer.insertAdjacentElement('afterend', martsDataBlock);
            } else {
                messageEl.appendChild(martsDataBlock);
            }
            
            showNotification('Данные по геолокации успешно получены', 'success');
        }).catch(error => {
            console.error('Ошибка при получении данных из витрин:', error);
            showNotification('Ошибка при получении данных', 'error');
        });
        
    } catch (error) {
        console.error('Ошибка при получении данных из витрин:', error);
        showNotification('Ошибка при получении данных', 'error');
    }
}