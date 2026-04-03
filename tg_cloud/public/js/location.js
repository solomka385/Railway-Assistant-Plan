import { state, saveUserLocation } from './state.js';
import { showNotification, setInputState } from './ui.js';
import { API_BASE_URL } from './constants.js';

const locationModal = document.getElementById('locationModal');
const useDeviceLocation = document.getElementById('useDeviceLocation');
const useMapLocation = document.getElementById('useMapLocation');
const useManualLocation = document.getElementById('useManualLocation');
const mapContainer = document.getElementById('mapContainer');
const confirmMapLocation = document.getElementById('confirmMapLocation');
const locationStatus = document.getElementById('locationStatus');
const manualLocationContainer = document.getElementById('manualLocationContainer');
const latitudeInput = document.getElementById('latitudeInput');
const longitudeInput = document.getElementById('longitudeInput');
const confirmManualLocation = document.getElementById('confirmManualLocation');
const manualLocationError = document.getElementById('manualLocationError');

// Функция для скрытия всех блоков выбора геолокации
function hideAllLocationOptions() {
    mapContainer.style.display = 'none';
    manualLocationContainer.style.display = 'none';
    manualLocationError.style.display = 'none';
}

// Обновление индикатора в шапке
export function updateLocationIndicator() {
    // Обновляем индикатор в mode-switch
    const indicator = document.getElementById('locationIndicator');
    const locationText = document.getElementById('locationText');
    if (indicator && locationText) {
        if (state.currentMode === 'plan') {
            indicator.classList.remove('hidden');
            if (state.userLocation) {
                indicator.className = 'location-indicator active';
                locationText.textContent = `✅ ${state.userLocation.latitude.toFixed(4)}, ${state.userLocation.longitude.toFixed(4)}`;
                setInputState(false); // Разблокировать ввод
            } else {
                indicator.className = 'location-indicator inactive';
                locationText.textContent = '⚠️ Геолокация не установлена';
                setInputState(true); // Заблокировать ввод
            }
        } else {
            indicator.classList.add('hidden');
            setInputState(false); // В режиме чата всегда разблокировать
        }
    }
}

export function openLocationModal() {
    locationModal.style.display = 'block';
    locationStatus.textContent = '';
    locationStatus.className = 'location-status';
    mapContainer.style.display = 'none';
    manualLocationContainer.style.display = 'none';
    manualLocationError.style.display = 'none';
    latitudeInput.value = '';
    longitudeInput.value = '';
    latitudeInput.classList.remove('error');
    longitudeInput.classList.remove('error');
}

export function closeLocationModal() {
    locationModal.style.display = 'none';
    mapContainer.style.display = 'none';
    if (state.yandexMap) {
        state.yandexMap.destroy();
        state.yandexMap = null;
    }
}

export function useDeviceGPS() {
    hideAllLocationOptions();
    if (!navigator.geolocation) {
        showLocationStatus('error', 'Ваше устройство не поддерживает геолокацию');
        return;
    }
    showLocationStatus('info', 'Получение координат...');
    navigator.geolocation.getCurrentPosition(
        (position) => {
            saveUserLocation({
                latitude: position.coords.latitude,
                longitude: position.coords.longitude,
                source: 'device'
            });
            showLocationStatus('success', `✅ Координаты получены: ${state.userLocation.latitude.toFixed(4)}, ${state.userLocation.longitude.toFixed(4)}`);
            updateLocationIndicator();
            setTimeout(closeLocationModal, 1500);
        },
        (error) => {
            let errorMessage = 'Не удалось получить координаты';
            switch(error.code) {
                case error.PERMISSION_DENIED:
                    errorMessage = 'Доступ к геолокации запрещен. Разрешите доступ в настройках браузера';
                    break;
                case error.POSITION_UNAVAILABLE:
                    errorMessage = 'Информация о местоположении недоступна';
                    break;
                case error.TIMEOUT:
                    errorMessage = 'Время ожидания истекло';
                    break;
            }
            showLocationStatus('error', errorMessage);
        },
        { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 }
    );
}

export function initYandexMap() {
    mapContainer.style.display = 'block';
    
    // Очищаем контейнер карты перед инициализацией
    const mapElement = document.getElementById('map');
    if (mapElement) {
        mapElement.innerHTML = '';
    }
    
    // Если карта уже существует, уничтожаем её
    if (state.yandexMap) {
        state.yandexMap.destroy();
        state.yandexMap = null;
    }
    state.mapPlacemark = null;

    // Проверяем, загружена ли уже библиотека ymaps
    if (typeof ymaps === 'undefined') {
        console.error('Yandex Maps API не загружен');
        return;
    }

    ymaps.ready(() => {
        // Проверяем, не создана ли карта уже в этом вызове ready
        if (state.yandexMap) {
            return;
        }
        
        const centerCoords = state.userLocation ?
            [state.userLocation.latitude, state.userLocation.longitude] :
            [55.751244, 37.618423];
        state.yandexMap = new ymaps.Map('map', {
            center: centerCoords,
            zoom: 12,
            controls: ['zoomControl', 'searchControl', 'geolocationControl']
        });
        state.yandexMap.events.add('click', (e) => {
            const coords = e.get('coords');
            if (state.mapPlacemark) {
                state.yandexMap.geoObjects.remove(state.mapPlacemark);
            }
            state.mapPlacemark = new ymaps.Placemark(coords, {
                balloonContent: `Координаты: ${coords[0].toFixed(4)}, ${coords[1].toFixed(4)}`
            }, { preset: 'islands#redDotIcon', draggable: true });
            state.yandexMap.geoObjects.add(state.mapPlacemark);
            state.userLocation = {
                latitude: coords[0],
                longitude: coords[1],
                source: 'map',
                temporary: true
            };
            showLocationStatus('info', `Выбрано: ${coords[0].toFixed(4)}, ${coords[1].toFixed(4)}`);
        });
        if (state.userLocation && !state.userLocation.temporary) {
            state.mapPlacemark = new ymaps.Placemark(
                [state.userLocation.latitude, state.userLocation.longitude],
                { balloonContent: 'Текущее местоположение' },
                { preset: 'islands#greenDotIcon', draggable: true }
            );
            state.yandexMap.geoObjects.add(state.mapPlacemark);
        }
    });
}

