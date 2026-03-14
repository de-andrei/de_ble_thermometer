# DE BLE Thermometer

Интеграция для Home Assistant, добавляющая поддержку термометра Relsib WT50 через Bluetooth.

![Relsib WT50](custom_components/de_ble_thermometer/brand/icon.png)

## Поддерживаемые устройства

- **Модель:** WT50 (термометр)
- **Производитель:** Relsib
- **Bluetooth-сервис:** `00001809-0000-1000-8000-00805f9b34fb` (Health Thermometer)

## Возможности

- Автоматическое обнаружение термометра через Bluetooth
- Отображение температуры тела (°C)
- Отображение уровня заряда батареи
- Сенсор статуса подключения
- Кнопка "Stop Thermometer" для блокировки подключения на 3.5 минуты
- Автоматическое подключение при появлении устройства
- Сохранение последних показаний при отключении

## Установка

### Через HACS (рекомендуется)

1. Убедитесь, что у вас установлен [HACS](https://hacs.xyz/)
2. Откройте HACS в Home Assistant
3. Нажмите на три точки в правом верхнем углу
4. Выберите "Пользовательские репозитории"
5. Добавьте:
   - **URL:** `https://github.com/de-andrei/de_ble_thermometer`
   - **Категория:** `Integration`
6. Нажмите "Добавить"
7. Найдите "DE BLE Thermometer" в списке интеграций HACS
8. Нажмите "Скачать"
9. Перезапустите Home Assistant

### Ручная установка

1. Скачайте последний релиз из [репозитория](https://github.com/de-andrei/de_ble_thermometer/releases)
2. Распакуйте папку `custom_components/de_ble_thermometer` в директорию `config/custom_components/` вашего Home Assistant
3. Перезапустите Home Assistant

## Настройка

1. Перейдите в **Настройки** → **Устройства и службы**
2. Нажмите **"Добавить интеграцию"**
3. Найдите **"DE BLE Thermometer"** в списке
4. Выберите ваш термометр WT50 из списка обнаруженных устройств
5. Нажмите "Отправить"

## Сенсоры

После настройки будут созданы следующие сенсоры:

| Сущность | Имя | Описание |
|----------|-----|----------|
| `sensor.thermometer_body_temperature` | Body Temperature | Температура тела (°C) |
| `sensor.thermometer_battery` | Battery | Уровень заряда батареи (%) |
| `sensor.thermometer_connection_status` | Connection Status | Статус подключения (Connected/Disconnected/Blocked) |
| `button.thermometer_stop_thermometer` | Stop Thermometer | Кнопка блокировки на 3.5 минуты |