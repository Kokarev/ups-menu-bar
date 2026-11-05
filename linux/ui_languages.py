"""Linux GUI strings. English keys are also the fallback catalog."""
import os

LANGUAGES = {'en': 'English', 'uk': 'Українська', 'de': 'Deutsch', 'ru': 'Русский'}
# Ukrainian, German, Russian; product names and NUT identifiers stay unchanged.
STRINGS = {
 'Mains': ('Електромережа', 'Stromnetz', 'Электросеть'),
 'Input': ('Вхід', 'Eingang', 'Вход'),
 'Output': ('Вихід', 'Ausgang', 'Выход'),
 'Frequency': ('Частота', 'Frequenz', 'Частота'),
 'Load': ('Навантаження', 'Auslastung', 'Нагрузка'),
 'Estimated power': ('Орієнтовна потужність', 'Geschätzte Leistung', 'Расчётная мощность'),
 'Battery': ('Акумулятор', 'Batterie', 'Аккумулятор'),
 'Voltage': ('Напруга', 'Spannung', 'Напряжение'),
 'Mode': ('Режим', 'Modus', 'Режим'),
 'No data': ('Немає даних', 'Keine Daten', 'Нет данных'),
 'Charge': ('Заряд', 'Ladezustand', 'Заряд'),
 'Runtime (NUT)': ('Час роботи (NUT)', 'Restlaufzeit (NUT)', 'Оставшееся время (NUT)'),
 'Power outages': ('Відключення мережі', 'Stromausfälle', 'Отключения сети'),
 'Last outage': ('Останнє відключення', 'Letzter Stromausfall', 'Последнее отключение'),
 'Not recorded': ('Не зафіксовано', 'Nicht erfasst', 'Не зафиксировано'),
 'Duration': ('Тривалість', 'Dauer', 'Продолжительность'),
 'Min. battery voltage': ('Мін. напруга АКБ', 'Min. Batteriespannung', 'Мин. напряжение АКБ'),
 'Voltage drop': ('Падіння напруги', 'Spannungsabfall', 'Падение напряжения'),
 'Event history is not available in this Linux preview.': ('Історія подій у цій Linux-версії ще недоступна.', 'Der Ereignisverlauf ist in dieser Linux-Vorschau noch nicht verfügbar.', 'История событий в этой Linux-версии пока недоступна.'),
 'Temperature': ('Температура', 'Temperatur', 'Температура'),
 'UPS': ('ДБЖ', 'USV', 'ИБП'),
 'Energy statistics': ('Статистика енергії', 'Energiestatistik', 'Статистика энергии'),
 'Today': ('Сьогодні', 'Heute', 'Сегодня'),
 'This month': ('Цього місяця', 'Diesen Monat', 'Этот месяц'),
 'Not calculated': ('Не обчислюється', 'Nicht berechnet', 'Не рассчитывается'),
 'Diagnostics': ('Діагностика', 'Diagnose', 'Диагностика'),
 'Disconnected': ('Відключено', 'Getrennt', 'Отключено'),
 'Connected': ('Підключено', 'Verbunden', 'Подключено'),
 'UPS status': ('Статус ДБЖ', 'USV-Status', 'Статус ИБП'),
 'Driver': ('Драйвер', 'Treiber', 'Драйвер'),
 'Last update': ('Останнє оновлення', 'Letzte Aktualisierung', 'Последнее обновление'),
 'Settings…': ('Налаштування…', 'Einstellungen…', 'Настройки…'),
 'Open CSV log': ('Відкрити журнал CSV', 'CSV-Protokoll öffnen', 'Открыть журнал CSV'),
 'Disconnect': ('Відключити', 'Trennen', 'Отключить'),
 'Quit': ('Вихід', 'Beenden', 'Выход'),
 'UPS Menu Bar Settings': ('Налаштування UPS Menu Bar', 'UPS Menu Bar Einstellungen', 'Настройки UPS Menu Bar'),
 'UPS Menu Bar · Linux preview': ('UPS Menu Bar · Linux-прототип', 'UPS Menu Bar · Linux-Vorschau', 'UPS Menu Bar · Linux-прототип'),
 'NUT server': ('Сервер NUT', 'NUT-Server', 'Сервер NUT'),
 'Port': ('Порт', 'Port', 'Порт'),
 'UPS name': ('Ім’я ДБЖ', 'USV-Name', 'Имя ИБП'),
 'Rated output power (W, optional)': ('Номінальна потужність (Вт, необов’язково)', 'Nennleistung (W, optional)', 'Номинальная мощность (Вт, необязательно)'),
 'Choose CSV…': ('Вибрати CSV…', 'CSV auswählen…', 'Выбрать CSV…'),
 'No CSV': ('Без CSV', 'Ohne CSV', 'Без CSV'),
 'Connect / Apply': ('Підключити / Застосувати', 'Verbinden / Anwenden', 'Подключить / Применить'),
 'Close': ('Закрити', 'Schließen', 'Закрыть'),
 'Language': ('Мова', 'Sprache', 'Язык'),
 'Not connected': ('Не підключено', 'Nicht verbunden', 'Не подключено'),
 'Connecting…': ('Підключення…', 'Verbindung wird hergestellt…', 'Подключение…'),
 'Waiting for current telemetry…': ('Очікування поточних показників…', 'Warte auf aktuelle Messwerte…', 'Ожидание текущих показателей…'),
 'Cannot start monitoring': ('Не вдалося запустити моніторинг', 'Überwachung kann nicht gestartet werden', 'Не удалось запустить мониторинг'),
 'No current data': ('Немає актуальних даних', 'Keine aktuellen Daten', 'Нет актуальных данных'),
 'Connection unavailable': ('Зв’язок недоступний', 'Verbindung nicht verfügbar', 'Связь недоступна'),
 'Low battery': ('Низький заряд', 'Batterie schwach', 'Низкий заряд'),
 'On battery': ('Від батареї', 'Batteriebetrieb', 'От батареи'),
 'Online': ('Від мережі', 'Netzbetrieb', 'От сети'),
 'Updated': ('Оновлено', 'Aktualisiert', 'Обновлено'),
 'Monitoring stopped. No UPS commands were sent.': ('Моніторинг зупинено. Команди ДБЖ не надсилалися.', 'Überwachung beendet. Keine USV-Befehle gesendet.', 'Мониторинг остановлен. Команды ИБП не отправлялись.'),
 'Enter your NUT server and UPS name to begin.': ('Вкажіть сервер NUT та ім’я ДБЖ у налаштуваннях.', 'NUT-Server und USV-Name in den Einstellungen eingeben.', 'Укажите сервер NUT и имя ИБП в настройках.'),
 'No CSV log selected. Choose a file in Settings and apply the connection.': ('Виберіть CSV у налаштуваннях і застосуйте підключення.', 'CSV-Datei in den Einstellungen auswählen und Verbindung anwenden.', 'Выберите CSV в настройках и примените подключение.'),
 'Choose a separate Linux CSV file': ('Виберіть окремий Linux-файл CSV', 'Separate Linux-CSV-Datei auswählen', 'Выберите отдельный Linux-файл CSV'),
 'No desktop file opener is installed. CSV: ': ('Не встановлено засіб відкриття файлів. CSV: ', 'Kein Programm zum Öffnen installiert. CSV: ', 'Не установлено средство открытия файлов. CSV: '),
 ' V': (' В', ' V', ' В'), ' W': (' Вт', ' W', ' Вт'),
 ' s': (' с', ' s', ' с'), ' Hz': (' Гц', ' Hz', ' Гц'),
}


def language_code(value=None):
    value = value or os.environ.get('LC_ALL') or os.environ.get('LC_MESSAGES') or os.environ.get('LANG', 'en')
    code = value.replace('-', '_').split('_')[0].split('.')[0].lower()
    return code if code in LANGUAGES else 'en'


def translate(text, language):
    if language == 'en' or text not in STRINGS:
        return text
    return STRINGS[text][{'uk': 0, 'de': 1, 'ru': 2}[language]]