export function confirmMapSelection() {
    if (!state.userLocation || !state.userLocation.temporary) {
        showLocationStatus('error', 'Выберите точку на карте');
        return;
    }
    hideAllLocationOptions();
    const locationToSave = {
        latitude: state.userLocation.latitude,
        longitude: state.userLocation.longitude,
        source: 'map'
    };
    saveUserLocation(locationToSave);
    showLocationStatus('success', `✅ Местоположение сохранено: ${state.userLocation.latitude.toFixed(4)}, ${state.userLocation.longitude.toFixed(4)}`);
    updateLocationIndicator();
    setTimeout(closeLocationModal, 1500);
}

function showLocationStatus(type, message) {
    locationStatus.className = `location-status ${type}`;
    locationStatus.textContent = message;
}

export function showLocationRequiredNotification() {
    const notification = document.createElement('div');
    notification.className = 'location-notification';
    notification.innerHTML = `
        <div class="notification-content">
            <span class="notification-icon">⚠️</span>
            <span class="notification-text">Для отправки сообщения в режиме плана необходимо указать местоположение</span>
            <button class="notification-btn" id="notificationSetLocation">Указать сейчас</button>
        </div>
    `;
    document.body.appendChild(notification);
    setTimeout(() => notification.classList.add('show'), 10);
    document.getElementById('notificationSetLocation').addEventListener('click', () => {
        notification.remove();
        openLocationModal();
    });
    setTimeout(() => {
        notification.classList.remove('show');
        setTimeout(() => notification.remove(), 300);
    }, 5000);
}

// Обработчик кнопки ручного ввода координат
if (useManualLocation) {
    useManualLocation.addEventListener('click', () => {
        hideAllLocationOptions();
        manualLocationContainer.style.display = 'block';
        manualLocationError.style.display = 'none';
        latitudeInput.classList.remove('error');
        longitudeInput.classList.remove('error');
        latitudeInput.focus();
    });
}

// Обработчик кнопки выбора на карте
if (useMapLocation) {
    useMapLocation.addEventListener('click', () => {
        hideAllLocationOptions();
        initYandexMap();
    });
}

// Обработчик нажатия Enter в полях ввода координат
if (latitudeInput) {
    latitudeInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            longitudeInput.focus();
            e.preventDefault();
        }
    });
}

if (longitudeInput) {
    longitudeInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            confirmManualLocation.click();
            e.preventDefault();
        }
    });
}

// Обработчик подтверждения ручных координат
if (confirmManualLocation) {
    confirmManualLocation.addEventListener('click', () => {
        const latitude = parseFloat(latitudeInput.value);
        const longitude = parseFloat(longitudeInput.value);
        
        // Валидация координат
        const latitudeError = validateCoordinate(latitude, 'Широта', -90, 90);
        const longitudeError = validateCoordinate(longitude, 'Долгота', -180, 180);
        
        if (latitudeError || longitudeError) {
            let errorMessage = '';
            if (latitudeError) errorMessage += latitudeError + '. ';
            if (longitudeError) errorMessage += longitudeError;
            manualLocationError.textContent = errorMessage;
            manualLocationError.style.display = 'block';
            if (latitudeError) latitudeInput.classList.add('error');
            if (longitudeError) longitudeInput.classList.add('error');
            return;
        }
        
        // Успешная валидация
        hideAllLocationOptions();
        state.userLocation = {
            latitude: latitude,
            longitude: longitude,
            source: 'manual'
        };
        manualLocationError.style.display = 'none';
        latitudeInput.classList.remove('error');
        longitudeInput.classList.remove('error');
        showLocationStatus('success', `✅ Координаты введены: ${latitude.toFixed(4)}, ${longitude.toFixed(4)}`);
        updateLocationIndicator();
        setTimeout(closeLocationModal, 1500);
    });
}

// Функция валидации координаты
function validateCoordinate(value, name, min, max) {
    if (isNaN(value)) {
        return `${name} не указана`;
    }
    if (value < min || value > max) {
        return `${name} должна быть в диапазоне от ${min} до ${max}`;
    }
    return null;
}