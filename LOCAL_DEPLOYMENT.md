# Локальный деплой bi-analytics

## Быстрый запуск

### Вариант 1: Использование bat-файла (Windows)
```bash
start_visualization_app.bat
```

### Вариант 2: Ручной запуск
```bash
cd bi-analytics
venv\Scripts\activate
streamlit run project_visualization_app.py
```

### Вариант 3: Прямой запуск без активации venv
```bash
cd bi-analytics
venv\Scripts\streamlit.exe run project_visualization_app.py
```

## Первоначальная настройка (если нужно)

Если виртуальное окружение не создано или зависимости не установлены:

1. **Создать виртуальное окружение:**
```bash
cd bi-analytics
python -m venv venv
```

2. **Активировать виртуальное окружение:**
```bash
# Windows PowerShell
venv\Scripts\Activate.ps1

# Windows CMD
venv\Scripts\activate.bat
```

3. **Установить зависимости:**
```bash
pip install -r requirements_visualization.txt
```

## Доступ к приложению

После запуска приложение будет доступно по адресу:
- **Локальный доступ:** http://localhost:8501
- **Сетевой доступ:** http://[ваш-ip]:8501

## Остановка приложения

Нажмите `Ctrl+C` в терминале, где запущено приложение.

## Примечания

- Приложение использует порт 8501 по умолчанию
- Если порт занят, Streamlit автоматически попробует следующий доступный порт
- Все необходимые зависимости уже установлены в виртуальном окружении

