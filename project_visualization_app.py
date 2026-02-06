import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np
import csv
from auth import (
    check_authentication,
    get_current_user,
    has_admin_access,
    has_report_access,
    get_user_role_display,
    logout,
    init_db,
    render_sidebar_menu,
    authenticate,
    generate_reset_token,
    reset_password,
    verify_reset_token,
    get_user_by_username,
)

# Russian month names mapping
RUSSIAN_MONTHS = {
    1: "Январь",
    2: "Февраль",
    3: "Март",
    4: "Апрель",
    5: "Май",
    6: "Июнь",
    7: "Июль",
    8: "Август",
    9: "Сентябрь",
    10: "Октябрь",
    11: "Ноябрь",
    12: "Декабрь",
}


def apply_default_filters(
    report_name: str, user_role: str, filter_widgets: dict
) -> dict:
    """
    Применение фильтров по умолчанию для отчета и роли

    Args:
        report_name: Название отчета
        user_role: Роль пользователя
        filter_widgets: Словарь с виджетами фильтров {filter_key: widget_value}

    Returns:
        Словарь с примененными фильтрами
    """
    try:
        from filters import get_default_filters

        default_filters = get_default_filters(user_role, report_name)

        # Применяем фильтры по умолчанию, если они заданы и виджет еще не имеет значения
        for filter_key, default_value in default_filters.items():
            if filter_key in filter_widgets and filter_widgets[filter_key] is None:
                filter_widgets[filter_key] = default_value
            elif filter_key not in filter_widgets:
                filter_widgets[filter_key] = default_value
    except ImportError:
        # Если модуль filters недоступен, просто возвращаем исходные виджеты
        pass

    return filter_widgets


def get_report_param_value(report_name: str, parameter_key: str, default=None):
    """
    Получение значения параметра отчета

    Args:
        report_name: Название отчета
        parameter_key: Ключ параметра
        default: Значение по умолчанию

    Returns:
        Значение параметра или default
    """
    try:
        from report_params import get_report_parameter

        param = get_report_parameter(report_name, parameter_key)
        if param and param.get("value") is not None:
            return param["value"]
    except ImportError:
        # Если модуль report_params недоступен, возвращаем значение по умолчанию
        pass

    return default


# Функция для применения стандартного фона к графикам
def apply_chart_background(fig):
    """Применяет стандартный фон #12385C ко всем графикам"""
    # Убираем все дефолтные темы и устанавливаем фон - делаем это в одном вызове
    fig.update_layout(
        template=None,  # Убираем дефолтные темы plotly
        plot_bgcolor="#12385C",  # Фон области графика
        paper_bgcolor="#12385C",  # Фон вокруг графика
        font=dict(color="#ffffff"),
        legend=dict(font=dict(color="#ffffff")),
        margin=dict(b=150, l=50, r=50, t=50),  # Увеличиваем нижний отступ для подписей оси X
    )
    # Обновляем оси - сетка и линии (для всех осей, включая вторичные)
    # Используем overwrite=True чтобы перезаписать все настройки
    fig.update_xaxes(
        gridcolor="rgba(255, 255, 255, 0.1)",
        linecolor="rgba(255, 255, 255, 0.3)",
        tickfont=dict(color="#ffffff", size=8),  # Уменьшаем размер шрифта для лучшей видимости
        title=dict(font=dict(color="#ffffff")),
        zerolinecolor="rgba(255, 255, 255, 0.3)",
        automargin=True,  # Автоматически увеличиваем отступы для предотвращения обрезания текста
        # Не устанавливаем tickangle по умолчанию, чтобы не перезаписывать существующие настройки
    )
    fig.update_yaxes(
        gridcolor="rgba(255, 255, 255, 0.1)",
        linecolor="rgba(255, 255, 255, 0.3)",
        tickfont=dict(color="#ffffff"),
        title=dict(font=dict(color="#ffffff")),
        zerolinecolor="rgba(255, 255, 255, 0.3)",
        overwrite=True,
    )
    # Принудительно устанавливаем фон еще раз в конце, чтобы перезаписать любые дефолтные значения
    # Используем прямое обращение к layout для гарантии
    fig.layout.plot_bgcolor = "#12385C"
    fig.layout.paper_bgcolor = "#12385C"

    # Настраиваем автоматические отступы для предотвращения обрезания текста на оси X
    # Проверяем существующие настройки margin и увеличиваем нижний отступ
    current_margin = fig.layout.margin if hasattr(fig.layout, 'margin') and fig.layout.margin else None
    if current_margin:
        # Если margin уже установлен, увеличиваем только нижний отступ
        if hasattr(current_margin, 'b'):
            # Увеличиваем нижний отступ до 150-200 пикселей для повернутых подписей
            new_bottom = max(current_margin.b if current_margin.b else 50, 150)
        else:
            new_bottom = 150
        # Сохраняем остальные отступы
        new_margin = dict(
            l=current_margin.l if hasattr(current_margin, 'l') and current_margin.l else 50,
            r=current_margin.r if hasattr(current_margin, 'r') and current_margin.r else 50,
            t=current_margin.t if hasattr(current_margin, 't') and current_margin.t else 50,
            b=new_bottom,
        )
        fig.update_layout(margin=new_margin)
    else:
        # Если margin не установлен, устанавливаем минимальные отступы с увеличенным нижним
        fig.update_layout(
            autosize=True,
            margin=dict(l=50, r=50, t=50, b=150),  # Увеличиваем нижний отступ для оси X с повернутыми подписями
        )

    return fig


def get_russian_month_name(period_val):
    """Get Russian month name from Period object"""
    if isinstance(period_val, pd.Period):
        # For monthly periods, get month number
        if period_val.freqstr == "M" or period_val.freqstr.startswith("M"):
            month_num = period_val.month
            return RUSSIAN_MONTHS.get(month_num, period_val.strftime("%B"))
        # For other periods, try to extract month if possible
        try:
            month_num = period_val.month
            return RUSSIAN_MONTHS.get(month_num, "")
        except:
            return ""
    elif isinstance(period_val, (int, pd.Timestamp)):
        month_num = period_val.month if hasattr(period_val, "month") else period_val
        return RUSSIAN_MONTHS.get(month_num, "")
    elif isinstance(period_val, str):
        # Try to parse string like "2025-01" or "2025-01-01"
        try:
            if "-" in period_val:
                parts = period_val.split("-")
                if len(parts) >= 2:
                    month_num = int(parts[1])
                    return RUSSIAN_MONTHS.get(month_num, "")
        except:
            pass
    return ""


def format_dataframe_as_html(df, conditional_cols=None, column_colors=None):
    """
    Форматирует DataFrame как HTML таблицу с единым стилем.

    Args:
        df: DataFrame для форматирования
        conditional_cols: Словарь {column_name: {'positive_color': '#ff4444', 'negative_color': '#44ff44'}}
                         для условного форматирования колонок
        column_colors: Словарь {column_name: 'color'} для установки цвета текста для колонок

    Returns:
        HTML строка с таблицей
    """
    import html as html_module

    if df is None or df.empty:
        return "<p>Нет данных для отображения</p>"

    html_table = "<table style='width:100%; border-collapse: collapse; background-color: #12385C; color: #ffffff;'>"

    # Header row
    html_table += "<thead><tr>"
    for col in df.columns:
        col_escaped = html_module.escape(str(col))
        html_table += f"<th style='border: 1px solid #ffffff; padding: 8px; background-color: rgba(18, 56, 92, 0.95);'>{col_escaped}</th>"
    html_table += "</tr></thead>"

    # Data rows
    html_table += "<tbody>"
    for idx, row in df.iterrows():
        html_table += "<tr>"
        for col in df.columns:
            value = row[col]

            # Check if this column needs conditional formatting
            if conditional_cols and col in conditional_cols:
                cond_config = conditional_cols[col]
                positive_color = cond_config.get('positive_color', '#ff4444')
                negative_color = cond_config.get('negative_color', '#44ff44')

                # Conditional formatting: red if positive, green if negative or zero
                if pd.notna(value) and isinstance(value, (int, float)):
                    if value > 0:
                        color = positive_color
                    else:
                        color = negative_color
                    formatted_value = f"{value:.2f}" if isinstance(value, float) else f"{int(value)}"
                    html_table += f"<td style='border: 1px solid #ffffff; padding: 8px; color: {color}; font-weight: bold;'>{formatted_value}</td>"
                else:
                    formatted_value = str(value) if pd.notna(value) else "0"
                    # Escape HTML special characters
                    formatted_value = html_module.escape(str(formatted_value))
                    html_table += f"<td style='border: 1px solid #ffffff; padding: 8px; color: {negative_color}; font-weight: bold;'>{formatted_value}</td>"
            else:
                # Regular formatting
                if isinstance(value, (int, float)) and pd.notna(value):
                    # Check if column name contains "млн руб." - always format as float with 2 decimals
                    if "млн руб" in str(col).lower():
                        formatted_value = f"{float(value):.2f}"
                    # Format numbers appropriately
                    elif isinstance(value, float) and (value % 1 != 0 or abs(value) < 1):
                        formatted_value = f"{value:.2f}"
                    else:
                        formatted_value = f"{int(value)}"
                else:
                    # For strings (including pre-formatted numbers), use as-is
                    formatted_value = str(value) if pd.notna(value) else ""
                    # Escape HTML special characters but preserve emojis and basic formatting
                    formatted_value = html_module.escape(str(formatted_value))

                # Check if this column has a specific color
                cell_style = "border: 1px solid #ffffff; padding: 8px;"
                if column_colors and col in column_colors:
                    cell_style += f" color: {column_colors[col]};"

                html_table += f"<td style='{cell_style}'>{formatted_value}</td>"
        html_table += "</tr>"
    html_table += "</tbody></table>"

    return html_table


# Инициализация базы данных
init_db()

# Page configuration (должно быть первым)
st.set_page_config(
    page_title="Панель аналитики проектов",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={"Get Help": None, "Report a bug": None, "About": None},
)

# Файлы с префиксом _ уже скрыты из меню автоматически Streamlit
# Дополнительная попытка скрыть через st.navigation (может быть недоступно в версии 1.52.1)
# Удаляем этот вызов, так как он может вызывать ошибки

# Custom CSS for better styling (dark theme)
st.markdown(
    """
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        margin-bottom: 1rem;
    }
    .metric-card {
        background-color: #262730;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    /* Force dark theme */
    .stApp {
        background-color: #12385C;
    }

    /* Стилизация хедера Streamlit - фон цвета основного фона */
    header[data-testid="stHeader"],
    .stHeader,
    header,
    div[data-testid="stHeader"],
    .stHeader > div,
    header > div,
    div[data-testid="stHeader"] > div {
        background-color: #12385C !important;
        border-bottom: 1px solid rgba(255, 255, 255, 0.1) !important;
    }

    /* Текст в хедере */
    header[data-testid="stHeader"] *,
    .stHeader *,
    header *,
    div[data-testid="stHeader"] * {
        color: #ffffff !important;
    }

    /* Основной контент - белый текст на темном фоне */
    .main .block-container,
    .main .element-container,
    .main h1, .main h2, .main h3, .main h4, .main h5, .main h6,
    .main p, .main span, .main div,
    .main label {
        color: #ffffff !important;
    }

    /* Контейнеры с контентом - темный фон */
    .main .block-container {
        background-color: rgba(18, 56, 92, 0.8) !important;
    }

    /* Стилизация полей ввода - подсветка для видимости на темном фоне */
    .stTextInput > div > div > input,
    .stTextInput > div > div > input:focus,
    input[type="text"],
    input[type="password"],
    input[type="email"],
    input[type="number"],
    textarea {
        background-color: #2a2a3a !important;
        color: #ffffff !important;
        border: 1px solid #4a5568 !important;
        border-radius: 4px !important;
        padding: 0.5rem !important;
    }
    .stTextInput > div > div > input:focus,
    input[type="text"]:focus,
    input[type="password"]:focus,
    input[type="email"]:focus,
    input[type="number"]:focus,
    textarea:focus {
        border-color: #1f77b4 !important;
        box-shadow: 0 0 0 2px rgba(31, 119, 180, 0.2) !important;
        outline: none !important;
    }

    /* Стилизация кнопок - фон цвета основного фона, белый текст */
    .stButton > button {
        background-color: #12385C !important;
        color: #ffffff !important;
        border: 1px solid rgba(255, 255, 255, 0.3) !important;
        border-radius: 4px !important;
        padding: 0.5rem 1rem !important;
        font-weight: 500 !important;
        transition: all 0.2s ease !important;
    }
    .stButton > button:hover {
        background-color: rgba(18, 56, 92, 0.9) !important;
        border-color: rgba(255, 255, 255, 0.5) !important;
        color: #ffffff !important;
    }
    .stButton > button:focus {
        border-color: #1f77b4 !important;
        box-shadow: 0 0 0 2px rgba(31, 119, 180, 0.2) !important;
        outline: none !important;
    }
    /* Кнопки primary - фон цвета основного фона с более яркой окантовкой */
    .stButton > button[kind="primary"] {
        background-color: #12385C !important;
        color: #ffffff !important;
        border: 1px solid #1f77b4 !important;
    }
    .stButton > button[kind="primary"]:hover {
        background-color: rgba(18, 56, 92, 0.9) !important;
        border-color: #2a8bc4 !important;
        color: #ffffff !important;
    }
    /* Отключенные кнопки */
    .stButton > button:disabled {
        background-color: rgba(18, 56, 92, 0.6) !important;
        color: #666666 !important;
        border-color: rgba(255, 255, 255, 0.2) !important;
        opacity: 0.6 !important;
    }
    /* Стилизация selectbox */
    .stSelectbox > div > div > select {
        background-color: #2a2a3a !important;
        color: #ffffff !important;
        border: 1px solid #4a5568 !important;
        border-radius: 4px !important;
    }
    .stSelectbox > div > div > select:focus {
        border-color: #1f77b4 !important;
        box-shadow: 0 0 0 2px rgba(31, 119, 180, 0.2) !important;
        outline: none !important;
    }
    /* Стилизация checkbox */
    .stCheckbox > label {
        color: #ffffff !important;
    }
    /* Стилизация date input */
    .stDateInput > div > div > input {
        background-color: #2a2a3a !important;
        color: #ffffff !important;
        border: 1px solid #4a5568 !important;
    }
    /* Стилизация number input */
    .stNumberInput > div > div > input {
        background-color: #2a2a3a !important;
        color: #ffffff !important;
        border: 1px solid #4a5568 !important;
        border-radius: 4px !important;
    }
    .stNumberInput > div > div > input:focus {
        border-color: #1f77b4 !important;
        box-shadow: 0 0 0 2px rgba(31, 119, 180, 0.2) !important;
        outline: none !important;
    }
    /* Стилизация multiselect */
    .stMultiSelect > div > div {
        background-color: #2a2a3a !important;
        color: #ffffff !important;
        border: 1px solid #4a5568 !important;
    }
    /* Стилизация file uploader */
    .stFileUploader > div {
        background-color: #2a2a3a !important;
        border: 1px solid #4a5568 !important;
        border-radius: 4px !important;
    }

    /* Стилизация sidebar (бокового меню) - фон цвета основного фона */
    .stSidebar,
    [data-testid="stSidebar"],
    section[data-testid="stSidebar"],
    div[data-testid="stSidebar"],
    .stSidebar > div,
    [data-testid="stSidebar"] > div,
    section[data-testid="stSidebar"] > div,
    div[data-testid="stSidebar"] > div {
        background-color: #12385C !important;
    }

    /* Разделитель между sidebar и основной областью - отступ 30px от границы кнопок */
    .stSidebar,
    [data-testid="stSidebar"],
    section[data-testid="stSidebar"],
    div[data-testid="stSidebar"] {
        border-right: 1px solid rgba(255, 255, 255, 0.3) !important;
        padding-right: 30px !important;
    }

    /* Текст в sidebar - белый */
    .stSidebar *,
    [data-testid="stSidebar"] *,
    section[data-testid="stSidebar"] *,
    div[data-testid="stSidebar"] * {
        color: #ffffff !important;
    }

    /* Стилизация таблиц (dataframes) - фон цвета основного фона с белым текстом и границами */
    /* Базовые контейнеры */
    .stDataFrame,
    div[data-testid="stDataFrame"],
    .dataframe {
        background-color: #12385C !important;
    }

    /* Вложенные div элементы */
    .stDataFrame > div,
    div[data-testid="stDataFrame"] > div,
    .dataframe > div,
    .stDataFrame div,
    div[data-testid="stDataFrame"] div,
    .dataframe div {
        background-color: #12385C !important;
    }

    /* Таблицы - белый текст и белые границы */
    .stDataFrame table,
    div[data-testid="stDataFrame"] table,
    .dataframe table {
        background-color: #12385C !important;
        border-collapse: collapse !important;
        border: 1px solid #ffffff !important;
        color: #ffffff !important;
    }

    /* Заголовки таблиц */
    .stDataFrame thead,
    div[data-testid="stDataFrame"] thead,
    .dataframe thead {
        background-color: rgba(18, 56, 92, 0.95) !important;
    }

    /* Тела таблиц */
    .stDataFrame tbody,
    div[data-testid="stDataFrame"] tbody,
    .dataframe tbody {
        background-color: #12385C !important;
    }

    /* Строки таблиц */
    .stDataFrame tr,
    div[data-testid="stDataFrame"] tr,
    .dataframe tr {
        background-color: #12385C !important;
        border-bottom: 1px solid #ffffff !important;
    }

    /* Заголовки ячеек - белый текст, белые границы */
    .stDataFrame th,
    div[data-testid="stDataFrame"] th,
    .dataframe th {
        background-color: rgba(18, 56, 92, 0.95) !important;
        color: #ffffff !important;
        border: 1px solid #ffffff !important;
        border-right: 1px solid #ffffff !important;
        border-bottom: 1px solid #ffffff !important;
        border-left: 1px solid #ffffff !important;
        border-top: 1px solid #ffffff !important;
        padding: 8px !important;
        font-weight: bold !important;
    }

    /* Ячейки таблиц - белый текст, белые границы */
    .stDataFrame td,
    div[data-testid="stDataFrame"] td,
    .dataframe td {
        background-color: rgba(18, 56, 92, 0.85) !important;
        color: #ffffff !important;
        border: 1px solid #ffffff !important;
        border-right: 1px solid #ffffff !important;
        border-bottom: 1px solid #ffffff !important;
        border-left: 1px solid #ffffff !important;
        border-top: 1px solid #ffffff !important;
        padding: 8px !important;
    }

    /* Четные строки */
    .stDataFrame tbody tr:nth-child(even),
    div[data-testid="stDataFrame"] tbody tr:nth-child(even),
    .dataframe tbody tr:nth-child(even) {
        background-color: rgba(18, 56, 92, 0.7) !important;
    }

    .stDataFrame tbody tr:nth-child(even) td,
    div[data-testid="stDataFrame"] tbody tr:nth-child(even) td,
    .dataframe tbody tr:nth-child(even) td {
        background-color: rgba(18, 56, 92, 0.7) !important;
        color: #ffffff !important;
        border: 1px solid #ffffff !important;
        border-right: 1px solid #ffffff !important;
        border-bottom: 1px solid #ffffff !important;
        border-left: 1px solid #ffffff !important;
        border-top: 1px solid #ffffff !important;
    }

    /* При наведении */
    .stDataFrame tbody tr:hover,
    div[data-testid="stDataFrame"] tbody tr:hover,
    .dataframe tbody tr:hover {
        background-color: rgba(18, 56, 92, 1) !important;
    }

    .stDataFrame tbody tr:hover td,
    div[data-testid="stDataFrame"] tbody tr:hover td,
    .dataframe tbody tr:hover td {
        background-color: rgba(18, 56, 92, 1) !important;
        color: #ffffff !important;
        border: 1px solid #ffffff !important;
        border-right: 1px solid #ffffff !important;
        border-bottom: 1px solid #ffffff !important;
        border-left: 1px solid #ffffff !important;
        border-top: 1px solid #ffffff !important;
    }

    /* Текст в таблицах - принудительно белый для всех элементов */
    /* ВАЖНО: Убираем универсальный селектор * чтобы не влиять на stDataEditor */
    .stDataFrame,
    div[data-testid="stDataFrame"],
    .dataframe {
        color: #ffffff !important;
    }

    /* КРИТИЧНО: Явно устанавливаем белый цвет для stDataEditor с максимальной специфичностью */
    div[data-testid="stDataEditor"],
    div[data-testid="stDataEditor"] table,
    div[data-testid="stDataEditor"] table td,
    div[data-testid="stDataEditor"] table th,
    div[data-testid="stDataEditor"] td,
    div[data-testid="stDataEditor"] th,
    div[data-testid="stDataEditor"] td span,
    div[data-testid="stDataEditor"] td div,
    div[data-testid="stDataEditor"] td p,
    div[data-testid="stDataEditor"] th span,
    div[data-testid="stDataEditor"] th div,
    div[data-testid="stDataEditor"] th p {
        color: #ffffff !important;
    }

    /* Специфичные селекторы для текста в ячейках - переопределяем все возможные стили Streamlit */
    .stDataFrame td,
    .stDataFrame th,
    div[data-testid="stDataFrame"] td,
    div[data-testid="stDataFrame"] th {
        color: #ffffff !important;
    }

    /* Вложенные элементы в ячейках - белый текст */
    /* ВАЖНО: Применяем только к конкретным элементам, не используем универсальный * */
    .stDataFrame td span,
    .stDataFrame th span,
    div[data-testid="stDataFrame"] td span,
    div[data-testid="stDataFrame"] th span,
    .stDataFrame td div,
    .stDataFrame th div,
    div[data-testid="stDataFrame"] td div,
    div[data-testid="stDataFrame"] th div,
    .stDataFrame td p,
    .stDataFrame th p,
    div[data-testid="stDataFrame"] td p,
    div[data-testid="stDataFrame"] th p,
    .stDataFrame td strong,
    .stDataFrame th strong,
    div[data-testid="stDataFrame"] td strong,
    div[data-testid="stDataFrame"] th strong {
        color: #ffffff !important;
    }

    /* КРИТИЧНО: Явно устанавливаем белый цвет для stDataEditor с максимальной специфичностью */
    /* Эти правила должны переопределить все глобальные стили */
    div[data-testid="stDataEditor"] td span,
    div[data-testid="stDataEditor"] td div,
    div[data-testid="stDataEditor"] td p,
    div[data-testid="stDataEditor"] th span,
    div[data-testid="stDataEditor"] th div,
    div[data-testid="stDataEditor"] th p {
        color: #ffffff !important;
    }

    /* КРИТИЧНО: Переопределяем ВСЕ глобальные стили для stDataEditor с максимальной специфичностью */
    /* Эти правила должны идти ПОСЛЕ глобальных, чтобы переопределить их */
    div[data-testid="stDataEditor"],
    div[data-testid="stDataEditor"] * {
        color: #ffffff !important;
    }

    div[data-testid="stDataEditor"] table,
    div[data-testid="stDataEditor"] table * {
        color: #ffffff !important;
        background-color: #12385C !important;
    }

    div[data-testid="stDataEditor"] thead th,
    div[data-testid="stDataEditor"] tbody td {
        color: #ffffff !important;
    }

    div[data-testid="stDataEditor"] td *,
    div[data-testid="stDataEditor"] th *,
    div[data-testid="stDataEditor"] td span,
    div[data-testid="stDataEditor"] td div,
    div[data-testid="stDataEditor"] td p,
    div[data-testid="stDataEditor"] td label {
        color: #ffffff !important;
    }

    /* Поля ввода в stDataEditor */
    div[data-testid="stDataEditor"] input,
    div[data-testid="stDataEditor"] select {
        color: #ffffff !important;
        background-color: rgba(18, 56, 92, 0.9) !important;
        border: 1px solid #ffffff !important;
    }
    </style>
""",
    unsafe_allow_html=True,
)


def detect_data_type(df, file_name=None):
    """Detect the type of data based on column structure and filename"""
    columns = [str(col).lower() for col in df.columns]
    file_name_lower = str(file_name).lower() if file_name else ""

    # Check for project data (has task name, plan start/end, budget plan)
    if (
        any(col in columns for col in ["задача", "task name"])
        and any(col in columns for col in ["старт план", "plan start"])
        and any(col in columns for col in ["бюджет план", "budget plan"])
    ):
        return "project"

    # Check for resources/technique data (has Контрагент/Подразделение, недели, План)
    # Check for contractor column (Контрагент or Подразделение)
    has_contractor = any(
        col in columns for col in ["контрагент", "подразделение", "contractor"]
    )
    # Check for week columns
    has_weeks = any(
        col in columns for col in ["1 неделя", "2 неделя", "3 неделя"]
    ) or any("неделя" in col for col in columns)
    # Check for plan column (План, План на месяц, etc.)
    has_plan = any(col in columns for col in ["план", "план на месяц", "plan"])
    # Check for delta column (Дельта, Отклонение)
    has_delta = any(
        col in columns for col in ["дельта", "отклонение", "deviation", "delta"]
    )

    if has_contractor and has_weeks and (has_plan or has_delta):
        # Check filename first for better accuracy
        if "ресурс" in file_name_lower or "resource" in file_name_lower:
            return "resources"
        elif "техник" in file_name_lower or "technique" in file_name_lower:
            return "technique"
        # If filename doesn't help, check column names more carefully
        elif "ресурс" in " ".join(columns) or "resource" in " ".join(columns):
            return "resources"
        elif "техник" in " ".join(columns) or "technique" in " ".join(columns):
            return "technique"
        # Check for "Среднее за неделю" (resources) vs "Среднее за месяц" (technique)
        elif any("среднее за неделю" in col for col in columns):
            return "resources"
        elif any("среднее за месяц" in col for col in columns):
            return "technique"
        else:
            # Default to resources if we can't determine (most common case)
            return "resources"

    # Default to project if we can't determine
    return "project"


def load_data(uploaded_file, file_name=None):
    """Load data from uploaded file and return DataFrame with metadata"""
    try:
        original_name = file_name if file_name else uploaded_file.name
        if uploaded_file.name.endswith(".csv"):
            # Try different encodings and delimiters
            # Priority: UTF-8 first (most common), then UTF-8 with BOM, then Windows encodings
            encodings = ["utf-8", "utf-8-sig", "windows-1251", "cp1251"]
            df = None
            for encoding in encodings:
                try:
                    # First try with semicolon delimiter (common in European CSV files)
                    uploaded_file.seek(0)  # Reset file pointer
                    df = pd.read_csv(
                        uploaded_file,
                        sep=";",
                        encoding=encoding,
                        quoting=csv.QUOTE_MINIMAL,
                        quotechar='"',
                        doublequote=True,
                    )
                    break
                except (UnicodeDecodeError, pd.errors.ParserError) as e:
                    try:
                        # If semicolon fails, try comma delimiter
                        uploaded_file.seek(0)  # Reset file pointer
                        df = pd.read_csv(
                            uploaded_file,
                            sep=",",
                            encoding=encoding,
                            quoting=csv.QUOTE_MINIMAL,
                            quotechar='"',
                            doublequote=True,
                        )
                        break
                    except (UnicodeDecodeError, pd.errors.ParserError):
                        continue
            if df is None:
                # Last resort: try with UTF-8 and default settings
                uploaded_file.seek(0)  # Reset file pointer
                try:
                    df = pd.read_csv(uploaded_file, encoding="utf-8")
                except:
                    uploaded_file.seek(0)  # Reset file pointer
                    df = pd.read_csv(uploaded_file)
        elif uploaded_file.name.endswith((".xlsx", ".xls")):
            df = pd.read_excel(uploaded_file)
        else:
            st.error("Неподдерживаемый формат файла. Загрузите CSV или Excel файл.")
            return None

        # Normalize column names: remove newlines and extra spaces from column names
        # This handles cases where CSV headers are split across multiple lines
        df.columns = [
            str(col).replace("\n", " ").replace("\r", " ").strip() for col in df.columns
        ]

        # Normalize column names: map Russian column names to English standard names
        # This allows the code to work with both English and Russian column names
        column_mapping = {
            "Проект": "project name",
            "Аббревиатура": "abbreviation",
            "Блок": "block",
            "Раздел": "section",
            "Задача": "task name",
            "Старт Факт": "base start",
            "Конец Факт": "base end",
            "Старт План": "plan start",
            "Конец План": "plan end",
            "Отклонение": "deviation",
            "Отклонений в днях": "deviation in days",
            "Причина отклонений": "reason of deviation",
            "Бюджет План": "budget plan",
            "Бюджет Факт": "budget fact",
            "Резерв": "reserve",
        }

        # Create aliases for Russian column names if they exist and English names don't
        for russian_name, english_name in column_mapping.items():
            if russian_name in df.columns and english_name not in df.columns:
                df[english_name] = df[russian_name]

        # Convert date columns - handle DD.MM.YYYY format
        date_columns = ["base start", "base end", "plan start", "plan end"]
        for col in date_columns:
            if col in df.columns:
                # Convert to string first if needed, then parse
                if df[col].dtype == "object":
                    # Try parsing with dayfirst=True for DD.MM.YYYY format
                    df[col] = pd.to_datetime(
                        df[col], errors="coerce", dayfirst=True, format="mixed"
                    )
                else:
                    df[col] = pd.to_datetime(df[col], errors="coerce", dayfirst=True)

        # Add time period columns for grouping from all date fields
        # Extract day, month, quarter, year from plan dates
        for date_col, prefix in [
            ("plan start", "plan_start"),
            ("plan end", "plan"),
            ("base start", "base_start"),
            ("base end", "base"),
        ]:
            if date_col in df.columns:
                mask = df[date_col].notna()
                if mask.any():
                    # Day level
                    df.loc[mask, f"{prefix}_day"] = df.loc[mask, date_col].dt.date
                    # Month level
                    df.loc[mask, f"{prefix}_month"] = df.loc[
                        mask, date_col
                    ].dt.to_period("M")
                    # Quarter level
                    df.loc[mask, f"{prefix}_quarter"] = df.loc[
                        mask, date_col
                    ].dt.to_period("Q")
                    # Year level
                    df.loc[mask, f"{prefix}_year"] = df.loc[
                        mask, date_col
                    ].dt.to_period("Y")

        # Also create plan_month, plan_quarter, plan_year for backward compatibility
        if "plan end" in df.columns:
            mask = df["plan end"].notna()
            if mask.any():
                df.loc[mask, "plan_month"] = df.loc[mask, "plan end"].dt.to_period("M")
                df.loc[mask, "plan_quarter"] = df.loc[mask, "plan end"].dt.to_period(
                    "Q"
                )
                df.loc[mask, "plan_year"] = df.loc[mask, "plan end"].dt.to_period("Y")

        if "base end" in df.columns:
            mask = df["base end"].notna()
            if mask.any():
                df.loc[mask, "actual_month"] = df.loc[mask, "base end"].dt.to_period(
                    "M"
                )
                df.loc[mask, "actual_quarter"] = df.loc[mask, "base end"].dt.to_period(
                    "Q"
                )
                df.loc[mask, "actual_year"] = df.loc[mask, "base end"].dt.to_period("Y")

        # Detect data type and add metadata
        data_type = detect_data_type(df, original_name)

        # Store metadata in DataFrame attributes
        df.attrs["data_type"] = data_type
        df.attrs["file_name"] = original_name

        return df
    except Exception as e:
        st.error(f"Ошибка загрузки файла: {str(e)}")
        return None


# ==================== DASHBOARD 1: Reasons of Deviation ====================
def dashboard_reasons_of_deviation(df):
    # Проверка на None или пустой DataFrame
    if df is None:
        st.warning(
            "⚠️ Нет данных для отображения. Пожалуйста, загрузите данные проекта."
        )
        return

    # Проверка, что df является DataFrame и имеет атрибут columns
    if not hasattr(df, "columns") or df.empty:
        st.warning(
            "⚠️ Нет данных для отображения. Пожалуйста, загрузите данные проекта."
        )
        return

    st.header("📋 Причины отклонений по месяцам")

    # Add CSS to force filters in one row
    st.markdown(
        """
        <style>
        div[data-testid="column"] {
            flex: 1 1 0%;
            min-width: 0;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Helper function to format months
    def format_month(period_val):
        if pd.isna(period_val):
            return "Н/Д"
        if isinstance(period_val, pd.Period):
            try:
                month_name = get_russian_month_name(period_val)
                year = period_val.year
                return f"{month_name} {year}"
            except:
                return str(period_val)
        return str(period_val)

    # All filters in one row - use compact layout (только проект, этап и месяц)
    col1, col2, col3 = st.columns(3)

    with col1:
        try:
            has_project_column = "project name" in df.columns
        except (AttributeError, TypeError):
            has_project_column = False

        if has_project_column:
            projects = ["Все"] + sorted(df["project name"].dropna().unique().tolist())
            selected_project = st.selectbox("Проект", projects, key="reason_project")
        else:
            selected_project = "Все"

    with col2:
        try:
            has_section_column = "section" in df.columns
        except (AttributeError, TypeError):
            has_section_column = False

        if has_section_column:
            sections = ["Все"] + sorted(df["section"].dropna().unique().tolist())
            selected_section = st.selectbox("Фильтр по этапу", sections, key="reason_section")
        else:
            selected_section = "Все"

    with col3:
        available_months = []
        try:
            has_plan_month_column = "plan_month" in df.columns
        except (AttributeError, TypeError):
            has_plan_month_column = False

        if has_plan_month_column:
            unique_months = df["plan_month"].dropna().unique()
            if len(unique_months) > 0:
                month_dict = {format_month(m): m for m in unique_months}
                available_months = sorted(
                    month_dict.keys(), key=lambda x: month_dict[x]
                )
        else:
            try:
                has_plan_end_column = "plan end" in df.columns
            except (AttributeError, TypeError):
                has_plan_end_column = False

            if has_plan_end_column:
                mask = df["plan end"].notna()
                if mask.any():
                    temp_months = df.loc[mask, "plan end"].dt.to_period("M").unique()
                    if len(temp_months) > 0:
                        month_dict = {format_month(m): m for m in temp_months}
                        available_months = sorted(
                            month_dict.keys(), key=lambda x: month_dict[x]
                        )

        if len(available_months) > 0:
            months = ["Все"] + available_months
            selected_month = st.selectbox("Месяц", months, key="reason_month")
        else:
            selected_month = "Все"
            st.selectbox("Месяц", ["Все"], key="reason_month", disabled=True)

    # Apply filters - только проект, этап и месяц
    filtered_df = df.copy()

    try:
        has_project_col = "project name" in filtered_df.columns
    except (AttributeError, TypeError):
        has_project_col = False

    if selected_project != "Все" and has_project_col:
        filtered_df = filtered_df[
            filtered_df["project name"].astype(str).str.strip()
            == str(selected_project).strip()
        ]

    try:
        has_section_col = "section" in filtered_df.columns
    except (AttributeError, TypeError):
        has_section_col = False

    if selected_section != "Все" and has_section_col:
        filtered_df = filtered_df[
            filtered_df["section"].astype(str).str.strip()
            == str(selected_section).strip()
        ]

    try:
        has_plan_month_col = "plan_month" in filtered_df.columns
    except (AttributeError, TypeError):
        has_plan_month_col = False

    if selected_month != "Все" and has_plan_month_col:
        # Convert selected month back to Period format for comparison
        def month_to_period(month_str):
            try:
                # Parse "Январь 2025" format (Russian month names)
                parts = month_str.split()
                if len(parts) == 2:
                    month_name, year = parts
                    # Find month number from Russian month name
                    month_num = None
                    for num, russian_name in RUSSIAN_MONTHS.items():
                        if russian_name == month_name:
                            month_num = num
                            break
                    if month_num:
                        return pd.Period(f"{year}-{month_num:02d}", freq="M")
            except:
                pass
            return None

        selected_period = month_to_period(selected_month)
        if selected_period is not None:
            filtered_df = filtered_df[filtered_df["plan_month"] == selected_period]
        else:
            # Fallback: try to match formatted string
            def format_month_for_comparison(period_val):
                if isinstance(period_val, pd.Period):
                    try:
                        month_name = get_russian_month_name(period_val)
                        year = period_val.year
                        return f"{month_name} {year}"
                    except:
                        pass
                return str(period_val)

            filtered_df = filtered_df[
                filtered_df["plan_month"].apply(format_month_for_comparison)
                == selected_month
            ]

    # Filter only tasks with deviations - check for deviation = 1 or True
    try:
        has_deviation_col = "deviation" in filtered_df.columns
    except (AttributeError, TypeError):
        has_deviation_col = False

    if has_deviation_col:
        # Handle different deviation formats: True, 1, 'True', '1', etc.
        deviation_mask = (
            (filtered_df["deviation"] == True)
            | (filtered_df["deviation"] == 1)
            | (filtered_df["deviation"].astype(str).str.lower() == "true")
            | (filtered_df["deviation"].astype(str).str.strip() == "1")
        )
        filtered_df = filtered_df[deviation_mask]

    # Filter out negative deviation days - only show positive or zero deviations
    try:
        has_deviation_days_col = "deviation in days" in filtered_df.columns
    except (AttributeError, TypeError):
        has_deviation_days_col = False

    if has_deviation_days_col:
        # Convert to numeric and filter out negative values
        filtered_df["deviation in days"] = pd.to_numeric(
            filtered_df["deviation in days"], errors="coerce"
        )
        # Keep only positive or zero values (>= 0)
        filtered_df = filtered_df[
            (filtered_df["deviation in days"] >= 0) | (filtered_df["deviation in days"].isna())
        ]

    if filtered_df.empty:
        st.info("Нет данных для выбранных фильтров.")
        return

    # Summary metrics - основная причина отклонения, процент и количество
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Всего задач с отклонениями", len(filtered_df))

    with col2:
        try:
            has_reason_col_metric = "reason of deviation" in filtered_df.columns
        except (AttributeError, TypeError):
            has_reason_col_metric = False

        if has_reason_col_metric and not filtered_df.empty:
            # Находим основную причину отклонения
            reason_counts = filtered_df["reason of deviation"].value_counts()
            if len(reason_counts) > 0:
                main_reason = reason_counts.index[0]
                main_reason_count = reason_counts.iloc[0]
                total_count = len(filtered_df)
                main_reason_percent = (main_reason_count / total_count * 100) if total_count > 0 else 0
                st.metric(
                    "Основная причина отклонения",
                    f"{main_reason}",
                    help=f"Процент: {main_reason_percent:.1f}%, Количество: {main_reason_count}"
                )
            else:
                st.metric("Основная причина отклонения", "Н/Д")
        else:
            st.metric("Основная причина отклонения", "Н/Д")

    with col3:
        try:
            has_reason_col_metric = "reason of deviation" in filtered_df.columns
        except (AttributeError, TypeError):
            has_reason_col_metric = False

        if has_reason_col_metric and not filtered_df.empty:
            # Процент и количество основной причины
            reason_counts = filtered_df["reason of deviation"].value_counts()
            if len(reason_counts) > 0:
                main_reason_count = reason_counts.iloc[0]
                total_count = len(filtered_df)
                main_reason_percent = (main_reason_count / total_count * 100) if total_count > 0 else 0
                st.metric(
                    "Процент / Количество",
                    f"{main_reason_percent:.1f}% / {main_reason_count}",
                )
            else:
                st.metric("Процент / Количество", "Н/Д")
        else:
            st.metric("Процент / Количество", "Н/Д")

    # Reasons breakdown
    try:
        has_reason_col_breakdown = "reason of deviation" in filtered_df.columns
    except (AttributeError, TypeError):
        has_reason_col_breakdown = False

    if has_reason_col_breakdown:
        st.subheader("Распределение по причинам")
        reason_counts = filtered_df["reason of deviation"].value_counts().reset_index()
        reason_counts.columns = ["Причина", "Количество"]

        col1, col2 = st.columns(2)

        with col1:
            fig = px.bar(
                reason_counts,
                x="Причина",
                y="Количество",
                title="Количество отклонений по причинам",
                labels={
                    "Причина": "Причина отклонения",
                    "Количество": "Количество отклонений",
                },
                text="Количество",
                template=None,  # Убираем дефолтный template
            )
            fig.update_xaxes(tickangle=-75, tickfont=dict(size=8), automargin=True)
            # Отображаем значения внутри столбцов
            fig.update_traces(
                textposition="inside", textfont=dict(size=14, color="white")
            )
            fig = apply_chart_background(fig)
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            fig = px.pie(
                reason_counts,
                values="Количество",
                names="Причина",
                title="Распределение отклонений по причинам",
            )
            fig.update_traces(
                texttemplate="%{label}<br>%{value}<br>(%{percent:.0%})",
                textposition="auto",
            )
            fig = apply_chart_background(fig)
            st.plotly_chart(fig, use_container_width=True)

    # Detailed table
    with st.expander("📊 Просмотр детальных данных"):
        display_cols = [
            "project name",
            "task name",
            "section",
            "deviation in days",
            "reason of deviation",
        ]

        try:
            has_plan_end_col = "plan end" in filtered_df.columns
        except (AttributeError, TypeError):
            has_plan_end_col = False

        if has_plan_end_col:
            display_cols.insert(-1, "plan end")

        try:
            has_base_end_col = "base end" in filtered_df.columns
        except (AttributeError, TypeError):
            has_base_end_col = False

        if has_base_end_col:
            display_cols.insert(-1, "base end")

        available_cols = [col for col in display_cols if col in filtered_df.columns]
        # Rename columns to Russian before display
        filtered_df_display = filtered_df[available_cols].rename(columns={
            "project name": "Проект",
            "task name": "Задача",
            "section": "Этап",
            "block": "Блок",
            "plan end": "План окончания",
            "base end": "Базовое окончание",
            "deviation in days": "Отклонение (дней)",
            "reason of deviation": "Причина отклонения"
        })
        html_table = format_dataframe_as_html(filtered_df_display)
        st.markdown(html_table, unsafe_allow_html=True)


# ==================== DASHBOARD 2: Dynamics of Deviations ====================
def dashboard_dynamics_of_deviations(df):
    st.header("📈 Причины отклонений (по видам причин)")

    col1, col2, col3 = st.columns(3)

    with col1:
        period_type = st.selectbox(
            "Группировать по",
            ["День", "Месяц", "Квартал", "Год"],
            key="dynamics_period",
        )
        period_map = {
            "День": "Day",
            "Месяц": "Month",
            "Квартал": "Quarter",
            "Год": "Year",
        }
        period_type_en = period_map.get(period_type, "Month")

    with col2:
        if "project name" in df.columns:
            projects = ["Все"] + sorted(df["project name"].dropna().unique().tolist())
            selected_project = st.selectbox(
                "Фильтр по проекту", projects, key="dynamics_project"
            )
        else:
            selected_project = "Все"

    with col3:
        if "reason of deviation" in df.columns:
            reasons = ["Все"] + sorted(
                df["reason of deviation"].dropna().unique().tolist()
            )
            selected_reason = st.selectbox(
                "Фильтр по причине", reasons, key="dynamics_reason"
            )
        else:
            selected_reason = "Все"

    # Apply filters
    filtered_df = df.copy()
    if selected_project != "Все" and "project name" in filtered_df.columns:
        filtered_df = filtered_df[
            filtered_df["project name"].astype(str).str.strip()
            == str(selected_project).strip()
        ]
    if selected_reason != "Все" and "reason of deviation" in df.columns:
        filtered_df = filtered_df[
            filtered_df["reason of deviation"].astype(str).str.strip()
            == str(selected_reason).strip()
        ]

    # Filter only tasks with deviations - check for deviation = 1 or True
    if "deviation" in filtered_df.columns:
        deviation_mask = (
            (filtered_df["deviation"] == True)
            | (filtered_df["deviation"] == 1)
            | (filtered_df["deviation"].astype(str).str.lower() == "true")
            | (filtered_df["deviation"].astype(str).str.strip() == "1")
        )
        filtered_df = filtered_df[deviation_mask]

    if filtered_df.empty:
        st.info("Нет данных для выбранных фильтров.")
        return

    # Extract period from plan end dates
    if period_type_en == "Day":
        # Use date (day level)
        if "plan end" in filtered_df.columns:
            mask = filtered_df["plan end"].notna()
            filtered_df.loc[mask, "period"] = filtered_df.loc[mask, "plan end"].dt.date
            period_label = "День"
        else:
            st.warning("Поле 'plan end' не найдено для группировки по дням.")
            return
    elif period_type_en == "Month":
        if "plan end" in filtered_df.columns:
            mask = filtered_df["plan end"].notna()
            filtered_df.loc[mask, "period"] = filtered_df.loc[
                mask, "plan end"
            ].dt.to_period("M")
            period_label = "Месяц"
        else:
            st.warning("Поле 'plan end' не найдено для группировки по месяцам.")
            return
    elif period_type_en == "Quarter":
        if "plan end" in filtered_df.columns:
            mask = filtered_df["plan end"].notna()
            filtered_df.loc[mask, "period"] = filtered_df.loc[
                mask, "plan end"
            ].dt.to_period("Q")
            period_label = "Квартал"
        else:
            st.warning("Поле 'plan end' не найдено для группировки по кварталам.")
            return
    else:  # Year
        if "plan end" in filtered_df.columns:
            mask = filtered_df["plan end"].notna()
            filtered_df.loc[mask, "period"] = filtered_df.loc[
                mask, "plan end"
            ].dt.to_period("Y")
            period_label = "Год"
        else:
            st.warning("Поле 'plan end' не найдено для группировки по годам.")
            return

    # Filter out rows without period data
    filtered_df = filtered_df[filtered_df["period"].notna()]

    if filtered_df.empty:
        st.info("Нет данных с указанными периодами.")
        return

    # Convert deviation in days to numeric and filter out negative values
    if "deviation in days" in filtered_df.columns:
        filtered_df["deviation in days"] = pd.to_numeric(
            filtered_df["deviation in days"], errors="coerce"
        )
        # Filter out negative deviation days - only show positive or zero deviations
        filtered_df = filtered_df[
            (filtered_df["deviation in days"] >= 0) | (filtered_df["deviation in days"].isna())
        ]

    # Group by project, period, and reason - count deviation days
    # Always include columns if they exist in original data to ensure consistent graph structure
    # The filtering will be applied to the data, but grouping structure remains stable
    group_cols = ["period"]
    has_project_col = "project name" in df.columns
    has_reason_col = "reason of deviation" in df.columns

    if has_project_col:
        group_cols.append("project name")
    if has_reason_col:
        group_cols.append("reason of deviation")

    # Aggregate: count tasks and sum deviation days
    # For average: sum deviation days / number of tasks (grouped by project if project is in group)
    agg_dict = {"deviation": "count"}  # Count tasks
    if "deviation in days" in filtered_df.columns:
        agg_dict["deviation in days"] = "sum"  # Sum deviation days

    grouped_data = filtered_df.groupby(group_cols).agg(agg_dict).reset_index()

    # Ensure period column is preserved as Period type if possible
    # After groupby, Period objects might be converted, so we need to handle this
    if "period" in grouped_data.columns:
        # Try to preserve Period type or convert back if needed
        try:
            # Check if period values are still Period objects
            if isinstance(grouped_data["period"].iloc[0], pd.Period):
                # Period objects are preserved, good
                pass
            else:
                # Try to convert back to Period if they're strings
                try:
                    # Try to convert string representations back to Period
                    def try_convert_to_period(val):
                        if isinstance(val, pd.Period):
                            return val
                        if isinstance(val, str) and "-" in val:
                            try:
                                parts = val.split("-")
                                if len(parts) >= 2:
                                    year = int(parts[0])
                                    month = int(parts[1])
                                    return pd.Period(f"{year}-{month:02d}", freq="M")
                            except:
                                pass
                        return val

                    grouped_data["period"] = grouped_data["period"].apply(
                        try_convert_to_period
                    )
                except:
                    pass
        except:
            pass

    # Calculate average: sum of deviation days / number of tasks
    if "deviation in days" in filtered_df.columns:
        # Rename columns
        if "deviation in days" in grouped_data.columns:
            grouped_data = grouped_data.rename(
                columns={
                    "deviation": "Количество задач",
                    "deviation in days": "Всего дней отклонений",
                }
            )
        else:
            grouped_data = grouped_data.rename(
                columns={"deviation": "Количество задач"}
            )
            grouped_data["Всего дней отклонений"] = 0

        # Calculate average: sum / count of tasks
        grouped_data["Среднее дней отклонений"] = (
            grouped_data["Всего дней отклонений"] / grouped_data["Количество задач"]
        ).round(2)
    else:
        grouped_data = grouped_data.rename(columns={"deviation": "Количество задач"})
        grouped_data["Всего дней отклонений"] = 0
        grouped_data["Среднее дней отклонений"] = 0

    # Format period for display - convert to readable format
    def format_period(period_val):
        if pd.isna(period_val):
            return "Н/Д"

        # Try to convert to Period if it's a string representation
        period_obj = None
        if isinstance(period_val, pd.Period):
            period_obj = period_val
        elif isinstance(period_val, str):
            # Try to parse string like "2025-01" or "2025-01-01"
            try:
                if "-" in period_val:
                    parts = period_val.split("-")
                    if len(parts) >= 2:
                        year = int(parts[0])
                        month = int(parts[1])
                        # Try to create Period object
                        try:
                            period_obj = pd.Period(f"{year}-{month:02d}", freq="M")
                        except:
                            # If that fails, try to parse as date and convert
                            try:
                                date_obj = pd.to_datetime(period_val)
                                period_obj = date_obj.to_period("M")
                            except:
                                pass
            except:
                pass

        # If we have a Period object, format it
        if period_obj is not None:
            try:
                if period_obj.freqstr == "M" or period_obj.freqstr.startswith(
                    "M"
                ):  # Month
                    month_name = get_russian_month_name(period_obj)
                    year = period_obj.year
                    if month_name:
                        return f"{month_name} {year}"
                elif period_obj.freqstr == "Q" or period_obj.freqstr.startswith(
                    "Q"
                ):  # Quarter
                    return f"Q{period_obj.quarter} {period_obj.year}"
                elif period_obj.freqstr == "Y" or period_obj.freqstr == "A-DEC":  # Year
                    return str(period_obj.year)
                else:
                    month_name = get_russian_month_name(period_obj)
                    year = period_obj.year
                    if month_name:
                        return f"{month_name} {year}"
            except:
                pass

        # If it's still a Period object (original), try direct formatting
        if isinstance(period_val, pd.Period):
            try:
                if period_val.freqstr == "M" or period_val.freqstr.startswith(
                    "M"
                ):  # Month
                    month_name = get_russian_month_name(period_val)
                    year = period_val.year
                    if month_name:
                        return f"{month_name} {year}"
                elif period_val.freqstr == "Q" or period_val.freqstr.startswith(
                    "Q"
                ):  # Quarter
                    return f"Q{period_val.quarter} {period_val.year}"
                elif period_val.freqstr == "Y" or period_val.freqstr == "A-DEC":  # Year
                    return str(period_val.year)
            except:
                pass

        # Try parsing as string
        period_str = str(period_val)
        try:
            if "-" in period_str:
                parts = period_str.split("-")
                if len(parts) >= 2:
                    year = parts[0]
                    month = parts[1]
                    # Remove any extra characters
                    month = month.split()[0] if " " in month else month
                    try:
                        month_num = int(month)
                        month_name = RUSSIAN_MONTHS.get(month_num, "")
                        if month_name:
                            return f"{month_name} {year}"
                    except:
                        pass
        except:
            pass

        # If it's a date, format it
        try:
            if isinstance(period_val, (pd.Timestamp, datetime)):
                return period_val.strftime("%d.%m.%Y")
        except:
            pass

        return period_str

    grouped_data["period"] = grouped_data["period"].apply(format_period)

    # Visualizations
    if len(group_cols) == 1:  # Only period
        col1, col2 = st.columns(2)

        with col1:
            fig = px.bar(
                grouped_data,
                x="period",
                y="Количество задач",
                title=f"Количество задач с отклонениями по {period_label.lower()}",
                labels={"period": period_label, "Количество задач": "Количество задач"},
                text="Количество задач",
            )
            fig.update_xaxes(tickangle=-75, tickfont=dict(size=8), automargin=True)
            fig.update_traces(
                textposition="outside", textfont=dict(size=14, color="white")
            )
            fig = apply_chart_background(fig)
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            # Показываем количество отклонений вместо дней
            fig = px.bar(
                grouped_data,
                x="period",
                y="Количество задач",
                title=f"Количество отклонений по {period_label.lower()}",
                labels={"period": period_label, "Количество задач": "Количество отклонений"},
                text="Количество задач",
            )
            fig.update_xaxes(tickangle=-75, tickfont=dict(size=8), automargin=True)
            fig.update_traces(
                textposition="outside", textfont=dict(size=14, color="white")
            )
            fig = apply_chart_background(fig)
            st.plotly_chart(fig, use_container_width=True)
    else:  # Grouped by project and/or reason
        # Show by project if project column exists in grouped data and has data
        if has_project_col and "project name" in grouped_data.columns and not grouped_data["project name"].isna().all():
            st.subheader("По проектам")
            # If reason is also in group_cols, aggregate by period and project only (sum across reasons)
            if has_reason_col and "reason of deviation" in grouped_data.columns:
                project_data = (
                    grouped_data.groupby(["period", "project name"])
                    .agg({"Всего дней отклонений": "sum", "Количество задач": "sum"})
                    .reset_index()
                )
            else:
                project_data = grouped_data

            if not project_data.empty:
                fig = px.bar(
                    project_data,
                    x="period",
                    y="Количество задач",
                    color="project name",
                    title="Количество отклонений по периоду",
                    labels={"period": "", "Количество задач": "Количество отклонений"},
                    text="Количество задач",
                )
                # Set barmode to 'group' to group bars by period
                fig.update_layout(barmode="group")
                fig.update_xaxes(tickangle=-75, title_text="", tickfont=dict(size=8), automargin=True)
                # Update traces to ensure horizontal text orientation
                fig.update_traces(
                    textposition="outside", textfont=dict(size=14, color="white")
                )
                # Explicitly set textangle to 0 for all traces to ensure horizontal text
                # In Plotly, textangle is set per trace
                for i, trace in enumerate(fig.data):
                    # Update trace with textangle=0 to ensure horizontal text
                    fig.data[i].update(textangle=0)
                fig = apply_chart_background(fig)
                fig = apply_chart_background(fig)
                st.plotly_chart(fig, use_container_width=True)

        # Show by reason if reason column exists in grouped data and has data
        if has_reason_col and "reason of deviation" in grouped_data.columns and not grouped_data["reason of deviation"].isna().all():
            st.subheader("По причинам")
            # Агрегируем данные по периоду и причинам (один столбец за месяц с секторами по причинам)
            if "project name" in group_cols:
                # Сначала суммируем по проектам и причинам, затем по периодам
                reason_data = (
                    grouped_data.groupby(["period", "reason of deviation"])
                    .agg({"Всего дней отклонений": "sum", "Количество задач": "sum"})
                    .reset_index()
                )
            else:
                reason_data = grouped_data

            fig = px.bar(
                reason_data,
                x="period",
                y="Количество задач",
                color="reason of deviation",
                title="Количество отклонений по периоду и причинам",
                labels={"period": "", "Количество задач": "Количество отклонений"},
                text="Количество задач",
            )
            # Используем накопление (stack) для отображения секторов причин в одном столбце
            fig.update_layout(barmode="stack")
            fig.update_xaxes(tickangle=-75, title_text="", tickfont=dict(size=8), automargin=True)
            # Показываем значения внутри столбцов
            fig.update_traces(
                textposition="inside", textfont=dict(size=12, color="white")
            )
            # Explicitly set textangle to 0 for all traces to ensure horizontal text
            # In Plotly, textangle is set per trace
            for i, trace in enumerate(fig.data):
                # Update trace with textangle=0 to ensure horizontal text
                fig.data[i].update(textangle=0)
            fig = apply_chart_background(fig)

            fig = apply_chart_background(fig)
            st.plotly_chart(fig, use_container_width=True)

    # Summary table
    # If project is in group, show summary grouped by project overall (aggregate across all periods)
    if "project name" in group_cols:
        # Create project-level summary (aggregate across all periods, not by day/period)
        project_summary_cols = ["project name"]
        if "reason of deviation" in group_cols:
            project_summary_cols.append("reason of deviation")

        # Получаем доступные периоды из grouped_data для фильтра
        available_periods = []
        if "period" in grouped_data.columns:
            available_periods = sorted(
                grouped_data["period"].dropna().unique().tolist()
            )

        st.subheader("Сводная таблица")

        # Добавляем селекторы для фильтрации таблицы
        filter_cols = st.columns(3)
        filtered_df_for_summary = filtered_df.copy()

        with filter_cols[0]:
            if "project name" in filtered_df_for_summary.columns:
                available_projects = ["Все"] + sorted(
                    filtered_df_for_summary["project name"].dropna().unique().tolist()
                )
                selected_project_filter = st.selectbox(
                    "Фильтр по проекту",
                    available_projects,
                    key="summary_project_filter",
                )
                if selected_project_filter != "Все":
                    filtered_df_for_summary = filtered_df_for_summary[
                        filtered_df_for_summary["project name"]
                        == selected_project_filter
                    ]

        with filter_cols[1]:
            if "reason of deviation" in filtered_df_for_summary.columns:
                available_reasons = ["Все"] + sorted(
                    filtered_df_for_summary["reason of deviation"]
                    .dropna()
                    .unique()
                    .tolist()
                )
                selected_reason_filter = st.selectbox(
                    "Фильтр по причине отклонения",
                    available_reasons,
                    key="summary_reason_filter",
                )
                if selected_reason_filter != "Все":
                    filtered_df_for_summary = filtered_df_for_summary[
                        filtered_df_for_summary["reason of deviation"]
                        == selected_reason_filter
                    ]

        with filter_cols[2]:
            # Фильтр по периоду
            period_options = ["Весь период"] + available_periods
            selected_period_filter = st.selectbox(
                "Фильтр по периоду", period_options, key="summary_period_filter"
            )

            # Применяем фильтр по периоду
            if (
                selected_period_filter != "Весь период"
                and "period" in filtered_df_for_summary.columns
            ):
                # Фильтруем по отформатированному периоду
                if "plan end" in filtered_df_for_summary.columns:
                    # Создаем временную колонку с отформатированными периодами для фильтрации
                    filtered_df_for_summary = filtered_df_for_summary.copy()
                    mask = filtered_df_for_summary["plan end"].notna()
                    if period_type_en == "Month":
                        filtered_df_for_summary.loc[mask, "temp_period"] = (
                            filtered_df_for_summary.loc[mask, "plan end"].dt.to_period(
                                "M"
                            )
                        )
                    elif period_type_en == "Quarter":
                        filtered_df_for_summary.loc[mask, "temp_period"] = (
                            filtered_df_for_summary.loc[mask, "plan end"].dt.to_period(
                                "Q"
                            )
                        )
                    elif period_type_en == "Year":
                        filtered_df_for_summary.loc[mask, "temp_period"] = (
                            filtered_df_for_summary.loc[mask, "plan end"].dt.to_period(
                                "Y"
                            )
                        )
                    else:
                        filtered_df_for_summary.loc[mask, "temp_period"] = (
                            filtered_df_for_summary.loc[mask, "plan end"].dt.date
                        )

                    # Форматируем периоды для сравнения
                    filtered_df_for_summary.loc[mask, "temp_period_formatted"] = (
                        filtered_df_for_summary.loc[mask, "temp_period"].apply(
                            format_period
                        )
                    )
                    # Фильтруем по выбранному периоду
                    period_mask = (
                        filtered_df_for_summary["temp_period_formatted"]
                        == selected_period_filter
                    )
                    filtered_df_for_summary = filtered_df_for_summary[period_mask]
                    # Удаляем временные колонки
                    filtered_df_for_summary = filtered_df_for_summary.drop(
                        columns=["temp_period", "temp_period_formatted"],
                        errors="ignore",
                    )

        # Aggregate by project (and reason if present) - sum across selected periods
        project_summary = (
            filtered_df_for_summary.groupby(project_summary_cols)
            .agg(
                {
                    "deviation": "count",  # Count tasks
                    "deviation in days": (
                        "sum"
                        if "deviation in days" in filtered_df_for_summary.columns
                        else "count"
                    ),
                }
            )
            .reset_index()
        )

        # Rename columns
        period_col_name = (
            f"Дни отклонений ({selected_period_filter})"
            if selected_period_filter != "Весь период"
            else "Всего дней отклонений"
        )
        project_summary = project_summary.rename(
            columns={
                "deviation": "Количество отклонений",
                "deviation in days": period_col_name,
            }
        )

        # Если нет данных по дням отклонений, добавляем нулевую колонку
        if period_col_name not in project_summary.columns:
            project_summary[period_col_name] = 0

        # Sort by total deviation days (descending)
        if period_col_name in project_summary.columns:
            project_summary = project_summary.sort_values(
                period_col_name, ascending=False
            )

        # Добавляем строку "Итого"
        total_row = {}
        for col in project_summary.columns:
            if col in project_summary_cols:
                total_row[col] = "Итого"
            elif col == "Количество отклонений":
                total_row[col] = int(project_summary[col].sum())
            elif col == period_col_name:
                total_row[col] = int(project_summary[col].sum())
            else:
                total_row[col] = ""

        # Создаем DataFrame для строки "Итого"
        total_df = pd.DataFrame([total_row])
        # Объединяем с основным DataFrame
        project_summary = pd.concat([project_summary, total_df], ignore_index=True)

        # Rename columns to Russian before display
        project_summary_display = project_summary.rename(columns={
            "project name": "Проект",
            "reason of deviation": "Причина отклонения",
            "period": "Период"
        })
        # Apply conditional formatting: positive values in red, negative/zero in green
        conditional_cols = {}
        # Add conditional formatting for numeric columns that can be negative
        for col in project_summary_display.columns:
            if col not in ["Проект", "Причина отклонения", "Период", "Итого"]:
                # Check if column contains numeric values
                if col in project_summary_display.columns:
                    try:
                        # Try to convert to numeric to check if it's a number column
                        numeric_values = pd.to_numeric(project_summary_display[col], errors='coerce')
                        if not numeric_values.isna().all():
                            conditional_cols[col] = {
                                "positive_color": "#ff4444",  # Red for positive
                                "negative_color": "#44ff44"   # Green for negative/zero
                            }
                    except:
                        pass
        html_table = format_dataframe_as_html(project_summary_display, conditional_cols=conditional_cols)
        st.markdown(html_table, unsafe_allow_html=True)
    else:
        # No project in group, show regular summary by period
        group_desc = [period_label] + [c for c in group_cols if c != "period"]
        st.subheader("Сводная таблица")
        # Rename columns to Russian before display
        grouped_data_display = grouped_data.rename(columns={
            "period": "Период",
            "project name": "Проект",
            "reason of deviation": "Причина отклонения"
        })
        # Apply conditional formatting: positive values in red, negative/zero in green
        conditional_cols = {}
        # Add conditional formatting for numeric columns that can be negative
        for col in grouped_data_display.columns:
            if col not in ["Период", "Проект", "Причина отклонения"]:
                # Check if column contains numeric values
                if col in grouped_data_display.columns:
                    try:
                        # Try to convert to numeric to check if it's a number column
                        numeric_values = pd.to_numeric(grouped_data_display[col], errors='coerce')
                        if not numeric_values.isna().all():
                            conditional_cols[col] = {
                                "positive_color": "#ff4444",  # Red for positive
                                "negative_color": "#44ff44"   # Green for negative/zero
                            }
                    except:
                        pass
        html_table = format_dataframe_as_html(grouped_data_display, conditional_cols=conditional_cols)
        st.markdown(html_table, unsafe_allow_html=True)


# ==================== DASHBOARD 3: Plan/Fact Dates for Tasks ====================
def dashboard_plan_fact_dates(df):
    st.header("📅 Отклонение текущего срока от базового плана")

    col1, col2, col3 = st.columns(3)

    with col1:
        if "project name" in df.columns:
            projects = ["Все"] + sorted(df["project name"].dropna().unique().tolist())
            selected_project = st.selectbox(
                "Фильтр по проекту", projects, key="dates_project"
            )
        else:
            selected_project = "Все"

    # Apply project filter first to get filtered data for task and section lists
    temp_filtered_df = df.copy()
    if selected_project != "Все" and "project name" in temp_filtered_df.columns:
        temp_filtered_df = temp_filtered_df[
            temp_filtered_df["project name"].astype(str).str.strip()
            == str(selected_project).strip()
        ]

    with col2:
        if "task name" in temp_filtered_df.columns:
            tasks = ["Все"] + sorted(temp_filtered_df["task name"].dropna().unique().tolist())
            selected_task = st.selectbox("Фильтр по задаче", tasks, key="dates_task")
        else:
            selected_task = "Все"

    with col3:
        if "section" in temp_filtered_df.columns:
            sections = ["Все"] + sorted(temp_filtered_df["section"].dropna().unique().tolist())
            selected_section = st.selectbox(
                "Фильтр по этапу", sections, key="dates_section"
            )
        else:
            selected_section = "Все"

    # Apply all filters
    filtered_df = df.copy()
    if selected_project != "Все" and "project name" in filtered_df.columns:
        filtered_df = filtered_df[
            filtered_df["project name"].astype(str).str.strip()
            == str(selected_project).strip()
        ]
    if selected_task != "Все" and "task name" in filtered_df.columns:
        filtered_df = filtered_df[
            filtered_df["task name"].astype(str).str.strip()
            == str(selected_task).strip()
        ]
    if selected_section != "Все" and "section" in filtered_df.columns:
        filtered_df = filtered_df[
            filtered_df["section"].astype(str).str.strip()
            == str(selected_section).strip()
        ]

    if filtered_df.empty:
        st.info("Нет данных для выбранных фильтров.")
        return

    # Prepare data for visualization - compare plan and fact dates
    # First, ensure all dates are datetime objects
    date_cols = ["plan start", "plan end", "base start", "base end"]
    for col in date_cols:
        if col in filtered_df.columns:
            filtered_df[col] = pd.to_datetime(
                filtered_df[col], errors="coerce", dayfirst=True
            )

    # Filter to rows that have at least plan OR fact dates (not necessarily both)
    has_plan_dates = filtered_df["plan start"].notna() & filtered_df["plan end"].notna()
    has_fact_dates = filtered_df["base start"].notna() & filtered_df["base end"].notna()
    has_any_dates = has_plan_dates | has_fact_dates
    filtered_df = filtered_df[has_any_dates]

    if filtered_df.empty:
        st.info("Нет задач с плановыми или фактическими датами для выбранных фильтров.")
        return

    # Calculate date differences for tasks that have both plan and fact
    filtered_df["plan_start_diff"] = None
    filtered_df["plan_end_diff"] = None
    filtered_df["total_diff_days"] = 0

    both_dates_mask = has_plan_dates & has_fact_dates
    if both_dates_mask.any():
        filtered_df.loc[both_dates_mask, "plan_start_diff"] = (
            filtered_df.loc[both_dates_mask, "base start"]
            - filtered_df.loc[both_dates_mask, "plan start"]
        ).dt.days
        filtered_df.loc[both_dates_mask, "plan_end_diff"] = (
            filtered_df.loc[both_dates_mask, "base end"]
            - filtered_df.loc[both_dates_mask, "plan end"]
        ).dt.days
        filtered_df.loc[both_dates_mask, "total_diff_days"] = filtered_df.loc[
            both_dates_mask, "plan_end_diff"
        ].abs()

    # Sort by task name (alphabetically) for consistent display
    filtered_df = filtered_df.sort_values("task name", ascending=True)

    # Prepare data for Gantt chart - compare plan vs fact
    viz_data = []
    for idx, row in filtered_df.iterrows():
        task_name = row.get("task name", "Неизвестно")
        project_name = row.get("project name", "Неизвестно")

        plan_start = row.get("plan start")
        plan_end = row.get("plan end")
        base_start = row.get("base start")
        base_end = row.get("base end")
        diff_days = row.get("total_diff_days", 0)

        # Add plan dates
        if pd.notna(plan_start) and pd.notna(plan_end):
            viz_data.append(
                {
                    "Task": f"{task_name} ({project_name})",
                    "Task_Original": task_name,
                    "Project": project_name,
                    "Start": plan_start,
                    "End": plan_end,
                    "Type": "План",
                    "Duration": (plan_end - plan_start).days,
                    "Diff_Days": diff_days,
                }
            )

        # Add fact dates
        if pd.notna(base_start) and pd.notna(base_end):
            viz_data.append(
                {
                    "Task": f"{task_name} ({project_name})",
                    "Task_Original": task_name,
                    "Project": project_name,
                    "Start": base_start,
                    "End": base_end,
                    "Type": "Факт",
                    "Duration": (base_end - base_start).days,
                    "Diff_Days": diff_days,
                }
            )

    if not viz_data:
        st.info("Нет валидных данных по датам.")
        return

    viz_df = pd.DataFrame(viz_data)

    # Sort tasks by difference (largest first) - maintain order from filtered_df
    task_order = filtered_df.sort_values("total_diff_days", ascending=False)[
        "task name"
    ].tolist()
    # Create a mapping for sorting
    task_order_map = {task: idx for idx, task in enumerate(task_order)}
    viz_df["sort_order"] = viz_df["Task_Original"].map(task_order_map).fillna(999)
    viz_df = viz_df.sort_values("sort_order")

    # Gantt chart - use proper timeline visualization with plotly express
    # Get unique tasks in sorted order (by task name)
    unique_tasks = filtered_df["task name"].unique().tolist()

    # Prepare data for bar chart - plan and fact side by side for each task
    # If "Все" projects selected, show all tasks from all projects
    bar_data = []
    for task_name in unique_tasks:
        task_rows = filtered_df[filtered_df["task name"] == task_name]
        if task_rows.empty:
            continue

        # If "Все" projects, show each task for each project separately
        if selected_project == "Все":
            for _, row in task_rows.iterrows():
                project_name = row.get("project name", "Неизвестно")
                display_name = f"{task_name} ({project_name})"
                diff_days = row.get("total_diff_days", 0)

                plan_start = row.get("plan start")
                plan_end = row.get("plan end")
                base_start = row.get("base start")
                base_end = row.get("base end")

                # Add plan entry
                if pd.notna(plan_start) and pd.notna(plan_end):
                    bar_data.append(
                        {
                            "Задача": display_name,
                            "Тип": "План",
                            "Дата начала": plan_start,
                            "Дата окончания": plan_end,
                            "Длительность": (plan_end - plan_start).days,
                            "Отклонение": diff_days,
                        }
                    )

                # Add fact entry
                if pd.notna(base_start) and pd.notna(base_end):
                    bar_data.append(
                        {
                            "Задача": display_name,
                            "Тип": "Факт",
                            "Дата начала": base_start,
                            "Дата окончания": base_end,
                            "Длительность": (base_end - base_start).days,
                            "Отклонение": diff_days,
                        }
                    )
        else:
            # If specific project selected, show only that project's tasks
            row = task_rows.iloc[0]
            project_name = row.get("project name", "Неизвестно")
            display_name = f"{task_name} ({project_name})"
            diff_days = row.get("total_diff_days", 0)

            plan_start = row.get("plan start")
            plan_end = row.get("plan end")
            base_start = row.get("base start")
            base_end = row.get("base end")

            # Add plan entry
            if pd.notna(plan_start) and pd.notna(plan_end):
                bar_data.append(
                    {
                        "Задача": display_name,
                        "Тип": "План",
                        "Дата начала": plan_start,
                        "Дата окончания": plan_end,
                        "Длительность": (plan_end - plan_start).days,
                        "Отклонение": diff_days,
                    }
                )

            # Add fact entry
            if pd.notna(base_start) and pd.notna(base_end):
                bar_data.append(
                    {
                        "Задача": display_name,
                        "Тип": "Факт",
                        "Дата начала": base_start,
                        "Дата окончания": base_end,
                        "Длительность": (base_end - base_start).days,
                        "Отклонение": diff_days,
                    }
                )

    bar_df = pd.DataFrame(bar_data)

    if bar_df.empty:
        st.info("Нет данных для отображения графика.")
    else:
        # Checkbox to show/hide completion percentage
        show_completion = st.checkbox(
            "Показать процент выполнения",
            value=False,
            key="show_completion_percent_dates",
        )

        # Initialize "Процент выполнения" column
        bar_df["Процент выполнения"] = ""

        # Calculate completion percentage if needed
        if show_completion:
            # Calculate completion percentage for each task
            for idx, row in bar_df.iterrows():
                if row["Тип"] == "План" and row["Длительность"] > 0:
                    # Find corresponding fact entry
                    fact_row = bar_df[
                        (bar_df["Задача"] == row["Задача"]) & (bar_df["Тип"] == "Факт")
                    ]
                    if not fact_row.empty:
                        fact_duration = fact_row.iloc[0]["Длительность"]
                        plan_duration = row["Длительность"]
                        if plan_duration > 0:
                            # Percentage = (fact / plan) * 100
                            completion_pct = (fact_duration / plan_duration) * 100
                            completion_pct_str = f"{completion_pct:.1f}%"
                            bar_df.loc[idx, "Процент выполнения"] = completion_pct_str
                            # Также сохраняем процент для соответствующей фактической записи
                            fact_idx = fact_row.index[0]
                            bar_df.loc[fact_idx, "Процент выполнения"] = (
                                completion_pct_str
                            )
                        else:
                            bar_df.loc[idx, "Процент выполнения"] = "Н/Д"
                    else:
                        bar_df.loc[idx, "Процент выполнения"] = "Н/Д"

        # Sort tasks by start date (earliest first)
        if not bar_df.empty:
            # Get unique tasks and sort by earliest start date
            task_start_dates = (
                bar_df.groupby("Задача")["Дата начала"].min().sort_values()
            )
            task_order = {task: idx for idx, task in enumerate(task_start_dates.index)}
            bar_df["sort_order"] = bar_df["Задача"].map(task_order)
            bar_df = bar_df.sort_values(["sort_order", "Тип"], ascending=[True, True])
            bar_df = bar_df.drop("sort_order", axis=1)
            bar_df = bar_df.reset_index(drop=True)

        # Create Gantt-style chart with dates on X-axis
        fig = go.Figure()

        # Prepare data for Plan bars
        plan_df = bar_df[bar_df["Тип"] == "План"].copy()
        fact_df = bar_df[bar_df["Тип"] == "Факт"].copy()

        # Get unique tasks in sorted order from all data that will be displayed
        # Use tasks from fact_df if show_completion is enabled, otherwise from both
        if show_completion:
            # When showing completion, only fact bars are displayed
            # Get tasks from fact_df and sort by earliest start date
            if not fact_df.empty:
                task_start_dates = fact_df.groupby("Задача")["Дата начала"].min().sort_values()
                unique_tasks_sorted = task_start_dates.index.tolist()
            else:
                unique_tasks_sorted = []
        else:
            # When showing both, use all tasks from bar_df
            # Sort by earliest start date to maintain consistent order
            if not bar_df.empty:
                task_start_dates = bar_df.groupby("Задача")["Дата начала"].min().sort_values()
                unique_tasks_sorted = task_start_dates.index.tolist()
            else:
                unique_tasks_sorted = []

        # Add Plan bars (только если не включен показ процента выполнения)
        if not plan_df.empty and not show_completion:
            plan_tasks = []
            plan_starts = []
            plan_ends = []
            plan_texts = []

            for idx, row in plan_df.iterrows():
                task = row["Задача"]
                start_date = row["Дата начала"]
                end_date = row["Дата окончания"]

                if pd.notna(start_date) and pd.notna(end_date):
                    plan_tasks.append(task)
                    plan_starts.append(start_date)
                    plan_ends.append(end_date)

                    # Text for end of bar (end date)
                    # Процент выполнения показываем только на фактических барах, не на плановых
                    end_date_str = end_date.strftime("%d.%m.%Y")
                    text_label = end_date_str
                    plan_texts.append(text_label)

            if plan_tasks:
                # For date axis, use end dates directly in x and start dates in base
                # The bar will span from base to x
                fig.add_trace(
                    go.Bar(
                        x=plan_ends,  # End dates on X-axis
                        base=plan_starts,  # Start dates as base
                        y=plan_tasks,
                        orientation="h",
                        name="План",
                        marker_color="#2E86AB",
                        text=plan_texts,
                        textposition="outside",
                        textfont=dict(size=12, color="white"),
                        hovertemplate="<b>%{y}</b><br>Тип: План<br>Начало: %{base|%d.%m.%Y}<br>Окончание: %{x|%d.%m.%Y}<br><extra></extra>",
                    )
                )

        # Add Fact bars
        if not fact_df.empty:
            fact_tasks = []
            fact_starts = []
            fact_ends = []
            fact_texts = []

            for idx, row in fact_df.iterrows():
                task = row["Задача"]
                start_date = row["Дата начала"]
                end_date = row["Дата окончания"]

                if pd.notna(start_date) and pd.notna(end_date):
                    fact_tasks.append(task)
                    fact_starts.append(start_date)
                    fact_ends.append(end_date)

                    # Text for end of bar (end date)
                    end_date_str = end_date.strftime("%d.%m.%Y")
                    text_label = end_date_str
                    if (
                        show_completion
                        and "Процент выполнения" in row
                        and pd.notna(row.get("Процент выполнения"))
                        and row["Процент выполнения"] != ""
                    ):
                        text_label = f"{end_date_str} ({row['Процент выполнения']})"
                    fact_texts.append(text_label)

            if fact_tasks:
                # For date axis, use end dates directly in x and start dates in base
                fig.add_trace(
                    go.Bar(
                        x=fact_ends,  # End dates on X-axis
                        base=fact_starts,  # Start dates as base
                        y=fact_tasks,
                        orientation="h",
                        name="Факт",
                        marker_color="#FF6347",
                        text=fact_texts,
                        textposition="outside",
                        textfont=dict(size=12, color="white"),
                        hovertemplate="<b>%{y}</b><br>Тип: Факт<br>Начало: %{base|%d.%m.%Y}<br>Окончание: %{x|%d.%m.%Y}<br><extra></extra>",
                    )
                )

        # Update layout
        # Формируем название графика с учетом выбранного проекта
        if selected_project == "Все":
            chart_title = "Срок работ план/факт (все проекты)"
        else:
            chart_title = f"Срок работ план/факт - {selected_project}"

    fig.update_layout(
        title=chart_title,
        xaxis_title="Дата",
        yaxis_title="Задача",
        height=max(600, len(unique_tasks_sorted) * 50),
        barmode="group",  # Grouped bars: plan and fact in separate columns
        hovermode="closest",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis=dict(type="date", tickformat="%d.%m.%Y"),  # Use date axis
        yaxis=dict(
            categoryorder="array",
            categoryarray=list(
                reversed(unique_tasks_sorted)
            ),  # Reverse to show first task at top
        ),
    )
    fig = apply_chart_background(fig)

    st.plotly_chart(fig, use_container_width=True)

    # Форматирование даты для отображения
    def format_date_display(date_val):
        if pd.isna(date_val):
            return "Н/Д"
        if isinstance(date_val, pd.Timestamp):
            return date_val.strftime("%d.%m.%Y")
        try:
            dt = pd.to_datetime(date_val, errors="coerce", dayfirst=True)
            if pd.notna(dt):
                return dt.strftime("%d.%m.%Y")
        except:
            pass
        return str(date_val) if date_val else "Н/Д"

    # Селектор задачи для метрик окончания проекта (только при выборе конкретного проекта)
    selected_task_for_metrics = None
    if (
        selected_project != "Все"
        and "task name" in df.columns
        and "project name" in df.columns
    ):
        # Получаем список задач выбранного проекта
        project_tasks = df[
            df["project name"].astype(str).str.strip() == str(selected_project).strip()
        ]
        if not project_tasks.empty:
            available_tasks = sorted(
                project_tasks["task name"].dropna().unique().tolist()
            )
            if available_tasks:
                # По умолчанию используем "Разрешение на ввод в эксплуатацию", если она есть
                default_task = (
                    "Разрешение на ввод в эксплуатацию"
                    if "Разрешение на ввод в эксплуатацию" in available_tasks
                    else available_tasks[0]
                )
                selected_task_for_metrics = st.selectbox(
                    "Задача для расчета окончания проекта",
                    available_tasks,
                    index=(
                        available_tasks.index(default_task)
                        if default_task in available_tasks
                        else 0
                    ),
                    key="task_for_project_end_metrics",
                )

    # Найти задачу для метрик (либо выбранную через селектор, либо "Разрешение на ввод в эксплуатацию" по умолчанию)
    task_name_to_find = (
        selected_task_for_metrics
        if selected_task_for_metrics
        else "Разрешение на ввод в эксплуатацию"
    )
    task_row = None

    if "task name" in df.columns:
        # Ищем задачу в исходных данных (не в отфильтрованных)
        task_mask = df["task name"].astype(str).str.strip() == task_name_to_find.strip()
        if task_mask.any():
            # Если выбран конкретный проект, ищем задачу только в этом проекте
            if selected_project != "Все" and "project name" in df.columns:
                project_mask = (
                    df["project name"].astype(str).str.strip()
                    == str(selected_project).strip()
                )
                task_row = df[task_mask & project_mask]
                if not task_row.empty:
                    task_row = task_row.iloc[0]
            else:
                task_row = df[task_mask].iloc[0]

    # Add comparison metrics
    col1, col2, col3 = st.columns(3)

    # Максимальное отклонение (дней) - отклонение факта от плана для выбранной задачи
    with col1:
        if task_row is not None:
            # Преобразуем даты в datetime если нужно
            plan_end = task_row.get("plan end")
            base_end = task_row.get("base end")

            if pd.notna(plan_end):
                plan_end = pd.to_datetime(plan_end, errors="coerce", dayfirst=True)
            if pd.notna(base_end):
                base_end = pd.to_datetime(base_end, errors="coerce", dayfirst=True)

            if pd.notna(plan_end) and pd.notna(base_end):
                deviation_days = (base_end - plan_end).days
                deviation_str = f"{deviation_days:.0f}"

                # Цвет: отрицательное = зеленый, положительное = красный
                # Используем delta_color="inverse": отрицательные значения = зеленый, положительные = красный
                st.metric(
                    "Максимальное отклонение (дней)",
                    deviation_str,
                    delta=f"{deviation_days:.0f}",
                    delta_color="inverse",
                )
            else:
                st.metric("Максимальное отклонение (дней)", "Н/Д")
        else:
            st.metric("Максимальное отклонение (дней)", "Н/Д")

    # План окончания проекта - дата из задачи "Разрешение на ввод в эксплуатацию"
    with col2:
        if task_row is not None:
            plan_end = task_row.get("plan end")
            if pd.notna(plan_end):
                plan_end = pd.to_datetime(plan_end, errors="coerce", dayfirst=True)
                plan_end_str = format_date_display(plan_end)
            else:
                plan_end_str = "Н/Д"
            st.metric("План окончания проекта", plan_end_str)
        else:
            st.metric("План окончания проекта", "Н/Д")

    # Факт окончания проекта - дата из задачи "Разрешение на ввод в эксплуатацию"
    with col3:
        if task_row is not None:
            base_end = task_row.get("base end")
            if pd.notna(base_end):
                base_end = pd.to_datetime(base_end, errors="coerce", dayfirst=True)
                fact_end_str = format_date_display(base_end)
            else:
                fact_end_str = "Н/Д"
            st.metric("Факт окончания проекта", fact_end_str)
        else:
            st.metric("Факт окончания проекта", "Н/Д")

    # Добавляем разделитель и аналогичные метрики для задачи "Разрешение на строительство"
    st.markdown("---")
    col1_construction, col2_construction, col3_construction = st.columns(3)

    # Найти задачу "Разрешение на строительство"
    task_name_construction = "Разрешение на строительство"
    task_row_construction = None

    if "task name" in df.columns:
        # Ищем задачу в исходных данных (не в отфильтрованных)
        task_mask_construction = (
            df["task name"].astype(str).str.strip() == task_name_construction.strip()
        )
        if task_mask_construction.any():
            task_row_construction = df[task_mask_construction].iloc[0]

    # Максимальное отклонение (дней) - отклонение факта от плана для задачи "Разрешение на строительство"
    with col1_construction:
        if task_row_construction is not None:
            # Преобразуем даты в datetime если нужно
            plan_end_construction = task_row_construction.get("plan end")
            base_end_construction = task_row_construction.get("base end")

            if pd.notna(plan_end_construction):
                plan_end_construction = pd.to_datetime(
                    plan_end_construction, errors="coerce", dayfirst=True
                )
            if pd.notna(base_end_construction):
                base_end_construction = pd.to_datetime(
                    base_end_construction, errors="coerce", dayfirst=True
                )

            if pd.notna(plan_end_construction) and pd.notna(base_end_construction):
                deviation_days_construction = (
                    base_end_construction - plan_end_construction
                ).days
                deviation_str_construction = f"{deviation_days_construction:.0f}"

                # Цвет: отрицательное = зеленый, положительное = красный
                # Используем delta_color="inverse": отрицательные значения = зеленый, положительные = красный
                st.metric(
                    "Максимальное отклонение (дней)",
                    deviation_str_construction,
                    delta=f"{deviation_days_construction:.0f}",
                    delta_color="inverse",
                )
            else:
                st.metric("Максимальное отклонение (дней)", "Н/Д")
        else:
            st.metric("Максимальное отклонение (дней)", "Н/Д")

    # План окончания проекта - дата из задачи "Разрешение на строительство"
    with col2_construction:
        if task_row_construction is not None:
            plan_end_construction = task_row_construction.get("plan end")
            if pd.notna(plan_end_construction):
                plan_end_construction = pd.to_datetime(
                    plan_end_construction, errors="coerce", dayfirst=True
                )
                plan_end_str_construction = format_date_display(plan_end_construction)
            else:
                plan_end_str_construction = "Н/Д"
            st.metric("План окончания проекта", plan_end_str_construction)
        else:
            st.metric("План окончания проекта", "Н/Д")

    # Факт окончания проекта - дата из задачи "Разрешение на строительство"
    with col3_construction:
        if task_row_construction is not None:
            base_end_construction = task_row_construction.get("base end")
            if pd.notna(base_end_construction):
                base_end_construction = pd.to_datetime(
                    base_end_construction, errors="coerce", dayfirst=True
                )
                fact_end_str_construction = format_date_display(base_end_construction)
            else:
                fact_end_str_construction = "Н/Д"
            st.metric("Факт окончания проекта", fact_end_str_construction)
        else:
            st.metric("Факт окончания проекта", "Н/Д")

    # Summary table - format dates properly, sorted by difference
    summary_data = []
    for idx, row in filtered_df.iterrows():
        plan_start = row.get("plan start", pd.NaT)
        plan_end = row.get("plan end", pd.NaT)
        base_start = row.get("base start", pd.NaT)
        base_end = row.get("base end", pd.NaT)
        diff_days = row.get("total_diff_days", 0)
        start_diff = row.get("plan_start_diff", 0)
        end_diff = row.get("plan_end_diff", 0)

        # Format dates for display
        def format_date(date_val):
            if pd.isna(date_val):
                return "Н/Д"
            if isinstance(date_val, pd.Timestamp):
                return date_val.strftime("%d.%m.%Y")
            try:
                dt = pd.to_datetime(date_val, errors="coerce", dayfirst=True)
                if pd.notna(dt):
                    return dt.strftime("%d.%m.%Y")
            except:
                pass
            return str(date_val) if date_val else "Н/Д"

        summary_data.append(
            {
                "Проект": row.get("project name", "Н/Д"),
                "Задача": row.get("task name", "Н/Д"),
                "Раздел": row.get("section", "Н/Д"),
                "План Начало": format_date(plan_start),
                "План Конец": format_date(plan_end),
                "Факт Начало": format_date(base_start),
                "Факт Конец": format_date(base_end),
                "Отклонение начала (дней)": start_diff,
                "Отклонение конца (дней)": end_diff,
            }
        )

    summary_df = pd.DataFrame(summary_data)
    # Convert 'Отклонение конца (дней)' to numeric for proper sorting
    summary_df["Отклонение конца (дней)"] = pd.to_numeric(
        summary_df["Отклонение конца (дней)"], errors="coerce"
    )
    summary_df["Отклонение начала (дней)"] = pd.to_numeric(
        summary_df["Отклонение начала (дней)"], errors="coerce"
    )

    # If "Все" projects selected, add summary column with totals per task
    if selected_project == "Все" and "Задача" in summary_df.columns:
        # Calculate totals per task
        task_totals = (
            summary_df.groupby("Задача")
            .agg({"Отклонение начала (дней)": "sum", "Отклонение конца (дней)": "sum"})
            .reset_index()
        )
        task_totals.columns = [
            "Задача",
            "Сумма отклонения начала (дней)",
            "Сумма отклонения конца (дней)",
        ]

        # Calculate total deviation per task (sum of start and end deviations)
        task_totals["Суммарное отклонение (дней)"] = task_totals[
            "Сумма отклонения начала (дней)"
        ].fillna(0) + task_totals["Сумма отклонения конца (дней)"].fillna(0)

        # Merge totals back to summary_df
        summary_df = summary_df.merge(task_totals, on="Задача", how="left")

        # Reorder columns to put summary columns after deviation columns
        cols = summary_df.columns.tolist()
        # Remove summary columns from their current position
        cols.remove("Сумма отклонения начала (дней)")
        cols.remove("Сумма отклонения конца (дней)")
        cols.remove("Суммарное отклонение (дней)")
        # Add them after deviation columns
        start_idx = cols.index("Отклонение начала (дней)")
        end_idx = cols.index("Отклонение конца (дней)")
        cols.insert(end_idx + 1, "Сумма отклонения начала (дней)")
        cols.insert(end_idx + 2, "Сумма отклонения конца (дней)")
        cols.insert(end_idx + 3, "Суммарное отклонение (дней)")
        summary_df = summary_df[cols]

    # Sort by end date difference (largest first, descending order)
    # Handle NaN values by placing them at the end
    summary_df = summary_df.sort_values(
        "Отклонение конца (дней)", ascending=False, na_position="last"
    )
    st.subheader("Детальные даты задач")
    # Устанавливаем цвета для колонок: даты начала - один цвет, даты окончания - другой
    column_colors = {
        "План Начало": "#4CAF50",  # Зеленый для дат начала
        "Факт Начало": "#4CAF50",  # Зеленый для дат начала
        "План Конец": "#FF9800",   # Оранжевый для дат окончания
        "Факт Конец": "#FF9800"    # Оранжевый для дат окончания
    }
    # Условное форматирование для колонок с отклонениями: > 0 - красный, = 0 - зеленый
    conditional_cols = {}
    deviation_columns = [
        "Отклонение начала (дней)",
        "Отклонение конца (дней)",
        "Сумма отклонения начала (дней)",
        "Сумма отклонения конца (дней)",
        "Суммарное отклонение (дней)"
    ]
    for col in deviation_columns:
        if col in summary_df.columns:
            conditional_cols[col] = {
                "positive_color": "#ff4444",  # Красный для > 0
                "negative_color": "#44ff44"   # Зеленый для <= 0 (включая 0)
            }
    html_table = format_dataframe_as_html(summary_df, conditional_cols=conditional_cols, column_colors=column_colors)
    st.markdown(html_table, unsafe_allow_html=True)


# ==================== DASHBOARD 4: Deviation Amount by Tasks ====================
def dashboard_deviation_by_tasks_current_month(df):
    # Проверка на None или пустой DataFrame
    if df is None:
        st.warning(
            "⚠️ Нет данных для отображения. Пожалуйста, загрузите данные проекта."
        )
        return

    # Проверка, что df является DataFrame и имеет атрибут columns
    if not hasattr(df, "columns") or df.empty:
        st.warning(
            "⚠️ Нет данных для отображения. Пожалуйста, загрузите данные проекта."
        )
        return

    st.header("📊 Значения отклонений от базового плана")

    # Start with full dataset (all periods, not just current month)
    filtered_df = df.copy()

    # Filters row 1: Project, Section (renamed to Этап)
    col1, col2 = st.columns(2)

    with col1:
        # Project filter - show all projects from full dataset
        selected_project = "Все"  # Initialize default value
        try:
            has_project_column = "project name" in df.columns
        except (AttributeError, TypeError):
            has_project_column = False

        if has_project_column:
            # Get all unique projects from the full dataset
            all_projects = sorted(df["project name"].dropna().unique().tolist())
            if all_projects:
                projects = ["Все"] + all_projects
                selected_project = st.selectbox(
                    "Фильтр по проекту", projects, key="deviation_tasks_project"
                )
            else:
                st.warning("Проекты не найдены в данных.")
                return
        else:
            st.warning("Поле 'project name' не найдено в данных.")
            return

    with col2:
        # Section filter - renamed to "Фильтр по этапу"
        try:
            has_section_column = "section" in df.columns
        except (AttributeError, TypeError):
            has_section_column = False

        if has_section_column:
            sections = ["Все"] + sorted(df["section"].dropna().unique().tolist())
            selected_section = st.selectbox(
                "Фильтр по этапу", sections, key="deviation_tasks_section"
            )
        else:
            selected_section = "Все"

    # Apply project filter
    try:
        has_project_col = "project name" in filtered_df.columns
    except (AttributeError, TypeError):
        has_project_col = False

    if selected_project != "Все" and has_project_col:
        filtered_df = filtered_df[
            filtered_df["project name"].astype(str).str.strip()
            == str(selected_project).strip()
        ]

    # Apply section filter
    try:
        has_section_col = "section" in filtered_df.columns
    except (AttributeError, TypeError):
        has_section_col = False

    if selected_section != "Все" and has_section_col:
        filtered_df = filtered_df[
            filtered_df["section"].astype(str).str.strip()
            == str(selected_section).strip()
        ]

    # Filter only tasks with deviations - check for deviation = 1 or True
    try:
        has_deviation_col = "deviation" in filtered_df.columns
    except (AttributeError, TypeError):
        has_deviation_col = False

    if has_deviation_col:
        deviation_mask = (
            (filtered_df["deviation"] == True)
            | (filtered_df["deviation"] == 1)
            | (filtered_df["deviation"].astype(str).str.lower() == "true")
            | (filtered_df["deviation"].astype(str).str.strip() == "1")
        )
        filtered_df = filtered_df[deviation_mask]
    else:
        st.warning("Поле 'deviation' не найдено в данных.")
        return

    # Filter out negative deviation values - only show positive deviations
    try:
        has_deviation_days_col = "deviation in days" in filtered_df.columns
    except (AttributeError, TypeError):
        has_deviation_days_col = False

    if has_deviation_days_col:
        filtered_df["deviation in days"] = pd.to_numeric(
            filtered_df["deviation in days"], errors="coerce"
        )
        # Filter out negative and zero values - only show positive deviations
        filtered_df = filtered_df[filtered_df["deviation in days"] > 0]

    if filtered_df.empty:
        st.info("Отклонения не найдены для выбранных фильтров.")
        return

    # Group by project and task - aggregate across all periods
    try:
        has_project_col = "project name" in filtered_df.columns
        has_task_col = "task name" in filtered_df.columns
    except (AttributeError, TypeError):
        has_project_col = False
        has_task_col = False

    if has_project_col and has_task_col:

        # Calculate completion percentage if dates are available
        try:
            has_plan_start = "plan start" in filtered_df.columns
            has_plan_end = "plan end" in filtered_df.columns
            has_base_start = "base start" in filtered_df.columns
            has_base_end = "base end" in filtered_df.columns
        except (AttributeError, TypeError):
            has_plan_start = False
            has_plan_end = False
            has_base_start = False
            has_base_end = False

        if has_plan_start and has_plan_end and has_base_start and has_base_end:
            # Convert dates to datetime
            for col in ["plan start", "plan end", "base start", "base end"]:
                filtered_df[col] = pd.to_datetime(
                    filtered_df[col], errors="coerce", dayfirst=True
                )

            # Calculate completion percentage:
            # (Планируемая дата окончания - планируемая дата начала) / (Фактическая дата окончания - фактическая дата начала) * 100
            filtered_df["plan_duration"] = (
                filtered_df["plan end"] - filtered_df["plan start"]
            ).dt.days
            filtered_df["fact_duration"] = (
                filtered_df["base end"] - filtered_df["base start"]
            ).dt.days

            # Calculate percentage: plan_duration / fact_duration * 100
            # Avoid division by zero
            filtered_df["completion_percent"] = (
                filtered_df["plan_duration"]
                / filtered_df["fact_duration"].replace(0, np.nan)
                * 100
            ).fillna(0)
            # Cap at reasonable values (0-200%)
            filtered_df["completion_percent"] = filtered_df["completion_percent"].clip(
                0, 200
            )
        else:
            filtered_df["completion_percent"] = None

        # Determine grouping level based on applied filters
        # Priority: section > project
        if selected_section != "Все":
            # If section is selected, group by section
            group_by_cols = ["section"]
            y_column = "Этап"
        elif selected_project != "Все":
            # If project is selected but not section, group by project
            group_by_cols = ["project name"]
            y_column = "Проект"
        else:
            # If nothing is selected, group by project
            group_by_cols = ["project name"]
            y_column = "Проект"

        # Group data based on determined grouping level
        deviations = (
            filtered_df.groupby(group_by_cols)
            .agg(
                {
                    "deviation in days": (
                        "sum" if "deviation in days" in filtered_df.columns else "count"
                    ),
                    "completion_percent": (
                        "mean"
                        if "completion_percent" in filtered_df.columns
                        and filtered_df["completion_percent"].notna().any()
                        else lambda x: None
                    ),
                }
            )
            .reset_index()
        )

        # Set column names based on grouping level
        if "section" in group_by_cols:
            deviations.columns = [
                "Этап",
                "Суммарно дней отклонений",
                "Процент выполнения",
            ]
            deviations["Отображение"] = deviations["Этап"]
        else:  # project only
            deviations.columns = [
                "Проект",
                "Суммарно дней отклонений",
                "Процент выполнения",
            ]
            deviations["Отображение"] = deviations["Проект"]

        # If completion percent calculation failed, set to None
        if "Процент выполнения" in deviations.columns:
            deviations["Процент выполнения"] = pd.to_numeric(
                deviations["Процент выполнения"], errors="coerce"
            )

        # Sort by deviation amount (descending - largest first)
        deviations = deviations.sort_values("Суммарно дней отклонений", ascending=False)

        if deviations.empty:
            st.info("Нет данных для отображения.")
            return

        # Checkboxes row 2: Top 5 and Completion percentage
        col5, col6 = st.columns(2)

        with col5:
            # Checkbox for Top 5 filter
            show_top5 = st.checkbox(
                "Топ 5 отклонений", value=False, key="show_top5_deviations"
            )

        with col6:
            # Checkbox to show/hide completion percentage
            show_completion = st.checkbox(
                "Показывать процент выполнения",
                value=False,
                key="show_completion_percent",
            )

        # Apply Top 5 filter if enabled
        if show_top5:
            deviations = deviations.head(5)

        # Visualization - horizontal bar chart
        # Format text for display on bars
        text_values = []
        for _, row in deviations.iterrows():
            if show_completion and pd.notna(row.get("Процент выполнения")):
                text_values.append(
                    f"{row['Суммарно дней отклонений']:.0f} ({row['Процент выполнения']:.1f}%)"
                )
            else:
                text_values.append(f"{row['Суммарно дней отклонений']:.0f}")

        fig = px.bar(
            deviations,
            x="Суммарно дней отклонений",
            y="Отображение",
            orientation="h",
            title="Отклонения от базового плана",
            labels={
                "Суммарно дней отклонений": "Суммарно дней отклонений",
                "Отображение": y_column,
            },
            text=text_values,
            color_discrete_sequence=["#1f77b4"],  # Blue color for all bars
        )

        # Set category order to show largest values at top (descending order)
        # For horizontal bars, reverse the list so largest is at top
        category_list = deviations["Отображение"].tolist()
        fig.update_layout(
            showlegend=False,
            yaxis=dict(
                categoryorder="array",
                categoryarray=list(
                    reversed(category_list)
                ),  # Reverse to show largest at top
            ),
        )
        fig.update_traces(
            textposition="outside", textfont=dict(size=14, color="white")
        )  # Show text outside bars at the end
        fig = apply_chart_background(fig)
        st.plotly_chart(fig, use_container_width=True)

        # Additional histogram with detail by section and task
        st.subheader("📊 Детализация отклонений по разделам и задачам")

        # Filter for detail histogram - only by project
        detail_df = df.copy()

        # Apply project filter if selected
        if selected_project != "Все" and "project name" in detail_df.columns:
            detail_df = detail_df[
                detail_df["project name"].astype(str).str.strip()
                == str(selected_project).strip()
            ]

        # Filter only tasks with deviations
        if "deviation" in detail_df.columns:
            deviation_mask = (
                (detail_df["deviation"] == True)
                | (detail_df["deviation"] == 1)
                | (detail_df["deviation"].astype(str).str.lower() == "true")
                | (detail_df["deviation"].astype(str).str.strip() == "1")
            )
            detail_df = detail_df[deviation_mask]

        if detail_df.empty:
            st.info("Нет данных для отображения детализации.")
        else:
            # Convert deviation in days to numeric and filter out negative values
            if "deviation in days" in detail_df.columns:
                detail_df["deviation in days"] = pd.to_numeric(
                    detail_df["deviation in days"], errors="coerce"
                )
                # Filter out negative deviation days - only show positive or zero deviations
                detail_df = detail_df[
                    (detail_df["deviation in days"] >= 0) | (detail_df["deviation in days"].isna())
                ]

            # Group by section and task
            if "section" in detail_df.columns and "task name" in detail_df.columns:
                detail_deviations = (
                    detail_df.groupby(["section", "task name"])
                    .agg(
                        {
                            "deviation in days": (
                                "sum"
                                if "deviation in days" in detail_df.columns
                                else "count"
                            )
                        }
                    )
                    .reset_index()
                )

                detail_deviations.columns = [
                    "Раздел",
                    "Задача",
                    "Суммарно дней отклонений",
                ]

                # Filter out negative values from grouped data as well
                detail_deviations = detail_deviations[
                    (detail_deviations["Суммарно дней отклонений"] >= 0) |
                    (detail_deviations["Суммарно дней отклонений"].isna())
                ]
                detail_deviations["Отображение"] = (
                    detail_deviations["Задача"]
                    + " ("
                    + detail_deviations["Раздел"]
                    + ")"
                )

                # Sort by deviation amount (descending)
                detail_deviations = detail_deviations.sort_values(
                    "Суммарно дней отклонений", ascending=False
                )

                # Create horizontal bar chart
                fig_detail = px.bar(
                    detail_deviations,
                    x="Суммарно дней отклонений",
                    y="Отображение",
                    orientation="h",
                    title="Детализация отклонений по разделам и задачам",
                    labels={
                        "Суммарно дней отклонений": "Суммарно дней отклонений",
                        "Отображение": "Задача (Раздел)",
                    },
                    text=detail_deviations["Суммарно дней отклонений"].apply(
                        lambda x: f"{int(x):,}" if pd.notna(x) else ""
                    ),
                    color_discrete_sequence=["#1f77b4"],
                )

                # Set category order to show largest values at top
                category_list_detail = detail_deviations["Отображение"].tolist()
                fig_detail.update_layout(
                    showlegend=False,
                    yaxis=dict(
                        categoryorder="array",
                        categoryarray=list(reversed(category_list_detail)),
                    ),
                    height=max(
                        400, len(detail_deviations) * 30
                    ),  # Dynamic height based on number of items
                )
                fig_detail.update_traces(
                    textposition="outside", textfont=dict(size=12, color="white")
                )

                fig_detail = apply_chart_background(fig_detail)
                st.plotly_chart(fig_detail, use_container_width=True)
            else:
                st.warning("Поля 'section' или 'task name' не найдены для детализации.")
    else:
        st.warning(
            "Необходимые поля 'project name' или 'task name' не найдены в данных."
        )


# ==================== DASHBOARD 5: Dynamics of Reasons by Month ====================
def dashboard_dynamics_of_reasons(df):
    # Проверка на None или пустой DataFrame
    if df is None:
        st.warning(
            "⚠️ Нет данных для отображения. Пожалуйста, загрузите данные проекта."
        )
        return

    # Проверка, что df является DataFrame и имеет атрибут columns
    if not hasattr(df, "columns") or df.empty:
        st.warning(
            "⚠️ Нет данных для отображения. Пожалуйста, загрузите данные проекта."
        )
        return

    st.header("📉 Динамика причин отклонений")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        period_type = st.selectbox(
            "Группировать по", ["Месяц", "Квартал", "Год"], key="reasons_period"
        )
        period_map = {"Месяц": "Month", "Квартал": "Quarter", "Год": "Year"}
        period_type_en = period_map.get(period_type, "Month")

    with col2:
        try:
            has_reason_column = "reason of deviation" in df.columns
        except (AttributeError, TypeError):
            has_reason_column = False

        if has_reason_column:
            reasons = ["Все"] + sorted(
                df["reason of deviation"].dropna().unique().tolist()
            )
            selected_reason = st.selectbox(
                "Фильтр по причине", reasons, key="reasons_reason"
            )
        else:
            selected_reason = "Все"

    with col3:
        try:
            has_project_column = "project name" in df.columns
        except (AttributeError, TypeError):
            has_project_column = False

        if has_project_column:
            projects = ["Все"] + sorted(df["project name"].dropna().unique().tolist())
            selected_project = st.selectbox(
                "Фильтр по проекту", projects, key="reasons_project"
            )
        else:
            selected_project = "Все"

    with col4:
        try:
            has_section_column = "section" in df.columns
        except (AttributeError, TypeError):
            has_section_column = False

        if has_section_column:
            sections = ["Все"] + sorted(df["section"].dropna().unique().tolist())
            selected_section = st.selectbox(
                "Фильтр по этапу", sections, key="reasons_section"
            )
        else:
            selected_section = "Все"

    # Additional filter row: Block
    col5 = st.columns(1)[0]
    with col5:
        try:
            has_block_column = "block" in df.columns
        except (AttributeError, TypeError):
            has_block_column = False

        if has_block_column:
            blocks = ["Все"] + sorted(df["block"].dropna().unique().tolist())
            selected_block = st.selectbox(
                "Фильтр по блоку", blocks, key="reasons_block"
            )
        else:
            selected_block = "Все"

    # View type selector
    view_type = st.selectbox(
        "Вид отображения", ["По причинам", "По месяцам"], key="reasons_view_type"
    )

    # Apply filters - fix filtering
    filtered_df = df.copy()

    try:
        has_reason_col = "reason of deviation" in df.columns
    except (AttributeError, TypeError):
        has_reason_col = False

    if selected_reason != "Все" and has_reason_col:
        filtered_df = filtered_df[
            filtered_df["reason of deviation"].astype(str).str.strip()
            == str(selected_reason).strip()
        ]

    try:
        has_project_col = "project name" in filtered_df.columns
    except (AttributeError, TypeError):
        has_project_col = False

    if selected_project != "Все" and has_project_col:
        filtered_df = filtered_df[
            filtered_df["project name"].astype(str).str.strip()
            == str(selected_project).strip()
        ]

    try:
        has_section_col = "section" in filtered_df.columns
    except (AttributeError, TypeError):
        has_section_col = False

    if selected_section != "Все" and has_section_col:
        filtered_df = filtered_df[
            filtered_df["section"].astype(str).str.strip()
            == str(selected_section).strip()
        ]

    try:
        has_block_col = "block" in filtered_df.columns
    except (AttributeError, TypeError):
        has_block_col = False

    if selected_block != "Все" and has_block_col:
        filtered_df = filtered_df[
            filtered_df["block"].astype(str).str.strip() == str(selected_block).strip()
        ]

    # Filter only tasks with deviations - check for deviation = 1 or True
    try:
        has_deviation_col = "deviation" in filtered_df.columns
    except (AttributeError, TypeError):
        has_deviation_col = False

    if has_deviation_col:
        # Handle different deviation formats: True, 1, 'True', '1', etc.
        deviation_mask = (
            (filtered_df["deviation"] == True)
            | (filtered_df["deviation"] == 1)
            | (filtered_df["deviation"].astype(str).str.lower() == "true")
            | (filtered_df["deviation"].astype(str).str.strip() == "1")
        )
        filtered_df = filtered_df[deviation_mask]

    if filtered_df.empty:
        st.info("Нет данных для выбранных фильтров.")
        return

    # Determine period column - use plan_month for month grouping
    try:
        has_plan_end_col = "plan end" in filtered_df.columns
    except (AttributeError, TypeError):
        has_plan_end_col = False

    if period_type_en == "Month":
        period_col = "plan_month"
        period_label = "Месяц"
        # If plan_month doesn't exist, try to create it from plan end
        try:
            has_period_col = period_col in filtered_df.columns
        except (AttributeError, TypeError):
            has_period_col = False

        if not has_period_col and has_plan_end_col:
            mask = filtered_df["plan end"].notna()
            filtered_df.loc[mask, period_col] = filtered_df.loc[
                mask, "plan end"
            ].dt.to_period("M")
    elif period_type_en == "Quarter":
        period_col = "plan_quarter"
        period_label = "Квартал"
        try:
            has_period_col = period_col in filtered_df.columns
        except (AttributeError, TypeError):
            has_period_col = False

        if not has_period_col and has_plan_end_col:
            mask = filtered_df["plan end"].notna()
            filtered_df.loc[mask, period_col] = filtered_df.loc[
                mask, "plan end"
            ].dt.to_period("Q")
    else:
        period_col = "plan_year"
        period_label = "Год"
        try:
            has_period_col = period_col in filtered_df.columns
        except (AttributeError, TypeError):
            has_period_col = False

        if not has_period_col and has_plan_end_col:
            mask = filtered_df["plan end"].notna()
            filtered_df.loc[mask, period_col] = filtered_df.loc[
                mask, "plan end"
            ].dt.to_period("Y")

    if period_col not in filtered_df.columns:
        st.warning(f"Столбец периода '{period_col}' не найден.")
        return

    # Group by period and reason - ensure we have both project name and reason
    if "reason of deviation" in filtered_df.columns:
        # Filter out rows without period data
        reason_dynamics = (
            filtered_df[filtered_df[period_col].notna()]
            .groupby([period_col, "reason of deviation"])
            .size()
            .reset_index(name="Количество")
        )

        # Format period for display
        def format_period(period_val):
            if pd.isna(period_val):
                return "Н/Д"
            if isinstance(period_val, pd.Period):
                try:
                    if period_val.freqstr == "M" or period_val.freqstr.startswith(
                        "M"
                    ):  # Month
                        month_name = get_russian_month_name(period_val)
                        year = period_val.year
                        return f"{month_name} {year}"
                    elif period_val.freqstr == "Q" or period_val.freqstr.startswith(
                        "Q"
                    ):  # Quarter
                        return f"Q{period_val.quarter} {period_val.year}"
                    elif (
                        period_val.freqstr == "Y" or period_val.freqstr == "A-DEC"
                    ):  # Year
                        return str(period_val.year)
                    else:
                        month_name = get_russian_month_name(period_val)
                    year = period_val.year
                    return f"{month_name} {year}"
                except:
                    # Try parsing as string
                    period_str = str(period_val)
                    try:
                        if "-" in period_str:
                            parts = period_str.split("-")
                            if len(parts) >= 2:
                                year = parts[0]
                                month = parts[1]
                                month_num = int(month)
                                month_name = RUSSIAN_MONTHS.get(month_num, "")
                                if month_name:
                                    return f"{month_name} {year}"
                    except:
                        pass
                    return str(period_val)
            elif isinstance(period_val, str):
                # Try parsing string like "2025-01"
                try:
                    if "-" in period_val:
                        parts = period_val.split("-")
                        if len(parts) >= 2:
                            year = parts[0]
                            month = parts[1]
                            month_num = int(month)
                            month_name = RUSSIAN_MONTHS.get(month_num, "")
                            if month_name:
                                return f"{month_name} {year}"
                except:
                    pass
            return str(period_val)

        reason_dynamics[period_col] = reason_dynamics[period_col].apply(format_period)

        # Aggregate again after formatting to handle potential duplicates from formatting
        reason_dynamics = (
            reason_dynamics.groupby([period_col, "reason of deviation"])["Количество"]
            .sum()
            .reset_index()
        )

        # Checkbox to show/hide trend line
        show_trend = st.checkbox(
            "Показывать линию тренда", value=False, key="show_trend_line"
        )

        # Build visualization based on view type
        if view_type == "По причинам":
            # View 1: By reasons - reason on X-axis, count on Y-axis
            # Group by reason and sum across all periods
            reason_summary = (
                reason_dynamics.groupby("reason of deviation")["Количество"]
                .sum()
                .reset_index()
            )
            reason_summary = reason_summary.sort_values("Количество", ascending=False)

            # Visualization - vertical bar chart with reasons on X-axis
            fig = px.bar(
                reason_summary,
                x="reason of deviation",
                y="Количество",
                title="Динамика причин отклонений по причинам",
                labels={
                    "reason of deviation": "Причина отклонения",
                    "Количество": "Количество отклонений",
                },
                text="Количество",
                color_discrete_sequence=["#1f77b4"],
            )
            fig.update_xaxes(tickangle=-75, tickfont=dict(size=8), automargin=True)
            fig.update_traces(
                textposition="outside", textfont=dict(size=12, color="white")
            )
        else:
            # View 2: By months - month on X-axis, count on Y-axis, reasons as colors (stacked)
            # If "Все" projects selected, show aggregated view (one column per period)
            if selected_project == "Все":
                # For chart: group only by period (sum all reasons)
                chart_data = (
                    reason_dynamics.groupby(period_col)["Количество"]
                    .sum()
                    .reset_index()
                )
                chart_data["reason of deviation"] = (
                    "Все проекты"  # Dummy column for consistency
                )

                # Visualization - vertical bar chart with single column per period
                fig = px.bar(
                    chart_data,
                    x=period_col,
                    y="Количество",
                    title="Динамика причин отклонений по периодам",
                    labels={
                        period_col: period_label,
                        "Количество": "Количество отклонений",
                    },
                    text="Количество",
                    color_discrete_sequence=["#1f77b4"],  # Single color for all bars
                )
            else:
                # Visualization - vertical bar chart with stacked reasons
                # Use period_col for x-axis and reason for color (legend)
                # Use stacked mode to show all reasons in one column per period
                fig = px.bar(
                    reason_dynamics,
                    x=period_col,
                    y="Количество",
                    color="reason of deviation",
                    title="Динамика причин отклонений по периодам",
                    labels={
                        period_col: period_label,
                        "reason of deviation": "Причина отклонения",
                        "Количество": "Количество отклонений",
                    },
                    text="Количество",
                    barmode="stack",  # Stacked bars: all reasons in one column per period
                )
        # Update layout based on view type
        if view_type == "По причинам":
            # For "По причинам" view, no additional annotations needed
            pass
        else:
            # For "По месяцам" view, add annotations and trend line
            fig.update_xaxes(tickangle=-75, tickfont=dict(size=8), automargin=True)
            # Show values inside bars for each reason - horizontal text (same as other charts)
            fig.update_traces(
                textposition="inside", textfont=dict(size=12, color="white")
            )
            # Set text angle to horizontal (0 degrees) for inside bar labels - same as other charts
            for i, trace in enumerate(fig.data):
                fig.data[i].update(textangle=0)

            # Add total values above bars and trend line
            if selected_project == "Все":
                # For "Все проекты": use chart_data for annotations and trend
                total_by_period = (
                    chart_data.groupby(period_col)["Количество"].sum().reset_index()
                )
                periods = sorted(chart_data[period_col].unique())
                max_y_value = chart_data["Количество"].max()
            else:
                # Calculate total deviations per period for annotations
                total_by_period = (
                    reason_dynamics.groupby(period_col)["Количество"]
                    .sum()
                    .reset_index()
                )
                total_by_period_dict = dict(
                    zip(total_by_period[period_col], total_by_period["Количество"])
                )
                periods = sorted(reason_dynamics[period_col].unique())
                max_y_value = reason_dynamics["Количество"].max()

                # Add annotations for individual project view
                for period in periods:
                    total = total_by_period_dict.get(period, 0)
                    if total > 0:
                        # Get all bars for this period to find max height
                        period_bars = reason_dynamics[
                            reason_dynamics[period_col] == period
                        ]
                        if not period_bars.empty:
                            # Find the maximum height among all bars in this period group
                            max_bar_height = period_bars["Количество"].max()

                            # Calculate offset
                            if max_y_value > 0:
                                y_offset = max_y_value * 0.10
                            else:
                                y_offset = max_bar_height * 0.10

                            # Position annotation
                            x_position = period
                            y_position = max_bar_height + y_offset

                            fig.add_annotation(
                                x=x_position,
                                y=y_position,
                                text=f"<b>{int(total)}</b>",
                                showarrow=False,
                                font=dict(size=14, color="white"),
                                xanchor="center",
                                yanchor="bottom",
                                bgcolor="rgba(0,0,0,0.5)",
                                xshift=10,
                            )

            # Add trend line if checkbox is checked
            if show_trend:
                # Calculate overall trend across all reasons (sum by period)
                total_by_period_sorted = total_by_period.sort_values(period_col)
                if len(total_by_period_sorted) > 1:
                    # Use period values as x positions
                    x_positions = total_by_period_sorted[period_col].tolist()
                    y_values = total_by_period_sorted["Количество"].values

                    # Create numeric x values for trend calculation (for fitting)
                    x_numeric = range(len(y_values))

                    # Calculate linear trend
                    z = np.polyfit(x_numeric, y_values, 1)
                    p = np.poly1d(z)
                    trend_y = p(x_numeric)

                    # Add single trend line across all data
                    fig.add_trace(
                        go.Scatter(
                            x=x_positions,
                            y=trend_y,
                            mode="lines",
                            name="Линия тренда",
                            line=dict(dash="dash", width=3, color="white"),
                            showlegend=True,
                            hoverinfo="skip",
                        )
                    )
        fig = apply_chart_background(fig)
        st.plotly_chart(fig, use_container_width=True)

        # Summary table - always show by reason (summarized values)
        # Group by reason and sum across all periods
        summary_by_reason = (
            reason_dynamics.groupby("reason of deviation")["Количество"]
            .sum()
            .reset_index()
        )
        summary_by_reason.columns = ["Причина отклонения", "Суммарное количество"]
        summary_by_reason = summary_by_reason.sort_values(
            "Суммарное количество", ascending=False
        )

        st.subheader("Сводная таблица")
        # Rename columns to Russian before display
        summary_by_reason_display = summary_by_reason.rename(columns={
            "reason of deviation": "Причина отклонения",
            "period": "Период"
        })
        # Apply conditional formatting: positive values in red, negative/zero in green
        conditional_cols = {
            "Суммарное количество": {
                "positive_color": "#ff4444",  # Red for positive
                "negative_color": "#44ff44"   # Green for negative/zero
            }
        }
        html_table = format_dataframe_as_html(summary_by_reason_display, conditional_cols=conditional_cols)
        st.markdown(html_table, unsafe_allow_html=True)
    else:
        st.warning("Столбец 'reason of deviation' не найден в данных.")


# ==================== DASHBOARD 6: Budget Plan/Fact/Reserve by Project by Period ====================
def dashboard_budget_by_period(df):
    st.header("💰 БДДС по месяцам")

    # Filters row 1: Period and Project
    col1, col2 = st.columns(2)

    with col1:
        period_type = st.selectbox(
            "Группировать по", ["Месяц", "Квартал", "Год"], key="budget_period"
        )
        period_map = {"Месяц": "Month", "Квартал": "Quarter", "Год": "Year"}
        period_type_en = period_map.get(period_type, "Month")

    with col2:
        if "project name" in df.columns:
            projects = ["Все"] + sorted(df["project name"].dropna().unique().tolist())
            selected_project = st.selectbox(
                "Фильтр по проекту", projects, key="budget_project"
            )
        else:
            selected_project = "Все"

    # Filters row 2: Section
    col3 = st.columns(1)[0]
    with col3:
        # Section filter
        if "section" in df.columns:
            sections = ["Все"] + sorted(df["section"].dropna().unique().tolist())
            selected_section = st.selectbox(
                "Фильтр по этапу", sections, key="budget_section"
            )
        else:
            selected_section = "Все"

    # Filters row 3: Hide adjusted budget and Hide reserve budget
    col4, col5 = st.columns(2)

    with col4:
        # Checkbox to hide/show adjusted budget
        hide_adjusted = st.checkbox(
            "Скрыть скорректированный бюджет",
            value=True,
            key="budget_period_hide_adjusted",
        )

    with col5:
        # Checkbox to hide/show reserve budget
        hide_reserve = st.checkbox(
            "Скрыть резерв бюджета", value=True, key="budget_period_hide_reserve"
        )

    # Set view_type to "За месяц" (monthly view only)
    view_type = "За месяц"

    # Apply filters
    filtered_df = df.copy()
    if selected_project != "Все" and "project name" in filtered_df.columns:
        filtered_df = filtered_df[
            filtered_df["project name"].astype(str).str.strip()
            == str(selected_project).strip()
        ]
    if selected_section != "Все" and "section" in filtered_df.columns:
        filtered_df = filtered_df[
            filtered_df["section"].astype(str).str.strip()
            == str(selected_section).strip()
        ]

    # Check for budget columns
    has_budget = (
        "budget plan" in filtered_df.columns and "budget fact" in filtered_df.columns
    )

    if not has_budget:
        st.warning("Столбцы бюджета (budget plan, budget fact) не найдены в данных.")
        return

    # Determine adjusted budget column name
    adjusted_budget_col = None
    if "budget adjusted" in filtered_df.columns:
        adjusted_budget_col = "budget adjusted"
    elif "adjusted budget" in filtered_df.columns:
        adjusted_budget_col = "adjusted budget"

    # Determine period column
    if period_type_en == "Month":
        period_col = "plan_month"
        period_label = "Месяц"
    elif period_type_en == "Quarter":
        period_col = "plan_quarter"
        period_label = "Квартал"
    else:
        period_col = "plan_year"
        period_label = "Год"

    if period_col not in filtered_df.columns:
        st.warning(f"Столбец периода '{period_col}' не найден.")
        return

    # Calculate reserve budget (plan - fact, negative means over budget)
    # Convert to numeric first to avoid TypeError
    filtered_df["budget plan"] = pd.to_numeric(
        filtered_df["budget plan"], errors="coerce"
    )
    filtered_df["budget fact"] = pd.to_numeric(
        filtered_df["budget fact"], errors="coerce"
    )
    filtered_df["reserve budget"] = (
        filtered_df["budget plan"] - filtered_df["budget fact"]
    )

    # Convert adjusted budget to numeric if it exists
    if adjusted_budget_col:
        filtered_df[adjusted_budget_col] = pd.to_numeric(
            filtered_df[adjusted_budget_col], errors="coerce"
        )

    # Group by period and project
    agg_dict = {"budget plan": "sum", "budget fact": "sum", "reserve budget": "sum"}
    if adjusted_budget_col:
        agg_dict[adjusted_budget_col] = "sum"

    budget_summary = (
        filtered_df.groupby([period_col, "project name"]).agg(agg_dict).reset_index()
    )

    # Format period for display
    def format_period_display(period_val):
        if pd.isna(period_val):
            return "Н/Д"
        if isinstance(period_val, pd.Period):
            try:
                if period_val.freqstr == "M" or period_val.freqstr.startswith(
                    "M"
                ):  # Month
                    month_name = get_russian_month_name(period_val)
                    year = period_val.year
                    return f"{month_name} {year}"
                elif period_val.freqstr == "Q" or period_val.freqstr.startswith(
                    "Q"
                ):  # Quarter
                    return f"Q{period_val.quarter} {period_val.year}"
                elif period_val.freqstr == "Y" or period_val.freqstr == "A-DEC":  # Year
                    return str(period_val.year)
                else:
                    month_name = get_russian_month_name(period_val)
                    year = period_val.year
                    return f"{month_name} {year}"
            except:
                # Try parsing as string
                period_str = str(period_val)
                try:
                    if "-" in period_str:
                        parts = period_str.split("-")
                        if len(parts) >= 2:
                            year = parts[0]
                            month = parts[1]
                            month_num = int(month)
                            month_name = RUSSIAN_MONTHS.get(month_num, "")
                            if month_name:
                                return f"{month_name} {year}"
                except:
                    pass
                return str(period_val)
        elif isinstance(period_val, str):
            # Try parsing string like "2025-01"
            try:
                if "-" in period_val:
                    parts = period_val.split("-")
                    if len(parts) >= 2:
                        year = parts[0]
                        month = parts[1]
                        month_num = int(month)
                        month_name = RUSSIAN_MONTHS.get(month_num, "")
                        if month_name:
                            return f"{month_name} {year}"
            except:
                pass
        return str(period_val)

    # Store original period values for sorting before formatting
    budget_summary["period_original"] = budget_summary[period_col]
    budget_summary[period_col] = budget_summary[period_col].apply(format_period_display)

    # Visualizations
    # Bar chart for selected period
    if selected_project != "Все":
        project_data = budget_summary[
            budget_summary["project name"] == selected_project
        ].copy()
    else:
        # Aggregate across all projects
        agg_dict_all = {
            "budget plan": "sum",
            "budget fact": "sum",
            "reserve budget": "sum",
            "period_original": "first",  # Keep first period_original for sorting
        }
        if adjusted_budget_col:
            agg_dict_all[adjusted_budget_col] = "sum"
        project_data = (
            budget_summary.groupby(period_col).agg(agg_dict_all).reset_index()
        )

    # Sort by original period value to ensure correct order for cumulative calculation
    # Convert period_original to sortable format if it's Period objects
    if "period_original" in project_data.columns:
        if project_data["period_original"].dtype == "object":
            # Try to convert to sortable format
            try:
                project_data["period_sort"] = project_data["period_original"].apply(
                    lambda x: (
                        x
                        if isinstance(x, pd.Period)
                        else (
                            pd.Period(str(x), freq=period_type_en[0])
                            if pd.notna(x)
                            else None
                        )
                    )
                )
                project_data = project_data.sort_values("period_sort").copy()
                project_data = project_data.drop("period_sort", axis=1)
            except:
                # If conversion fails, try to sort by string representation
                project_data = project_data.sort_values("period_original").copy()
        else:
            project_data = project_data.sort_values("period_original").copy()
        # Remove period_original after sorting
        project_data = project_data.drop(columns=["period_original"], errors="ignore")

    # Calculate cumulative sums if "Накопительно" is selected
    if view_type == "Накопительно":
        project_data["budget plan"] = project_data["budget plan"].cumsum()
        project_data["budget fact"] = project_data["budget fact"].cumsum()
        project_data["reserve budget"] = project_data["reserve budget"].cumsum()
        if adjusted_budget_col and adjusted_budget_col in project_data.columns:
            project_data[adjusted_budget_col] = project_data[
                adjusted_budget_col
            ].cumsum()
        title_suffix = " (накопительно)"
    else:
        title_suffix = ""

    # Convert to millions for display
    project_data["budget plan_millions"] = project_data["budget plan"] / 1_000_000
    project_data["budget fact_millions"] = project_data["budget fact"] / 1_000_000
    project_data["reserve budget_millions"] = project_data["reserve budget"] / 1_000_000
    if adjusted_budget_col and adjusted_budget_col in project_data.columns:
        project_data[f"{adjusted_budget_col}_millions"] = project_data[adjusted_budget_col] / 1_000_000

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=project_data[period_col],
            y=project_data["budget plan_millions"],
            name="Бюджет План",
            marker_color="#2E86AB",
            text=project_data["budget plan_millions"].apply(
                lambda x: (
                    f"{x:.2f}" if pd.notna(x) and x != 0 else "" if pd.notna(x) else ""
                )
            ),
            textposition="outside",
            textfont=dict(size=14, color="white"),
            customdata=project_data["budget plan_millions"].apply(
                lambda x: f"{x:.2f}" if pd.notna(x) else ""
            ),
            hovertemplate="<b>%{x}</b><br>Бюджет План: %{customdata} млн руб.<br><extra></extra>",
        )
    )
    fig.add_trace(
        go.Bar(
            x=project_data[period_col],
            y=project_data["budget fact_millions"],
            name="Бюджет Факт",
            marker_color="#A23B72",
            text=project_data["budget fact_millions"].apply(
                lambda x: (
                    f"{x:.2f}" if pd.notna(x) and x != 0 else "" if pd.notna(x) else ""
                )
            ),
            textposition="outside",
            textfont=dict(size=14, color="white"),
            customdata=project_data["budget fact_millions"].apply(
                lambda x: f"{x:.2f}" if pd.notna(x) else ""
            ),
            hovertemplate="<b>%{x}</b><br>Бюджет Факт: %{customdata} млн руб.<br><extra></extra>",
        )
    )

    # Add reserve budget only if checkbox is not checked (reserve is not hidden)
    if not hide_reserve:
        fig.add_trace(
            go.Bar(
                x=project_data[period_col],
                y=project_data["reserve budget_millions"],
                name="Резерв бюджета",
                marker_color="#06A77D",
                text=project_data["reserve budget_millions"].apply(
                    lambda x: (
                        f"{x:.2f}"
                        if pd.notna(x) and x != 0
                        else "" if pd.notna(x) else ""
                    )
                ),
                textposition="outside",
                textfont=dict(size=14, color="white"),
                customdata=project_data["reserve budget_millions"].apply(
                    lambda x: f"{x:.2f}" if pd.notna(x) else ""
                ),
                hovertemplate="<b>%{x}</b><br>Резерв бюджета: %{customdata} млн руб.<br><extra></extra>",
            )
        )

    # Add adjusted budget if available and not hidden
    if (
        adjusted_budget_col
        and adjusted_budget_col in project_data.columns
        and not hide_adjusted
    ):
        fig.add_trace(
            go.Bar(
                x=project_data[period_col],
                y=project_data[f"{adjusted_budget_col}_millions"],
                name="Скорректированный бюджет",
                marker_color="#F18F01",
                text=project_data[f"{adjusted_budget_col}_millions"].apply(
                    lambda x: (
                        f"{x:.2f}"
                        if pd.notna(x) and x != 0
                        else "" if pd.notna(x) else ""
                    )
                ),
                textposition="outside",
                textfont=dict(size=14, color="white"),
                customdata=project_data[f"{adjusted_budget_col}_millions"].apply(
                    lambda x: f"{x:.2f}" if pd.notna(x) else ""
                ),
                hovertemplate="<b>%{x}</b><br>Скорректированный бюджет: %{customdata} млн руб.<br><extra></extra>",
            )
        )

    fig.update_layout(
        title=f"БДДС{title_suffix}",
        xaxis_title=period_label,
        yaxis_title="Сумма бюджета, млн руб.",
        barmode="group",
        xaxis=dict(tickangle=-75, tickfont=dict(size=8), automargin=True),
    )
    fig = apply_chart_background(fig)
    st.plotly_chart(fig, use_container_width=True)

    # Summary table - remove period_original and rename columns to Russian, convert to millions
    budget_summary_display = budget_summary.drop(columns=["period_original"], errors="ignore").copy()
    # Convert to millions
    budget_summary_display["budget plan"] = (budget_summary_display["budget plan"] / 1_000_000).round(2)
    budget_summary_display["budget fact"] = (budget_summary_display["budget fact"] / 1_000_000).round(2)
    # Add reserve budget column: факт - план
    budget_summary_display["Резервный бюджет"] = (budget_summary_display["budget fact"] - budget_summary_display["budget plan"]).round(2)
    # Remove "reserve budget" column if it exists
    budget_summary_display = budget_summary_display.drop(columns=["reserve budget"], errors="ignore")
    if adjusted_budget_col and adjusted_budget_col in budget_summary_display.columns:
        budget_summary_display[adjusted_budget_col] = (budget_summary_display[adjusted_budget_col] / 1_000_000).round(2)
    budget_summary_display = budget_summary_display.rename(columns={
        period_col: period_label,
        "budget plan": "Бюджет План, млн руб.",
        "budget fact": "Бюджет Факт, млн руб.",
        "project name": "Проект",
        "section": "Этап"
    })
    if adjusted_budget_col and adjusted_budget_col in budget_summary_display.columns:
        budget_summary_display = budget_summary_display.rename(columns={
            adjusted_budget_col: "Скорректированный бюджет, млн руб."
        })
    st.subheader(f"Сводка бюджета по {period_label.lower()}")
    # Use format_dataframe_as_html with conditional formatting for reserve budget column
    conditional_cols = {
        "Резервный бюджет": {
            'positive_color': '#ff4444',
            'negative_color': '#44ff44'
        }
    }
    html_table = format_dataframe_as_html(budget_summary_display, conditional_cols=conditional_cols)
    st.markdown(html_table, unsafe_allow_html=True)


# ==================== DASHBOARD 6.5: Budget Cumulative ====================
def dashboard_budget_cumulative(df):
    st.header("💰 БДДС накопительно")

    # Filters row 1: Period and Project
    col1, col2 = st.columns(2)

    with col1:
        period_type = st.selectbox(
            "Группировать по", ["Месяц", "Квартал", "Год"], key="budget_cum_period"
        )
        period_map = {"Месяц": "Month", "Квартал": "Quarter", "Год": "Year"}
        period_type_en = period_map.get(period_type, "Month")

    with col2:
        if "project name" in df.columns:
            projects = ["Все"] + sorted(df["project name"].dropna().unique().tolist())
            selected_project = st.selectbox(
                "Фильтр по проекту", projects, key="budget_cum_project"
            )
        else:
            selected_project = "Все"

    # Filters row 2: Section
    col3 = st.columns(1)[0]
    with col3:
        # Section filter
        if "section" in df.columns:
            sections = ["Все"] + sorted(df["section"].dropna().unique().tolist())
            selected_section = st.selectbox(
                "Фильтр по этапу", sections, key="budget_cum_section"
            )
        else:
            selected_section = "Все"

    # Apply filters
    filtered_df = df.copy()
    if selected_project != "Все" and "project name" in filtered_df.columns:
        filtered_df = filtered_df[
            filtered_df["project name"].astype(str).str.strip()
            == str(selected_project).strip()
        ]
    if selected_section != "Все" and "section" in filtered_df.columns:
        filtered_df = filtered_df[
            filtered_df["section"].astype(str).str.strip()
            == str(selected_section).strip()
        ]

    # Check for budget columns
    has_budget = (
        "budget plan" in filtered_df.columns and "budget fact" in filtered_df.columns
    )

    if not has_budget:
        st.warning("Столбцы бюджета (budget plan, budget fact) не найдены в данных.")
        return

    # Determine adjusted budget column name
    adjusted_budget_col = None
    if "budget adjusted" in filtered_df.columns:
        adjusted_budget_col = "budget adjusted"
    elif "adjusted budget" in filtered_df.columns:
        adjusted_budget_col = "adjusted budget"

    # Determine period column
    if period_type_en == "Month":
        period_col = "plan_month"
        period_label = "Месяц"
    elif period_type_en == "Quarter":
        period_col = "plan_quarter"
        period_label = "Квартал"
    else:
        period_col = "plan_year"
        period_label = "Год"

    if period_col not in filtered_df.columns:
        st.warning(f"Столбец периода '{period_col}' не найден.")
        return

    # Convert to numeric
    filtered_df["budget plan"] = pd.to_numeric(
        filtered_df["budget plan"], errors="coerce"
    )
    filtered_df["budget fact"] = pd.to_numeric(
        filtered_df["budget fact"], errors="coerce"
    )
    if adjusted_budget_col:
        filtered_df[adjusted_budget_col] = pd.to_numeric(
            filtered_df[adjusted_budget_col], errors="coerce"
        )

    # Group by period and project
    agg_dict = {"budget plan": "sum", "budget fact": "sum"}
    if adjusted_budget_col:
        agg_dict[adjusted_budget_col] = "sum"

    budget_summary = (
        filtered_df.groupby([period_col, "project name"]).agg(agg_dict).reset_index()
    )

    # Format period for display
    def format_period_display(period_val):
        if pd.isna(period_val):
            return "Н/Д"
        if isinstance(period_val, pd.Period):
            try:
                if period_val.freqstr == "M" or period_val.freqstr.startswith(
                    "M"
                ):  # Month
                    month_name = get_russian_month_name(period_val)
                    year = period_val.year
                    return f"{month_name} {year}"
                elif period_val.freqstr == "Q" or period_val.freqstr.startswith(
                    "Q"
                ):  # Quarter
                    return f"Q{period_val.quarter} {period_val.year}"
                elif period_val.freqstr == "Y" or period_val.freqstr == "A-DEC":  # Year
                    return str(period_val.year)
                else:
                    month_name = get_russian_month_name(period_val)
                    year = period_val.year
                    return f"{month_name} {year}"
            except:
                # Try parsing as string
                period_str = str(period_val)
                try:
                    if "-" in period_str:
                        parts = period_str.split("-")
                        if len(parts) >= 2:
                            year = parts[0]
                            month = parts[1]
                            month_num = int(month)
                            month_name = RUSSIAN_MONTHS.get(month_num, "")
                            if month_name:
                                return f"{month_name} {year}"
                except:
                    pass
                return str(period_val)
        elif isinstance(period_val, str):
            # Try parsing string like "2025-01"
            try:
                if "-" in period_val:
                    parts = period_val.split("-")
                    if len(parts) >= 2:
                        year = parts[0]
                        month = parts[1]
                        month_num = int(month)
                        month_name = RUSSIAN_MONTHS.get(month_num, "")
                        if month_name:
                            return f"{month_name} {year}"
            except:
                pass
        return str(period_val)

    budget_summary[period_col] = budget_summary[period_col].apply(format_period_display)

    # Aggregate data
    if selected_project != "Все":
        project_data = budget_summary[
            budget_summary["project name"] == selected_project
        ]
    else:
        agg_dict_all = {"budget plan": "sum", "budget fact": "sum"}
        if adjusted_budget_col:
            agg_dict_all[adjusted_budget_col] = "sum"
        project_data = (
            budget_summary.groupby(period_col).agg(agg_dict_all).reset_index()
        )

    # Sort data by period to ensure correct cumulative calculation
    project_data_sorted = project_data.sort_values(period_col).copy()

    # Calculate cumulative sums
    project_data_sorted["budget plan_cum"] = project_data_sorted["budget plan"].cumsum()
    project_data_sorted["budget fact_cum"] = project_data_sorted["budget fact"].cumsum()
    if adjusted_budget_col and adjusted_budget_col in project_data_sorted.columns:
        project_data_sorted[f"{adjusted_budget_col}_cum"] = project_data_sorted[
            adjusted_budget_col
        ].cumsum()

    # Convert to millions for display
    project_data_sorted["budget plan_cum_millions"] = project_data_sorted["budget plan_cum"] / 1_000_000
    project_data_sorted["budget fact_cum_millions"] = project_data_sorted["budget fact_cum"] / 1_000_000
    if adjusted_budget_col and adjusted_budget_col in project_data_sorted.columns:
        project_data_sorted[f"{adjusted_budget_col}_cum_millions"] = project_data_sorted[f"{adjusted_budget_col}_cum"] / 1_000_000

    # Create cumulative chart
    fig_cum = go.Figure()
    fig_cum.add_trace(
        go.Bar(
            x=project_data_sorted[period_col],
            y=project_data_sorted["budget plan_cum_millions"],
            name="Бюджет План (накопительно)",
            marker_color="#2E86AB",
            text=project_data_sorted["budget plan_cum_millions"].apply(
                lambda x: f"{x:.2f}" if pd.notna(x) else ""
            ),
            textposition="outside",
            textfont=dict(size=14, color="white"),
        )
    )
    fig_cum.add_trace(
        go.Bar(
            x=project_data_sorted[period_col],
            y=project_data_sorted["budget fact_cum_millions"],
            name="Бюджет Факт (накопительно)",
            marker_color="#A23B72",
            text=project_data_sorted["budget fact_cum_millions"].apply(
                lambda x: f"{x:.2f}" if pd.notna(x) else ""
            ),
            textposition="outside",
            textfont=dict(size=14, color="white"),
        )
    )

    # Add adjusted budget cumulative if available
    if adjusted_budget_col and adjusted_budget_col in project_data_sorted.columns:
        fig_cum.add_trace(
            go.Bar(
                x=project_data_sorted[period_col],
                y=project_data_sorted[f"{adjusted_budget_col}_cum_millions"],
                name="Скорректированный бюджет (накопительно)",
                marker_color="#F18F01",
                text=project_data_sorted[f"{adjusted_budget_col}_cum_millions"].apply(
                    lambda x: f"{x:.2f}" if pd.notna(x) else ""
                ),
                textposition="outside",
                textfont=dict(size=14, color="white"),
            )
        )

    fig_cum.update_layout(
        title="БДДС накопительно",
        xaxis_title=period_label,
        yaxis_title="Сумма бюджета, млн руб.",
        barmode="group",
        xaxis=dict(tickangle=-75, tickfont=dict(size=8), automargin=True),
    )
    fig_cum = apply_chart_background(fig_cum)
    st.plotly_chart(fig_cum, use_container_width=True)

    # Summary table with cumulative data - rename columns to Russian, convert to millions
    st.subheader(f"Сводка бюджета (накопительно) по {period_label.lower()}")
    summary_cum = project_data_sorted[
        [period_col, "budget plan_cum_millions", "budget fact_cum_millions"]
    ].copy()
    if (
        adjusted_budget_col
        and f"{adjusted_budget_col}_cum_millions" in project_data_sorted.columns
    ):
        summary_cum[f"{adjusted_budget_col}_cum_millions"] = project_data_sorted[
            f"{adjusted_budget_col}_cum_millions"
        ]
    # Round to 2 decimal places
    summary_cum["budget plan_cum_millions"] = summary_cum["budget plan_cum_millions"].round(2)
    summary_cum["budget fact_cum_millions"] = summary_cum["budget fact_cum_millions"].round(2)
    if adjusted_budget_col and f"{adjusted_budget_col}_cum_millions" in summary_cum.columns:
        summary_cum[f"{adjusted_budget_col}_cum_millions"] = summary_cum[f"{adjusted_budget_col}_cum_millions"].round(2)
    # Rename columns to Russian
    rename_dict = {
        period_col: period_label,
        "budget plan_cum_millions": "Бюджет План (накопительно), млн руб.",
        "budget fact_cum_millions": "Бюджет Факт (накопительно), млн руб.",
    }
    if adjusted_budget_col and f"{adjusted_budget_col}_cum_millions" in summary_cum.columns:
        rename_dict[f"{adjusted_budget_col}_cum_millions"] = "Скорректированный бюджет (накопительно), млн руб."
    summary_cum = summary_cum.rename(columns=rename_dict)
    html_table = format_dataframe_as_html(summary_cum)
    st.markdown(html_table, unsafe_allow_html=True)


# ==================== DASHBOARD 7: Budget Plan/Fact/Reserve by Section by Period ====================
def dashboard_budget_by_section(df):
    st.header("💰 БДДС по лотам")

    col1, col2, col3 = st.columns(3)

    with col1:
        period_type = st.selectbox(
            "Группировать по", ["Месяц", "Квартал", "Год"], key="budget_section_period"
        )
        period_map = {"Месяц": "Month", "Квартал": "Quarter", "Год": "Year"}
        period_type_en = period_map.get(period_type, "Month")

    with col2:
        if "section" in df.columns:
            sections = ["Все"] + sorted(df["section"].dropna().unique().tolist())
            selected_section = st.selectbox(
                "Фильтр по этапу", sections, key="budget_section"
            )
        else:
            selected_section = "Все"

    with col3:
        # Filter for monthly or cumulative view
        view_type = st.selectbox(
            "Вид отображения", ["За месяц", "Накопительно"], key="budget_section_view"
        )

    # Apply filters
    filtered_df = df.copy()
    if selected_section != "Все" and "section" in filtered_df.columns:
        filtered_df = filtered_df[
            filtered_df["section"].astype(str).str.strip()
            == str(selected_section).strip()
        ]

    # Check for budget columns
    has_budget = (
        "budget plan" in filtered_df.columns and "budget fact" in filtered_df.columns
    )

    if not has_budget:
        st.warning("Столбцы бюджета (budget plan, budget fact) не найдены в данных.")
        return

    # Determine period column
    if period_type_en == "Month":
        period_col = "plan_month"
        period_label = "Месяц"
    elif period_type_en == "Quarter":
        period_col = "plan_quarter"
        period_label = "Квартал"
    else:
        period_col = "plan_year"
        period_label = "Год"

    if period_col not in filtered_df.columns:
        st.warning(f"Столбец периода '{period_col}' не найден.")
        return

    # Calculate reserve budget (fact - plan)
    # Convert to numeric first to avoid TypeError
    filtered_df["budget plan"] = pd.to_numeric(
        filtered_df["budget plan"], errors="coerce"
    )
    filtered_df["budget fact"] = pd.to_numeric(
        filtered_df["budget fact"], errors="coerce"
    )
    filtered_df["reserve budget"] = (
        filtered_df["budget fact"] - filtered_df["budget plan"]
    )

    # Group by period and section
    budget_summary = (
        filtered_df.groupby([period_col, "section"])
        .agg({"budget plan": "sum", "budget fact": "sum", "reserve budget": "sum"})
        .reset_index()
    )

    # Format period for display
    def format_period_display(period_val):
        if pd.isna(period_val):
            return "Н/Д"
        if isinstance(period_val, pd.Period):
            try:
                if period_val.freqstr == "M" or period_val.freqstr.startswith(
                    "M"
                ):  # Month
                    month_name = get_russian_month_name(period_val)
                    year = period_val.year
                    return f"{month_name} {year}"
                elif period_val.freqstr == "Q" or period_val.freqstr.startswith(
                    "Q"
                ):  # Quarter
                    return f"Q{period_val.quarter} {period_val.year}"
                elif period_val.freqstr == "Y" or period_val.freqstr == "A-DEC":  # Year
                    return str(period_val.year)
                else:
                    month_name = get_russian_month_name(period_val)
                    year = period_val.year
                    return f"{month_name} {year}"
            except:
                # Try parsing as string
                period_str = str(period_val)
                try:
                    if "-" in period_str:
                        parts = period_str.split("-")
                        if len(parts) >= 2:
                            year = parts[0]
                            month = parts[1]
                            month_num = int(month)
                            month_name = RUSSIAN_MONTHS.get(month_num, "")
                            if month_name:
                                return f"{month_name} {year}"
                except:
                    pass
                return str(period_val)
        elif isinstance(period_val, str):
            # Try parsing string like "2025-01"
            try:
                if "-" in period_val:
                    parts = period_val.split("-")
                    if len(parts) >= 2:
                        year = parts[0]
                        month = parts[1]
                        month_num = int(month)
                        month_name = RUSSIAN_MONTHS.get(month_num, "")
                        if month_name:
                            return f"{month_name} {year}"
            except:
                pass
        return str(period_val)

    # Store original period values for sorting before formatting
    budget_summary["period_original"] = budget_summary[period_col]
    budget_summary[period_col] = budget_summary[period_col].apply(format_period_display)

    # Checkbox to hide/show reserve budget
    hide_reserve = st.checkbox(
        "Скрыть резерв", value=True, key="budget_section_hide_reserve"
    )

    # Filter by period for chart (show sections for selected period)
    available_periods = sorted(budget_summary[period_col].unique().tolist())
    if available_periods:
        selected_period_chart = st.selectbox(
            f"Выберите {period_label.lower()} для графика",
            options=["Все"] + available_periods,
            key="budget_section_period_chart"
        )
    else:
        selected_period_chart = "Все"

    # Prepare data for chart - group by sections
    if selected_period_chart != "Все":
        # Filter by selected period
        chart_data = budget_summary[
            budget_summary[period_col] == selected_period_chart
        ].copy()
    else:
        # Aggregate across all periods
        chart_data = (
            budget_summary.groupby("section")
            .agg(
                {
                    "budget plan": "sum",
                    "budget fact": "sum",
                    "reserve budget": "sum",
                }
            )
            .reset_index()
        )

    # Sort by budget plan descending
    chart_data = chart_data.sort_values("budget plan", ascending=False).copy()

    # Round values to millions for display
    chart_data["budget plan_millions"] = chart_data["budget plan"] / 1_000_000
    chart_data["budget fact_millions"] = chart_data["budget fact"] / 1_000_000
    chart_data["reserve budget_millions"] = chart_data["reserve budget"] / 1_000_000

    # Create horizontal bar chart with sections on Y axis
    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            y=chart_data["section"],
            x=chart_data["budget plan_millions"],
            name="Бюджет План",
            marker_color="#2E86AB",
            orientation='h',
            text=chart_data["budget plan_millions"].apply(
                lambda x: f"{x:.2f}" if pd.notna(x) else ""
            ),
            textposition="outside",
            textfont=dict(size=14, color="white"),
        )
    )
    fig.add_trace(
        go.Bar(
            y=chart_data["section"],
            x=chart_data["budget fact_millions"],
            name="Бюджет Факт",
            marker_color="#A23B72",
            orientation='h',
            text=chart_data["budget fact_millions"].apply(
                lambda x: f"{x:.2f}" if pd.notna(x) else ""
            ),
            textposition="outside",
            textfont=dict(size=14, color="white"),
        )
    )

    # Add reserve budget only if checkbox is not checked (reserve is not hidden)
    if not hide_reserve:
        fig.add_trace(
            go.Bar(
                y=chart_data["section"],
                x=chart_data["reserve budget_millions"],
                name="Резерв бюджета",
                marker_color="#06A77D",
                orientation='h',
                text=chart_data["reserve budget_millions"].apply(
                    lambda x: f"{x:.2f}" if pd.notna(x) else ""
                ),
                textposition="outside",
                textfont=dict(size=14, color="white"),
            )
        )

    period_suffix = f" ({selected_period_chart})" if selected_period_chart != "Все" else ""
    fig.update_layout(
        title=dict(text=f"План/факт/резерв по лотам{period_suffix}", font=dict(size=24)),
        xaxis_title=dict(text="Сумма бюджета, млн руб.", font=dict(size=20)),
        yaxis_title=dict(text="Этап", font=dict(size=20)),
        barmode="group",
        xaxis=dict(tickfont=dict(size=16)),
        yaxis=dict(tickfont=dict(size=14), tickangle=45),
        legend=dict(font=dict(size=18)),
        height=max(400, len(chart_data) * 40),
    )
    fig = apply_chart_background(fig)
    st.plotly_chart(fig, use_container_width=True)

    # Summary table - round to millions, remove period_original and rename columns
    budget_summary_display = budget_summary.drop(columns=["period_original"], errors="ignore").copy()
    budget_summary_display["budget plan"] = (budget_summary_display["budget plan"] / 1_000_000).round(2)
    budget_summary_display["budget fact"] = (budget_summary_display["budget fact"] / 1_000_000).round(2)
    # Add reserve budget column: факт - план
    budget_summary_display["Резервный бюджет"] = (budget_summary_display["budget fact"] - budget_summary_display["budget plan"]).round(2)
    # Remove "reserve budget" column if it exists
    budget_summary_display = budget_summary_display.drop(columns=["reserve budget"], errors="ignore")

    # Rename columns to Russian
    rename_dict = {
        period_col: period_label,
        "budget plan": "Бюджет План, млн руб.",
        "budget fact": "Бюджет Факт, млн руб.",
        "section": "Этап"
    }
    budget_summary_display = budget_summary_display.rename(columns=rename_dict)

    st.subheader("Сводка бюджета по периоду")

    # Use format_dataframe_as_html with conditional formatting for reserve budget column
    conditional_cols = {
        "Резервный бюджет": {
            'positive_color': '#ff4444',
            'negative_color': '#44ff44'
        }
    }
    html_table = format_dataframe_as_html(budget_summary_display, conditional_cols=conditional_cols)
    st.markdown(html_table, unsafe_allow_html=True)


# ==================== DASHBOARD 8.6: RD Delay Chart ====================
def dashboard_rd_delay(df):
    st.subheader("⏱️ Просрочка выдачи РД")

    # Find column names (they might have different formats)
    # Try to find columns by partial name matching
    def find_column(df, possible_names):
        """Find column by possible names"""
        for col in df.columns:
            # Normalize column name: remove newlines, extra spaces, normalize case
            col_normalized = str(col).replace("\n", " ").replace("\r", " ").strip()
            col_lower = col_normalized.lower()

            for name in possible_names:
                name_lower = name.lower().strip()
                # Exact match (case insensitive)
                if name_lower == col_lower:
                    return col
                # Substring match
                if name_lower in col_lower or col_lower in name_lower:
                    return col
                # Check if all key words from name are in column
                name_words = [w for w in name_lower.split() if len(w) > 2]
                if name_words and all(word in col_lower for word in name_words):
                    return col

        # Special handling for RD count column with key words
        if any(
            "разделов" in n.lower() and "рд" in n.lower() and "договор" in n.lower()
            for n in possible_names
        ):
            for col in df.columns:
                col_lower = str(col).lower().replace("\n", " ").replace("\r", " ")
                key_words = ["разделов", "рд", "договор", "количество"]
                if all(word in col_lower for word in key_words if len(word) > 3):
                    return col

        return None

    # Find required columns
    # Column for Y-axis: "Отклонение разделов РД" (exact match from CSV file)
    # This is column 17 in the CSV file (after header row)
    rd_deviation_col = None

    # First try exact match
    if "Отклонение разделов РД" in df.columns:
        rd_deviation_col = "Отклонение разделов РД"
    else:
        # Try with find_column function for variations
        rd_deviation_col = find_column(
            df,
            [
                "Отклонение разделов РД",
                "Отклонение разделов рд",
                "отклонение разделов рд",
                "Отклон. Количества разделов РД",
                "Отклонение количества разделов РД",
                "Отклон. разделов РД",
                "Отклонение разделов РД по Договору",
            ],
        )

        # Special handling: if not found, try to find by key words
        if not rd_deviation_col:
            for col in df.columns:
                col_lower = str(col).lower().replace("\n", " ").replace("\r", " ")
                key_words = ["отклон", "раздел", "рд"]
                if all(word in col_lower for word in key_words if len(word) > 3):
                    rd_deviation_col = col
                    break

    if not rd_deviation_col:
        st.warning("⚠️ Колонка 'Отклонение разделов РД' не найдена.")
        return

    # Find required columns
    plan_start_col = (
        "plan start"
        if "plan start" in df.columns
        else find_column(df, ["Старт План", "План Старт"])
    )
    project_col = (
        "project name"
        if "project name" in df.columns
        else find_column(df, ["Проект", "project"])
    )
    section_col = (
        "section" if "section" in df.columns else find_column(df, ["Раздел", "section"])
    )
    task_col = (
        "task name"
        if "task name" in df.columns
        else find_column(df, ["Задача", "task"])
    )

    # Check if required columns exist
    missing_cols = []
    if not project_col or project_col not in df.columns:
        missing_cols.append("Проект (project name)")
    if not section_col or section_col not in df.columns:
        missing_cols.append("Раздел (section)")
    if not task_col or task_col not in df.columns:
        missing_cols.append("Задача (task name)")

    if missing_cols:
        st.warning(f"⚠️ Отсутствуют необходимые колонки: {', '.join(missing_cols)}")
        st.info("Пожалуйста, убедитесь, что файл содержит все необходимые колонки.")
        return

    # Add filters
    st.subheader("Фильтры")
    filter_col1, filter_col2, filter_col3 = st.columns(3)

    # Project filter
    with filter_col1:
        try:
            projects = ["Все"] + sorted(df[project_col].dropna().unique().tolist())
            selected_project = st.selectbox(
                "Фильтр по проекту", projects, key="rd_delay_project"
            )
        except Exception as e:
            st.error(f"Ошибка при загрузке списка проектов: {str(e)}")
            return

    # Section filter
    with filter_col2:
        try:
            sections = ["Все"] + sorted(df[section_col].dropna().unique().tolist())
            selected_section = st.selectbox(
                "Фильтр по этапу", sections, key="rd_delay_section"
            )
        except Exception as e:
            st.error(f"Ошибка при загрузке списка разделов: {str(e)}")
            return

    # Apply filters
    filtered_df = df.copy()

    if selected_project != "Все":
        filtered_df = filtered_df[
            filtered_df[project_col].astype(str).str.strip()
            == str(selected_project).strip()
        ]

    if selected_section != "Все":
        filtered_df = filtered_df[
            filtered_df[section_col].astype(str).str.strip()
            == str(selected_section).strip()
        ]

    if filtered_df.empty:
        st.info("Нет данных для выбранных фильтров.")
        return

    # Prepare data for "Просрочка выдачи РД"
    # X-axis: "Задача" (each task is a separate bar)
    # Y-axis: "Отклонение разделов РД" (deviation values)
    try:
        # Convert "Отклонение разделов РД" to numeric - handle comma as decimal separator
        # First, get the raw column values
        rd_deviation_raw = filtered_df[rd_deviation_col].copy()

        # Convert to string, handling NaN properly
        rd_deviation_str = rd_deviation_raw.astype(str)

        # Replace various representations of empty/NaN values with empty string
        rd_deviation_str = rd_deviation_str.replace(
            ["nan", "None", "NaN", "NaT", "<NA>", "None"], ""
        )

        # Strip whitespace
        rd_deviation_str = rd_deviation_str.str.strip()

        # Replace comma with dot for decimal separator FIRST (European format: 6,00 -> 6.00)
        rd_deviation_str = rd_deviation_str.str.replace(",", ".", regex=False)

        # Now replace empty strings with '0' AFTER comma replacement
        rd_deviation_str = rd_deviation_str.replace("", "0")

        # Convert to numeric - this handles most cases
        filtered_df["rd_deviation_numeric"] = pd.to_numeric(
            rd_deviation_str, errors="coerce"
        ).fillna(0)

        # Determine grouping mode: if section is selected, show tasks; otherwise group by project
        show_by_tasks = selected_section != "Все"

        if show_by_tasks:
            # Prepare data for chart - each task is a separate bar
            # Create label combining section and task for better readability
            if section_col and section_col in filtered_df.columns:
                filtered_df["Задача_полная"] = (
                    filtered_df[section_col].astype(str)
                    + " | "
                    + filtered_df[task_col].astype(str)
                )
            else:
                filtered_df["Задача_полная"] = filtered_df[task_col].astype(str)

            chart_data = filtered_df[
                [task_col, "Задача_полная", "rd_deviation_numeric"]
            ].copy()
            chart_data.columns = ["Задача", "Задача_полная", "Отклонение разделов РД"]

            # Sort by deviation value (descending) to show largest deviations first
            chart_data = chart_data.sort_values(
                "Отклонение разделов РД", ascending=False
            )
            y_column = "Задача_полная"
            y_title = "Задача"
        else:
            # Group by project and sum deviations
            if project_col and project_col in filtered_df.columns:
                chart_data = (
                    filtered_df.groupby(project_col)
                    .agg({"rd_deviation_numeric": "sum"})
                    .reset_index()
                )
                chart_data.columns = ["Проект", "Отклонение разделов РД"]

                # Sort by deviation value (descending)
                chart_data = chart_data.sort_values(
                    "Отклонение разделов РД", ascending=False
                )
                y_column = "Проект"
                y_title = "Проект"
            else:
                st.info("Нет данных для построения графика.")
                return

        if chart_data.empty:
            st.info("Нет данных для построения графика.")
            return

        # Format text values for display on bars (same approach as "Отклонение от базового плана")
        text_values = []
        for _, row in chart_data.iterrows():
            val = row["Отклонение разделов РД"]
            if pd.notna(val):
                text_values.append(f"{val:.0f}")
            else:
                text_values.append("")

        # Create horizontal bar chart
        fig = px.bar(
            chart_data,
            x="Отклонение разделов РД",
            y=y_column,
            orientation="h",
            title="Просрочка выдачи РД",
            labels={
                y_column: y_title,
                "Отклонение разделов РД": "Отклонение разделов РД",
            },
            text=text_values,
            color_discrete_sequence=["#2E86AB"],  # Single color for all bars
        )

        # Format text labels (same as "Отклонение от базового плана")
        fig.update_traces(
            textposition="outside",
            textfont=dict(size=14, color="white"),
            marker=dict(line=dict(width=1, color="white")),
            showlegend=False,  # Hide legend
        )

        # Add vertical line at 0 to separate positive and negative deviations (without annotation)
        fig.add_vline(x=0, line_dash="dash", line_color="gray")

        # Set category order to show largest values at top (descending order)
        # For horizontal bars, reverse the list so largest is at top
        category_list = chart_data[y_column].tolist()
        fig.update_layout(
            xaxis_title="Отклонение разделов РД",
            yaxis_title=y_title,
            height=max(
                600, len(chart_data) * 40
            ),  # Adjust height based on number of items
            showlegend=False,
            yaxis=dict(
                tickangle=0,  # Horizontal labels
                categoryorder="array",
                categoryarray=list(
                    reversed(category_list)
                ),  # Reverse to show largest at top
            ),
            bargap=0.1,  # Reduce gap between bars to make them appear larger
        )
        fig = apply_chart_background(fig)
        st.plotly_chart(fig, use_container_width=True)

        # Summary table
        st.subheader("Сводка по просрочке")
        # Show appropriate columns based on grouping mode
        if show_by_tasks:
            summary_table = chart_data[
                ["Задача_полная", "Отклонение разделов РД"]
            ].copy()
            summary_table.columns = ["Задача", "Отклонение разделов РД"]
        else:
            summary_table = chart_data[["Проект", "Отклонение разделов РД"]].copy()
        html_table = format_dataframe_as_html(summary_table)
        st.markdown(html_table, unsafe_allow_html=True)

        # Summary metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            total_deviation = chart_data["Отклонение разделов РД"].sum()
            st.metric(
                "Сумма отклонений",
                f"{total_deviation:,.0f}" if pd.notna(total_deviation) else "Н/Д",
            )
        with col2:
            positive_deviation = chart_data[chart_data["Отклонение разделов РД"] > 0][
                "Отклонение разделов РД"
            ].sum()
            st.metric(
                "Положительные отклонения",
                f"{positive_deviation:,.0f}" if pd.notna(positive_deviation) else "0",
            )
        with col3:
            negative_deviation = chart_data[chart_data["Отклонение разделов РД"] < 0][
                "Отклонение разделов РД"
            ].sum()
            st.metric(
                "Отрицательные отклонения",
                f"{negative_deviation:,.0f}" if pd.notna(negative_deviation) else "0",
            )

    except Exception as e:
        st.error(f"Ошибка при построении графика 'Просрочка выдачи РД': {str(e)}")
        import traceback

        st.code(traceback.format_exc())


# ==================== DASHBOARD 8.6.5: Technique Visualization ====================
def dashboard_technique(df):
    st.header("🔧 Аналитика по технике")

    # Get technique data from session state
    technique_df = st.session_state.get("technique_data", None)

    if technique_df is None or technique_df.empty:
        st.warning(
            "⚠️ Для отображения аналитики по технике необходимо загрузить файл с данными о технике."
        )
        st.info(
            "📋 Ожидаемые колонки в файле: Проект, Контрагент, Период, План, Среднее за месяц, недели, Дельта"
        )
        return

    # Create working copy
    work_df = technique_df.copy()

    # Helper function to find columns by partial match (handles encoding issues)
    def find_column_by_partial(df, possible_names):
        """Find column by possible names (exact or partial match)"""
        for col in df.columns:
            col_lower = str(col).lower().strip()
            for name in possible_names:
                name_lower = str(name).lower().strip()
                if (
                    name_lower == col_lower
                    or name_lower in col_lower
                    or col_lower in name_lower
                ):
                    return col
        return None

    # Expected columns: Проект, Контрагент, Период, План, Среднее за месяц, 1 неделя, 2 неделя, 3 неделя, 4 неделя, 5 неделя, Дельта, Дельта (%)
    # Use Russian column names directly

    # Check required columns - Контрагент is essential
    if "Контрагент" not in work_df.columns:
        # Try to find contractor column by partial match
        contractor_col = find_column_by_partial(
            work_df,
            [
                "Контрагент",
                "контрагент",
                "Подразделение",
                "подразделение",
                "contractor",
            ],
        )
        if contractor_col:
            work_df["Контрагент"] = work_df[contractor_col]
        else:
            st.error(f"❌ Отсутствует необходимая колонка 'Контрагент'")
            st.info(f"Доступные колонки: {', '.join(work_df.columns)}")
            return

    # Find week columns dynamically - also try partial match
    week_columns = []
    for week_num in range(1, 6):
        week_col = f"{week_num} неделя"
        if week_col in work_df.columns:
            week_columns.append(week_col)
        else:
            # Try to find by partial match
            found_col = find_column_by_partial(
                work_df,
                [
                    week_col,
                    f"{week_num} недел",
                    f"недел {week_num}",
                    f"week {week_num}",
                ],
            )
            if found_col:
                week_columns.append(found_col)

    # Check if we have any data
    if work_df.empty:
        st.warning("⚠️ Данные пусты после обработки.")
        return

    # Process numeric columns
    # Process План
    if "План" in work_df.columns:
        work_df["План_numeric"] = pd.to_numeric(
            work_df["План"].astype(str).str.replace(",", ".").str.replace(" ", ""),
            errors="coerce",
        ).fillna(0)
    else:
        work_df["План_numeric"] = 0

    # Process week columns - convert to numeric, handle empty strings
    for week_col in week_columns:
        work_df[f"{week_col}_numeric"] = pd.to_numeric(
            work_df[week_col]
            .astype(str)
            .str.replace(",", ".")
            .str.replace(" ", "")
            .replace("", "0"),
            errors="coerce",
        ).fillna(0)

    # Calculate sum of weeks (fact for the month = среднее за месяц)
    # Handle "Среднее за месяц" for technique
    if "Среднее за месяц" in work_df.columns:
        # If we have Среднее за месяц (technique), use it directly as week_sum
        work_df["Среднее_за_месяц_numeric"] = pd.to_numeric(
            work_df["Среднее за месяц"]
            .astype(str)
            .str.replace(",", ".")
            .str.replace(" ", ""),
            errors="coerce",
        ).fillna(0)
        work_df["week_sum"] = work_df["Среднее_за_месяц_numeric"]
    elif week_columns:
        # Calculate from week columns if available
        week_numeric_cols = [f"{col}_numeric" for col in week_columns]
        work_df["week_sum"] = work_df[week_numeric_cols].sum(axis=1)
    else:
        work_df["week_sum"] = 0

    # Process Дельта (Delta) if available - try to find column by partial match
    delta_col = None
    if "Дельта" in work_df.columns:
        delta_col = "Дельта"
    else:
        delta_col = find_column_by_partial(
            work_df, ["Дельта", "дельта", "delta", "Delta", "Дельта (без %)"]
        )

    if delta_col and delta_col in work_df.columns:
        work_df["Дельта_numeric"] = pd.to_numeric(
            work_df[delta_col].astype(str).str.replace(",", ".").str.replace(" ", ""),
            errors="coerce",
        ).fillna(0)
    else:
        # Calculate delta as plan - fact (week_sum)
        work_df["Дельта_numeric"] = work_df["План_numeric"] - work_df["week_sum"]

    # Process Дельта (%) (Delta %) if available - extract numeric value from percentage string
    # Try to find column by partial match
    delta_pct_col = None
    if "Дельта (%)" in work_df.columns:
        delta_pct_col = "Дельта (%)"
    else:
        delta_pct_col = find_column_by_partial(
            work_df,
            [
                "Дельта (%)",
                "Дельта %",
                "дельта (%)",
                "дельта %",
                "Delta %",
                "delta %",
                "Дельта(%)",
                "Дельта%",
            ],
        )

    if delta_pct_col and delta_pct_col in work_df.columns:

        def extract_percentage(value):
            """Extract numeric value from percentage string like '-90%' or '90%', or numeric value"""
            if pd.isna(value):
                return 0
            # If already numeric, return as is
            if isinstance(value, (int, float)):
                return float(value)
            # Otherwise, try to extract from string
            value_str = str(value).strip()
            # Remove % sign and convert to float
            value_str = value_str.replace("%", "").replace(",", ".").replace(" ", "")
            try:
                return float(value_str)
            except:
                return 0

        work_df["Дельта_процент_numeric"] = work_df[delta_pct_col].apply(
            extract_percentage
        )
    else:
        # Calculate delta percentage if we have delta and plan
        work_df["Дельта_процент_numeric"] = 0
        if "Дельта_numeric" in work_df.columns and "План_numeric" in work_df.columns:
            mask = work_df["План_numeric"] != 0
            work_df.loc[mask, "Дельта_процент_numeric"] = (
                work_df.loc[mask, "Дельта_numeric"] / work_df.loc[mask, "План_numeric"]
            ) * 100
        work_df["Дельта_процент_numeric"] = work_df["Дельта_процент_numeric"].fillna(0)

    # Find Проект column
    period_col = None
    if "Период" in work_df.columns:
        period_col = "Период"
    else:
        # Try to find period column by partial match
        period_col = find_column_by_partial(
            work_df, ["Период", "период", "period", "Месяц", "месяц", "month"]
        )

    if period_col:
        # Parse period format like "дек.25" or "декабрь 2025"
        def parse_period(period_val):
            if pd.isna(period_val):
                return None
            period_str = str(period_val).strip()
            # Try to extract year and month
            # Format: "дек.25" -> period="дек.2025"
            # Format: "декабрь 2025" -> period="декабрь 2025"
            if "." in period_str:
                parts = period_str.split(".")
                if len(parts) >= 2:
                    month_part = parts[0].strip()
                    year_part = parts[1].strip()
                    try:
                        year = int(year_part)
                        if year < 100:
                            year = 2000 + year
                        return f"{month_part}.{year}"
                    except:
                        pass
            return period_str

        work_df["period_display"] = work_df[period_col].apply(parse_period)
    else:
        work_df["period_display"] = "Н/Д"

    # Find Проект column
    project_col = None
    if "Проект" in work_df.columns:
        project_col = "Проект"
    else:
        project_col = find_column_by_partial(
            work_df, ["Проект", "проект", "project", "Project"]
        )

    # Filters - project and contractor filters
    col1, col2 = st.columns(2)

    with col1:
        # Project filter - multiselect для выбора нескольких проектов
        if project_col and project_col in work_df.columns:
            all_projects = sorted(work_df[project_col].dropna().unique().tolist())
            selected_projects = st.multiselect(
                "Фильтр по проектам (можно выбрать несколько)",
                all_projects,
                default=all_projects if len(all_projects) <= 3 else all_projects[:3],
                key="technique_projects",
            )
        else:
            selected_projects = []
            st.info("Колонка 'Проект' не найдена")

    with col2:
        # Contractor filter
        if "Контрагент" in work_df.columns:
            contractors = ["Все"] + sorted(
                work_df["Контрагент"].dropna().unique().tolist()
            )
            selected_contractor = st.selectbox(
                "Фильтр по контрагенту", contractors, key="technique_contractor"
            )
        else:
            selected_contractor = "Все"
            st.info("Колонка 'Контрагент' не найдена")

    # Apply filters
    filtered_df = work_df.copy()
    if selected_projects and project_col and project_col in filtered_df.columns:
        # Фильтруем по выбранным проектам
        project_mask = (
            filtered_df[project_col]
            .astype(str)
            .str.strip()
            .isin([str(p).strip() for p in selected_projects])
        )
        filtered_df = filtered_df[project_mask]
    if selected_contractor != "Все" and "Контрагент" in filtered_df.columns:
        # Use string comparison with strip to handle whitespace
        filtered_df = filtered_df[
            filtered_df["Контрагент"].astype(str).str.strip()
            == str(selected_contractor).strip()
        ]

    if filtered_df.empty:
        st.info("Нет данных для отображения с выбранными фильтрами.")
        return

    # Ensure Контрагент column exists and has values
    if (
        "Контрагент" not in filtered_df.columns
        or filtered_df["Контрагент"].isna().all()
    ):
        st.error("❌ Колонка 'Контрагент' отсутствует или пуста после фильтрации.")
        return

    # Remove rows where Контрагент is NaN before grouping
    filtered_df = filtered_df[filtered_df["Контрагент"].notna()].copy()

    if filtered_df.empty:
        st.info("Нет данных с указанными контрагентами после фильтрации.")
        return

    # Определяем список проектов для обработки
    if selected_projects and project_col and project_col in filtered_df.columns:
        projects_to_process = selected_projects
    else:
        # Если проекты не выбраны или колонка не найдена, обрабатываем все проекты
        if project_col and project_col in filtered_df.columns:
            projects_to_process = sorted(
                filtered_df[project_col].dropna().unique().tolist()
            )
        else:
            projects_to_process = ["Все проекты"]

    # Обрабатываем каждый проект отдельно
    for project_name in projects_to_process:
        # Фильтруем данные по проекту
        project_filtered_df = filtered_df.copy()
        if (
            project_col
            and project_col in project_filtered_df.columns
            and project_name != "Все проекты"
        ):
            project_filtered_df = project_filtered_df[
                project_filtered_df[project_col].astype(str).str.strip()
                == str(project_name).strip()
            ]

        if project_filtered_df.empty:
            continue

        # Заголовок для проекта
        if len(projects_to_process) > 1:
            st.markdown("---")
            st.subheader(f"📊 Проект: {project_name}")

        # ========== Chart 1: Pie Chart by Contractor (Delta %) ==========
        st.subheader("📊 Круговая диаграмма: Распределение дельты (%) по контрагентам")

        # Group by Контрагент and aggregate for pie chart (Delta %)
        # Ensure Дельта_процент_numeric exists - check if it was created in work_df
        if "Дельта_процент_numeric" not in project_filtered_df.columns:
            # Try to find Дельта (%) column by partial match
            delta_pct_col = None
            if "Дельта (%)" in project_filtered_df.columns:
                delta_pct_col = "Дельта (%)"
            else:
                delta_pct_col = find_column_by_partial(
                    project_filtered_df,
                    [
                        "Дельта (%)",
                        "Дельта %",
                        "дельта (%)",
                        "дельта %",
                        "Delta %",
                        "delta %",
                        "Дельта(%)",
                        "Дельта%",
                    ],
                )

            if delta_pct_col and delta_pct_col in project_filtered_df.columns:
                # Extract percentage values from the column
                def extract_percentage(value):
                    """Extract numeric value from percentage string like '-90%' or '90%', or numeric value"""
                    if pd.isna(value):
                        return 0
                    # If already numeric, return as is
                    if isinstance(value, (int, float)):
                        return float(value)
                    # Otherwise, try to extract from string
                    value_str = str(value).strip()
                    # Remove % sign and convert to float
                    value_str = (
                        value_str.replace("%", "").replace(",", ".").replace(" ", "")
                    )
                    try:
                        return float(value_str)
                    except:
                        return 0

                project_filtered_df["Дельта_процент_numeric"] = project_filtered_df[
                    delta_pct_col
                ].apply(extract_percentage)
            else:
                # Try to calculate from Дельта and План if available
                if (
                    "Дельта_numeric" in project_filtered_df.columns
                    and "План_numeric" in project_filtered_df.columns
                ):
                    project_filtered_df["Дельта_процент_numeric"] = 0
                    mask = project_filtered_df["План_numeric"] != 0
                    project_filtered_df.loc[mask, "Дельта_процент_numeric"] = (
                        project_filtered_df.loc[mask, "Дельта_numeric"]
                        / project_filtered_df.loc[mask, "План_numeric"]
                    ) * 100
                    project_filtered_df["Дельта_процент_numeric"] = project_filtered_df[
                        "Дельта_процент_numeric"
                    ].fillna(0)
                else:
                    st.error(
                        "❌ Не удалось найти или рассчитать Дельта (%). Отсутствуют необходимые колонки."
                    )
                    st.info(
                        f"Доступные колонки: {', '.join(project_filtered_df.columns)}"
                    )
                    contractor_delta_pct = pd.DataFrame(
                        columns=["Контрагент", "Дельта (%)"]
                    )

        # Group by contractor and aggregate
        if "Дельта_процент_numeric" in project_filtered_df.columns:
            # Check if we have any data before grouping
            if (
                not project_filtered_df.empty
                and "Контрагент" in project_filtered_df.columns
            ):
                contractor_delta_pct = (
                    project_filtered_df.groupby("Контрагент")
                    .agg({"Дельта_процент_numeric": "sum"})  # Sum of delta percentages
                    .reset_index()
                )

                contractor_delta_pct.columns = ["Контрагент", "Дельта (%)"]
            else:
                contractor_delta_pct = pd.DataFrame(
                    columns=["Контрагент", "Дельта (%)"]
                )
    else:
        contractor_delta_pct = pd.DataFrame(columns=["Контрагент", "Дельта (%)"])

    # Check if we have data
    if contractor_delta_pct.empty or len(contractor_delta_pct) == 0:
        st.info("Нет данных для отображения круговой диаграммы.")
    else:
        # Ensure Дельта (%) is numeric
        contractor_delta_pct["Дельта (%)"] = pd.to_numeric(
            contractor_delta_pct["Дельта (%)"], errors="coerce"
        ).fillna(0)

        # Check if we have any non-zero values
        total_abs_sum = contractor_delta_pct["Дельта (%)"].abs().sum()

        if total_abs_sum == 0:
            st.info(
                "Все значения дельты (%) равны нулю. Диаграмма не может быть построена."
            )
        else:
            # Remove only exactly zero values (not small values)
            non_zero_data = contractor_delta_pct[
                contractor_delta_pct["Дельта (%)"] != 0
            ].copy()

            # Use non-zero data if available
            if not non_zero_data.empty:
                contractor_delta_pct = non_zero_data

            # Sort by absolute value for better visualization
            contractor_delta_pct = contractor_delta_pct.sort_values(
                "Дельта (%)", key=abs, ascending=False
            )

            # Create a copy with absolute values for pie chart (pie charts don't support negative values)
            contractor_delta_pct_abs = contractor_delta_pct.copy()
            contractor_delta_pct_abs["Дельта (%)_abs"] = contractor_delta_pct_abs[
                "Дельта (%)"
            ].abs()

            # Store original values for display
            original_values = contractor_delta_pct_abs["Дельта (%)"].tolist()

            # Create pie chart using absolute values
            fig_pie = px.pie(
                contractor_delta_pct_abs,
                values="Дельта (%)_abs",
                names="Контрагент",
                title="Распределение дельты (%) по контрагентам",
                color_discrete_sequence=px.colors.qualitative.Set3,
            )

            fig_pie.update_layout(
                height=600,
                showlegend=True,
                legend=dict(
                    orientation="v", yanchor="middle", y=0.5, xanchor="left", x=1.1
                ),
                title_font_size=16,
            )

            # Update traces to show original (signed) values in text and hover
            fig_pie.update_traces(
                textposition="inside",
                textinfo="percent+label",
                texttemplate="%{label}<br>%{customdata:.0f}%<br>(%{percent})",
                textfont=dict(size=12, color="white"),
                customdata=original_values,
                hovertemplate="<b>%{label}</b><br>Дельта (%): %{customdata:.0f}%<br>Процент: %{percent}<br><extra></extra>",
            )

            fig_pie = apply_chart_background(fig_pie)
            st.plotly_chart(fig_pie, use_container_width=True)

        # ========== Chart 2: Bar Chart by Contractor (Plan, Average, Delta) ==========
        st.subheader(
            "📊 Столбчатая диаграмма: План, Среднее за месяц, Дельта (группировка по контрагенту)"
        )

        # Group by Контрагент and aggregate
        # Ensure Дельта_numeric exists
        if "Дельта_numeric" not in project_filtered_df.columns:
            # Try to calculate if missing
            if (
                "План_numeric" in project_filtered_df.columns
                and "week_sum" in project_filtered_df.columns
            ):
                project_filtered_df["Дельта_numeric"] = (
                    project_filtered_df["План_numeric"]
                    - project_filtered_df["week_sum"]
                )
            else:
                project_filtered_df["Дельта_numeric"] = 0

        contractor_data = (
            project_filtered_df.groupby("Контрагент")
            .agg(
                {
                    "План_numeric": "sum",  # Sum of plans
                    "week_sum": "sum",  # Sum of weeks = среднее за месяц
                    "Дельта_numeric": "sum",  # Sum of deltas
                }
            )
            .reset_index()
        )

        contractor_data.columns = ["Контрагент", "План", "Среднее за месяц", "Дельта"]

        # Ensure Дельта column has numeric values
        contractor_data["Дельта"] = pd.to_numeric(
            contractor_data["Дельта"], errors="coerce"
        ).fillna(0)

        # Sort by contractor name
        contractor_data = contractor_data.sort_values("Контрагент")

        # Create bar chart
        fig_bar = go.Figure()

        # Add bars for Plan
        fig_bar.add_trace(
            go.Bar(
                name="План",
                x=contractor_data["Контрагент"],
                y=contractor_data["План"],
                marker_color="#3498db",
                text=contractor_data["План"].apply(
                    lambda x: f"{int(x)}" if pd.notna(x) else "0"
                ),
                textposition="outside",
                textfont=dict(size=12, color="white"),
            )
        )

        # Add bars for Average
        fig_bar.add_trace(
            go.Bar(
                name="Среднее за месяц",
                x=contractor_data["Контрагент"],
                y=contractor_data["Среднее за месяц"],
                marker_color="#2ecc71",
                text=contractor_data["Среднее за месяц"].apply(
                    lambda x: f"{int(x)}" if pd.notna(x) else "0"
                ),
                textposition="outside",
                textfont=dict(size=12, color="white"),
            )
        )

        # Add bars for Delta - ensure values are properly formatted
        # Разделяем на положительные и отрицательные значения для разных цветов
        delta_values = contractor_data["Дельта"].fillna(0)
        delta_abs = delta_values.abs()  # Абсолютные значения для отображения

        # Положительные значения дельты (зеленый)
        positive_mask = delta_values > 0
        if positive_mask.any():
            fig_bar.add_trace(
                go.Bar(
                    name="Дельта (+)",
                    x=contractor_data.loc[positive_mask, "Контрагент"],
                    y=delta_abs[positive_mask],
                    marker_color="#2ecc71",  # Зеленый для положительных
                    text=delta_abs[positive_mask].apply(
                        lambda x: f"{int(x)}" if pd.notna(x) and abs(x) >= 0.5 else "0"
                    ),
                    textposition="outside",
                    textfont=dict(size=12, color="white"),
                    showlegend=False,
                )
            )

        # Отрицательные значения дельты (красный)
        negative_mask = delta_values < 0
        if negative_mask.any():
            fig_bar.add_trace(
                go.Bar(
                    name="Дельта (-)",
                    x=contractor_data.loc[negative_mask, "Контрагент"],
                    y=delta_abs[negative_mask],
                    marker_color="#e74c3c",  # Красный для отрицательных
                    text=delta_abs[negative_mask].apply(
                        lambda x: f"{int(x)}" if pd.notna(x) and abs(x) >= 0.5 else "0"
                    ),
                    textposition="outside",
                    textfont=dict(size=12, color="white"),
                    showlegend=False,
                )
            )

        # Нулевые значения (если есть)
        zero_mask = delta_values == 0
        if zero_mask.any():
            fig_bar.add_trace(
                go.Bar(
                    name="Дельта (0)",
                    x=contractor_data.loc[zero_mask, "Контрагент"],
                    y=delta_abs[zero_mask],
                    marker_color="#95a5a6",  # Серый для нулевых
                    text=delta_abs[zero_mask].apply(
                        lambda x: f"{int(x)}" if pd.notna(x) and abs(x) >= 0.5 else "0"
                    ),
                    textposition="outside",
                    textfont=dict(size=12, color="white"),
                    showlegend=False,
                )
            )

        # Update layout
        fig_bar.update_layout(
            title="План, Среднее за месяц и Дельта по контрагентам",
            xaxis_title="Контрагент",
            yaxis_title="Значение",
            barmode="group",
            height=600,
            legend=dict(
                orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1
            ),
            xaxis=dict(tickangle=-75, tickfont=dict(size=8), automargin=True),
        )

        fig_bar = apply_chart_background(fig_bar)
        st.plotly_chart(fig_bar, use_container_width=True)

        # ========== Chart 3: Pie Chart by Contractor (Plan + Average) ==========
        st.subheader(
            "📊 Круговая диаграмма: Распределение суммы Плана и Среднего за месяц по контрагентам"
        )

        # Group by Контрагент and aggregate for pie chart (Plan + Average)
        contractor_plan_avg = (
            project_filtered_df.groupby("Контрагент")
            .agg(
                {
                    "План_numeric": "sum",  # Sum of plans
                    "week_sum": "sum",  # Sum of weeks = среднее за месяц
                    "Дельта_numeric": "sum",  # Sum of deltas
                }
            )
            .reset_index()
        )

        contractor_plan_avg.columns = [
            "Контрагент",
            "План",
            "Среднее за месяц",
            "Дельта",
        ]

        # Calculate sum of Plan + Average for each contractor
        contractor_plan_avg["Сумма"] = (
            contractor_plan_avg["План"] + contractor_plan_avg["Среднее за месяц"]
        )

        # Calculate доля факта (Среднее за месяц / Сумма * 100) and доля отклонения (Дельта / План * 100)
        contractor_plan_avg["Доля факта (%)"] = 0
        contractor_plan_avg["Доля отклонения (%)"] = 0
        mask_sum = contractor_plan_avg["Сумма"] != 0
        contractor_plan_avg.loc[mask_sum, "Доля факта (%)"] = (
            contractor_plan_avg.loc[mask_sum, "Среднее за месяц"]
            / contractor_plan_avg.loc[mask_sum, "Сумма"]
        ) * 100
        mask_plan = contractor_plan_avg["План"] != 0
        contractor_plan_avg.loc[mask_plan, "Доля отклонения (%)"] = (
            contractor_plan_avg.loc[mask_plan, "Дельта"]
            / contractor_plan_avg.loc[mask_plan, "План"]
        ) * 100

        # Remove zero values for pie chart
        contractor_plan_avg = contractor_plan_avg[
            contractor_plan_avg["Сумма"] != 0
        ].copy()

        if contractor_plan_avg.empty:
            st.info("Нет данных для отображения.")
        else:
            # Sort by sum value for better visualization
            contractor_plan_avg = contractor_plan_avg.sort_values(
                "Сумма", ascending=False
            )

            # Create pie chart
            fig_pie_plan_avg = px.pie(
                contractor_plan_avg,
                values="Сумма",
                names="Контрагент",
                title="Распределение суммы Плана и Среднего за месяц по контрагентам",
                color_discrete_sequence=px.colors.qualitative.Set2,
            )

            fig_pie_plan_avg.update_layout(
                height=600,
                showlegend=True,
                legend=dict(
                    orientation="v", yanchor="middle", y=0.5, xanchor="left", x=1.1
                ),
                title_font_size=16,
            )

            # Prepare custom text with доля факта and доля отклонения
            total_sum = contractor_plan_avg["Сумма"].sum()
            custom_texts = []
            for idx, row in contractor_plan_avg.iterrows():
                fact_pct = row["Доля факта (%)"]
                delta_pct = row["Доля отклонения (%)"]
                percent_val = (row["Сумма"] / total_sum * 100) if total_sum > 0 else 0
                text = f"{row['Контрагент']}<br>Факт: {fact_pct:.0f}%<br>Отклонение: {delta_pct:.0f}%<br>({percent_val:.0f}%)"
                custom_texts.append(text)

            fig_pie_plan_avg.update_traces(
                textposition="inside",
                textinfo="label",
                texttemplate="%{label}",
                textfont=dict(size=11, color="white"),
                customdata=list(
                    zip(
                        contractor_plan_avg["Доля факта (%)"],
                        contractor_plan_avg["Доля отклонения (%)"],
                        contractor_plan_avg["Сумма"],
                    )
                ),
                hovertemplate="<b>%{label}</b><br>Сумма: %{customdata[2]:.0f}<br>Процент: %{percent}<br>Доля факта: %{customdata[0]:.0f}%<br>Доля отклонения: %{customdata[1]:.0f}%<br><extra></extra>",
            )

            # Update text manually to show факт and отклонение
            for i, trace in enumerate(fig_pie_plan_avg.data):
                if i < len(custom_texts):
                    trace.text = [custom_texts[i]]

            fig_pie_plan_avg = apply_chart_background(fig_pie_plan_avg)
            st.plotly_chart(fig_pie_plan_avg, use_container_width=True)

        # ========== Summary Table ==========
        st.subheader("📋 Сводная таблица по контрагентам")

        # Format numbers for display
        summary_table = contractor_data.copy()
        summary_table["План"] = summary_table["План"].apply(
            lambda x: f"{int(x)}" if pd.notna(x) else "0"
        )
        summary_table["Среднее за месяц"] = summary_table["Среднее за месяц"].apply(
            lambda x: f"{int(x)}" if pd.notna(x) else "0"
        )
        summary_table["Дельта"] = summary_table["Дельта"].apply(
            lambda x: f"{int(x)}" if pd.notna(x) else "0"
        )

        html_table = format_dataframe_as_html(summary_table)
        st.markdown(html_table, unsafe_allow_html=True)

        # Summary metrics
        col1, col2, col3 = st.columns(3)

        with col1:
            total_plan = contractor_data["План"].sum()
            st.metric("Общий план", f"{int(total_plan)}")

        with col2:
            total_average = contractor_data["Среднее за месяц"].sum()
            st.metric("Общее среднее за месяц", f"{int(total_average)}")

        with col3:
            total_delta = contractor_data["Дельта"].sum()
            st.metric("Общая дельта", f"{int(total_delta)}")


# ==================== DASHBOARD 8.6.7: Workforce Movement ====================
def dashboard_workforce_movement(df):
    st.header("👥 График движения рабочей силы")

    # Get resources and technique data from session state
    resources_df = st.session_state.get("resources_data", None)
    technique_df = st.session_state.get("technique_data", None)

    # Combine both data sources if available
    combined_df = None

    if resources_df is not None and not resources_df.empty:
        combined_df = resources_df.copy()
        combined_df["data_source"] = "Ресурсы"

    if technique_df is not None and not technique_df.empty:
        if combined_df is not None:
            technique_copy = technique_df.copy()
            technique_copy["data_source"] = "Техника"
            # Align columns before concatenation to avoid issues
            # If technique has "Среднее за месяц" but resources has "Среднее за неделю", keep both
            combined_df = pd.concat(
                [combined_df, technique_copy], ignore_index=True, sort=False
            )
        else:
            combined_df = technique_df.copy()
            combined_df["data_source"] = "Техника"

    if combined_df is None or combined_df.empty:
        st.warning(
            "⚠️ Для отображения графика движения рабочей силы необходимо загрузить файл с данными о ресурсах или технике."
        )
        st.info(
            "📋 Ожидаемые колонки в файле: Проект, Контрагент, Период, План, Среднее за неделю (для ресурсов) или Среднее за месяц (для техники), недели, Дельта"
        )
        return

    # Create working copy
    work_df = combined_df.copy()

    # Helper function to find columns by partial match (handles encoding issues)
    def find_column_by_partial(df, possible_names):
        """Find column by possible names (exact or partial match)"""
        for col in df.columns:
            col_lower = str(col).lower().strip()
            for name in possible_names:
                name_lower = str(name).lower().strip()
                if (
                    name_lower == col_lower
                    or name_lower in col_lower
                    or col_lower in name_lower
                ):
                    return col
        return None

    # Expected columns: Проект, Контрагент, Период, План, Среднее за неделю, 1 неделя, 2 неделя, 3 неделя, 4 неделя, 5 неделя, Дельта, Дельта (%)
    # Use Russian column names directly

    # Check required columns - Контрагент is essential
    if "Контрагент" not in work_df.columns:
        # Try to find contractor column by partial match
        contractor_col = find_column_by_partial(
            work_df,
            [
                "Контрагент",
                "контрагент",
                "Подразделение",
                "подразделение",
                "contractor",
            ],
        )
        if contractor_col:
            work_df["Контрагент"] = work_df[contractor_col]
        else:
            st.error(f"❌ Отсутствует необходимая колонка 'Контрагент'")
            st.info(f"Доступные колонки: {', '.join(work_df.columns)}")
            return

    # Find week columns dynamically - also try partial match
    week_columns = []
    for week_num in range(1, 6):
        week_col = f"{week_num} неделя"
        if week_col in work_df.columns:
            week_columns.append(week_col)
        else:
            # Try to find by partial match
            found_col = find_column_by_partial(
                work_df,
                [
                    week_col,
                    f"{week_num} недел",
                    f"недел {week_num}",
                    f"week {week_num}",
                ],
            )
            if found_col:
                week_columns.append(found_col)

    # Check if we have any data
    if work_df.empty:
        st.warning("⚠️ Данные пусты после обработки.")
        return

    # Process numeric columns
    # Process План
    if "План" in work_df.columns:
        work_df["План_numeric"] = pd.to_numeric(
            work_df["План"].astype(str).str.replace(",", ".").str.replace(" ", ""),
            errors="coerce",
        ).fillna(0)
    else:
        work_df["План_numeric"] = 0

    # Process week columns - convert to numeric, handle empty strings
    for week_col in week_columns:
        work_df[f"{week_col}_numeric"] = pd.to_numeric(
            work_df[week_col]
            .astype(str)
            .str.replace(",", ".")
            .str.replace(" ", "")
            .replace("", "0"),
            errors="coerce",
        ).fillna(0)

    # Calculate sum of weeks (fact for the month = среднее за месяц)
    # Handle both "Среднее за неделю" (resources) and "Среднее за месяц" (technique)
    if "Среднее за неделю" in work_df.columns:
        # If we have Среднее за неделю (resources), multiply by number of weeks (typically 4-5)
        work_df["Среднее_за_неделю_numeric"] = pd.to_numeric(
            work_df["Среднее за неделю"]
            .astype(str)
            .str.replace(",", ".")
            .str.replace(" ", ""),
            errors="coerce",
        ).fillna(0)
        # Calculate week_sum as Среднее за неделю * number of weeks
        num_weeks = len(week_columns) if week_columns else 4
        work_df["week_sum"] = work_df["Среднее_за_неделю_numeric"] * num_weeks
    elif "Среднее за месяц" in work_df.columns:
        # If we have Среднее за месяц (technique), use it directly as week_sum
        work_df["Среднее_за_месяц_numeric"] = pd.to_numeric(
            work_df["Среднее за месяц"]
            .astype(str)
            .str.replace(",", ".")
            .str.replace(" ", ""),
            errors="coerce",
        ).fillna(0)
        work_df["week_sum"] = work_df["Среднее_за_месяц_numeric"]
        # Also create Среднее_за_неделю_numeric for consistency (divide by number of weeks)
        num_weeks = len(week_columns) if week_columns else 4
        work_df["Среднее_за_неделю_numeric"] = (
            work_df["week_sum"] / num_weeks if num_weeks > 0 else 0
        )
    elif week_columns:
        # Calculate from week columns if available
        week_numeric_cols = [f"{col}_numeric" for col in week_columns]
        work_df["week_sum"] = work_df[week_numeric_cols].sum(axis=1)
        # Calculate average per week
        num_weeks = len(week_columns) if week_columns else 4
        work_df["Среднее_за_неделю_numeric"] = (
            work_df["week_sum"] / num_weeks if num_weeks > 0 else 0
        )
    else:
        work_df["week_sum"] = 0
        work_df["Среднее_за_неделю_numeric"] = 0

    # Process Дельта (Delta) if available - try to find column by partial match
    delta_col = None
    if "Дельта" in work_df.columns:
        delta_col = "Дельта"
    else:
        delta_col = find_column_by_partial(
            work_df, ["Дельта", "дельта", "delta", "Delta", "Дельта (без %)"]
        )

    if delta_col and delta_col in work_df.columns:
        work_df["Дельта_numeric"] = pd.to_numeric(
            work_df[delta_col].astype(str).str.replace(",", ".").str.replace(" ", ""),
            errors="coerce",
        ).fillna(0)
    else:
        # Calculate delta as plan - fact (week_sum)
        work_df["Дельта_numeric"] = work_df["План_numeric"] - work_df["week_sum"]

    # Process Дельта (%) (Delta %) if available - extract numeric value from percentage string
    # Try to find column by partial match
    delta_pct_col = None
    if "Дельта (%)" in work_df.columns:
        delta_pct_col = "Дельта (%)"
    else:
        delta_pct_col = find_column_by_partial(
            work_df,
            [
                "Дельта (%)",
                "Дельта %",
                "дельта (%)",
                "дельта %",
                "Delta %",
                "delta %",
                "Дельта(%)",
                "Дельта%",
            ],
        )

    if delta_pct_col and delta_pct_col in work_df.columns:

        def extract_percentage(value):
            """Extract numeric value from percentage string like '-90%' or '90%', or numeric value"""
            if pd.isna(value):
                return 0
            # If already numeric, return as is
            if isinstance(value, (int, float)):
                return float(value)
            # Otherwise, try to extract from string
            value_str = str(value).strip()
            # Remove % sign and convert to float
            value_str = value_str.replace("%", "").replace(",", ".").replace(" ", "")
            try:
                return float(value_str)
            except:
                return 0

        work_df["Дельта_процент_numeric"] = work_df[delta_pct_col].apply(
            extract_percentage
        )
    else:
        # Calculate delta percentage if we have delta and plan
        work_df["Дельта_процент_numeric"] = 0
        if "Дельта_numeric" in work_df.columns and "План_numeric" in work_df.columns:
            mask = work_df["План_numeric"] != 0
            work_df.loc[mask, "Дельта_процент_numeric"] = (
                work_df.loc[mask, "Дельта_numeric"] / work_df.loc[mask, "План_numeric"]
            ) * 100
        work_df["Дельта_процент_numeric"] = work_df["Дельта_процент_numeric"].fillna(0)

    # Ensure Среднее_за_неделю_numeric exists (should already be calculated above)
    if "Среднее_за_неделю_numeric" not in work_df.columns:
        # Fallback: calculate from week_sum / number of weeks
        num_weeks = len(week_columns) if week_columns else 4
        work_df["Среднее_за_неделю_numeric"] = (
            work_df["week_sum"] / num_weeks if num_weeks > 0 else 0
        )

    # Find Проект column
    project_col = None
    if "Проект" in work_df.columns:
        project_col = "Проект"
    else:
        project_col = find_column_by_partial(
            work_df, ["Проект", "проект", "project", "Project"]
        )

    # Filters - project and contractor filters
    col1, col2 = st.columns(2)

    with col1:
        # Project filter - multiselect для выбора нескольких проектов
        if project_col and project_col in work_df.columns:
            all_projects = sorted(work_df[project_col].dropna().unique().tolist())
            selected_projects = st.multiselect(
                "Фильтр по проектам (можно выбрать несколько)",
                all_projects,
                default=all_projects if len(all_projects) <= 3 else all_projects[:3],
                key="workforce_projects",
            )
        else:
            selected_projects = []
            st.info("Колонка 'Проект' не найдена")

    with col2:
        # Contractor filter
        if "Контрагент" in work_df.columns:
            contractors = ["Все"] + sorted(
                work_df["Контрагент"].dropna().unique().tolist()
            )
            selected_contractor = st.selectbox(
                "Фильтр по контрагенту", contractors, key="workforce_contractor"
            )
        else:
            selected_contractor = "Все"
            st.info("Колонка 'Контрагент' не найдена")

    # Apply filters
    filtered_df = work_df.copy()
    if selected_projects and project_col and project_col in filtered_df.columns:
        # Фильтруем по выбранным проектам
        project_mask = (
            filtered_df[project_col]
            .astype(str)
            .str.strip()
            .isin([str(p).strip() for p in selected_projects])
        )
        filtered_df = filtered_df[project_mask]
    if selected_contractor != "Все" and "Контрагент" in filtered_df.columns:
        # Use string comparison with strip to handle whitespace
        filtered_df = filtered_df[
            filtered_df["Контрагент"].astype(str).str.strip()
            == str(selected_contractor).strip()
        ]

    if filtered_df.empty:
        st.info("Нет данных для отображения с выбранными фильтрами.")
        return

    # Ensure Контрагент column exists and has values
    if (
        "Контрагент" not in filtered_df.columns
        or filtered_df["Контрагент"].isna().all()
    ):
        st.error("❌ Колонка 'Контрагент' отсутствует или пуста после фильтрации.")
        return

    # Remove rows where Контрагент is NaN before grouping
    filtered_df = filtered_df[filtered_df["Контрагент"].notna()].copy()

    if filtered_df.empty:
        st.info("Нет данных с указанными контрагентами после фильтрации.")
        return

    # Определяем список проектов для обработки
    if selected_projects and project_col and project_col in filtered_df.columns:
        projects_to_process = selected_projects
    else:
        # Если проекты не выбраны или колонка не найдена, обрабатываем все проекты
        if project_col and project_col in filtered_df.columns:
            projects_to_process = sorted(
                filtered_df[project_col].dropna().unique().tolist()
            )
        else:
            projects_to_process = ["Все проекты"]

    # Обрабатываем каждый проект отдельно
    for project_name in projects_to_process:
        # Фильтруем данные по проекту
        project_filtered_df = filtered_df.copy()
        if (
            project_col
            and project_col in project_filtered_df.columns
            and project_name != "Все проекты"
        ):
            project_filtered_df = project_filtered_df[
                project_filtered_df[project_col].astype(str).str.strip()
                == str(project_name).strip()
            ]

        if project_filtered_df.empty:
            continue

        # Заголовок для проекта
        if len(projects_to_process) > 1:
            st.markdown("---")
            st.subheader(f"📊 Проект: {project_name}")

        # ========== Chart 1: Pie Chart by Contractor (Delta %) ==========
        st.subheader("📊 Круговая диаграмма: Распределение дельты (%) по контрагентам")

        # Group by Контрагент and aggregate for pie chart (Delta %)
        # Ensure Дельта_процент_numeric exists - check if it was created in work_df
        if "Дельта_процент_numeric" not in project_filtered_df.columns:
            # Try to find Дельта (%) column by partial match
            delta_pct_col = None
            if "Дельта (%)" in project_filtered_df.columns:
                delta_pct_col = "Дельта (%)"
            else:
                delta_pct_col = find_column_by_partial(
                    project_filtered_df,
                    [
                        "Дельта (%)",
                        "Дельта %",
                        "дельта (%)",
                        "дельта %",
                        "Delta %",
                        "delta %",
                        "Дельта(%)",
                        "Дельта%",
                    ],
                )

            if delta_pct_col and delta_pct_col in project_filtered_df.columns:
                # Extract percentage values from the column
                def extract_percentage(value):
                    """Extract numeric value from percentage string like '-90%' or '90%', or numeric value"""
                    if pd.isna(value):
                        return 0
                    # If already numeric, return as is
                    if isinstance(value, (int, float)):
                        return float(value)
                    # Otherwise, try to extract from string
                    value_str = str(value).strip()
                    # Remove % sign and convert to float
                    value_str = (
                        value_str.replace("%", "").replace(",", ".").replace(" ", "")
                    )
                    try:
                        return float(value_str)
                    except:
                        return 0

                project_filtered_df["Дельта_процент_numeric"] = project_filtered_df[
                    delta_pct_col
                ].apply(extract_percentage)
            else:
                # Try to calculate from Дельта and План if available
                if (
                    "Дельта_numeric" in project_filtered_df.columns
                    and "План_numeric" in project_filtered_df.columns
                ):
                    project_filtered_df["Дельта_процент_numeric"] = 0
                    mask = project_filtered_df["План_numeric"] != 0
                    project_filtered_df.loc[mask, "Дельта_процент_numeric"] = (
                        project_filtered_df.loc[mask, "Дельта_numeric"]
                        / project_filtered_df.loc[mask, "План_numeric"]
                    ) * 100
                    project_filtered_df["Дельта_процент_numeric"] = project_filtered_df[
                        "Дельта_процент_numeric"
                    ].fillna(0)
                else:
                    st.error(
                        "❌ Не удалось найти или рассчитать Дельта (%). Отсутствуют необходимые колонки."
                    )
                    st.info(
                        f"Доступные колонки: {', '.join(project_filtered_df.columns)}"
                    )
                    contractor_delta_pct = pd.DataFrame(
                        columns=["Контрагент", "Дельта (%)"]
                    )

        # Group by contractor and aggregate
        if "Дельта_процент_numeric" in project_filtered_df.columns:
            # Check if we have any data before grouping
            if (
                not project_filtered_df.empty
                and "Контрагент" in project_filtered_df.columns
            ):
                contractor_delta_pct = (
                    project_filtered_df.groupby("Контрагент")
                    .agg({"Дельта_процент_numeric": "sum"})  # Sum of delta percentages
                    .reset_index()
                )

                contractor_delta_pct.columns = ["Контрагент", "Дельта (%)"]
            else:
                contractor_delta_pct = pd.DataFrame(
                    columns=["Контрагент", "Дельта (%)"]
                )
    else:
        contractor_delta_pct = pd.DataFrame(columns=["Контрагент", "Дельта (%)"])

    # Check if we have data
    if contractor_delta_pct.empty or len(contractor_delta_pct) == 0:
        st.info("Нет данных для отображения круговой диаграммы.")
    else:
        # Ensure Дельта (%) is numeric
        contractor_delta_pct["Дельта (%)"] = pd.to_numeric(
            contractor_delta_pct["Дельта (%)"], errors="coerce"
        ).fillna(0)

        # Check if we have any non-zero values
        total_abs_sum = contractor_delta_pct["Дельта (%)"].abs().sum()

        if total_abs_sum == 0:
            st.info(
                "Все значения дельты (%) равны нулю. Диаграмма не может быть построена."
            )
        else:
            # Remove only exactly zero values (not small values)
            non_zero_data = contractor_delta_pct[
                contractor_delta_pct["Дельта (%)"] != 0
            ].copy()

            # Use non-zero data if available
            if not non_zero_data.empty:
                contractor_delta_pct = non_zero_data

            # Sort by absolute value for better visualization
            contractor_delta_pct = contractor_delta_pct.sort_values(
                "Дельта (%)", key=abs, ascending=False
            )

            # Create a copy with absolute values for pie chart (pie charts don't support negative values)
            contractor_delta_pct_abs = contractor_delta_pct.copy()
            contractor_delta_pct_abs["Дельта (%)_abs"] = contractor_delta_pct_abs[
                "Дельта (%)"
            ].abs()

            # Store original values for display
            original_values = contractor_delta_pct_abs["Дельта (%)"].tolist()

            # Create pie chart using absolute values
            fig_pie = px.pie(
                contractor_delta_pct_abs,
                values="Дельта (%)_abs",
                names="Контрагент",
                title="Распределение дельты (%) по контрагентам",
                color_discrete_sequence=px.colors.qualitative.Set3,
            )

            fig_pie.update_layout(
                height=600,
                showlegend=True,
                legend=dict(
                    orientation="v", yanchor="middle", y=0.5, xanchor="left", x=1.1
                ),
                title_font_size=16,
            )

            # Update traces to show original (signed) values in text and hover
            fig_pie.update_traces(
                textposition="inside",
                textinfo="percent+label",
                texttemplate="%{label}<br>%{customdata:.0f}%<br>(%{percent})",
                textfont=dict(size=12, color="white"),
                customdata=original_values,
                hovertemplate="<b>%{label}</b><br>Дельта (%): %{customdata:.0f}%<br>Процент: %{percent}<br><extra></extra>",
            )

            fig_pie = apply_chart_background(fig_pie)
            st.plotly_chart(fig_pie, use_container_width=True)

    # ========== Chart 2: Bar Chart by Contractor (Plan, Average, Delta) ==========
    st.subheader(
        "📊 Столбчатая диаграмма: План, Среднее за месяц, Дельта (группировка по контрагенту)"
    )

    # Group by Контрагент and aggregate for bar chart
    contractor_data = (
        project_filtered_df.groupby("Контрагент")
        .agg(
            {
                "План_numeric": "sum",  # Sum of plans
                "week_sum": "sum",  # Sum of weeks = среднее за месяц
                "Дельта_numeric": "sum",  # Sum of deltas
            }
        )
        .reset_index()
    )

    contractor_data.columns = ["Контрагент", "План", "Среднее за месяц", "Дельта"]

    # Ensure Дельта column has numeric values
    contractor_data["Дельта"] = pd.to_numeric(
        contractor_data["Дельта"], errors="coerce"
    ).fillna(0)

    # Sort by contractor name
    contractor_data = contractor_data.sort_values("Контрагент")

    # Create bar chart
    fig_bar = go.Figure()

    # Add bars for Plan
    fig_bar.add_trace(
        go.Bar(
            name="План",
            x=contractor_data["Контрагент"],
            y=contractor_data["План"],
            marker_color="#3498db",
            text=contractor_data["План"].apply(
                lambda x: f"{int(x)}" if pd.notna(x) else "0"
            ),
            textposition="outside",
            textfont=dict(size=12, color="white"),
        )
    )

    # Add bars for Average
    fig_bar.add_trace(
        go.Bar(
            name="Среднее за месяц",
            x=contractor_data["Контрагент"],
            y=contractor_data["Среднее за месяц"],
            marker_color="#2ecc71",
            text=contractor_data["Среднее за месяц"].apply(
                lambda x: f"{int(x)}" if pd.notna(x) else "0"
            ),
            textposition="outside",
            textfont=dict(size=12, color="white"),
        )
    )

    # Add bars for Delta - ensure values are properly formatted
    # Разделяем на положительные и отрицательные значения для разных цветов
    delta_values = contractor_data["Дельта"].fillna(0)
    delta_abs = delta_values.abs()  # Абсолютные значения для отображения

    # Положительные значения дельты (зеленый)
    positive_mask = delta_values > 0
    if positive_mask.any():
        fig_bar.add_trace(
            go.Bar(
                name="Дельта (+)",
                x=contractor_data.loc[positive_mask, "Контрагент"],
                y=delta_abs[positive_mask],
                marker_color="#2ecc71",  # Зеленый для положительных
                text=delta_abs[positive_mask].apply(
                    lambda x: f"{int(x)}" if pd.notna(x) and abs(x) >= 0.5 else "0"
                ),
                textposition="outside",
                textfont=dict(size=12, color="white"),
                showlegend=False,
            )
        )

    # Отрицательные значения дельты (красный)
    negative_mask = delta_values < 0
    if negative_mask.any():
        fig_bar.add_trace(
            go.Bar(
                name="Дельта (-)",
                x=contractor_data.loc[negative_mask, "Контрагент"],
                y=delta_abs[negative_mask],
                marker_color="#e74c3c",  # Красный для отрицательных
                text=delta_abs[negative_mask].apply(
                    lambda x: f"{int(x)}" if pd.notna(x) and abs(x) >= 0.5 else "0"
                ),
                textposition="outside",
                textfont=dict(size=12, color="white"),
                showlegend=False,
            )
        )

    # Нулевые значения (если есть)
    zero_mask = delta_values == 0
    if zero_mask.any():
        fig_bar.add_trace(
            go.Bar(
                name="Дельта (0)",
                x=contractor_data.loc[zero_mask, "Контрагент"],
                y=delta_abs[zero_mask],
                marker_color="#95a5a6",  # Серый для нулевых
                text=delta_abs[zero_mask].apply(
                    lambda x: f"{int(x)}" if pd.notna(x) and abs(x) >= 0.5 else "0"
                ),
                textposition="outside",
                textfont=dict(size=12, color="white"),
                showlegend=False,
            )
        )

    # Update layout
    fig_bar.update_layout(
        title="План, Среднее за месяц и Дельта по контрагентам",
        xaxis_title="Контрагент",
        yaxis_title="Значение",
        barmode="group",
        height=600,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis=dict(tickangle=-75, tickfont=dict(size=8), automargin=True),
    )
    fig_bar = apply_chart_background(fig_bar)
    st.plotly_chart(fig_bar, use_container_width=True)

    # ========== Chart 3: Pie Chart by Contractor (Plan + Average) ==========
    st.subheader(
        "📊 Круговая диаграмма: Распределение суммы Плана и Среднего за месяц по контрагентам"
    )

    # Group by Контрагент and aggregate for pie chart (Plan + Average)
    contractor_plan_avg = (
        project_filtered_df.groupby("Контрагент")
        .agg(
            {
                "План_numeric": "sum",  # Sum of plans
                "week_sum": "sum",  # Sum of weeks = среднее за месяц
                "Дельта_numeric": "sum",  # Sum of deltas
            }
        )
        .reset_index()
    )

    contractor_plan_avg.columns = ["Контрагент", "План", "Среднее за месяц", "Дельта"]

    # Calculate sum of Plan + Average for each contractor
    contractor_plan_avg["Сумма"] = (
        contractor_plan_avg["План"] + contractor_plan_avg["Среднее за месяц"]
    )

    # Calculate доля факта (Среднее за месяц / Сумма * 100) and доля отклонения (Дельта / План * 100)
    contractor_plan_avg["Доля факта (%)"] = 0
    contractor_plan_avg["Доля отклонения (%)"] = 0
    mask_sum = contractor_plan_avg["Сумма"] != 0
    contractor_plan_avg.loc[mask_sum, "Доля факта (%)"] = (
        contractor_plan_avg.loc[mask_sum, "Среднее за месяц"]
        / contractor_plan_avg.loc[mask_sum, "Сумма"]
    ) * 100
    mask_plan = contractor_plan_avg["План"] != 0
    contractor_plan_avg.loc[mask_plan, "Доля отклонения (%)"] = (
        contractor_plan_avg.loc[mask_plan, "Дельта"]
        / contractor_plan_avg.loc[mask_plan, "План"]
    ) * 100

    # Remove zero values for pie chart
    contractor_plan_avg = contractor_plan_avg[contractor_plan_avg["Сумма"] != 0].copy()

    if contractor_plan_avg.empty:
        st.info("Нет данных для отображения.")
    else:
        # Sort by sum value for better visualization
        contractor_plan_avg = contractor_plan_avg.sort_values("Сумма", ascending=False)

        # Create pie chart
        fig_pie_plan_avg = px.pie(
            contractor_plan_avg,
            values="Сумма",
            names="Контрагент",
            title="Распределение суммы Плана и Среднего за месяц по контрагентам",
            color_discrete_sequence=px.colors.qualitative.Set2,
        )

        fig_pie_plan_avg.update_layout(
            height=600,
            showlegend=True,
            legend=dict(
                orientation="v", yanchor="middle", y=0.5, xanchor="left", x=1.1
            ),
            title_font_size=16,
        )

        # Prepare custom text with доля факта and доля отклонения
        total_sum = contractor_plan_avg["Сумма"].sum()
        custom_texts = []
        for idx, row in contractor_plan_avg.iterrows():
            fact_pct = row["Доля факта (%)"]
            delta_pct = row["Доля отклонения (%)"]
            percent_val = (row["Сумма"] / total_sum * 100) if total_sum > 0 else 0
            text = f"{row['Контрагент']}<br>Факт: {fact_pct:.0f}%<br>Отклонение: {delta_pct:.0f}%<br>({percent_val:.0f}%)"
            custom_texts.append(text)

        fig_pie_plan_avg.update_traces(
            textposition="inside",
            textinfo="label",
            texttemplate="%{label}",
            textfont=dict(size=11, color="white"),
            customdata=list(
                zip(
                    contractor_plan_avg["Доля факта (%)"],
                    contractor_plan_avg["Доля отклонения (%)"],
                    contractor_plan_avg["Сумма"],
                )
            ),
            hovertemplate="<b>%{label}</b><br>Сумма: %{customdata[2]:.0f}<br>Процент: %{percent}<br>Доля факта: %{customdata[0]:.0f}%<br>Доля отклонения: %{customdata[1]:.0f}%<br><extra></extra>",
        )

        # Update text manually to show факт and отклонение
        for i, trace in enumerate(fig_pie_plan_avg.data):
            if i < len(custom_texts):
                trace.text = [custom_texts[i]]
        fig_pie_plan_avg = apply_chart_background(fig_pie_plan_avg)
        st.plotly_chart(fig_pie_plan_avg, use_container_width=True)

        # ========== Summary Table ==========
        st.subheader("📋 Сводная таблица по контрагентам")

        # Format numbers for display
        summary_table = contractor_data.copy()
        summary_table["План"] = summary_table["План"].apply(
            lambda x: f"{int(x)}" if pd.notna(x) else "0"
        )
        summary_table["Среднее за месяц"] = summary_table["Среднее за месяц"].apply(
            lambda x: f"{int(x)}" if pd.notna(x) else "0"
        )
        summary_table["Дельта"] = summary_table["Дельта"].apply(
            lambda x: f"{int(x)}" if pd.notna(x) else "0"
        )

        html_table = format_dataframe_as_html(summary_table)
        st.markdown(html_table, unsafe_allow_html=True)

        # Summary metrics
        col1, col2, col3 = st.columns(3)

        with col1:
            total_plan = contractor_data["План"].sum()
            st.metric("Общий план", f"{int(total_plan)}")

        with col2:
            total_average = contractor_data["Среднее за месяц"].sum()
            st.metric("Общее среднее за месяц", f"{int(total_average)}")

        with col3:
            total_delta = contractor_data["Дельта"].sum()
            st.metric("Общая дельта", f"{int(total_delta)}")


# ==================== DASHBOARD 8.6: SKUD Stroyka ====================
def dashboard_skud_stroyka(df):
    st.header("🏗️ СКУД стройка")

    # Get resources data from session state
    resources_df = st.session_state.get("resources_data", None)

    if resources_df is None or resources_df.empty:
        st.warning(
            "⚠️ Для отображения графика СКУД стройка необходимо загрузить файл с данными о ресурсах."
        )
        st.info(
            "📋 Ожидаемые колонки в файле: Проект, Контрагент, Период, Среднее за неделю или Среднее за месяц"
        )
        # Debug info
        if "loaded_files_info" in st.session_state:
            st.info(
                f"Загруженные файлы: {list(st.session_state.loaded_files_info.keys())}"
            )
        return

    # Create working copy
    work_df = resources_df.copy()

    # Debug: Show data info (can be removed later)
    with st.expander("🔍 Отладочная информация", expanded=False):
        st.write(f"**Количество строк в исходных данных:** {len(work_df)}")
        st.write(f"**Колонки:** {', '.join(work_df.columns.tolist())}")
        if len(work_df) > 0:
            st.write("**Первые строки данных:**")
            # Rename columns to Russian and remove period_original
            work_df_display = work_df.drop(columns=["period_original"], errors="ignore").head().copy()
            work_df_display = work_df_display.rename(columns={
                "project name": "Проект",
                "section": "Этап",
                "block": "Блок",
                "period_month": "Период",
                "period_display": "Период"
            })
            html_table = format_dataframe_as_html(work_df_display)
            st.markdown(html_table, unsafe_allow_html=True)
            if "Среднее_numeric" in work_df.columns:
                st.write(f"**Среднее_numeric статистика:**")
                st.write(
                    f"- Не пустых значений: {work_df['Среднее_numeric'].notna().sum()}"
                )
                st.write(f"- Среднее значение: {work_df['Среднее_numeric'].mean():.2f}")
                st.write(f"- Минимум: {work_df['Среднее_numeric'].min():.2f}")
                st.write(f"- Максимум: {work_df['Среднее_numeric'].max():.2f}")

    # Helper function to find columns by partial match
    def find_column_by_partial(df, possible_names):
        """Find column by possible names (exact or partial match)"""
        for col in df.columns:
            col_lower = str(col).lower().strip()
            for name in possible_names:
                name_lower = str(name).lower().strip()
                if (
                    name_lower == col_lower
                    or name_lower in col_lower
                    or col_lower in name_lower
                ):
                    return col
        return None

    # Find required columns
    project_col = find_column_by_partial(
        work_df, ["Проект", "проект", "project", "Project"]
    )
    contractor_col = find_column_by_partial(
        work_df,
        ["Контрагент", "контрагент", "Подразделение", "подразделение", "contractor"],
    )
    period_col = find_column_by_partial(
        work_df, ["Период", "период", "period", "Period", "Месяц", "месяц"]
    )

    # Find average column (Среднее за неделю or Среднее за месяц)
    avg_col = None
    if "Среднее за неделю" in work_df.columns:
        avg_col = "Среднее за неделю"
    elif "Среднее за месяц" in work_df.columns:
        avg_col = "Среднее за месяц"
    else:
        avg_col = find_column_by_partial(
            work_df, ["Среднее за неделю", "Среднее за месяц", "среднее", "average"]
        )

    if not avg_col:
        st.error(
            "❌ Не найдена колонка со средним значением (Среднее за неделю или Среднее за месяц)"
        )
        st.info(f"Доступные колонки: {', '.join(work_df.columns)}")
        st.info(f"Количество строк в данных: {len(work_df)}")
        return

    # Period column is optional - we can work without it
    if not period_col:
        st.info(
            "ℹ️ Колонка с периодом не найдена. Данные будут отображаться без временной группировки."
        )
        st.info(f"Доступные колонки: {', '.join(work_df.columns)}")

    # Process average column to numeric
    work_df["Среднее_numeric"] = pd.to_numeric(
        work_df[avg_col].astype(str).str.replace(",", ".").str.replace(" ", ""),
        errors="coerce",
    )

    # Check if we have any valid numeric values
    if work_df["Среднее_numeric"].isna().all():
        st.error("❌ Все значения в колонке со средним значением не являются числами.")
        st.info(
            f"Примеры значений из колонки '{avg_col}': {work_df[avg_col].head(10).tolist()}"
        )
        return

    # Fill NaN with 0 only for display purposes, but keep track of valid data
    work_df["Среднее_numeric"] = work_df["Среднее_numeric"].fillna(0)

    # Process period column - try to convert to datetime/period
    if period_col and period_col in work_df.columns:
        # Try to parse period as date
        work_df["period_parsed"] = pd.to_datetime(
            work_df[period_col], errors="coerce", dayfirst=True
        )
        # If parsing failed, try to extract month/year from string
        mask = work_df["period_parsed"].isna()
        if mask.any():
            # Try to extract month and year from period string
            def extract_period(val):
                if pd.isna(val):
                    return None
                val_str = str(val)
                # Try patterns like "2025-01", "01.2025", "январь 2025", etc.
                try:
                    # Try YYYY-MM format
                    if "-" in val_str:
                        parts = val_str.split("-")
                        if len(parts) >= 2:
                            year = int(parts[0])
                            month = int(parts[1])
                            return pd.Period(f"{year}-{month:02d}", freq="M")
                    # Try DD.MM.YYYY or MM.YYYY
                    if "." in val_str:
                        parts = val_str.split(".")
                        if len(parts) >= 2:
                            if len(parts) == 3:  # DD.MM.YYYY
                                year = int(parts[2])
                                month = int(parts[1])
                            else:  # MM.YYYY
                                year = int(parts[1])
                                month = int(parts[0])
                            return pd.Period(f"{year}-{month:02d}", freq="M")
                except:
                    pass
                return None

            work_df.loc[mask, "period_parsed"] = work_df.loc[mask, period_col].apply(
                extract_period
            )

        # Convert to Period if possible
        work_df["period_month"] = work_df["period_parsed"].apply(
            lambda x: (
                x.to_period("M")
                if pd.notna(x) and isinstance(x, pd.Timestamp)
                else (x if isinstance(x, pd.Period) else None)
            )
        )
    else:
        work_df["period_month"] = None

    # Filters
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        # Grouping filter
        grouping_options = [
            "По проектам",
            "По контрагентам",
            "По проектам и контрагентам",
            "Без группировки",
        ]
        selected_grouping = st.selectbox(
            "Группировка", grouping_options, key="skud_grouping"
        )

    with col2:
        # Period from filter
        if "period_month" in work_df.columns and work_df["period_month"].notna().any():
            available_months = sorted(
                work_df[work_df["period_month"].notna()]["period_month"].unique()
            )
            month_options = ["Все"] + [str(m) for m in available_months]
            selected_period_from = st.selectbox(
                "Период от", month_options, key="skud_period_from"
            )
        else:
            selected_period_from = "Все"
            st.info("Периоды не найдены")

    with col3:
        # Period to filter
        if "period_month" in work_df.columns and work_df["period_month"].notna().any():
            available_months = sorted(
                work_df[work_df["period_month"].notna()]["period_month"].unique()
            )
            month_options = ["Все"] + [str(m) for m in available_months]
            selected_period_to = st.selectbox(
                "Период до", month_options, key="skud_period_to"
            )
        else:
            selected_period_to = "Все"
            st.info("Периоды не найдены")

    with col4:
        # Project filter
        if project_col and project_col in work_df.columns:
            projects = ["Все"] + sorted(work_df[project_col].dropna().unique().tolist())
            selected_project = st.selectbox(
                "Фильтр по проекту", projects, key="skud_project"
            )
        else:
            selected_project = "Все"
            st.info("Проекты не найдены")

    with col5:
        # Contractor filter
        if contractor_col and contractor_col in work_df.columns:
            contractors = ["Все"] + sorted(
                work_df[contractor_col].dropna().unique().tolist()
            )
            selected_contractor = st.selectbox(
                "Фильтр по контрагенту", contractors, key="skud_contractor"
            )
        else:
            selected_contractor = "Все"
            st.info("Контрагенты не найдены")

    # Apply filters
    filtered_df = work_df.copy()

    if selected_project != "Все" and project_col and project_col in filtered_df.columns:
        # More robust filtering - handle NaN values and case-insensitive comparison
        project_mask = (
            filtered_df[project_col].astype(str).str.strip().str.lower()
            == str(selected_project).strip().lower()
        )
        filtered_df = filtered_df[project_mask]

    if (
        selected_contractor != "Все"
        and contractor_col
        and contractor_col in filtered_df.columns
    ):
        # More robust filtering - handle NaN values and case-insensitive comparison
        contractor_mask = (
            filtered_df[contractor_col].astype(str).str.strip().str.lower()
            == str(selected_contractor).strip().lower()
        )
        filtered_df = filtered_df[contractor_mask]

    # Apply period filters
    if (
        "period_month" in filtered_df.columns
        and filtered_df["period_month"].notna().any()
    ):
        if selected_period_from != "Все":
            try:
                period_from = pd.Period(selected_period_from, freq="M")
                filtered_df = filtered_df[filtered_df["period_month"] >= period_from]
            except Exception as e:
                st.warning(f"Ошибка при фильтрации по периоду от: {e}")

        if selected_period_to != "Все":
            try:
                period_to = pd.Period(selected_period_to, freq="M")
                filtered_df = filtered_df[filtered_df["period_month"] <= period_to]
            except Exception as e:
                st.warning(f"Ошибка при фильтрации по периоду до: {e}")

    if filtered_df.empty:
        st.warning("⚠️ Нет данных для отображения с выбранными фильтрами.")
        with st.expander("🔍 Информация о фильтрах", expanded=False):
            st.write(f"**Исходных строк:** {len(work_df)}")
            st.write(f"**Строк после фильтрации:** {len(filtered_df)}")
            st.write(f"**Выбранный проект:** {selected_project}")
            st.write(f"**Выбранный контрагент:** {selected_contractor}")
            st.write(f"**Период от:** {selected_period_from}")
            st.write(f"**Период до:** {selected_period_to}")
            if project_col and project_col in work_df.columns:
                unique_projects = work_df[project_col].dropna().unique()
                st.write(
                    f"**Доступные проекты:** {', '.join(map(str, unique_projects[:10]))}"
                )
            if contractor_col and contractor_col in work_df.columns:
                unique_contractors = work_df[contractor_col].dropna().unique()
                st.write(
                    f"**Доступные контрагенты:** {', '.join(map(str, unique_contractors[:10]))}"
                )
        return

    # Group data based on selected grouping
    group_cols = []
    if (
        selected_grouping == "По проектам"
        and project_col
        and project_col in filtered_df.columns
    ):
        group_cols.append(project_col)
    elif (
        selected_grouping == "По контрагентам"
        and contractor_col
        and contractor_col in filtered_df.columns
    ):
        group_cols.append(contractor_col)
    elif selected_grouping == "По проектам и контрагентам":
        if project_col and project_col in filtered_df.columns:
            group_cols.append(project_col)
        if contractor_col and contractor_col in filtered_df.columns:
            group_cols.append(contractor_col)

    # Always group by period_month for time series (only if not filtering by specific period range)
    # Only add period_month if it has valid (non-NaN) values
    if (
        (selected_period_from == "Все" and selected_period_to == "Все")
        and "period_month" in filtered_df.columns
        and filtered_df["period_month"].notna().any()
    ):
        group_cols.append("period_month")

    if group_cols:
        # Filter out rows where any grouping column is NaN before grouping
        mask = pd.Series([True] * len(filtered_df))
        for col in group_cols:
            if col in filtered_df.columns:
                mask = mask & filtered_df[col].notna()

        if mask.any():
            grouped_data = (
                filtered_df[mask]
                .groupby(group_cols)["Среднее_numeric"]
                .mean()
                .reset_index()
            )
            grouped_data.columns = list(group_cols) + ["Среднее за месяц"]
        else:
            # All grouping columns are NaN, aggregate without grouping
            grouped_data = pd.DataFrame(
                {"Среднее за месяц": [filtered_df["Среднее_numeric"].mean()]}
            )
    else:
        # No grouping, just aggregate by period if available
        if (
            "period_month" in filtered_df.columns
            and filtered_df["period_month"].notna().any()
        ):
            grouped_data = (
                filtered_df.groupby("period_month")["Среднее_numeric"]
                .mean()
                .reset_index()
            )
            grouped_data.columns = ["period_month", "Среднее за месяц"]
        else:
            # No period available, just aggregate all data
            mean_value = filtered_df["Среднее_numeric"].mean()
            if pd.isna(mean_value):
                mean_value = 0
            grouped_data = pd.DataFrame({"Среднее за месяц": [mean_value]})

    # Format period for display
    def format_period_display(period_val):
        if pd.isna(period_val):
            return "Н/Д"
        if isinstance(period_val, pd.Period):
            try:
                month_name = get_russian_month_name(period_val)
                year = period_val.year
                if month_name:
                    return f"{month_name} {year}"
                return str(period_val)
            except:
                return str(period_val)
        return str(period_val)

    if "period_month" in grouped_data.columns:
        grouped_data["period_display"] = grouped_data["period_month"].apply(
            format_period_display
        )

    # Check if we have data to display
    if grouped_data.empty:
        st.warning("⚠️ Нет данных для отображения после применения фильтров.")
        with st.expander("🔍 Детали проблемы", expanded=True):
            st.write(f"**Исходных строк:** {len(work_df)}")
            st.write(f"**Строк после фильтрации:** {len(filtered_df)}")
            st.write(f"**Строк после группировки:** {len(grouped_data)}")
            st.write(f"**Выбранная группировка:** {selected_grouping}")
            st.write(f"**Колонки для группировки:** {group_cols}")
            st.write(f"**Выбранный проект:** {selected_project}")
            st.write(f"**Выбранный контрагент:** {selected_contractor}")
            st.write(f"**Период от:** {selected_period_from}")
            st.write(f"**Период до:** {selected_period_to}")
            if len(filtered_df) > 0:
                st.write("**Данные после фильтрации (первые 10 строк):**")
                # Rename columns to Russian and remove period_original
                filtered_df_display = filtered_df.drop(columns=["period_original"], errors="ignore").head(10).copy()
                filtered_df_display = filtered_df_display.rename(columns={
                    "project name": "Проект",
                    "section": "Этап",
                    "block": "Блок",
                    "period_month": "Период",
                    "period_display": "Период"
                })
                html_table = format_dataframe_as_html(filtered_df_display)
                st.markdown(html_table, unsafe_allow_html=True)
                if "Среднее_numeric" in filtered_df.columns:
                    st.write(f"**Среднее_numeric в отфильтрованных данных:**")
                    st.write(
                        f"- Не пустых значений: {filtered_df['Среднее_numeric'].notna().sum()}"
                    )
                    st.write(
                        f"- Среднее значение: {filtered_df['Среднее_numeric'].mean():.2f}"
                    )
                    st.write(f"- Сумма: {filtered_df['Среднее_numeric'].sum():.2f}")
            else:
                st.write(
                    "**Проблема:** После применения фильтров не осталось ни одной строки."
                )
                st.write("**Возможные причины:**")
                st.write("- Фильтры слишком строгие")
                st.write("- Данные не соответствуют выбранным фильтрам")
                st.write("- Проблемы с типами данных при сравнении")
        return

    # Check if all values are NaN (but allow zeros - zeros are valid data)
    if "Среднее за месяц" in grouped_data.columns:
        if grouped_data["Среднее за месяц"].isna().all():
            st.warning("⚠️ Все значения среднего равны NaN после группировки.")
            with st.expander("🔍 Детали проблемы", expanded=True):
                st.write(f"**Строк после группировки:** {len(grouped_data)}")
                # Rename columns to Russian and remove period_original
                grouped_data_display = grouped_data.drop(columns=["period_original"], errors="ignore").copy()
                grouped_data_display = grouped_data_display.rename(columns={
                    "project name": "Проект",
                    "section": "Этап",
                    "block": "Блок",
                    "period_month": "Период",
                    "period_display": "Период"
                })
                html_table = format_dataframe_as_html(grouped_data_display)
                st.markdown(html_table, unsafe_allow_html=True)
            return

    # Create visualization
    has_period = (
        "period_month" in grouped_data.columns
        or "period_display" in grouped_data.columns
    )

    if selected_grouping == "Без группировки":
        if has_period:
            # Simple line chart with time series
            x_col = (
                "period_display"
                if "period_display" in grouped_data.columns
                else "period_month"
            )
            fig = px.line(
                grouped_data,
                x=x_col,
                y="Среднее за месяц",
                title="Среднее за месяц по людям в динамике",
                labels={x_col: "Месяц", "Среднее за месяц": "Среднее за месяц (чел.)"},
                markers=True,
            )
            fig.update_xaxes(tickangle=-75, tickfont=dict(size=8), automargin=True)
            fig = apply_chart_background(fig)
            st.plotly_chart(fig, use_container_width=True)
        else:
            # Single value bar chart
            fig = px.bar(
                grouped_data,
                y="Среднее за месяц",
                title="Среднее за месяц по людям",
                labels={"Среднее за месяц": "Среднее за месяц (чел.)"},
                text="Среднее за месяц",
            )
            fig.update_traces(
                textposition="outside", textfont=dict(size=12, color="white")
            )
            fig = apply_chart_background(fig)
            st.plotly_chart(fig, use_container_width=True)
    else:
        # Grouped visualization
        grouping_cols = [col for col in group_cols if col != "period_month"]

        if has_period and len(grouping_cols) > 0:
            # Grouped bar chart with time series
            x_col = (
                "period_display"
                if "period_display" in grouped_data.columns
                else "period_month"
            )
            color_col = grouping_cols[0] if len(grouping_cols) == 1 else None

            if color_col:
                fig = px.bar(
                    grouped_data,
                    x=x_col,
                    y="Среднее за месяц",
                    color=color_col,
                    title="Среднее за месяц по людям в динамике",
                    labels={
                        x_col: "Месяц",
                        "Среднее за месяц": "Среднее за месяц (чел.)",
                    },
                    text="Среднее за месяц",
                )
                fig.update_layout(barmode="group")
                fig.update_xaxes(tickangle=-75, tickfont=dict(size=8), automargin=True)
                fig.update_traces(
                    textposition="outside", textfont=dict(size=12, color="white")
                )
                fig = apply_chart_background(fig)
                st.plotly_chart(fig, use_container_width=True)
            elif len(grouping_cols) > 1:
                # Multiple grouping columns - use first for color, show others in hover
                fig = px.bar(
                    grouped_data,
                    x=x_col,
                    y="Среднее за месяц",
                    color=grouping_cols[0],
                    title="Среднее за месяц по людям в динамике",
                    labels={
                        x_col: "Месяц",
                        "Среднее за месяц": "Среднее за месяц (чел.)",
                    },
                    text="Среднее за месяц",
                    facet_col=grouping_cols[1] if len(grouping_cols) > 1 else None,
                )
                fig.update_layout(barmode="group")
                fig.update_xaxes(tickangle=-75, tickfont=dict(size=8), automargin=True)
                fig.update_traces(
                    textposition="outside", textfont=dict(size=12, color="white")
                )
                fig = apply_chart_background(fig)
                st.plotly_chart(fig, use_container_width=True)
            else:
                # Fallback to line chart
                fig = px.line(
                    grouped_data,
                    x=x_col,
                    y="Среднее за месяц",
                    title="Среднее за месяц по людям в динамике",
                    labels={
                        x_col: "Месяц",
                        "Среднее за месяц": "Среднее за месяц (чел.)",
                    },
                    markers=True,
                )
                fig.update_xaxes(tickangle=-75, tickfont=dict(size=8), automargin=True)
                fig = apply_chart_background(fig)
            st.plotly_chart(fig, use_container_width=True)
        elif len(grouping_cols) > 0:
            # Grouped bar chart without time series (single month selected)
            color_col = grouping_cols[0] if len(grouping_cols) == 1 else None
            if color_col:
                fig = px.bar(
                    grouped_data,
                    x=color_col,
                    y="Среднее за месяц",
                    title="Среднее за месяц по людям",
                    labels={"Среднее за месяц": "Среднее за месяц (чел.)"},
                    text="Среднее за месяц",
                )
                fig.update_traces(
                    textposition="outside", textfont=dict(size=12, color="white")
                )
                fig.update_xaxes(tickangle=-75, tickfont=dict(size=8), automargin=True)
                fig = apply_chart_background(fig)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Не удалось построить график с выбранной группировкой.")
        else:
            st.info("Не удалось построить график с выбранной группировкой.")

    # Summary table
    if not grouped_data.empty:
        st.subheader("📋 Сводная таблица")
        display_cols = []

        # Add period column only if not filtering by specific period range
        if (selected_period_from == "Все" and selected_period_to == "Все") and (
            "period_display" in grouped_data.columns
            or "period_month" in grouped_data.columns
        ):
            display_cols.append(
                "period_display"
                if "period_display" in grouped_data.columns
                else "period_month"
            )

        # Add grouping columns
        if selected_grouping != "Без группировки":
            for col in group_cols:
                if col != "period_month" and col in grouped_data.columns:
                    display_cols.append(col)

        display_cols.append("Среднее за месяц")

        # Filter to only existing columns
        display_cols = [col for col in display_cols if col in grouped_data.columns]

        summary_table = grouped_data[display_cols].copy()
        summary_table["Среднее за месяц"] = summary_table["Среднее за месяц"].apply(
            lambda x: f"{x:.2f}" if pd.notna(x) else "0"
        )
        # Rename columns to Russian
        summary_table = summary_table.rename(columns={
            "period_display": "Период",
            "period_month": "Период",
            "project name": "Проект",
            "section": "Этап",
            "block": "Блок"
        })
        html_table = format_dataframe_as_html(summary_table)
        st.markdown(html_table, unsafe_allow_html=True)


# ==================== DASHBOARD 8.7: Documentation ====================
def dashboard_documentation(df):
    st.header("📚 Выдача рабочей/проектной документации")

    # Find column names (they might have different formats)
    # Try to find columns by partial name matching
    def find_column(df, possible_names):
        """Find column by possible names"""
        for col in df.columns:
            # Normalize column name: remove newlines, extra spaces, normalize case
            col_normalized = str(col).replace("\n", " ").replace("\r", " ").strip()
            col_lower = col_normalized.lower()

            for name in possible_names:
                name_lower = name.lower().strip()
                # Exact match (case insensitive)
                if name_lower == col_lower:
                    return col
                # Substring match
                if name_lower in col_lower or col_lower in name_lower:
                    return col
                # Check if all key words from name are in column
                name_words = [w for w in name_lower.split() if len(w) > 2]
                if name_words and all(word in col_lower for word in name_words):
                    return col

        # Special handling for RD count column with key words
        if any(
            "разделов" in n.lower() and "рд" in n.lower() and "договор" in n.lower()
            for n in possible_names
        ):
            for col in df.columns:
                col_lower = str(col).lower().replace("\n", " ").replace("\r", " ")
                key_words = ["разделов", "рд", "договор", "количество"]
                if all(word in col_lower for word in key_words if len(word) > 3):
                    return col

        return None

    # Find required columns - expanded search for RD count column
    rd_count_col = find_column(
        df,
        [
            "Количество разделов РД по Договору",
            "Количество разделов РД",
            "разделов РД",
            "Количетсов разделов РД по Договору",  # Handle typo
            "Количество разделов РД по договору",
            "Количество разделов РД по Договору",
        ],
    )

    on_approval_col = find_column(df, ["На согласовании", "согласовании"])
    in_production_col = find_column(
        df, ["Выдано в производство работ", "производство работ", "в производство"]
    )
    plan_start_col = (
        "plan start"
        if "plan start" in df.columns
        else find_column(df, ["Старт План", "План Старт"])
    )
    plan_end_col = (
        "plan end"
        if "plan end" in df.columns
        else find_column(df, ["Конец План", "План Конец"])
    )
    base_start_col = (
        "base start"
        if "base start" in df.columns
        else find_column(df, ["Старт Факт", "Факт Старт"])
    )
    base_end_col = (
        "base end"
        if "base end" in df.columns
        else find_column(df, ["Конец Факт", "Факт Конец"])
    )

    # Check if required columns exist
    missing_cols = []
    if not rd_count_col:
        missing_cols.append("Количество разделов РД по Договору")
    if not on_approval_col:
        missing_cols.append("На согласовании")
    if not in_production_col:
        missing_cols.append("Выдано в производство работ")

    if missing_cols:
        st.warning(f"⚠️ Отсутствуют необходимые колонки: {', '.join(missing_cols)}")
        st.info("Пожалуйста, убедитесь, что файл содержит все необходимые колонки.")
        return

    # Find project column for filtering
    project_col = (
        "project name"
        if "project name" in df.columns
        else find_column(df, ["Проект", "project"])
    )

    # Add filters
    st.subheader("Фильтры")
    filter_col1, filter_col2, filter_col3 = st.columns(3)

    # Filter by project
    selected_project = "Все"
    if project_col and project_col in df.columns:
        with filter_col1:
            projects = ["Все"] + sorted(df[project_col].dropna().unique().tolist())
            selected_project = st.selectbox(
                "Фильтр по проекту", projects, key="doc_project_filter"
            )

    # Filter by date period
    selected_date_start = None
    selected_date_end = None
    if plan_start_col and plan_start_col in df.columns:
        with filter_col2:
            # Convert dates for filtering
            plan_start_str = df[plan_start_col].astype(str)
            df_dates = pd.to_datetime(
                plan_start_str, errors="coerce", dayfirst=True, format="mixed"
            )
            valid_dates = df_dates[df_dates.notna()]

            if not valid_dates.empty:
                min_date = valid_dates.min().date()
                max_date = valid_dates.max().date()
                selected_date_start = st.date_input(
                    "Дата начала периода",
                    value=min_date,
                    min_value=min_date,
                    max_value=max_date,
                    key="doc_date_start",
                )
                selected_date_end = st.date_input(
                    "Дата окончания периода",
                    value=max_date,
                    min_value=min_date,
                    max_value=max_date,
                    key="doc_date_end",
                )

    # Filter by RD status
    with filter_col3:
        rd_status_options = ["Все"]
        if on_approval_col and on_approval_col in df.columns:
            rd_status_options.append("На согласовании")
        if in_production_col and in_production_col in df.columns:
            rd_status_options.append("Выдано в производство работ")

        # Find other status columns
        contractor_col = find_column(df, ["Выдана подрядчику", "подрядчику"])
        rework_col = find_column(df, ["На доработке", "доработке"])

        if contractor_col and contractor_col in df.columns:
            rd_status_options.append("Выдана подрядчику")
        if rework_col and rework_col in df.columns:
            rd_status_options.append("На доработке")

        selected_statuses = st.multiselect(
            "Фильтр по статусу РД",
            options=rd_status_options,
            default=["Все"],
            key="doc_status_filter",
        )

    # Apply filters to data
    filtered_df = df.copy()

    # Apply project filter
    if selected_project != "Все" and project_col and project_col in df.columns:
        filtered_df = filtered_df[
            filtered_df[project_col].astype(str).str.strip()
            == str(selected_project).strip()
        ]

    # Apply date filter
    if (
        selected_date_start
        and selected_date_end
        and plan_start_col
        and plan_start_col in df.columns
    ):
        plan_start_str = filtered_df[plan_start_col].astype(str)
        filtered_df[plan_start_col + "_parsed"] = pd.to_datetime(
            plan_start_str, errors="coerce", dayfirst=True, format="mixed"
        )
        date_mask = (
            filtered_df[plan_start_col + "_parsed"].notna()
            & (filtered_df[plan_start_col + "_parsed"].dt.date >= selected_date_start)
            & (filtered_df[plan_start_col + "_parsed"].dt.date <= selected_date_end)
        )
        filtered_df = filtered_df[date_mask].copy()

    # Apply status filter
    if "Все" not in selected_statuses and selected_statuses:
        status_mask = pd.Series([False] * len(filtered_df), index=filtered_df.index)

        if (
            "На согласовании" in selected_statuses
            and on_approval_col
            and on_approval_col in filtered_df.columns
        ):
            on_approval_series = (
                filtered_df[on_approval_col]
                .astype(str)
                .str.replace(",", ".", regex=False)
            )
            on_approval_numeric = pd.to_numeric(
                on_approval_series, errors="coerce"
            ).fillna(0)
            status_mask = status_mask | (on_approval_numeric > 0)

        if (
            "Выдано в производство работ" in selected_statuses
            and in_production_col
            and in_production_col in filtered_df.columns
        ):
            in_production_series = (
                filtered_df[in_production_col]
                .astype(str)
                .str.replace(",", ".", regex=False)
            )
            in_production_numeric = pd.to_numeric(
                in_production_series, errors="coerce"
            ).fillna(0)
            status_mask = status_mask | (in_production_numeric > 0)

        if (
            "Выдана подрядчику" in selected_statuses
            and contractor_col
            and contractor_col in filtered_df.columns
        ):
            contractor_series = (
                filtered_df[contractor_col]
                .astype(str)
                .str.replace(",", ".", regex=False)
            )
            contractor_numeric = pd.to_numeric(
                contractor_series, errors="coerce"
            ).fillna(0)
            status_mask = status_mask | (contractor_numeric > 0)

        if (
            "На доработке" in selected_statuses
            and rework_col
            and rework_col in filtered_df.columns
        ):
            rework_series = (
                filtered_df[rework_col].astype(str).str.replace(",", ".", regex=False)
            )
            rework_numeric = pd.to_numeric(rework_series, errors="coerce").fillna(0)
            status_mask = status_mask | (rework_numeric > 0)

        filtered_df = filtered_df[status_mask].copy()

    if filtered_df.empty:
        st.info("Нет данных для выбранных фильтров.")
        return

    # Use filtered_df for all subsequent operations
    df = filtered_df

    # Prepare data for pie chart "Исполнение РД"
    # Sum values for "На согласовании" and "Выдано в производство работ"
    try:
        # Convert to numeric, handling comma as decimal separator
        on_approval_series = (
            df[on_approval_col].astype(str).str.replace(",", ".", regex=False)
        )
        on_approval_sum = (
            pd.to_numeric(on_approval_series, errors="coerce").fillna(0).sum()
        )

        in_production_series = (
            df[in_production_col].astype(str).str.replace(",", ".", regex=False)
        )
        in_production_sum = (
            pd.to_numeric(in_production_series, errors="coerce").fillna(0).sum()
        )

        # Create pie chart
        if on_approval_sum > 0 or in_production_sum > 0:
            st.subheader("Исполнение РД")
            # Округляем значения до целых
            pie_data = {
                "На согласовании": int(round(on_approval_sum)),
                "Выдано в производство работ": int(round(in_production_sum)),
            }

            fig_pie = px.pie(
                values=list(pie_data.values()),
                names=list(pie_data.keys()),
                title="Исполнение РД",
                color_discrete_map={
                    "На согласовании": "#2E86AB",
                    "Выдано в производство работ": "#06A77D",
                },
            )
            # Подготавливаем текст с значениями и процентами
            total = sum(pie_data.values())
            custom_texts = []
            for name, value in pie_data.items():
                percent_val = (value / total * 100) if total > 0 else 0
                text = f"{name}<br>{value}<br>({percent_val:.0f}%)"
                custom_texts.append(text)

            fig_pie.update_traces(
                textposition="inside",
                textinfo="label",
                texttemplate="%{label}",
                textfont=dict(size=14, color="white"),
                customdata=list(pie_data.values()),
                hovertemplate="<b>%{label}</b><br>Значение: %{customdata}<br>Процент: %{percent:.0f}%<br><extra></extra>",
            )

            # Обновляем текст вручную для отображения значений и процентов
            for i, trace in enumerate(fig_pie.data):
                if i < len(custom_texts):
                    trace.text = [custom_texts[i]]

            fig_pie = apply_chart_background(fig_pie)
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("Нет данных для построения графика 'Исполнение РД'.")
    except Exception as e:
        st.error(f"Ошибка при построении графика 'Исполнение РД': {str(e)}")

    # Prepare data for "Динамика выдачи РД"
    # X-axis: "Старт План" (plan start date)
    # Plan (Y-axis): "РД по Договору" (grouped by "Старт План")
    # Fact (Y-axis): "Выдано в производство работ" (grouped by "Старт План")
    try:
        # Find column for plan data: "РД по Договору"
        rd_plan_col = find_column(
            df, ["РД по Договору", "РД по договору", "рд по договору", "РД по Договору"]
        )

        # Check if required columns exist
        if not plan_start_col or plan_start_col not in df.columns:
            st.warning(
                "⚠️ Для построения графика 'Динамика выдачи РД' необходима колонка 'Старт План' (plan start)."
            )
            return

        if not rd_plan_col or rd_plan_col not in df.columns:
            st.warning(
                "⚠️ Для построения графика 'Динамика выдачи РД' необходима колонка 'РД по Договору'."
            )
            return

        if not in_production_col or in_production_col not in df.columns:
            st.warning(
                "⚠️ Для построения графика 'Динамика выдачи РД' необходима колонка 'Выдано в производство работ'."
            )
            return

        # Convert columns to numeric - handle comma as decimal separator
        # Replace comma with dot for numeric conversion
        # Plan: use "РД по Договору"
        rd_plan_series = df[rd_plan_col].astype(str).str.replace(",", ".", regex=False)
        df["rd_plan_numeric"] = pd.to_numeric(rd_plan_series, errors="coerce").fillna(0)

        # Convert "Выдано в производство работ" to numeric - handle comma as decimal separator
        in_production_series = (
            df[in_production_col].astype(str).str.replace(",", ".", regex=False)
        )
        df["in_production_numeric"] = pd.to_numeric(
            in_production_series, errors="coerce"
        ).fillna(0)

        # Convert dates - handle DD.MM.YYYY format
        # First convert to string, then parse with dayfirst=True
        plan_start_str = df[plan_start_col].astype(str)
        df[plan_start_col] = pd.to_datetime(
            plan_start_str, errors="coerce", dayfirst=True, format="mixed"
        )

        # Prepare data
        # Both Plan and Fact are grouped by plan_start_col (Старт план)
        dynamics_data = []

        # Plan data: group by plan start date, sum "РД по Договору"
        # Always include plan data, even if some values are 0
        plan_mask = df[plan_start_col].notna()
        if plan_mask.any():
            plan_grouped = (
                df[plan_mask]
                .groupby(df[plan_mask][plan_start_col].dt.date)
                .agg({"rd_plan_numeric": "sum"})
                .reset_index()
            )
            plan_grouped.columns = ["Дата", "Количество"]
            plan_grouped["Тип"] = "План"
            # Fill NaN with 0 and ensure all values are numeric
            plan_grouped["Количество"] = plan_grouped["Количество"].fillna(0)
            # Always add plan data, even if all values are 0
            dynamics_data.append(plan_grouped)

        # Fact data: group by plan start date (same as Plan!), sum "Выдано в производство работ"
        fact_mask = df[plan_start_col].notna()  # Use plan_start_col for both!
        if fact_mask.any():
            fact_grouped = (
                df[fact_mask]
                .groupby(df[fact_mask][plan_start_col].dt.date)
                .agg({"in_production_numeric": "sum"})
                .reset_index()
            )
            fact_grouped.columns = ["Дата", "Количество"]
            fact_grouped["Тип"] = "Факт"
            # Fill NaN with 0 and ensure all values are numeric
            fact_grouped["Количество"] = fact_grouped["Количество"].fillna(0)
            # Filter out rows where sum is 0 for fact (only show actual production)
            fact_grouped = fact_grouped[fact_grouped["Количество"] > 0]
            if not fact_grouped.empty:
                dynamics_data.append(fact_grouped)

        # Always show graph if we have plan data, even if fact data is empty
        if dynamics_data:
            st.subheader("Динамика выдачи РД")
            dynamics_df = pd.concat(dynamics_data, ignore_index=True)
            dynamics_df = dynamics_df.sort_values("Дата")

            # Вычисляем накопительные значения для каждого типа отдельно
            dynamics_df["Накопительное_значение"] = 0
            for typ in dynamics_df["Тип"].unique():
                mask = dynamics_df["Тип"] == typ
                dynamics_df.loc[mask, "Накопительное_значение"] = dynamics_df.loc[
                    mask, "Количество"
                ].cumsum()

            # Используем накопительные значения для графика
            dynamics_df["Количество"] = dynamics_df["Накопительное_значение"]

            # Create line chart with text labels always visible
            # Prepare text labels for each data point
            dynamics_df["Текст"] = dynamics_df["Количество"].apply(
                lambda x: f"{x:.0f}" if pd.notna(x) else ""
            )

            fig_dynamics = px.line(
                dynamics_df,
                x="Дата",
                y="Количество",
                color="Тип",
                title="Динамика выдачи РД",
                markers=True,
                labels={"Количество": "Количество", "Дата": "Дата (Старт План)"},
                text="Текст",
            )

            fig_dynamics.update_layout(
                xaxis_title="Дата (Старт План)",
                yaxis_title="Количество",
                hovermode="x unified",
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1,
                    title_text="",
                ),
            )
            # Update legend labels to be more descriptive
            fig_dynamics.for_each_trace(
                lambda t: t.update(
                    name=(
                        "План (РД по Договору)"
                        if t.name == "План"
                        else (
                            "Факт (Выдано в производство работ)"
                            if t.name == "Факт"
                            else t.name
                        )
                    )
                )
            )
            # Add text labels and format - ensure text is always visible
            fig_dynamics.update_traces(
                line=dict(width=2),
                marker=dict(size=8),
                mode="lines+markers+text",  # Enable text display mode
                textposition="top center",
                textfont=dict(size=10, color="white"),
            )
            fig_dynamics = apply_chart_background(fig_dynamics)
            st.plotly_chart(fig_dynamics, use_container_width=True)
        else:
            st.warning("⚠️ Нет данных для построения графика 'Динамика выдачи РД'.")
    except Exception as e:
        st.error(f"Ошибка при построении графика 'Динамика выдачи РД': {str(e)}")
        import traceback

        st.code(traceback.format_exc())

    # Add separator
    st.divider()

    # Add "Просрочка выдачи РД" chart
    dashboard_rd_delay(df)


# ==================== DASHBOARD 7.1: BDDR by Period (Mock) ====================
def dashboard_bddr_by_period(df):
    """
    Заглушка для отчета БДДР по месяцам.
    Данные БДДР будут подключены позднее, сейчас отображается только описание.
    """
    st.header("💰 БДДР по месяцам")
    st.info(
        "Отчет **БДДР по месяцам** находится в разработке. "
        "После подключения источника данных здесь будет аналитика по доходам и расходам (БДДР) в разрезе месяцев."
    )


# ==================== DASHBOARD 7.2: BDDR by Section (Mock) ====================
def dashboard_bddr_by_section(df):
    """
    Заглушка для отчета БДДР по лотам.
    Данные БДДР будут подключены позднее, сейчас отображается только описание.
    """
    st.header("💰 БДДР по лотам")
    st.info(
        "Отчет **БДДР по лотам** находится в разработке. "
        "После подключения источника данных здесь будет аналитика БДДР по лотам/разделам и периодам."
    )


# ==================== DASHBOARD 8: Budget by Type (Plan/Fact/Reserve) ====================
def dashboard_budget_by_type(df):
    # Переключатель типа бюджета (БДДС / БДДР)
    type_col = st.columns(1)[0]
    with type_col:
        budget_view_type = st.radio(
            "Тип бюджета",
            ["БДДС", "БДДР"],
            index=0,
            key="budget_view_type",
            horizontal=True,
            help=(
                "Выберите, для какого типа бюджета (БДДС или БДДР) смотреть план/факт. "
                "Сейчас используется единый набор данных, переключатель влияет только на отображение."
            ),
        )

    st.header(f"💰 Бюджет План/Прогноз/Факт ({budget_view_type})")

    col1, col2 = st.columns(2)

    with col1:
        if "project name" in df.columns:
            projects = ["Все"] + sorted(df["project name"].dropna().unique().tolist())
            selected_project = st.selectbox(
                "Фильтр по проекту", projects, key="budget_type_project"
            )
        else:
            selected_project = "Все"
            st.info("Колонка 'project name' не найдена")

    with col2:
        if "section" in df.columns:
            sections = ["Все"] + sorted(df["section"].dropna().unique().tolist())
            selected_section = st.selectbox(
                "Фильтр по этапу", sections, key="budget_type_section"
            )
        else:
            selected_section = "Все"

    # Apply filters
    filtered_df = df.copy()
    if selected_project != "Все" and "project name" in filtered_df.columns:
        filtered_df = filtered_df[
            filtered_df["project name"].astype(str).str.strip()
            == str(selected_project).strip()
        ]
    if selected_section != "Все" and "section" in filtered_df.columns:
        filtered_df = filtered_df[
            filtered_df["section"].astype(str).str.strip()
            == str(selected_section).strip()
        ]

    # Check for budget columns
    has_budget = (
        "budget plan" in filtered_df.columns and "budget fact" in filtered_df.columns
    )

    if not has_budget:
        st.warning("Столбцы бюджета (budget plan, budget fact) не найдены в данных.")
        return

    # Calculate reserve budget (plan - fact, negative means over budget)
    # Convert to numeric first to avoid TypeError
    filtered_df["budget plan"] = pd.to_numeric(
        filtered_df["budget plan"], errors="coerce"
    )
    filtered_df["budget fact"] = pd.to_numeric(
        filtered_df["budget fact"], errors="coerce"
    )
    filtered_df["reserve budget"] = (
        filtered_df["budget plan"] - filtered_df["budget fact"]
    )

    # ========== Histogram: Budget by Project and Type ==========
    st.subheader(
        "📊 Гистограмма: Бюджет План/Прогноз/Факт/корректировка/резерв по проектам"
    )

    # Check for adjusted budget column in original dataframe
    adjusted_budget_col = None
    if "budget adjusted" in df.columns:
        adjusted_budget_col = "budget adjusted"
    elif "adjusted budget" in df.columns:
        adjusted_budget_col = "adjusted budget"

    # Filters for histogram
    col_hist1 = st.columns(1)[0]

    with col_hist1:
        # Checkbox for showing reserve
        show_reserve = st.checkbox(
            "Показать резерв", value=False, key="budget_show_reserve"
        )

        # Budget types to show (always show Plan and Fact, optionally Reserve)
        selected_budget_types = ["Бюджет План", "Бюджет Факт"]
        if adjusted_budget_col:
            selected_budget_types.append("Бюджет Корректировка")
        if show_reserve:
            selected_budget_types.append("Резерв бюджета")

    # Apply filters for histogram - use filtered_df to respect project filter
    hist_df = filtered_df.copy()

    if selected_section != "Все" and "section" in hist_df.columns:
        hist_df = hist_df[
            hist_df["section"].astype(str).str.strip() == str(selected_section).strip()
        ]

    if hist_df.empty:
        st.info("Нет данных для отображения гистограммы с выбранными фильтрами.")
    else:
        # Convert budget columns to numeric
        hist_df["budget plan"] = pd.to_numeric(
            hist_df["budget plan"], errors="coerce"
        ).fillna(0)
        hist_df["budget fact"] = pd.to_numeric(
            hist_df["budget fact"], errors="coerce"
        ).fillna(0)
        hist_df["reserve budget"] = hist_df["budget plan"] - hist_df["budget fact"]

        # Group by project and aggregate
        if "project name" in hist_df.columns:
            budget_by_project = (
                hist_df.groupby("project name")
                .agg(
                    {
                        "budget plan": "sum",
                        "budget fact": "sum",
                        "reserve budget": "sum",
                    }
                )
                .reset_index()
            )

            # Add adjusted budget if available
            if adjusted_budget_col and adjusted_budget_col in hist_df.columns:
                # Convert to numeric first
                hist_df[adjusted_budget_col] = pd.to_numeric(
                    hist_df[adjusted_budget_col], errors="coerce"
                ).fillna(0)
                budget_by_project["budget adjusted"] = (
                    hist_df.groupby("project name")[adjusted_budget_col].sum().values
                )
            else:
                budget_by_project["budget adjusted"] = 0

            # Transform to long format
            hist_melted = []
            for idx, row in budget_by_project.iterrows():
                project = row["project name"]

                if "Бюджет План" in selected_budget_types:
                    hist_melted.append(
                        {
                            "project name": project,
                            "Тип бюджета": "Бюджет План",
                            "Сумма": row["budget plan"],
                        }
                    )

                if "Бюджет Факт" in selected_budget_types:
                    hist_melted.append(
                        {
                            "project name": project,
                            "Тип бюджета": "Бюджет Факт",
                            "Сумма": row["budget fact"],
                        }
                    )

                if (
                    "Бюджет Корректировка" in selected_budget_types
                    and adjusted_budget_col
                ):
                    hist_melted.append(
                        {
                            "project name": project,
                            "Тип бюджета": "Бюджет Корректировка",
                            "Сумма": row["budget adjusted"],
                        }
                    )

                if "Резерв бюджета" in selected_budget_types:
                    hist_melted.append(
                        {
                            "project name": project,
                            "Тип бюджета": "Резерв бюджета",
                            "Сумма": row["reserve budget"],
                        }
                    )

            hist_by_type_df = pd.DataFrame(hist_melted)

            if hist_by_type_df.empty:
                st.info("Нет данных для отображения с выбранными типами бюджета.")
            else:
                # Преобразуем значения в миллионы рублей для отображения на столбцах
                hist_by_type_df["Сумма_млн"] = hist_by_type_df["Сумма"] / 1000000

                # Create histogram - use millions for y-axis
                fig_hist = px.bar(
                    hist_by_type_df,
                    x="project name",
                    y="Сумма_млн",
                    color="Тип бюджета",
                    title="Бюджет План/Прогноз/Факт/корректировка/резерв по проектам",
                    labels={"project name": "Проект", "Сумма_млн": "Сумма бюджета, млн руб."},
                    barmode="group",
                    text="Сумма_млн",
                    template=None,  # Убираем дефолтный template
                    color_discrete_map={
                        "Бюджет План": "#2E86AB",
                        "Бюджет Факт": "#A23B72",
                        "Бюджет Корректировка": "#F18F01",
                        "Резерв бюджета": "#06A77D",
                    },
                )

                # Update layout
                fig_hist.update_layout(
                    xaxis_title="Проект",
                    yaxis_title="Сумма бюджета, млн руб.",
                    height=600,
                    legend=dict(
                        orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1
                    ),
                    xaxis=dict(tickangle=-75, tickfont=dict(size=8), automargin=True),
                )

                # Add text labels on the edge of bars (в миллионах рублей)
                fig_hist.update_traces(
                    textposition="outside",
                    texttemplate="%{text:.2f} млн руб.",
                    textfont=dict(size=12, color="white"),
                )

                fig_hist = apply_chart_background(fig_hist)
                st.plotly_chart(fig_hist, use_container_width=True)

                # Summary table
                with st.expander("📋 Сводная таблица по проектам", expanded=False):
                    summary_hist = hist_by_type_df.pivot_table(
                        index="project name",
                        columns="Тип бюджета",
                        values="Сумма",
                        aggfunc="sum",
                        fill_value=0,
                    ).reset_index()

                    # Convert to millions
                    for col in summary_hist.columns:
                        if col != "project name" and col in summary_hist.columns:
                            summary_hist[col] = (summary_hist[col] / 1_000_000).round(2)

                    # Add "Отклонение" column: фактический бюджет - плановый
                    if "Бюджет Факт" in summary_hist.columns and "Бюджет План" in summary_hist.columns:
                        summary_hist["Отклонение"] = (
                            summary_hist["Бюджет Факт"] - summary_hist["Бюджет План"]
                        ).round(2)

                    # Rename "project name" to Russian and add "млн руб." to budget columns
                    summary_hist = summary_hist.rename(columns={"project name": "Проект"})
                    # Rename budget columns to include "млн руб."
                    rename_budget_cols = {}
                    for col in summary_hist.columns:
                        if col not in ["Проект", "Отклонение"]:
                            rename_budget_cols[col] = f"{col}, млн руб."
                    summary_hist = summary_hist.rename(columns=rename_budget_cols)

                    # Use format_dataframe_as_html with conditional formatting for "Отклонение" column
                    conditional_cols = {
                        "Отклонение": {
                            'positive_color': '#ff4444',
                            'negative_color': '#44ff44'
                        }
                    }
                    html_table = format_dataframe_as_html(summary_hist, conditional_cols=conditional_cols)
                    st.markdown(html_table, unsafe_allow_html=True)
        else:
            st.warning(
                "Колонка 'project name' не найдена в данных для построения гистограммы."
            )


# ==================== DASHBOARD 8.1: Budget Old Charts ====================
def dashboard_budget_old_charts(df):
    st.header("💰 БДДС (старые графики)")

    col1, col2, col3 = st.columns(3)

    with col1:
        period_type = st.selectbox(
            "Группировать по", ["Месяц", "Квартал", "Год"], key="budget_old_period"
        )
        period_map = {"Месяц": "Month", "Квартал": "Quarter", "Год": "Year"}
        period_type_en = period_map.get(period_type, "Month")

    with col2:
        if "project name" in df.columns:
            projects = ["Все"] + sorted(df["project name"].dropna().unique().tolist())
            selected_project = st.selectbox(
                "Фильтр по проекту", projects, key="budget_old_project"
            )
        else:
            selected_project = "Все"

    with col3:
        if "section" in df.columns:
            sections = ["Все"] + sorted(df["section"].dropna().unique().tolist())
            selected_section = st.selectbox(
                "Фильтр по этапу", sections, key="budget_old_section"
            )
        else:
            selected_section = "Все"

    # Additional filter row: Block
    col4 = st.columns(1)[0]
    with col4:
        if "block" in df.columns:
            blocks = ["Все"] + sorted(df["block"].dropna().unique().tolist())
            selected_block = st.selectbox(
                "Фильтр по блоку", blocks, key="budget_old_block"
            )
        else:
            selected_block = "Все"

    # Apply filters
    filtered_df = df.copy()
    if selected_project != "Все" and "project name" in filtered_df.columns:
        filtered_df = filtered_df[
            filtered_df["project name"].astype(str).str.strip()
            == str(selected_project).strip()
        ]
    if selected_section != "Все" and "section" in filtered_df.columns:
        filtered_df = filtered_df[
            filtered_df["section"].astype(str).str.strip()
            == str(selected_section).strip()
        ]
    if selected_block != "Все" and "block" in filtered_df.columns:
        filtered_df = filtered_df[
            filtered_df["block"].astype(str).str.strip() == str(selected_block).strip()
        ]

    # Check for budget columns
    has_budget = (
        "budget plan" in filtered_df.columns and "budget fact" in filtered_df.columns
    )

    if not has_budget:
        st.warning("Столбцы бюджета (budget plan, budget fact) не найдены в данных.")
        return

    # Determine period column
    if period_type_en == "Month":
        period_col = "plan_month"
        period_label = "Месяц"
    elif period_type_en == "Quarter":
        period_col = "plan_quarter"
        period_label = "Квартал"
    else:
        period_col = "plan_year"
        period_label = "Год"

    if period_col not in filtered_df.columns:
        st.warning(f"Столбец периода '{period_col}' не найден.")
        return

    # Calculate reserve budget (plan - fact, negative means over budget)
    # Convert to numeric first to avoid TypeError
    filtered_df["budget plan"] = pd.to_numeric(
        filtered_df["budget plan"], errors="coerce"
    )
    filtered_df["budget fact"] = pd.to_numeric(
        filtered_df["budget fact"], errors="coerce"
    )
    filtered_df["reserve budget"] = (
        filtered_df["budget plan"] - filtered_df["budget fact"]
    )

    # Group by period first to get totals
    budget_by_period = (
        filtered_df.groupby(period_col)
        .agg({"budget plan": "sum", "budget fact": "sum", "reserve budget": "sum"})
        .reset_index()
    )

    # Format period for display
    def format_period_display(period_val):
        if pd.isna(period_val):
            return "Н/Д"
        if isinstance(period_val, pd.Period):
            try:
                if period_val.freqstr == "M" or period_val.freqstr.startswith(
                    "M"
                ):  # Month
                    month_name = get_russian_month_name(period_val)
                    year = period_val.year
                    return f"{month_name} {year}"
                elif period_val.freqstr == "Q" or period_val.freqstr.startswith(
                    "Q"
                ):  # Quarter
                    return f"Q{period_val.quarter} {period_val.year}"
                elif period_val.freqstr == "Y" or period_val.freqstr == "A-DEC":  # Year
                    return str(period_val.year)
                else:
                    month_name = get_russian_month_name(period_val)
                    year = period_val.year
                    return f"{month_name} {year}"
            except:
                # Try parsing as string
                period_str = str(period_val)
                try:
                    if "-" in period_str:
                        parts = period_str.split("-")
                        if len(parts) >= 2:
                            year = parts[0]
                            month = parts[1]
                            month_num = int(month)
                            month_name = RUSSIAN_MONTHS.get(month_num, "")
                            if month_name:
                                return f"{month_name} {year}"
                except:
                    pass
                return str(period_val)
        elif isinstance(period_val, str):
            # Try parsing string like "2025-01"
            try:
                if "-" in period_val:
                    parts = period_val.split("-")
                    if len(parts) >= 2:
                        year = parts[0]
                        month = parts[1]
                        month_num = int(month)
                        month_name = RUSSIAN_MONTHS.get(month_num, "")
                        if month_name:
                            return f"{month_name} {year}"
            except:
                pass
        return str(period_val)

    budget_by_period[period_col] = budget_by_period[period_col].apply(
        format_period_display
    )

    # Checkbox to hide/show reserve budget (default: hidden)
    hide_reserve = st.checkbox(
        "Скрыть резерв", value=True, key="budget_old_hide_reserve"
    )

    # Transform data to long format - group by budget type
    budget_melted = []
    for idx, row in budget_by_period.iterrows():
        period = row[period_col]
        budget_melted.append(
            {
                period_col: period,
                "Тип бюджета": "Бюджет План",
                "Сумма": row["budget plan"],
            }
        )
        budget_melted.append(
            {
                period_col: period,
                "Тип бюджета": "Бюджет Факт",
                "Сумма": row["budget fact"],
            }
        )
        # Add reserve only if not hidden
        if not hide_reserve:
            budget_melted.append(
                {
                    period_col: period,
                    "Тип бюджета": "Резерв бюджета",
                    "Сумма": row["reserve budget"],
                }
            )

    budget_by_type_df = pd.DataFrame(budget_melted)

    # Convert to millions
    budget_by_type_df["Сумма_млн"] = (budget_by_type_df["Сумма"] / 1_000_000).round(2)

    # Visualizations
    col1, col2 = st.columns(2)

    with col1:
        # Stacked area chart showing all budget types
        fig = px.area(
            budget_by_type_df,
            x=period_col,
            y="Сумма_млн",
            color="Тип бюджета",
            title="Бюджет по типам по периоду (накопительно)",
            labels={period_col: period_label, "Сумма_млн": "Сумма бюджета, млн руб."},
            text="Сумма_млн",
        )
        fig.update_xaxes(tickangle=-75, tickfont=dict(size=8), automargin=True)
        fig.update_traces(textposition="top center", texttemplate="%{text:.2f} млн руб.")
        fig = apply_chart_background(fig)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Grouped bar chart
        fig = px.bar(
            budget_by_type_df,
            x=period_col,
            y="Сумма_млн",
            color="Тип бюджета",
            title="Бюджет по типам по периоду",
            labels={period_col: period_label, "Сумма_млн": "Сумма бюджета, млн руб."},
            barmode="group",
            text="Сумма_млн",
            color_discrete_map={
                "Бюджет План": "#2E86AB",
                "Бюджет Факт": "#A23B72",
                "Резерв бюджета": "#06A77D",
            },
        )
        fig.update_xaxes(tickangle=-75, tickfont=dict(size=8), automargin=True)
        fig.update_traces(textposition="outside", texttemplate="%{text:.2f} млн руб.", textfont=dict(size=14, color="white"))
        fig = apply_chart_background(fig)
        st.plotly_chart(fig, use_container_width=True)

    # Line chart comparing all types
    fig = px.line(
        budget_by_type_df,
        x=period_col,
        y="Сумма_млн",
        color="Тип бюджета",
        title="Сравнение типов бюджета по периоду",
        labels={period_col: period_label, "Сумма_млн": "Сумма бюджета, млн руб."},
        markers=True,
        text="Сумма_млн",
    )
    fig.update_xaxes(tickangle=-45)
    fig.update_traces(textposition="top center", texttemplate="%{text:.2f} млн руб.")
    fig = apply_chart_background(fig)
    st.plotly_chart(fig, use_container_width=True)

    # Summary metrics - convert to millions
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        total_plan = budget_by_type_df[
            budget_by_type_df["Тип бюджета"] == "Бюджет План"
        ]["Сумма_млн"].sum()
        st.metric("Всего План", f"{total_plan:.2f} млн руб." if pd.notna(total_plan) else "Н/Д")
    with col2:
        total_fact = budget_by_type_df[
            budget_by_type_df["Тип бюджета"] == "Бюджет Факт"
        ]["Сумма_млн"].sum()
        st.metric("Всего Факт", f"{total_fact:.2f} млн руб." if pd.notna(total_fact) else "Н/Д")
    with col3:
        total_reserve = (
            budget_by_type_df[budget_by_type_df["Тип бюджета"] == "Резерв бюджета"][
                "Сумма_млн"
            ].sum()
            if "Резерв бюджета" in budget_by_type_df["Тип бюджета"].values
            else 0
        )
        st.metric(
            "Всего Резерв",
            f"{total_reserve:.2f} млн руб." if pd.notna(total_reserve) else "Н/Д",
        )
    with col4:
        variance = (
            total_plan - total_fact
            if pd.notna(total_plan) and pd.notna(total_fact)
            else None
        )
        st.metric(
            "Отклонение",
            (
                f"{variance:.2f} млн руб."
                if variance is not None and pd.notna(variance)
                else "Н/Д"
            ),
        )

    # Pivot table for better readability - use millions
    pivot_table = budget_by_type_df.pivot(
        index=period_col, columns="Тип бюджета", values="Сумма_млн"
    ).fillna(0)

    # Detailed table - format with budget types as separate columns
    st.subheader("Детальная таблица")
    # Use pivot table format for detailed table (same as summary but with better formatting)
    detailed_table = pivot_table.copy()

    # Round to 2 decimal places
    for col in detailed_table.columns:
        detailed_table[col] = detailed_table[col].round(2)

    # Rename columns to include "млн руб."
    detailed_table = detailed_table.rename(columns={col: f"{col}, млн руб." for col in detailed_table.columns})

    html_table = format_dataframe_as_html(detailed_table)
    st.markdown(html_table, unsafe_allow_html=True)
    # Reset index to make period a column
    detailed_table = detailed_table.reset_index()
    # Rename columns for better readability - remove period_original and rename to Russian
    detailed_table.columns.name = None
    # Rename period column to Russian
    period_label_map = {"plan_month": "Месяц", "plan_quarter": "Квартал", "plan_year": "Год"}
    period_display_name = period_label_map.get(period_col, period_col)
    detailed_table = detailed_table.rename(columns={period_col: period_display_name})
    html_table = format_dataframe_as_html(detailed_table)
    st.markdown(html_table, unsafe_allow_html=True)


# ==================== DASHBOARD: Approved Budget ====================
def calculate_approved_budget(df, rule_name="default"):
    """
    Рассчитывает утвержденный бюджет на основе правил распределения.

    Логика расчета:
    1. Группируем задачи по проекту/разделу/задаче
    2. Для каждой группы находим все месяцы этапа (от минимальной даты начала до максимальной даты окончания)
    3. Для каждого месяца находим все задачи, активные в этом месяце
    4. Суммируем плановый бюджет активных задач - это 100% для месяца
    5. Распределяем эту сумму по правилу между месяцами этапа

    Правила распределения:
    - default: 50% - первый месяц, 45% - равномерно по промежуточным месяцам, 5% - последний месяц

    Args:
        df: DataFrame с данными проектов
        rule_name: название правила из справочника

    Returns:
        DataFrame с распределением утвержденного бюджета по месяцам
    """
    # Справочник правил распределения бюджета
    budget_rules = {
        "default": {
            "first_month_percent": 0.50,  # 50% на первый месяц
            "middle_months_percent": 0.45,  # 45% на промежуточные месяцы
            "last_month_percent": 0.05,  # 5% на последний месяц
            "description": "50% - первый месяц, 45% - равномерно по промежуточным месяцам, 5% - последний месяц",
        }
    }

    # Получаем правило
    if rule_name not in budget_rules:
        rule_name = "default"
    rule = budget_rules[rule_name]

    # Проверяем наличие необходимых колонок
    required_cols = ["budget plan", "plan start", "plan end"]
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        return (
            pd.DataFrame(),
            f"Отсутствуют необходимые колонки: {', '.join(missing_cols)}",
        )

    # Копируем данные для работы
    work_df = df.copy()

    # Конвертируем даты
    work_df["plan start"] = pd.to_datetime(
        work_df["plan start"], errors="coerce", dayfirst=True
    )
    work_df["plan end"] = pd.to_datetime(
        work_df["plan end"], errors="coerce", dayfirst=True
    )
    work_df["budget plan"] = pd.to_numeric(work_df["budget plan"], errors="coerce")

    # Фильтруем строки с валидными данными
    valid_mask = (
        work_df["plan start"].notna()
        & work_df["plan end"].notna()
        & work_df["budget plan"].notna()
        & (work_df["budget plan"] > 0)
        & (work_df["plan start"] <= work_df["plan end"])
    )
    work_df = work_df[valid_mask].copy()

    if work_df.empty:
        return pd.DataFrame(), "Нет данных с валидными датами и бюджетом"

    # Определяем группировку: группируем по комбинации project + section + task
    # Это позволяет правильно обрабатывать случаи, когда выбраны разные уровни фильтрации
    grouping_cols = []
    if "project name" in work_df.columns:
        grouping_cols.append("project name")
    if "section" in work_df.columns:
        grouping_cols.append("section")
    if "task name" in work_df.columns:
        grouping_cols.append("task name")

    # Если нет колонок для группировки, обрабатываем все задачи вместе
    if not grouping_cols:
        # Создаем фиктивную группу для всех задач
        work_df["_group"] = "all"
        grouping_cols = ["_group"]

    # Список для хранения результатов
    approved_budget_rows = []

    # Группируем задачи
    if grouping_cols:
        grouped = work_df.groupby(grouping_cols)
    else:
        # Если нет колонок для группировки, создаем одну группу
        grouped = [("all", work_df)]

    for group_key, group_df in grouped:
        # Находим минимальную дату начала и максимальную дату окончания для группы
        min_start = group_df["plan start"].min()
        max_end = group_df["plan end"].max()

        if pd.isna(min_start) or pd.isna(max_end):
            continue

        # Генерируем все месяцы этапа
        current_date = min_start.replace(day=1)
        end_month = max_end.replace(day=1)

        months = []
        while current_date <= end_month:
            months.append(current_date.to_period("M"))
            # Переходим к следующему месяцу
            if current_date.month == 12:
                current_date = current_date.replace(year=current_date.year + 1, month=1)
            else:
                current_date = current_date.replace(month=current_date.month + 1)

        if len(months) == 0:
            continue

        # Для каждого месяца находим активные задачи и суммируем их плановый бюджет
        monthly_budgets = {}
        for month in months:
            month_start = month.start_time
            month_end = month.end_time

            # Находим задачи, активные в этом месяце
            active_tasks = group_df[
                (group_df["plan start"] <= month_end)
                & (group_df["plan end"] >= month_start)
            ]

            # Суммируем плановый бюджет активных задач - это 100% для месяца
            total_budget = active_tasks["budget plan"].sum()
            monthly_budgets[month] = total_budget

        # Рассчитываем распределение бюджета по правилу
        num_months = len(months)

        if num_months == 1:
            # Если только один месяц, весь бюджет идет туда
            first_month_percent = 1.0
            middle_months_percent = 0.0
            last_month_percent = 0.0
        elif num_months == 2:
            # Если два месяца: 50% на первый, 50% на последний
            first_month_percent = rule["first_month_percent"]
            middle_months_percent = 0.0
            last_month_percent = (
                rule["middle_months_percent"] + rule["last_month_percent"]
            )
        else:
            # Если больше двух месяцев: 50% на первый, 45% равномерно на промежуточные, 5% на последний
            first_month_percent = rule["first_month_percent"]
            last_month_percent = rule["last_month_percent"]
            middle_months_percent = rule["middle_months_percent"] / (num_months - 2)

        # Распределяем бюджет по месяцам
        for i, month in enumerate(months):
            # Берем бюджет для этого месяца (100%)
            month_total_budget = monthly_budgets.get(month, 0)

            if month_total_budget == 0:
                continue

            # Определяем процент для этого месяца
            if i == 0:
                # Первый месяц
                month_percent = first_month_percent
            elif i == len(months) - 1:
                # Последний месяц
                month_percent = last_month_percent
            else:
                # Промежуточные месяцы
                month_percent = middle_months_percent

            # Рассчитываем утвержденный бюджет для месяца
            approved_budget = month_total_budget * month_percent

            # Получаем значения группировки
            group_dict = {}
            if grouping_cols:
                if isinstance(group_key, tuple):
                    group_dict = dict(zip(grouping_cols, group_key))
                elif len(grouping_cols) == 1:
                    group_dict = {grouping_cols[0]: group_key}
                else:
                    # Если group_key не кортеж и колонок несколько, возможно это одна группа
                    for col in grouping_cols:
                        if col in group_df.columns:
                            # Берем первое значение из группы
                            group_dict[col] = (
                                group_df[col].iloc[0] if len(group_df) > 0 else ""
                            )

            # Создаем строку с данными
            approved_row = {
                "month": month,
                "approved budget": approved_budget,
                "budget plan": month_total_budget,  # Плановый бюджет для месяца (100%)
                "rule_name": rule_name,
            }

            # Добавляем значения группировки (исключаем фиктивную колонку _group)
            for col in grouping_cols:
                if col != "_group":
                    approved_row[col] = group_dict.get(col, "")

            approved_budget_rows.append(approved_row)

    # Создаем DataFrame из результатов
    if not approved_budget_rows:
        return pd.DataFrame(), "Нет данных для расчета утвержденного бюджета"

    approved_budget_df = pd.DataFrame(approved_budget_rows)

    return approved_budget_df, None


def dashboard_approved_budget(df):
    """Панель для отображения утвержденного бюджета"""
    st.header("💰 Утвержденный бюджет")

    # Информация о правилах
    with st.expander("ℹ️ Правила распределения бюджета", expanded=False):
        st.markdown(
            """
        **Текущее правило (default):**
        - 50% планового бюджета - на первый месяц этапа
        - 45% планового бюджета - равномерно распределяется между промежуточными месяцами
        - 5% планового бюджета - на последний месяц этапа

        При изменении дат начала и окончания этапа бюджет автоматически пересчитывается.
        """
        )

    # Фильтры
    col1, col2 = st.columns(2)

    with col1:
        if "project name" in df.columns:
            projects = ["Все"] + sorted(df["project name"].dropna().unique().tolist())
            selected_project = st.selectbox(
                "Фильтр по проекту", projects, key="approved_budget_project"
            )
        else:
            selected_project = "Все"

    with col2:
        if "section" in df.columns:
            sections = ["Все"] + sorted(df["section"].dropna().unique().tolist())
            selected_section = st.selectbox(
                "Фильтр по этапу", sections, key="approved_budget_section"
            )
        else:
            selected_section = "Все"

    # Применяем фильтры
    filtered_df = df.copy()
    if selected_project != "Все" and "project name" in filtered_df.columns:
        filtered_df = filtered_df[
            filtered_df["project name"].astype(str).str.strip()
            == str(selected_project).strip()
        ]
    if selected_section != "Все" and "section" in filtered_df.columns:
        filtered_df = filtered_df[
            filtered_df["section"].astype(str).str.strip()
            == str(selected_section).strip()
        ]

    # Рассчитываем утвержденный бюджет
    approved_budget_df, error = calculate_approved_budget(
        filtered_df, rule_name="default"
    )

    if error:
        st.error(error)
        return

    if approved_budget_df.empty:
        st.info("Нет данных для построения графика утвержденного бюджета.")
        return

    # Группируем по месяцам для графика
    monthly_approved = (
        approved_budget_df.groupby("month")
        .agg({"approved budget": "sum", "budget plan": "sum"})  # Для сравнения
        .reset_index()
    )

    # Сортируем по месяцам
    monthly_approved = monthly_approved.sort_values("month")

    # Форматируем месяц для отображения
    def format_month_display(period_val):
        if pd.isna(period_val):
            return "Н/Д"
        try:
            if isinstance(period_val, pd.Period):
                month_num = period_val.month
                year = period_val.year
                RUSSIAN_MONTHS = {
                    1: "Январь",
                    2: "Февраль",
                    3: "Март",
                    4: "Апрель",
                    5: "Май",
                    6: "Июнь",
                    7: "Июль",
                    8: "Август",
                    9: "Сентябрь",
                    10: "Октябрь",
                    11: "Ноябрь",
                    12: "Декабрь",
                }
                return f"{RUSSIAN_MONTHS.get(month_num, 'Н/Д')} {year}"
            return str(period_val)
        except:
            return str(period_val)

    monthly_approved["Месяц"] = monthly_approved["month"].apply(format_month_display)

    # Convert to millions
    monthly_approved["approved budget_millions"] = (monthly_approved["approved budget"] / 1_000_000).round(2)
    monthly_approved["budget plan_millions"] = (monthly_approved["budget plan"] / 1_000_000).round(2)

    # Создаем график
    fig = go.Figure()

    # Добавляем утвержденный бюджет
    fig.add_trace(
        go.Bar(
            x=monthly_approved["Месяц"],
            y=monthly_approved["approved budget_millions"],
            name="Утвержденный бюджет",
            marker_color="#2E86AB",
            text=monthly_approved["approved budget_millions"].apply(
                lambda x: f"{x:.2f}" if pd.notna(x) else ""
            ),
            textposition="outside",
            textfont=dict(size=14, color="white"),
        )
    )

    # Добавляем плановый бюджет для сравнения (линия)
    fig.add_trace(
        go.Scatter(
            x=monthly_approved["Месяц"],
            y=monthly_approved["budget plan_millions"],
            name="Плановый бюджет (сумма)",
            mode="lines+markers",
            line=dict(color="#F18F01", width=2),
            marker=dict(size=8, color="#F18F01"),
        )
    )

    fig.update_layout(
        title="Утвержденный бюджет по месяцам",
        xaxis_title="Месяц",
        yaxis_title="Бюджет, млн руб.",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=600,
    )
    fig = apply_chart_background(fig)
    st.plotly_chart(fig, use_container_width=True)

    # Сводная таблица
    st.subheader("Сводная таблица утвержденного бюджета по месяцам")
    summary_table = monthly_approved[["Месяц", "approved budget_millions", "budget plan_millions"]].copy()
    summary_table.columns = ["Месяц", "Утвержденный бюджет, млн руб.", "Плановый бюджет (сумма), млн руб."]
    html_table = format_dataframe_as_html(summary_table)
    st.markdown(html_table, unsafe_allow_html=True)

    # Детальная таблица (опционально)
    with st.expander("📋 Детальная таблица распределения бюджета", expanded=False):
        detail_table = approved_budget_df[
            [
                "project name",
                "section",
                "task name",
                "month",
                "budget plan",
                "approved budget",
            ]
        ].copy()
        detail_table["month"] = detail_table["month"].apply(format_month_display)
        # Convert to millions
        detail_table["budget plan"] = (detail_table["budget plan"] / 1_000_000).round(2)
        detail_table["approved budget"] = (detail_table["approved budget"] / 1_000_000).round(2)
        detail_table.columns = [
            "Проект",
            "Раздел",
            "Задача",
            "Месяц",
            "Плановый бюджет, млн руб.",
            "Утвержденный бюджет, млн руб.",
        ]
        html_table = format_dataframe_as_html(detail_table)
        st.markdown(html_table, unsafe_allow_html=True)


# ==================== DASHBOARD: Forecast Budget ====================
def calculate_forecast_budget(df, edited_data=None, rule_name="default"):
    """
    Рассчитывает прогнозный бюджет на основе утвержденного бюджета с учетом возможных изменений.

    Args:
        df: DataFrame с исходными данными проектов
        edited_data: DataFrame с отредактированными данными (даты, утвержденный бюджет)
        rule_name: название правила распределения

    Returns:
        DataFrame с распределением прогнозного бюджета по месяцам
    """
    # Используем отредактированные данные, если они есть, иначе исходные
    work_df = edited_data.copy() if edited_data is not None else df.copy()

    # Рассчитываем утвержденный бюджет на основе текущих данных
    approved_budget_df, error = calculate_approved_budget(work_df, rule_name=rule_name)

    if error:
        return pd.DataFrame(), error

    # Прогнозный бюджет = утвержденный бюджет (но может быть изменен пользователем)
    # Если пользователь изменил утвержденный бюджет вручную, используем эти значения
    forecast_budget_df = approved_budget_df.copy()

    # Переименовываем колонку для ясности
    if "approved budget" in forecast_budget_df.columns:
        forecast_budget_df["forecast budget"] = forecast_budget_df["approved budget"]

    return forecast_budget_df, None


def dashboard_forecast_budget(df):
    """Панель для отображения и редактирования прогнозного бюджета"""
    st.header("📈 Прогнозный бюджет")

    # Информация о прогнозном бюджете
    with st.expander("ℹ️ О прогнозном бюджете", expanded=False):
        st.markdown(
            """
        **Прогнозный бюджет** рассчитывается на основе утвержденного бюджета и может быть скорректирован:
        - При изменении плановых дат начала и окончания этапов
        - При изменении утвержденного бюджета по задачам

        Прогнозный бюджет автоматически пересчитывается при любых изменениях.
        """
        )

    # Фильтр по проекту (обязательный для прогнозного бюджета)
    if "project name" not in df.columns:
        st.warning(
            "Колонка 'project name' не найдена. Необходима для работы с прогнозным бюджетом."
        )
        return

    projects = sorted(df["project name"].dropna().unique().tolist())
    if not projects:
        st.warning("Проекты не найдены в данных.")
        return

    selected_project = st.selectbox(
        "Выберите проект", projects, key="forecast_budget_project"
    )

    # Фильтруем данные по выбранному проекту
    project_df = df[
        df["project name"].astype(str).str.strip() == str(selected_project).strip()
    ].copy()

    if project_df.empty:
        st.info("Нет данных для выбранного проекта.")
        return

    # Проверяем наличие необходимых колонок
    required_cols = ["budget plan", "plan start", "plan end", "task name"]
    missing_cols = [col for col in required_cols if col not in project_df.columns]
    if missing_cols:
        st.warning(f"Отсутствуют необходимые колонки: {', '.join(missing_cols)}")
        return

    # Инициализируем session_state для хранения отредактированных данных
    if f"forecast_edited_data_{selected_project}" not in st.session_state:
        st.session_state[f"forecast_edited_data_{selected_project}"] = project_df.copy()

    # Инициализируем session_state для хранения отредактированной таблицы (для отображения)
    if f"forecast_edit_table_{selected_project}" not in st.session_state:
        # Подготавливаем данные для редактирования в первый раз
        current_data = project_df.copy()

        # Проверяем наличие всех необходимых колонок
        required_cols = ["task name", "section", "plan start", "plan end", "budget plan"]
        available_cols = [col for col in required_cols if col in current_data.columns]

        if len(available_cols) < len(required_cols):
            missing = [col for col in required_cols if col not in available_cols]
            st.warning(f"Отсутствуют колонки для редактирования: {', '.join(missing)}")
            return

        edit_df = current_data[required_cols].copy()

        # Конвертируем даты в datetime для корректного отображения
        edit_df["plan start"] = pd.to_datetime(
            edit_df["plan start"], errors="coerce", dayfirst=True
        )
        edit_df["plan end"] = pd.to_datetime(
            edit_df["plan end"], errors="coerce", dayfirst=True
        )

        # Форматируем для отображения - только если дата не NaN
        edit_df["plan start"] = edit_df["plan start"].apply(
            lambda x: x.date() if pd.notna(x) else None
        )
        edit_df["plan end"] = edit_df["plan end"].apply(
            lambda x: x.date() if pd.notna(x) else None
        )

        # Переименовываем колонки для удобства
        edit_df.columns = [
            "Задача",
            "Раздел",
            "План. начало",
            "План. окончание",
            "Плановый бюджет",
        ]

        # Убеждаемся, что бюджет - числовой тип
        edit_df["Плановый бюджет"] = pd.to_numeric(
            edit_df["Плановый бюджет"], errors="coerce"
        )

        st.session_state[f"forecast_edit_table_{selected_project}"] = edit_df.copy()

    # Получаем текущую таблицу для редактирования
    edit_df = st.session_state[f"forecast_edit_table_{selected_project}"].copy()

    # Проверяем, что таблица не пустая
    if edit_df.empty:
        st.warning("⚠️ Таблица для редактирования пуста. Попробуйте выбрать другой проект или проверьте данные.")
        return

    st.subheader("📝 Редактирование данных задач")
    st.info(
        "Измените даты начала/окончания или плановый бюджет. Изменения применяются автоматически при нажатии 'Применить изменения'."
    )

    # Используем HTML таблицу для отображения данных вместо st.data_editor
    # Это позволит избежать проблем с глобальными CSS стилями
    html_table = format_dataframe_as_html(edit_df)
    st.markdown(html_table, unsafe_allow_html=True)

    st.info("💡 Для редактирования данных используйте форму ниже")

    # Форма для редактирования данных
    with st.form("edit_tasks_form", clear_on_submit=False):
        st.subheader("Редактирование данных")

        # Создаем поля для редактирования каждой задачи
        edited_data = []
        for idx, row in edit_df.iterrows():
            with st.expander(f"Задача: {row['Задача']}", expanded=False):
                col1, col2, col3 = st.columns(3)

                with col1:
                    plan_start = st.date_input(
                        "План. начало",
                        value=row['План. начало'] if pd.notna(row['План. начало']) else None,
                        key=f"plan_start_{idx}"
                    )

                with col2:
                    plan_end = st.date_input(
                        "План. окончание",
                        value=row['План. окончание'] if pd.notna(row['План. окончание']) else None,
                        key=f"plan_end_{idx}"
                    )

                with col3:
                    # Преобразуем значение бюджета в float, учитывая возможную запятую как разделитель
                    budget_value = row['Плановый бюджет']
                    if pd.notna(budget_value):
                        # Если это строка, заменяем запятую на точку
                        if isinstance(budget_value, str):
                            budget_value = budget_value.replace(',', '.')
                        try:
                            budget_value = float(budget_value)
                        except (ValueError, TypeError):
                            budget_value = 0.0
                    else:
                        budget_value = 0.0

                    budget = st.number_input(
                        "Плановый бюджет",
                        value=budget_value,
                        step=1000.0,
                        key=f"budget_{idx}"
                    )

                edited_data.append({
                    "Задача": row['Задача'],
                    "Раздел": row['Раздел'],
                    "План. начало": plan_start,
                    "План. окончание": plan_end,
                    "Плановый бюджет": budget
                })

        # Кнопки формы должны быть вне колонок для корректной работы
        submitted = st.form_submit_button("✅ Применить изменения", type="primary", use_container_width=False)
        reset_form = st.form_submit_button("🔄 Сбросить", use_container_width=False)

        if submitted:
            # Обновляем данные
            edited_df = pd.DataFrame(edited_data)
            st.session_state[f"forecast_edit_table_{selected_project}"] = edited_df.copy()
            st.success("✅ Изменения применены!")
            st.rerun()

    # Получаем отредактированные данные для дальнейшей обработки
    edited_df = st.session_state[f"forecast_edit_table_{selected_project}"].copy()

    # Обновляем исходные данные проекта с учетом изменений из формы
    current_data = st.session_state[f"forecast_edited_data_{selected_project}"].copy()
    updated_data = current_data.copy().reset_index(drop=True)
    edited_df_reset = edited_df.reset_index(drop=True)

    # Обновляем даты и бюджет по индексам
    if len(updated_data) == len(edited_df_reset):
        # Обновляем даты - конвертируем из date обратно в datetime
        if "План. начало" in edited_df_reset.columns:
            updated_data["plan start"] = pd.to_datetime(
                edited_df_reset["План. начало"], errors="coerce"
            )
        if "План. окончание" in edited_df_reset.columns:
            updated_data["plan end"] = pd.to_datetime(
                edited_df_reset["План. окончание"], errors="coerce"
            )
        if "Плановый бюджет" in edited_df_reset.columns:
            updated_data["budget plan"] = pd.to_numeric(
                edited_df_reset["Плановый бюджет"], errors="coerce"
            )

        # Сохраняем обновленные данные в session_state
        st.session_state[f"forecast_edited_data_{selected_project}"] = updated_data

    # ВСЕГДА используем актуальные данные из отредактированной таблицы для расчета
    # Это позволяет видеть изменения сразу после применения
    current_data = updated_data

    # Рассчитываем прогнозный бюджет с актуальными данными
    forecast_budget_df, error = calculate_forecast_budget(
        df, edited_data=current_data, rule_name="default"
    )

    if error:
        st.error(error)
        return

    if forecast_budget_df.empty:
        st.info("Нет данных для построения графика прогнозного бюджета.")
        return

    # Группируем по месяцам для графика
    monthly_forecast = (
        forecast_budget_df.groupby("month")
        .agg({"forecast budget": "sum", "budget plan": "sum"})  # Для сравнения
        .reset_index()
    )

    # Сортируем по месяцам
    monthly_forecast = monthly_forecast.sort_values("month")

    # Форматируем месяц для отображения
    def format_month_display(period_val):
        if pd.isna(period_val):
            return "Н/Д"
        try:
            if isinstance(period_val, pd.Period):
                month_num = period_val.month
                year = period_val.year
                RUSSIAN_MONTHS = {
                    1: "Январь",
                    2: "Февраль",
                    3: "Март",
                    4: "Апрель",
                    5: "Май",
                    6: "Июнь",
                    7: "Июль",
                    8: "Август",
                    9: "Сентябрь",
                    10: "Октябрь",
                    11: "Ноябрь",
                    12: "Декабрь",
                }
                return f"{RUSSIAN_MONTHS.get(month_num, 'Н/Д')} {year}"
            return str(period_val)
        except:
            return str(period_val)

    monthly_forecast["Месяц"] = monthly_forecast["month"].apply(format_month_display)

    # Convert to millions
    monthly_forecast["forecast budget_millions"] = (monthly_forecast["forecast budget"] / 1_000_000).round(2)
    monthly_forecast["budget plan_millions"] = (monthly_forecast["budget plan"] / 1_000_000).round(2)

    # Создаем график
    fig = go.Figure()

    # Добавляем прогнозный бюджет
    fig.add_trace(
        go.Bar(
            x=monthly_forecast["Месяц"],
            y=monthly_forecast["forecast budget_millions"],
            name="Прогнозный бюджет",
            marker_color="#06A77D",
            text=monthly_forecast["forecast budget_millions"].apply(
                lambda x: f"{x:.2f}" if pd.notna(x) else ""
            ),
            textposition="outside",
            textfont=dict(size=14, color="white"),
        )
    )

    # Добавляем плановый бюджет для сравнения (линия)
    fig.add_trace(
        go.Scatter(
            x=monthly_forecast["Месяц"],
            y=monthly_forecast["budget plan_millions"],
            name="Плановый бюджет (сумма)",
            mode="lines+markers",
            line=dict(color="#F18F01", width=2),
            marker=dict(size=8, color="#F18F01"),
        )
    )

    fig.update_layout(
        title=f"Прогнозный бюджет по месяцам (Проект: {selected_project})",
        xaxis_title="Месяц",
        yaxis_title="Бюджет, млн руб.",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=600,
    )
    fig = apply_chart_background(fig)
    st.plotly_chart(fig, use_container_width=True)

    # Сводная таблица
    st.subheader("Сводная таблица прогнозного бюджета по месяцам")
    summary_table = monthly_forecast[["Месяц", "forecast budget_millions", "budget plan_millions"]].copy()
    summary_table.columns = ["Месяц", "Прогнозный бюджет, млн руб.", "Плановый бюджет (сумма), млн руб."]
    html_table = format_dataframe_as_html(summary_table)
    st.markdown(html_table, unsafe_allow_html=True)

    # Детальная таблица (опционально)
    with st.expander(
        "📋 Детальная таблица распределения прогнозного бюджета", expanded=False
    ):
        detail_table = forecast_budget_df[
            [
                "project name",
                "section",
                "task name",
                "month",
                "budget plan",
                "forecast budget",
            ]
        ].copy()
        detail_table["month"] = detail_table["month"].apply(format_month_display)
        # Convert to millions
        detail_table["budget plan"] = (detail_table["budget plan"] / 1_000_000).round(2)
        detail_table["forecast budget"] = (detail_table["forecast budget"] / 1_000_000).round(2)
        detail_table.columns = [
            "Проект",
            "Раздел",
            "Задача",
            "Месяц",
            "Плановый бюджет, млн руб.",
            "Прогнозный бюджет, млн руб.",
        ]
        html_table = format_dataframe_as_html(detail_table)
        st.markdown(html_table, unsafe_allow_html=True)


# ==================== MAIN APP ====================
def main():
    # Проверка авторизации - если не авторизован, показываем форму входа
    if not check_authentication():
        # Скрываем боковую панель на странице входа и настраиваем ширину формы
        st.markdown(
            """
            <style>
            /* Фон приложения - новый цвет */
            .stApp {
                background-color: #12385C !important;
            }

            /* Основной контент - белый текст */
            .main .block-container,
            .main .element-container,
            .main h1, .main h2, .main h3, .main h4, .main h5, .main h6,
            .main p, .main span, .main div,
            .main label {
                color: #ffffff !important;
            }

            .stSidebar {
                display: none !important;
            }
            [data-testid="stSidebar"] {
                display: none !important;
            }

            /* Контейнер для формы авторизации - 75% ширины экрана */
            /* Используем более специфичные селекторы для переопределения Streamlit */
            section[data-testid="stAppViewContainer"] .main .block-container,
            section[data-testid="stAppViewContainer"] .main > div,
            .main .block-container,
            .main > div,
            div[data-testid="stAppViewContainer"] .main .block-container,
            div[data-testid="stAppViewContainer"] .main > div,
            [data-testid="stAppViewContainer"] .main .block-container,
            [data-testid="stAppViewContainer"] .main > div {
                max-width: 75% !important;
                width: 75% !important;
                margin-left: auto !important;
                margin-right: auto !important;
                padding-top: 3rem !important;
                padding-bottom: 3rem !important;
            }

            /* Убеждаемся, что основной контейнер занимает всю ширину для центрирования */
            .main,
            section[data-testid="stAppViewContainer"] .main,
            div[data-testid="stAppViewContainer"] .main,
            [data-testid="stAppViewContainer"] .main {
                width: 100% !important;
                max-width: 100% !important;
            }

            /* Переопределяем стандартные ограничения Streamlit */
            section[data-testid="stAppViewContainer"] > div,
            div[data-testid="stAppViewContainer"] > div,
            [data-testid="stAppViewContainer"] > div {
                max-width: 100% !important;
                width: 100% !important;
            }

            /* Переопределяем для layout="wide" */
            .stApp[data-layout="wide"] .main .block-container,
            .stApp[data-layout="wide"] .main > div,
            [data-layout="wide"] .main .block-container,
            [data-layout="wide"] .main > div {
                max-width: 75% !important;
                width: 75% !important;
                margin-left: auto !important;
                margin-right: auto !important;
            }

            /* Дополнительно переопределяем все возможные inline стили */
            .element-container {
                max-width: 100% !important;
                width: 100% !important;
            }

            /* Центрируем форму входа */
            .stForm {
                max-width: 100% !important;
                width: 100% !important;
                margin: 0 auto !important;
            }
            form[data-testid="stForm"] {
                max-width: 100% !important;
                width: 100% !important;
                margin: 0 auto !important;
            }

            /* Убеждаемся, что все элементы формы используют доступную ширину */
            .stForm > div {
                max-width: 100% !important;
                width: 100% !important;
            }

            /* Переопределяем внутренние контейнеры Streamlit */
            [data-testid="stForm"] {
                max-width: 100% !important;
                width: 100% !important;
            }

            [data-testid="stForm"] > div {
                max-width: 100% !important;
                width: 100% !important;
            }

            /* Expander также 50% ширины */
            .stExpander {
                max-width: 100% !important;
                width: 100% !important;
            }

            /* Центрируем колонки формы */
            [data-testid="column"] {
                max-width: 100% !important;
            }

            /* Центрируем заголовок и другой контент */
            h1, h2, h3, p {
                text-align: center !important;
            }

            /* Центрируем markdown блоки */
            .element-container {
                max-width: 100% !important;
            }

            /* Стилизация кнопок - фон цвета основного фона #12385C */
            .stButton > button {
                width: 100% !important;
                min-width: 100% !important;
                max-width: 100% !important;
                min-height: 45px !important;
                height: 45px !important;
                max-height: 45px !important;
                background-color: #12385C !important;
                color: #ffffff !important;
                border: 1px solid rgba(255, 255, 255, 0.3) !important;
                border-radius: 4px !important;
                padding: 0 !important;
                font-weight: 500 !important;
                transition: all 0.2s ease !important;
                box-sizing: border-box !important;
                white-space: nowrap !important;
                overflow: hidden !important;
                text-overflow: ellipsis !important;
                line-height: 1 !important;
                display: flex !important;
                align-items: center !important;
                justify-content: center !important;
            }
            .stButton > button:hover {
                background-color: rgba(18, 56, 92, 0.9) !important;
                border-color: rgba(255, 255, 255, 0.5) !important;
            }
            .stButton > button[kind="primary"] {
                background-color: #12385C !important;
                border: 1px solid #1f77b4 !important;
            }
            .stButton > button[kind="primary"]:hover {
                background-color: rgba(18, 56, 92, 0.9) !important;
                border-color: #2a8bc4 !important;
            }
            .stButton > button[kind="secondary"] {
                background-color: #12385C !important;
                border: 1px solid rgba(255, 255, 255, 0.3) !important;
            }
            .stButton > button[kind="secondary"]:hover {
                background-color: rgba(18, 56, 92, 0.9) !important;
                border-color: rgba(255, 255, 255, 0.5) !important;
            }
            /* Стилизация внутренних элементов кнопки */
            .stButton > button > div,
            .stButton > button > span,
            .stButton > button > p {
                margin: 0 !important;
                padding: 0.5rem 1rem !important;
                line-height: 1 !important;
                white-space: nowrap !important;
                overflow: hidden !important;
                text-overflow: ellipsis !important;
                max-width: 100% !important;
                display: flex !important;
                align-items: center !important;
                justify-content: center !important;
            }
            /* Убеждаемся, что кнопки в колонках имеют одинаковую ширину и высоту */
            [data-testid="column"] .stButton > button {
                width: 100% !important;
                min-width: 100% !important;
                max-width: 100% !important;
                min-height: 45px !important;
                height: 45px !important;
                max-height: 45px !important;
                padding: 0 !important;
                box-sizing: border-box !important;
                white-space: nowrap !important;
                overflow: hidden !important;
                text-overflow: ellipsis !important;
                line-height: 1 !important;
                display: flex !important;
                align-items: center !important;
                justify-content: center !important;
            }
            /* Стилизация внутренних элементов кнопки в колонках */
            [data-testid="column"] .stButton > button > div,
            [data-testid="column"] .stButton > button > span,
            [data-testid="column"] .stButton > button > p {
                margin: 0 !important;
                padding: 0.5rem 1rem !important;
                line-height: 1 !important;
                white-space: nowrap !important;
                overflow: hidden !important;
                text-overflow: ellipsis !important;
                max-width: 100% !important;
                display: flex !important;
                align-items: center !important;
                justify-content: center !important;
            }
            /* Кнопки в формах также должны иметь одинаковую высоту и ширину */
            form .stButton > button {
                min-height: 45px !important;
                height: 45px !important;
                max-height: 45px !important;
                width: 100% !important;
                padding: 0 !important;
                box-sizing: border-box !important;
                white-space: nowrap !important;
                overflow: hidden !important;
                text-overflow: ellipsis !important;
                line-height: 1 !important;
                display: flex !important;
                align-items: center !important;
                justify-content: center !important;
            }
            /* Стилизация внутренних элементов кнопки в формах */
            form .stButton > button > div,
            form .stButton > button > span,
            form .stButton > button > p {
                margin: 0 !important;
                padding: 0.5rem 1rem !important;
                line-height: 1 !important;
                white-space: nowrap !important;
                overflow: hidden !important;
                text-overflow: ellipsis !important;
                max-width: 100% !important;
                display: flex !important;
                align-items: center !important;
                justify-content: center !important;
            }
            /* Дополнительно для кнопок в колонках формы входа */
            form [data-testid="column"] .stButton > button {
                width: 100% !important;
                min-width: 100% !important;
                max-width: 100% !important;
                min-height: 45px !important;
                height: 45px !important;
                max-height: 45px !important;
                padding: 0 !important;
                box-sizing: border-box !important;
                white-space: nowrap !important;
                overflow: hidden !important;
                text-overflow: ellipsis !important;
                line-height: 1 !important;
                display: flex !important;
                align-items: center !important;
                justify-content: center !important;
            }
            /* Стилизация внутренних элементов кнопки в колонках формы входа */
            form [data-testid="column"] .stButton > button > div,
            form [data-testid="column"] .stButton > button > span,
            form [data-testid="column"] .stButton > button > p {
                margin: 0 !important;
                padding: 0.5rem 1rem !important;
                line-height: 1 !important;
                white-space: nowrap !important;
                overflow: hidden !important;
                text-overflow: ellipsis !important;
                max-width: 100% !important;
                display: flex !important;
                align-items: center !important;
                justify-content: center !important;
            }
            </style>
            <script>
            // Принудительно применяем ширину контейнера после загрузки
            function setContainerWidth() {
                const containers = document.querySelectorAll('.main .block-container, .main > div');
                containers.forEach(container => {
                    container.style.setProperty('max-width', '75%', 'important');
                    container.style.setProperty('width', '75%', 'important');
                    container.style.setProperty('margin-left', 'auto', 'important');
                    container.style.setProperty('margin-right', 'auto', 'important');
                });
            }
            // Применяем сразу и после загрузки DOM
            if (document.readyState === 'loading') {
                document.addEventListener('DOMContentLoaded', setContainerWidth);
            } else {
                setContainerWidth();
            }
            // Также применяем после небольшой задержки для Streamlit
            setTimeout(setContainerWidth, 100);
            setTimeout(setContainerWidth, 500);
            setTimeout(setContainerWidth, 1000);
            // Наблюдаем за изменениями DOM (Streamlit динамически обновляет страницу)
            const observer = new MutationObserver(setContainerWidth);
            observer.observe(document.body, { childList: true, subtree: true });
            </script>
        """,
            unsafe_allow_html=True,
        )

        # Заголовок страницы входа
        st.markdown(
            """
            <div style="text-align: center; margin-bottom: 2rem;">
                <h1 style="color: #ffffff; font-size: 3rem; margin-bottom: 0.5rem;">🔐</h1>
                <h1 style="color: #ffffff; font-size: 2rem; margin-bottom: 0.5rem;">BI Analytics</h1>
                <p style="color: #a0a0a0; font-size: 1.1rem;">Войдите в систему для доступа к панели аналитики!!!fff</p>
            </div>
        """,
            unsafe_allow_html=True,
        )

        # Инициализация переменных для восстановления пароля
        if "reset_mode" not in st.session_state:
            st.session_state.reset_mode = False
        if "reset_token" not in st.session_state:
            st.session_state.reset_token = None

        # Режим восстановления пароля по токену
        if st.session_state.reset_mode and st.session_state.reset_token:
            st.subheader("Восстановление пароля")

            token = st.session_state.reset_token
            username = verify_reset_token(token)

            if not username:
                st.error("⚠️ Токен восстановления недействителен или истек")
                st.session_state.reset_mode = False
                st.session_state.reset_token = None
                if st.button("Вернуться к входу"):
                    st.rerun()
                st.stop()

            st.info(f"Восстановление пароля для пользователя: **{username}**")

            new_password = st.text_input(
                "Новый пароль", type="password", key="new_password"
            )
            confirm_password = st.text_input(
                "Подтвердите пароль", type="password", key="confirm_password"
            )

            col1, col2 = st.columns(2)

            with col1:
                if st.button("Сбросить пароль", type="primary"):
                    if not new_password or len(new_password) < 6:
                        st.error("Пароль должен содержать минимум 6 символов")
                    elif new_password != confirm_password:
                        st.error("Пароли не совпадают")
                    else:
                        if reset_password(token, new_password):
                            st.success("✅ Пароль успешно изменен!")
                            st.info("Теперь вы можете войти с новым паролем")
                            st.session_state.reset_mode = False
                            st.session_state.reset_token = None
                            if st.button("Перейти к входу"):
                                st.rerun()
                        else:
                            st.error("Ошибка при сбросе пароля")

            with col2:
                if st.button("Отмена"):
                    st.session_state.reset_mode = False
                    st.session_state.reset_token = None
                    st.rerun()
            st.stop()

        # Режим запроса восстановления пароля
        elif st.session_state.reset_mode:
            st.subheader("Восстановление пароля")

            tab1, tab2 = st.tabs(["По имени пользователя", "По токену"])

            with tab1:
                username = st.text_input(
                    "Введите имя пользователя", key="reset_username"
                )

                col1, col2 = st.columns(2)

                with col1:
                    if st.button("Создать токен восстановления", type="primary"):
                        if username:
                            user = get_user_by_username(username)
                            if user:
                                token = generate_reset_token(username)
                                if token:
                                    st.success("✅ Токен восстановления создан!")
                                    st.info(f"**Токен восстановления:** `{token}`")
                                    st.warning(
                                        "⚠️ В реальном приложении токен будет отправлен на email пользователя"
                                    )
                                    st.info(
                                        "Для демонстрации скопируйте токен и используйте вкладку 'По токену'"
                                    )

                                    st.session_state.reset_token = token
                                    st.rerun()
                                else:
                                    st.error("Ошибка при создании токена")
                            else:
                                st.error("Пользователь не найден")
                        else:
                            st.warning("Введите имя пользователя")

                with col2:
                    if st.button("Отмена"):
                        st.session_state.reset_mode = False
                        st.rerun()

            with tab2:
                token_input = st.text_input(
                    "Введите токен восстановления", key="token_input"
                )

                col1, col2 = st.columns(2)

                with col1:
                    if st.button("Использовать токен", type="primary"):
                        if token_input:
                            username = verify_reset_token(token_input)
                            if username:
                                st.session_state.reset_token = token_input
                                st.rerun()
                            else:
                                st.error("⚠️ Токен недействителен или истек")
                        else:
                            st.warning("Введите токен")

                with col2:
                    if st.button("Отмена", key="cancel_token"):
                        st.session_state.reset_mode = False
                        st.rerun()

            st.markdown("---")
            if st.button("← Вернуться к входу"):
                st.session_state.reset_mode = False
                st.rerun()
            st.stop()

        # Режим входа
        else:
            # Форма входа в центрированном контейнере (50% ширины экрана)
            # Используем пустые колонки для центрирования
            col_left, col_center, col_right = st.columns([1, 1, 1])
            with col_center:
                with st.form("login_form", clear_on_submit=False):
                    st.markdown("### Вход в систему")
                    st.markdown("---")

                    username = st.text_input(
                        "👤 Имя пользователя",
                        key="login_username",
                        placeholder="Введите имя пользователя",
                        autocomplete="username",
                    )

                    password = st.text_input(
                        "🔒 Пароль",
                        type="password",
                        key="login_password",
                        placeholder="Введите пароль",
                        autocomplete="current-password",
                    )

                    col1, col2 = st.columns(2)

                    with col1:
                        submit_button = st.form_submit_button(
                            "🚀 Войти", type="primary", use_container_width=True
                        )

                    with col2:
                        if st.form_submit_button(
                            "❓ Забыли пароль?", use_container_width=True
                        ):
                            st.session_state.reset_mode = True
                            st.rerun()

                    if submit_button:
                        if username and password:
                            success, user = authenticate(username, password)
                            if success and user:
                                st.session_state.authenticated = True
                                st.session_state.user = user
                                st.success(f"✅ Добро пожаловать, {user['username']}!")
                                st.balloons()
                                import time

                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error("❌ Неверное имя пользователя или пароль")
                        else:
                            st.warning("⚠️ Заполните все поля")

                st.markdown("---")

                # Информация о демо-доступе
                with st.expander("ℹ️ Демо-доступ", expanded=False):
                    st.markdown(
                        """
                    **Тестовые учетные данные:**
                    - **Имя пользователя:** `admin`
                    - **Пароль:** `admin123`
                    - **Роль:** Суперадминистратор
                    """
                    )

        st.stop()

    user = get_current_user()

    # Проверка, что пользователь получен
    if not user:
        st.error("⚠️ Ошибка получения данных пользователя")
        st.info("Пожалуйста, войдите в систему заново.")
        if st.button("Перейти к авторизации", type="primary"):
            logout()
            st.rerun()
        st.stop()

    # Проверка прав доступа к отчетам
    if not has_report_access(user["role"]):
        st.error("⚠️ У вас нет доступа к отчетам")
        st.info("Доступ к отчетам имеют менеджеры, аналитики и администраторы.")
        if st.button("Выйти"):
            logout()
            st.rerun()
        st.stop()

    st.markdown(
        '<h1 class="main-header">📊 Панель аналитики проектов</h1>',
        unsafe_allow_html=True,
    )

    # Боковая панель с меню навигации
    render_sidebar_menu(current_page="reports")

    # Загрузка данных - перенесена в основную область
    uploaded_files = st.file_uploader(
        "📁 Загрузите файлы с данными (можно несколько)",
        type=["csv", "xlsx", "xls"],
        accept_multiple_files=True,
        help="Загрузите CSV или Excel файлы с данными проекта, ресурсов или техники",
    )

    # Initialize session state for storing different data types
    if "project_data" not in st.session_state:
        st.session_state.project_data = None
    if "resources_data" not in st.session_state:
        st.session_state.resources_data = None
    if "technique_data" not in st.session_state:
        st.session_state.technique_data = None
    if "loaded_files_info" not in st.session_state:
        st.session_state.loaded_files_info = {}
    if "previous_uploaded_files" not in st.session_state:
        st.session_state.previous_uploaded_files = []

    # Initialize df variable
    df = None

    # Track uploaded files to distinguish between rerun and user removing files
    current_file_names = [f.name for f in uploaded_files] if uploaded_files else []

    # Don't clear data automatically after rerun - keep it for navigation
    # After st.rerun(), uploaded_files will be None/empty, but data in session_state persists
    # This allows navigation in sidebar to work after CSV files are loaded
    # Data will only be cleared if user explicitly removes files through UI
    # (which is handled in the file processing section below)

    if uploaded_files is not None and len(uploaded_files) > 0:
        # Get list of current file names
        current_file_names = [f.name for f in uploaded_files]

        # Remove info for files that are no longer uploaded
        files_to_remove = [
            f
            for f in st.session_state.loaded_files_info.keys()
            if f not in current_file_names
        ]
        for file_name in files_to_remove:
            file_info = st.session_state.loaded_files_info[file_name]
            file_type = file_info["type"]

            # Clear the corresponding data
            if file_type == "project":
                st.session_state.project_data = None
            elif file_type == "resources":
                st.session_state.resources_data = None
            elif file_type == "technique":
                st.session_state.technique_data = None

            del st.session_state.loaded_files_info[file_name]

        # Reset and reload data if files changed
        if files_to_remove:
            # Clear all data and reload from remaining files
            st.session_state.project_data = None
            st.session_state.resources_data = None
            st.session_state.technique_data = None
            st.session_state.loaded_files_info = {}

        # Process each uploaded file
        for uploaded_file in uploaded_files:
            file_id = uploaded_file.name

            # Skip if already processed and file hasn't changed
            if file_id in st.session_state.loaded_files_info:
                # Check if file content might have changed by checking file size
                # For now, we'll reload if files were removed (handled above)
                continue

            df = load_data(uploaded_file, file_id)

            if df is not None:
                data_type = df.attrs.get("data_type", "project")

                # Store data based on type
                if data_type == "project":
                    if st.session_state.project_data is None:
                        st.session_state.project_data = df
                    else:
                        # Concatenate if multiple project files
                        st.session_state.project_data = pd.concat(
                            [st.session_state.project_data, df], ignore_index=True
                        )
                    st.session_state.loaded_files_info[file_id] = {
                        "type": "project",
                        "rows": len(df),
                        "columns": list(df.columns),
                    }
                elif data_type == "resources":
                    if st.session_state.resources_data is None:
                        st.session_state.resources_data = df
                    else:
                        st.session_state.resources_data = pd.concat(
                            [st.session_state.resources_data, df], ignore_index=True
                        )
                    st.session_state.loaded_files_info[file_id] = {
                        "type": "resources",
                        "rows": len(df),
                        "columns": list(df.columns),
                    }
                elif data_type == "technique":
                    if st.session_state.technique_data is None:
                        st.session_state.technique_data = df
                    else:
                        st.session_state.technique_data = pd.concat(
                            [st.session_state.technique_data, df], ignore_index=True
                        )
                    st.session_state.loaded_files_info[file_id] = {
                        "type": "technique",
                        "rows": len(df),
                        "columns": list(df.columns),
                    }

    # Use project data as main df for backward compatibility
    df = st.session_state.project_data

    # Dashboard selection - allow access if any data is loaded (project, resources, or technique)
    has_project_data = df is not None and not df.empty
    resources_data = st.session_state.get("resources_data")
    technique_data = st.session_state.get("technique_data")
    has_resources_data = resources_data is not None and not resources_data.empty
    has_technique_data = technique_data is not None and not technique_data.empty
    has_any_data = has_project_data or has_resources_data or has_technique_data

    if has_any_data:
        # Initialize session state for dashboard selection
        if "current_dashboard" not in st.session_state:
            # Set default dashboard: отклонения от базового плана по срокам
            st.session_state.current_dashboard = (
                "Отклонение текущего срока от базового плана"
            )

        # Check if dashboard was selected from sidebar menu
        dashboard_selected_from_menu = st.session_state.get(
            "dashboard_selected_from_menu", False
        )

        # Get current dashboard from session_state - it persists across reruns
        # This ensures that when filters change, the same dashboard is shown
        current_dashboard = st.session_state.get("current_dashboard", "")

        # If dashboard was selected (from menu or radio buttons), show only the selected dashboard
        # without the selection panels
        if current_dashboard:
            # Display only the selected dashboard
            selected_dashboard = current_dashboard
            # Reset the flag after processing (only if it was set from menu)
            if dashboard_selected_from_menu:
                st.session_state.dashboard_selected_from_menu = False

            # Route to selected dashboard
            try:
                if selected_dashboard == "Причины отклонений по месяцам":
                    dashboard_reasons_of_deviation(df)
                elif selected_dashboard == "Причины отклонений (по видам причин)":
                    dashboard_dynamics_of_deviations(df)
                elif selected_dashboard == "БДДС по месяцам":
                    dashboard_budget_by_period(df)
                elif selected_dashboard == "БДДС по лотам":
                    dashboard_budget_by_section(df)
                elif selected_dashboard == "БДДС накопительно":
                    dashboard_budget_cumulative(df)
                elif selected_dashboard == "Бюджет План/Прогноз/Факт":
                    dashboard_budget_by_type(df)
                elif selected_dashboard == "Утвержденный бюджет":
                    dashboard_approved_budget(df)
                elif selected_dashboard == "Прогнозный бюджет":
                    dashboard_forecast_budget(df)
                elif (
                    selected_dashboard == "Отклонение текущего срока от базового плана"
                ):
                    dashboard_plan_fact_dates(df)
                elif selected_dashboard == "Значения отклонений от базового плана":
                    dashboard_deviation_by_tasks_current_month(df)
                elif selected_dashboard == "Динамика причин отклонений":
                    dashboard_dynamics_of_reasons(df)
                elif selected_dashboard == "Выдача рабочей/проектной документации":
                    dashboard_documentation(df)
                elif selected_dashboard == "Аналитика по технике":
                    dashboard_technique(df)
                elif selected_dashboard == "График движения рабочей силы":
                    dashboard_workforce_movement(df)
                elif selected_dashboard == "СКУД стройка":
                    dashboard_skud_stroyka(df)
                else:
                    st.warning(
                        f"График '{selected_dashboard}' не найден. Пожалуйста, выберите другой график."
                    )
            except Exception as e:
                st.error(
                    f"Ошибка при отображении графика '{selected_dashboard}': {str(e)}"
                )
                st.exception(e)

            # Stop here - don't show selection panels
            st.stop()

        # Выбор панели - перенесен в основную область
        st.markdown("### 📊 Выбор панели")

        # Define all options
        reason_options = [
            "Причины отклонений по месяцам",
            "Причины отклонений (по видам причин)",
            "Динамика причин отклонений",
        ]
        budget_options = [
            "БДДС по месяцам",
            "БДДС по лотам",
            "БДДС накопительно",
            "БДДР по месяцам",
            "БДДР по лотам",
            "Утвержденный бюджет",
            "Прогнозный бюджет",
            "Бюджет План/Прогноз/Факт",
        ]
        plan_fact_options = [
            "Отклонение текущего срока от базового плана",
            "Значения отклонений от базового плана",
            "Причины отклонений по месяцам",
            "Причины отклонений (по видам причин)",
            "Динамика причин отклонений",
        ]
        other_options = [
            "Выдача рабочей/проектной документации",
            "Аналитика по технике",
            "График движения рабочей силы",
            "СКУД стройка",
        ]

        # Determine current selection indices based on current_dashboard
        # Also sync radio button values in session_state when dashboard is selected from menu
        dashboard_selected_from_menu = st.session_state.get(
            "dashboard_selected_from_menu", False
        )

        # Determine indices and sync session_state for radio buttons
        # When dashboard is selected from menu, we need to ensure radio buttons reflect the selection
        current_dashboard = st.session_state.get("current_dashboard", "")

        # If dashboard was selected from menu, sync all radio buttons
        # We need to set the actual option value, not the index, for Streamlit radio buttons
        if dashboard_selected_from_menu and current_dashboard:
            # Set the selected radio button to the correct value (not index)
            if current_dashboard in reason_options:
                st.session_state.reason_radio = current_dashboard
                # Reset other radio buttons to first option value
                if budget_options:
                    st.session_state.budget_radio = budget_options[0]
                if plan_fact_options:
                    st.session_state.plan_fact_radio = plan_fact_options[0]
                if other_options:
                    st.session_state.other_radio = other_options[0]
            elif current_dashboard in budget_options:
                st.session_state.budget_radio = current_dashboard
                # Reset other radio buttons to first option value
                if reason_options:
                    st.session_state.reason_radio = reason_options[0]
                if plan_fact_options:
                    st.session_state.plan_fact_radio = plan_fact_options[0]
                if other_options:
                    st.session_state.other_radio = other_options[0]
            elif current_dashboard in plan_fact_options:
                st.session_state.plan_fact_radio = current_dashboard
                # Reset other radio buttons to first option value
                if reason_options:
                    st.session_state.reason_radio = reason_options[0]
                if budget_options:
                    st.session_state.budget_radio = budget_options[0]
                if other_options:
                    st.session_state.other_radio = other_options[0]
            elif current_dashboard in other_options:
                st.session_state.other_radio = current_dashboard
                # Reset other radio buttons to first option value
                if reason_options:
                    st.session_state.reason_radio = reason_options[0]
                if budget_options:
                    st.session_state.budget_radio = budget_options[0]
                if plan_fact_options:
                    st.session_state.plan_fact_radio = plan_fact_options[0]

        # Determine indices from session_state or current_dashboard
        # Streamlit radio stores the actual option value, not the index
        # So we need to find the index of the value in the options list
        reason_index = 0
        if current_dashboard in reason_options:
            reason_index = reason_options.index(current_dashboard)
        elif "reason_radio" in st.session_state:
            try:
                # session_state contains the actual option value, not index
                if st.session_state.reason_radio in reason_options:
                    reason_index = reason_options.index(st.session_state.reason_radio)
                else:
                    # If value is not in options, use default
                    reason_index = 0
            except (ValueError, TypeError, IndexError):
                reason_index = 0

        budget_index = 0
        if current_dashboard in budget_options:
            budget_index = budget_options.index(current_dashboard)
        elif "budget_radio" in st.session_state:
            try:
                if st.session_state.budget_radio in budget_options:
                    budget_index = budget_options.index(st.session_state.budget_radio)
                else:
                    budget_index = 0
            except (ValueError, TypeError, IndexError):
                budget_index = 0

        plan_fact_index = 0
        if current_dashboard in plan_fact_options:
            plan_fact_index = plan_fact_options.index(current_dashboard)
        elif "plan_fact_radio" in st.session_state:
            try:
                if st.session_state.plan_fact_radio in plan_fact_options:
                    plan_fact_index = plan_fact_options.index(
                        st.session_state.plan_fact_radio
                    )
                else:
                    plan_fact_index = 0
            except (ValueError, TypeError, IndexError):
                plan_fact_index = 0

        other_index = 0
        if current_dashboard in other_options:
            other_index = other_options.index(current_dashboard)
        elif "other_radio" in st.session_state:
            try:
                if st.session_state.other_radio in other_options:
                    other_index = other_options.index(st.session_state.other_radio)
                else:
                    other_index = 0
            except (ValueError, TypeError, IndexError):
                other_index = 0

        # Определяем, какой expander должен быть развернут при выборе из меню
        current_dashboard = st.session_state.get("current_dashboard", "")

        # По умолчанию разворачиваем блок «Отклонения от базового плана»
        expand_plan_fact = True
        expand_budget = False
        expand_other = False

        if dashboard_selected_from_menu and current_dashboard:
            # Если выбор сделан из меню, разворачиваем соответствующий expander
            if current_dashboard in reason_options or current_dashboard in plan_fact_options:
                expand_plan_fact = True
                expand_budget = False
                expand_other = False
            elif current_dashboard in budget_options:
                expand_plan_fact = False
                expand_budget = True
                expand_other = False
            elif current_dashboard in other_options:
                expand_plan_fact = False
                expand_budget = False
                expand_other = True

        # Section 1: Отклонения от базового плана (включая причины отклонений)
        with st.expander(
            "📅 Отклонения от базового плана", expanded=expand_plan_fact
        ):
            st.markdown("**Отклонения от базового плана**")
            plan_fact_dashboard = st.radio(
                "",
                plan_fact_options,
                key="plan_fact_radio",
                label_visibility="collapsed",
                index=plan_fact_index,
            )

            st.markdown("**Причины отклонений**")
            reason_dashboard = st.radio(
                "",
                reason_options,
                key="reason_radio",
                label_visibility="collapsed",
                index=reason_index,
            )

        # Section 2: Аналитика по финансам
        with st.expander("💰 Аналитика по финансам", expanded=expand_budget):
            budget_dashboard = st.radio(
                "",
                budget_options,
                key="budget_radio",
                label_visibility="collapsed",
                index=budget_index,
            )

        # Section 3: Прочее
        with st.expander("🔧 Прочее", expanded=expand_other):
            other_dashboard = st.radio(
                "",
                other_options,
                key="other_radio",
                label_visibility="collapsed",
                index=other_index,
            )

            # Determine selected dashboard based on radio button values
            # Note: Selection from sidebar menu is handled earlier and stops execution with st.stop()
            # So this code only runs when user selects dashboard via radio buttons in main area
            # Always use current radio button values to determine selected dashboard
            # This ensures that clicking on a radio button (even if already selected) works correctly
            if reason_dashboard != st.session_state.get(
                "prev_reason", reason_options[0]
            ):
                selected_dashboard = reason_dashboard
                st.session_state.current_dashboard = reason_dashboard
                st.session_state.prev_reason = reason_dashboard
                # Reset other prev values
                st.session_state.prev_budget = budget_options[0]
                st.session_state.prev_plan_fact = plan_fact_options[0]
                st.session_state.prev_other = other_options[0]
            elif budget_dashboard != st.session_state.get(
                "prev_budget", budget_options[0]
            ):
                selected_dashboard = budget_dashboard
                st.session_state.current_dashboard = budget_dashboard
                st.session_state.prev_budget = budget_dashboard
                # Reset other prev values
                st.session_state.prev_reason = reason_options[0]
                st.session_state.prev_plan_fact = plan_fact_options[0]
                st.session_state.prev_other = other_options[0]
            elif plan_fact_dashboard != st.session_state.get(
                "prev_plan_fact", plan_fact_options[0]
            ):
                selected_dashboard = plan_fact_dashboard
                st.session_state.current_dashboard = plan_fact_dashboard
                st.session_state.prev_plan_fact = plan_fact_dashboard
                # Reset other prev values
                st.session_state.prev_reason = reason_options[0]
                st.session_state.prev_budget = budget_options[0]
                st.session_state.prev_other = other_options[0]
            elif other_dashboard != st.session_state.get(
                "prev_other", other_options[0]
            ):
                selected_dashboard = other_dashboard
                st.session_state.current_dashboard = other_dashboard
                st.session_state.prev_other = other_dashboard
                # Reset other prev values
                st.session_state.prev_reason = reason_options[0]
                st.session_state.prev_budget = budget_options[0]
                st.session_state.prev_plan_fact = plan_fact_options[0]
            else:
                # If no radio button change detected, determine from current radio values
                # This handles the case when user clicks on already selected radio button
                if reason_dashboard in reason_options:
                    selected_dashboard = reason_dashboard
                elif budget_dashboard in budget_options:
                    selected_dashboard = budget_dashboard
                elif plan_fact_dashboard in plan_fact_options:
                    selected_dashboard = plan_fact_dashboard
                elif other_dashboard in other_options:
                    selected_dashboard = other_dashboard
                else:
                    # Fallback to current_dashboard
                    selected_dashboard = st.session_state.current_dashboard

                # Update current_dashboard to match selected
                st.session_state.current_dashboard = selected_dashboard

        # Route to selected dashboard
        try:
            if selected_dashboard == "Причины отклонений по месяцам":
                dashboard_reasons_of_deviation(df)
            elif selected_dashboard == "Причины отклонений (по видам причин)":
                dashboard_dynamics_of_deviations(df)
            elif selected_dashboard == "БДДС по месяцам":
                dashboard_budget_by_period(df)
            elif selected_dashboard == "БДДС по лотам":
                dashboard_budget_by_section(df)
            elif selected_dashboard == "БДДС накопительно":
                dashboard_budget_cumulative(df)
            elif selected_dashboard == "БДДР по месяцам":
                dashboard_bddr_by_period(df)
            elif selected_dashboard == "БДДР по лотам":
                dashboard_bddr_by_section(df)
            elif selected_dashboard == "Бюджет План/Прогноз/Факт":
                dashboard_budget_by_type(df)
            elif selected_dashboard == "Утвержденный бюджет":
                dashboard_approved_budget(df)
            elif selected_dashboard == "Прогнозный бюджет":
                dashboard_forecast_budget(df)
            elif selected_dashboard == "Отклонение текущего срока от базового плана":
                dashboard_plan_fact_dates(df)
            elif selected_dashboard == "Значения отклонений от базового плана":
                dashboard_deviation_by_tasks_current_month(df)
            elif selected_dashboard == "Динамика причин отклонений":
                dashboard_dynamics_of_reasons(df)
            elif selected_dashboard == "Выдача рабочей/проектной документации":
                dashboard_documentation(df)
            elif selected_dashboard == "Аналитика по технике":
                dashboard_technique(df)
            elif selected_dashboard == "График движения рабочей силы":
                dashboard_workforce_movement(df)
            elif selected_dashboard == "СКУД стройка":
                dashboard_skud_stroyka(df)
            else:
                st.warning(
                    f"График '{selected_dashboard}' не найден. Пожалуйста, выберите другой график."
                )
                st.info(f"Текущий выбор: {selected_dashboard}")
        except Exception as e:
            st.error(f"Ошибка при отображении графика '{selected_dashboard}': {str(e)}")
            st.exception(e)
    else:
        # Welcome message
        st.info(
            """
        👋 **Добро пожаловать в Панель аналитики проектов!**

        Эта панель предоставляет комплексную аналитику для управления проектами:

        **Доступные панели:**

        **🔍 Причины отклонений:**
        - **Причины отклонений по месяцам** - Анализ причин отклонений с фильтрами по месяцу, проекту и причине
        - **Причины отклонений (по видам причин)** - Отслеживание трендов отклонений по месяцам, кварталам или годам

        **💰 Аналитика по финансам:**
        - **БДДС по месяцам** - Анализ выполнения бюджета по периодам (накопительно или за месяц)
        - **БДДС по лотам** - Анализ выполнения бюджета по разделам и периодам
        - **БДДР по месяцам** - (заглушка) будущий отчет по доходам и расходам в разрезе месяцев
        - **БДДР по лотам** - (заглушка) будущий отчет по доходам и расходам в разрезе лотов/разделов
        - **Бюджет План/Прогноз/Факт** - Сравнение типов бюджета (План, Прогноз, Факт, Резерв) по периодам с учетом выбора типа бюджета (БДДС/БДДР)
        - **Утвержденный бюджет** - Распределение утвержденного бюджета по месяцам на основе правил
        - **Прогнозный бюджет** - Прогнозный бюджет с возможностью редактирования дат и бюджета задач

        **📅 Отклонения от базового плана:**
        - **Отклонение текущего срока от базового плана** - Сравнение запланированных и фактических дат с диаграммами Ганта
        - **Значения отклонений от базового плана** - Просмотр отклонений по задачам и проектам за все периоды
        - **Причины отклонений по месяцам** - Анализ причин отклонений с фильтрами по месяцу, проекту и причине
        - **Причины отклонений (по видам причин)** - Отслеживание трендов отклонений по месяцам, кварталам или годам
        - **Динамика причин отклонений** - Аналитика распределения и динамики причин отклонений

        **🔧 Прочее:**
        - **Выдача рабочей/проектной документации** - Анализ выдачи рабочей и проектной документации, включая просрочку выдачи РД

        **Для начала работы:**
        1. Загрузите файл с данными (CSV или Excel) через боковую панель
        2. Выберите панель из меню боковой панели
        3. Используйте фильтры для фокусировки на конкретных данных
        """
        )


if __name__ == "__main__":
    main()
