import { state } from './state.js';

// Формирование HTML блока с источниками
export function renderSources(sources) {
    console.log('[renderSources] Получены источники:', sources);
    // Если sources - строка (из JSON в БД), парсим её
    if (typeof sources === 'string') {
        try {
            sources = JSON.parse(sources);
        } catch (e) {
            console.error('[renderSources] Ошибка парсинга sources:', e, 'sources:', sources);
            return '';
        }
    }
    
    if (!sources || sources.length === 0) {
        console.log('[renderSources] Источники отсутствуют или пустые');
        return '';
    }
    let html = '<div class="message-sources"><details><summary>📚 Источники</summary><ul>';
    sources.forEach(src => {
        const filename = src.source_file || 'Неизвестный файл';
        const preview = src.content_preview || '';
        html += `<li><a href="/api/download/${encodeURIComponent(filename)}" download target="_blank">📄 ${filename}</a>`;
        if (preview) {
            html += `<div class="source-preview">${preview}</div>`;
        }
        html += '</li>';
    });
    html += '</ul></details></div>';
    
    return html;
}

// Кнопка копирования текста сообщения
export function addCopyButtonToMessage(messageEl, text) {
    if (!messageEl || messageEl.querySelector('.copy-btn')) return;
    
    // Ищем или создаем контейнер для кнопок
    let actionsContainer = messageEl.querySelector('.message-actions');
    if (!actionsContainer) {
        actionsContainer = document.createElement('div');
        actionsContainer.className = 'message-actions';
        messageEl.appendChild(actionsContainer);
    }
    
    const copyBtn = document.createElement('button');
    copyBtn.type = 'button';
    copyBtn.className = 'copy-btn';
    copyBtn.textContent = '📋 Копировать';
    copyBtn.onclick = () => {
        navigator.clipboard.writeText(text).then(() => {
            copyBtn.textContent = '✅ Скопировано!';
            setTimeout(() => { copyBtn.textContent = '📋 Копировать'; }, 2000);
        });
    };
    actionsContainer.appendChild(copyBtn);
}

// Кнопка получения данных по станциям
export function addMartsDataButton(container, skip = false) {
    // Находим родительский элемент сообщения
    const messageEl = container.closest('.message');
    if (!messageEl) {
        console.error('[addMartsDataButton] Не найден родительский элемент сообщения');
        return;
    }
    
    // Проверяем, есть ли уже кнопка в сообщении
    if (messageEl.querySelector('.marts-data-btn') || skip) return;
    
    // Ищем или создаем контейнер для кнопок
    let actionsContainer = container.querySelector('.message-actions');
    if (!actionsContainer) {
        actionsContainer = document.createElement('div');
        actionsContainer.className = 'message-actions';
        container.appendChild(actionsContainer);
    }
    
    // Кнопка "Данные по станциям"
    const martsBtn = document.createElement('button');
    martsBtn.type = 'button';
    martsBtn.className = 'marts-data-btn';
    martsBtn.textContent = '📊 Данные по станциям';
    martsBtn.onclick = (e) => {
        e.preventDefault();
        e.stopPropagation();
        // Находим родительский элемент сообщения
        const messageEl = container.closest('.message');
        if (!messageEl) {
            console.error('[addMartsDataButton] Не найден родительский элемент сообщения');
            return;
        }
        
        // Проверяем, есть ли уже блок с данными внутри сообщения
        let martsDataBlock = messageEl.querySelector('.marts-data-block');
        if (martsDataBlock) {
            // Если блок есть, просто переключаем атрибут open у details
            const details = martsDataBlock.querySelector('details');
            if (details) {
                details.toggleAttribute('open');
            }
            return;
        }
        
        // Если блока нет, загружаем данные и отображаем их
        import('./marts.js').then(module => {
            module.fetchAndDisplayMartsDataInPlace(container);
        });
    };
    actionsContainer.appendChild(martsBtn);
    
    // Кнопка "Экспорт в Excel"
    const exportBtn = document.createElement('button');
    exportBtn.type = 'button';
    exportBtn.className = 'export-excel-btn';
    exportBtn.textContent = '📥 Экспорт в Excel';
    exportBtn.onclick = (e) => {
        e.preventDefault();
        e.stopPropagation();
        import('./marts.js').then(module => {
            module.exportMartsDataToExcelFile();
        });
    };
    actionsContainer.appendChild(exportBtn);
}

// Функция для отображения данных из витрин в том же блоке, где кнопка (с использованием details)
export function fetchAndDisplayMartsDataInPlaceWithDetails(container) {
    try {
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
        fetchMartsData(geoTags).then(data => {
            // Находим родительский элемент сообщения
            const messageEl = container.closest('.message');
            if (!messageEl) {
                console.error('[fetchAndDisplayMartsDataInPlaceWithDetails] Не найден родительский элемент сообщения');
                return;
            }
            
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
            
            // Создаем блок с данными с использованием details для сворачивания
            martsDataBlock = document.createElement('div');
            martsDataBlock.className = 'marts-data-block';
            
            if (!data) {
                // summary не нужен, так как кнопка уже существует в .message-actions
                martsDataBlock.innerHTML = '<details><div class="marts-data-container"><p>Нет данных для отображения</p></div></details>';
            } else {
                // Формируем HTML с красивым форматированием
                let html = '<details><div class="marts-data-container">';
                
                // Техника по станциям
                if (data.equipment && Object.keys(data.equipment).length > 0) {
                    html += '<div class="marts-section"><h3>🔧 Техника по станциям</h3>';
                    for (const [stationName, equipmentList] of Object.entries(data.equipment)) {
                        html += `<div class="station-block"><h4>📍 ${stationName}: ${equipmentList.length} единиц</h4><ul class="equipment-list">`;
                        for (const eq of equipmentList) {
                            html += `<li>${eq.equipment_name} — ${eq.quantity} шт.</li>`;
                        }
                        html += '</ul></div>';
                    }
                    html += '</div>';
                }
                
                // Сотрудники по станциям (только Должность-кол-во)
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
                martsDataBlock.innerHTML = html;
            }
            
            // Вставляем блок после контейнера кнопок
            container.insertAdjacentElement('afterend', martsDataBlock);
            
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

// Форматирование структурированного ответа (для режима плана)
export function formatStructuredMessage(text) {
    if (!text) return '';
    let formattedText = text;
    formattedText = formattedText.replace(/\xa0/g, ' ');

    const headers = [
        { regex: /Необходимая техника:/g, replacement: '<div class="section-title">Необходимая техника:</div>' },
        { regex: /Необходимые подразделения:/g, replacement: '<div class="section-title">Необходимые подразделения:</div>' },
        { regex: /Необходимые сотрудники:/g, replacement: '<div class="section-title">Необходимые сотрудники:</div>' },
        { regex: /План работ:/g, replacement: '<div class="section-title">План работ:</div>' }
    ];
    headers.forEach(header => {
        formattedText = formattedText.replace(header.regex, header.replacement);
    });

    formattedText = formattedText.replace(/\*\*(Этап \d+: [^*]+)\*\*/g, '<div class="stage-title">$1</div>');

    const subHeaders = [
        { regex: /- Подразделения:/g, replacement: '<br><strong>Подразделения:</strong> ' },
        { regex: /- Техника:/g, replacement: '<br><strong>Техника:</strong> ' },
        { regex: /- Сотрудники:/g, replacement: '<br><strong>Сотрудники:</strong> ' },
        { regex: /- Действия:/g, replacement: '<br><strong>Действия:</strong> ' },
        { regex: /- Пояснение:/g, replacement: '<br><strong>Пояснение:</strong> ' }
    ];
    subHeaders.forEach(sub => {
        formattedText = formattedText.replace(sub.regex, sub.replacement);
    });

    // Маркированные списки
    let lines = formattedText.split('\n');
    let inList = false;
    let listBuffer = [];
    let resultLines = [];
    for (let line of lines) {
        const trimmed = line.trim();
        if (trimmed.startsWith('- ') && !trimmed.match(/^-\s*(Подразделения|Техника|Сотрудники|Действия|Пояснение):/)) {
            if (!inList) {
                inList = true;
                listBuffer = ['<ul class="bullet-list">'];
            }
            listBuffer.push(`<li>${trimmed.substring(2)}</li>`);
        } else {
            if (inList) {
                listBuffer.push('</ul>');
                resultLines.push(listBuffer.join('\n'));
                inList = false;
                listBuffer = [];
            }
            resultLines.push(line);
        }
    }
    if (inList) {
        listBuffer.push('</ul>');
        resultLines.push(listBuffer.join('\n'));
    }
    formattedText = resultLines.join('\n');

    // Нумерованные списки
    lines = formattedText.split('\n');
    inList = false;
    listBuffer = [];
    resultLines = [];
    for (let line of lines) {
        const trimmed = line.trim();
        const match = trimmed.match(/^(\d+)\.\s+(.*)$/);
        if (match) {
            if (!inList) {
                inList = true;
                listBuffer = ['<ol class="numbered-list">'];
            }
            listBuffer.push(`<li value="${match[1]}">${match[2]}</li>`);
        } else {
            if (inList) {
                listBuffer.push('</ol>');
                resultLines.push(listBuffer.join('\n'));
                inList = false;
                listBuffer = [];
            }
            resultLines.push(line);
        }
    }
    if (inList) {
        listBuffer.push('</ol>');
        resultLines.push(listBuffer.join('\n'));
    }
    formattedText = resultLines.join('\n');

    return formattedText;
}

// Прокрутка контейнера сообщений вниз
export function scrollToBottom(container) {
    container.scrollTo({
        top: container.scrollHeight,
        behavior: 'smooth'
    });
}
// Приветственное сообщение
export function getWelcomeMessage(userName) {
    if (state.currentMode === 'plan') {
        return `
            <div class="welcome-message">
                <h3>Добро пожаловать, ${userName}!</h3>
                <p>Я помогу вам сформировать план действий при аварийных ситуациях на железной дороге.</p>
                <div class="mode-explanation">
                    <p><strong>Режим плана:</strong> подробный анализ с указанием подразделений, необходимой техники, сотрудников и пошагового плана работ.</p>
                </div>
                <p>Опишите ситуацию, и я составлю план.</p>
            </div>
        `;
    } else {
        return `
            <div class="welcome-message">
                <h3>Добро пожаловать, ${userName}!</h3>
                <p>Я — ваш помощник по вопросам железнодорожных аварий.</p>
                <div class="mode-explanation">
                    <p><strong>Чат-режим:</strong> быстрые ответы на вопросы с использованием истории диалога.</p> 
                </div>
                <p>Задайте вопрос, и я постараюсь помочь.</p>
            </div>
        `;
    }
}