"""
Административная панель
"""

import sys
import os

# Добавляем родительскую директорию в путь для импорта
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd
from datetime import datetime
import sqlite3

from auth import (
    check_authentication,
    get_current_user,
    has_admin_access,
    require_auth,
    get_user_role_display,
    ROLES,
    init_db,
    DB_PATH,
    render_sidebar_menu,
)
from logger import log_action, get_logs, get_logs_count
from settings import get_setting, set_setting, get_all_settings, SETTING_KEYS
from project_visualization_app import format_dataframe_as_html
from permissions import (
    grant_project_access,
    revoke_project_access,
    get_user_projects,
    get_project_users,
    get_all_project_permissions,
    has_project_access,
    get_all_projects,
)

try:
    from filters import (
        get_default_filters,
        set_default_filter,
        delete_default_filter,
        get_all_default_filters,
        copy_filters_to_role,
        AVAILABLE_REPORTS,
        FILTER_TYPES,
    )
except ImportError as e:
    # Определяем заглушки для избежания ошибок
    AVAILABLE_REPORTS = []
    FILTER_TYPES = {}

    def get_default_filters(*args, **kwargs):
        return {}

    def set_default_filter(*args, **kwargs):
        return False

    def delete_default_filter(*args, **kwargs):
        return False

    def get_all_default_filters(*args, **kwargs):
        return []

    def copy_filters_to_role(*args, **kwargs):
        return False

    # Логируем ошибку, но не используем st, так как он может быть не инициализирован
    import warnings

    warnings.warn(f"Ошибка импорта модуля filters: {e}")

# Инициализация базы данных
init_db()


# Проверка, что мы в контексте Streamlit
def is_streamlit_context():
    """Проверка, что код выполняется в контексте Streamlit"""
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx

        return get_script_run_ctx() is not None
    except:
        return False


# Выполняем код только в контексте Streamlit
if is_streamlit_context():
    # Настройка страницы
    st.set_page_config(
        page_title="Настройки - BI Analytics",
        page_icon="⚙️",
        layout="wide",
        menu_items={"Get Help": None, "Report a bug": None, "About": None},
    )

    # Custom CSS для фона страницы
    st.markdown(
        """
        <style>
        /* Фон приложения - основной цвет */
        .stApp {
            background-color: #12385C !important;
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
        .stDataFrame,
        div[data-testid="stDataFrame"],
        .dataframe,
        .stDataFrame *,
        div[data-testid="stDataFrame"] *,
        .dataframe * {
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
        .stDataFrame td *,
        .stDataFrame th *,
        div[data-testid="stDataFrame"] td *,
        div[data-testid="stDataFrame"] th *,
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
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Проверка авторизации
    require_auth()

    user = get_current_user()

    # Проверка, что пользователь получен
    if not user:
        st.error("⚠️ Ошибка получения данных пользователя")
        st.stop()

    # Проверка прав доступа
    if not has_admin_access(user["role"]):
        st.error("⚠️ У вас нет доступа к административной панели")
        st.info(
            "Доступ к настройкам имеют только администраторы и суперадминистраторы."
        )
        if st.button("Вернуться к отчетам"):
            st.switch_page("project_visualization_app.py")
        st.stop()
    # Если пользователь прошел проверку, продолжаем выполнение
else:
    # Если не в контексте Streamlit, создаем заглушку для user
    user = None

# Весь остальной код выполняется только если user определен (т.е. в контексте Streamlit)
if user is not None:
    # Боковая панель с меню навигации
    render_sidebar_menu(current_page="admin")

    # Заголовок
    st.title("⚙️ Административная панель")
    st.markdown("---")

    # Информация о текущем пользователе
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Пользователь", user["username"])
    with col2:
        st.metric("Роль", get_user_role_display(user["role"]))
    with col3:
        if st.button("🚪 Выйти"):
            from auth import logout

            log_action(user["username"], "logout", "Выход из системы")
            logout()
            st.success("Вы вышли из системы")
            st.rerun()

    st.markdown("---")

    # JavaScript для автоматического скролла к содержимому выбранной вкладки
    st.markdown(
        """
        <script>
        (function() {
            function scrollToActiveTabContent() {
                setTimeout(function() {
                    // Находим активную панель вкладки (содержимое, не заголовок)
                    const activePanel = document.querySelector('[role="tabpanel"][aria-hidden="false"]');
                    if (!activePanel) return;
                    
                    // Находим первый значимый элемент контента внутри панели
                    // Пропускаем заголовки вкладок и ищем реальное содержимое
                    const contentElements = activePanel.querySelectorAll('div[data-testid="stVerticalBlock"] > div, h1, h2, h3, .stSubheader');
                    let targetElement = null;
                    
                    // Ищем первый элемент, который не является частью заголовка вкладки
                    for (let i = 0; i < contentElements.length; i++) {
                        const elem = contentElements[i];
                        // Проверяем, что элемент не находится в заголовке вкладки
                        if (!elem.closest('[data-baseweb="tab-list"]') && 
                            !elem.closest('[data-baseweb="tab"]')) {
                            targetElement = elem;
                            break;
                        }
                    }
                    
                    // Если не нашли, используем саму панель, но с отступом
                    if (!targetElement) {
                        targetElement = activePanel;
                    }
                    
                    // Вычисляем позицию с учетом отступа от верха
                    const elementPosition = targetElement.getBoundingClientRect().top;
                    const offsetPosition = elementPosition + window.pageYOffset - 100; // 100px отступ от верха
                    
                    // Плавный скролл
                    window.scrollTo({
                        top: offsetPosition,
                        behavior: 'smooth'
                    });
                }, 200);
            }
            
            // Выполняем скролл при загрузке
            if (document.readyState === 'loading') {
                document.addEventListener('DOMContentLoaded', scrollToActiveTabContent);
            } else {
                scrollToActiveTabContent();
            }
            
            // Отслеживаем клики по вкладкам
            document.addEventListener('click', function(e) {
                if (e.target.closest('[data-baseweb="tab"]')) {
                    scrollToActiveTabContent();
                }
            });
            
            // Отслеживаем изменения активной вкладки через MutationObserver
            const observer = new MutationObserver(function(mutations) {
                mutations.forEach(function(mutation) {
                    if (mutation.type === 'attributes') {
                        // Проверяем изменения aria-selected или aria-hidden
                        if ((mutation.attributeName === 'aria-selected' && 
                             mutation.target.getAttribute('aria-selected') === 'true') ||
                            (mutation.attributeName === 'aria-hidden' && 
                             mutation.target.getAttribute('aria-hidden') === 'false' &&
                             mutation.target.getAttribute('role') === 'tabpanel')) {
                            scrollToActiveTabContent();
                        }
                    }
                });
            });
            
            // Наблюдаем за вкладками и панелями
            setTimeout(function() {
                const tabs = document.querySelectorAll('[data-baseweb="tab"]');
                const panels = document.querySelectorAll('[role="tabpanel"]');
                
                tabs.forEach(tab => {
                    observer.observe(tab, { 
                        attributes: true, 
                        attributeFilter: ['aria-selected'] 
                    });
                });
                
                panels.forEach(panel => {
                    observer.observe(panel, { 
                        attributes: true, 
                        attributeFilter: ['aria-hidden'] 
                    });
                });
            }, 500);
        })();
        </script>
    """,
        unsafe_allow_html=True,
    )

    # Вкладки административной панели
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(
        [
            "👥 Управление пользователями",
            "📊 Статистика",
            "🔧 Настройки системы",
            "📝 Логи действий",
            "🔄 Обновление отчетов",
            "🔐 Права доступа к проектам",
            "🔍 Фильтры по умолчанию",
        ]
    )

    # ==================== TAB 1: Управление пользователями ====================
    with tab1:
        st.subheader("Управление пользователями")

        # Список пользователей
        st.markdown("### Список пользователей")

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT id, username, role, email, created_at, last_login, is_active
            FROM users
            ORDER BY created_at DESC
        """
        )

        users = cursor.fetchall()
        conn.close()

        if users:
            # Таблица пользователей
            users_data = []
            for u in users:
                users_data.append(
                    {
                        "ID": u[0],
                        "Имя пользователя": u[1],
                        "Роль": get_user_role_display(u[2]),
                        "Email": u[3] or "-",
                        "Создан": u[4] if u[4] else "-",
                        "Последний вход": u[5] if u[5] else "Никогда",
                        "Активен": "✅" if u[6] else "❌",
                    }
                )

            df_users = pd.DataFrame(users_data)
            html_table = format_dataframe_as_html(df_users)
            st.markdown(html_table, unsafe_allow_html=True)
        else:
            st.info("Пользователи не найдены")

        st.markdown("---")

        # Добавление нового пользователя
        st.markdown("### Добавить нового пользователя")

        with st.form("add_user_form"):
            col1, col2 = st.columns(2)

            with col1:
                new_username = st.text_input("Имя пользователя *")
                new_email = st.text_input("Email")

            with col2:
                new_password = st.text_input("Пароль *", type="password")
                new_role = st.selectbox(
                    "Роль *", options=list(ROLES.keys()), format_func=lambda x: ROLES[x]
                )

            submitted = st.form_submit_button("Добавить пользователя", type="primary")

            if submitted:
                if new_username and new_password:
                    from auth import create_user

                    if create_user(
                        new_username,
                        new_password,
                        new_role,
                        new_email if new_email else None,
                        user["username"],
                    ):
                        st.success(f"✅ Пользователь {new_username} успешно создан!")
                        st.rerun()
                    else:
                        st.error(
                            "❌ Ошибка при создании пользователя. Возможно, пользователь с таким именем уже существует."
                        )
                else:
                    st.warning("Заполните обязательные поля (отмечены *)")

        st.markdown("---")

        # Изменение роли пользователя
        st.markdown("### Изменить роль пользователя")

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, username, role FROM users WHERE is_active = 1 ORDER BY username"
        )
        active_users = cursor.fetchall()
        conn.close()

        if active_users:
            with st.form("change_role_form"):
                user_options = {
                    f"{u[1]} ({get_user_role_display(u[2])})": u[0]
                    for u in active_users
                }
                selected_user_display = st.selectbox(
                    "Выберите пользователя", options=list(user_options.keys())
                )
                selected_user_id = user_options[selected_user_display]

                # Получаем текущую роль
                selected_username = selected_user_display.split(" (")[0]
                current_role = None
                for u in active_users:
                    if u[0] == selected_user_id:
                        current_role = u[2]
                        break

                new_role = st.selectbox(
                    "Новая роль *",
                    options=list(ROLES.keys()),
                    format_func=lambda x: ROLES[x],
                    index=list(ROLES.keys()).index(current_role) if current_role else 0,
                )

                submitted = st.form_submit_button("Изменить роль", type="primary")

                if submitted:
                    if new_role != current_role:
                        conn = sqlite3.connect(DB_PATH)
                        cursor = conn.cursor()
                        cursor.execute(
                            "UPDATE users SET role = ? WHERE id = ?",
                            (new_role, selected_user_id),
                        )
                        conn.commit()
                        conn.close()

                        log_action(
                            user["username"],
                            "change_role",
                            f"Изменена роль пользователя {selected_username} с {get_user_role_display(current_role)} на {get_user_role_display(new_role)}",
                        )
                        st.success(
                            f"✅ Роль пользователя {selected_username} успешно изменена на {get_user_role_display(new_role)}!"
                        )
                        st.rerun()
                    else:
                        st.warning("Выберите другую роль")
        else:
            st.info("Нет активных пользователей")

    # ==================== TAB 2: Статистика ====================
    with tab2:
        st.subheader("Статистика системы")

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Общая статистика
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM users WHERE is_active = 1")
        active_users = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM users WHERE last_login IS NOT NULL")
        users_with_login = cursor.fetchone()[0]

        # Статистика по ролям
        cursor.execute(
            """
            SELECT role, COUNT(*) as count
            FROM users
            GROUP BY role
        """
        )
        role_stats = cursor.fetchall()

        # Статистика логов
        total_logs = get_logs_count()
        recent_logs = get_logs_count(action="login")

        conn.close()

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Всего пользователей", total_users)
        with col2:
            st.metric("Активных пользователей", active_users)
        with col3:
            st.metric("Пользователей с входом", users_with_login)
        with col4:
            st.metric("Всего действий в логах", total_logs)

        st.markdown("---")

        # Статистика по ролям
        st.markdown("### Распределение по ролям")
        if role_stats:
            role_data = [
                {"Роль": get_user_role_display(r[0]), "Количество": r[1]}
                for r in role_stats
            ]
            df_roles = pd.DataFrame(role_data)
            html_table = format_dataframe_as_html(df_roles)
            st.markdown(html_table, unsafe_allow_html=True)
        else:
            st.info("Нет данных")

    # ==================== TAB 3: Настройки системы ====================
    with tab3:
        st.subheader("Настройки путей к файлам данных")

        st.info(
            """
        Здесь можно настроить пути к файлам, которые служат источником данных для отчетов:
        - **Финансы**: файлы с финансовыми данными
        - **План-факт**: файлы с данными план-факт анализа
        - **Ресурсы**: файлы с данными по ресурсам
        """
        )

        st.markdown("---")

        # Получаем текущие настройки
        settings = get_all_settings()

        # Форма для настройки путей
        with st.form("settings_form"):
            st.markdown("### Настройка путей к файлам")

            finance_path = st.text_input(
                "Путь к файлам финансовых данных",
                value=settings.get("finance_files_path", {}).get("value", ""),
                help="Укажите путь к директории или файлу с финансовыми данными",
            )

            plan_fact_path = st.text_input(
                "Путь к файлам план-факт данных",
                value=settings.get("plan_fact_files_path", {}).get("value", ""),
                help="Укажите путь к директории или файлу с данными план-факт",
            )

            resources_path = st.text_input(
                "Путь к файлам данных по ресурсам",
                value=settings.get("resources_files_path", {}).get("value", ""),
                help="Укажите путь к директории или файлу с данными по ресурсам",
            )

            submitted = st.form_submit_button("Сохранить настройки", type="primary")

            if submitted:
                try:
                    set_setting(
                        "finance_files_path",
                        finance_path,
                        SETTING_KEYS.get("finance_files_path"),
                        user["username"],
                    )
                    set_setting(
                        "plan_fact_files_path",
                        plan_fact_path,
                        SETTING_KEYS.get("plan_fact_files_path"),
                        user["username"],
                    )
                    set_setting(
                        "resources_files_path",
                        resources_path,
                        SETTING_KEYS.get("resources_files_path"),
                        user["username"],
                    )

                    log_action(
                        user["username"],
                        "update_settings",
                        "Обновлены настройки путей к файлам",
                    )
                    st.success("✅ Настройки успешно сохранены!")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Ошибка при сохранении настроек: {str(e)}")

        st.markdown("---")

        # Текущие настройки
        st.markdown("### Текущие настройки")
        if settings:
            settings_data = []
            for key, value in settings.items():
                settings_data.append(
                    {
                        "Настройка": SETTING_KEYS.get(key, key),
                        "Значение": value.get("value", ""),
                        "Обновлено": value.get("updated_at", ""),
                        "Обновил": value.get("updated_by", ""),
                    }
                )
            df_settings = pd.DataFrame(settings_data)
            st.dataframe(df_settings, use_container_width=True, hide_index=True)
        else:
            st.info("Настройки еще не заданы")

    # ==================== TAB 4: Логи действий ====================
    with tab4:
        st.subheader("Логи действий пользователей")

        # Фильтры
        col1, col2, col3 = st.columns(3)

        with col1:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT DISTINCT username FROM user_activity_logs ORDER BY username"
            )
            usernames = [row[0] for row in cursor.fetchall()]
            conn.close()

            filter_username = st.selectbox(
                "Фильтр по пользователю", options=["Все"] + usernames
            )

        with col2:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT DISTINCT action FROM user_activity_logs ORDER BY action"
            )
            actions = [row[0] for row in cursor.fetchall()]
            conn.close()

            filter_action = st.selectbox(
                "Фильтр по действию", options=["Все"] + actions
            )

        with col3:
            log_limit = st.number_input(
                "Количество записей", min_value=10, max_value=1000, value=100, step=10
            )

        # Применение фильтров
        username_filter = None if filter_username == "Все" else filter_username
        action_filter = None if filter_action == "Все" else filter_action

        # Получение логов
        logs = get_logs(limit=log_limit, username=username_filter, action=action_filter)

        if logs:
            logs_data = []
            for log in logs:
                logs_data.append(
                    {
                        "ID": log["id"],
                        "Пользователь": log["username"],
                        "Действие": log["action"],
                        "Детали": log["details"] or "-",
                        "IP адрес": log["ip_address"] or "-",
                        "Время": log["created_at"] if log["created_at"] else "-",
                    }
                )

            df_logs = pd.DataFrame(logs_data)
            html_table = format_dataframe_as_html(df_logs)
            st.markdown(html_table, unsafe_allow_html=True)

            # Экспорт логов
            csv = df_logs.to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                label="📥 Скачать логи (CSV)",
                data=csv,
                file_name=f"logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
            )
        else:
            st.info("Логи не найдены")

    # ==================== TAB 5: Обновление отчетов ====================
    with tab5:
        st.subheader("Принудительное обновление отчетов")

        st.info(
            """
        Здесь можно принудительно обновить отчеты, загрузив данные из настроенных источников.
        """
        )

        st.markdown("---")

        # Информация о последнем обновлении
        last_update = st.session_state.get("last_report_update", None)
        if last_update:
            st.info(f"Последнее обновление: {last_update}")
        else:
            st.warning("Отчеты еще не обновлялись")

        st.markdown("---")

        # Кнопка обновления
        col1, col2, col3 = st.columns([1, 1, 2])

        with col1:
            if st.button(
                "🔄 Обновить отчеты", type="primary", use_container_width=True
            ):
                try:
                    # Здесь должна быть логика обновления отчетов
                    # Для демонстрации просто обновляем время
                    st.session_state["last_report_update"] = datetime.now().strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )

                    log_action(
                        user["username"],
                        "force_update_reports",
                        "Принудительное обновление отчетов",
                    )
                    st.success("✅ Отчеты успешно обновлены!")
                    st.rerun()
                except Exception as e:
                    log_action(
                        user["username"],
                        "force_update_reports_error",
                        f"Ошибка обновления отчетов: {str(e)}",
                    )
                    st.error(f"❌ Ошибка при обновлении отчетов: {str(e)}")

        with col2:
            if st.button("🔄 Очистить кэш", use_container_width=True):
                try:
                    # Очистка кэша данных
                    if "project_data" in st.session_state:
                        del st.session_state["project_data"]
                    if "resources_data" in st.session_state:
                        del st.session_state["resources_data"]
                    if "loaded_files_info" in st.session_state:
                        del st.session_state["loaded_files_info"]

                    log_action(user["username"], "clear_cache", "Очистка кэша данных")
                    st.success("✅ Кэш очищен!")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Ошибка при очистке кэша: {str(e)}")

        st.markdown("---")

        # Информация о настройках путей
        st.markdown("### Используемые пути к файлам")
        settings = get_all_settings()
        if settings:
            for key, value in settings.items():
                path_value = value.get("value", "Не задано")
                st.text(f"{SETTING_KEYS.get(key, key)}: {path_value}")
        else:
            st.warning(
                "⚠️ Настройки путей к файлам не заданы. Перейдите во вкладку 'Настройки системы' для настройки."
            )

    # ==================== TAB 6: Права доступа к проектам ====================
    with tab6:
        st.subheader("Управление правами доступа к проектам")

        st.info(
            """
        Здесь можно управлять правами доступа пользователей к определенным проектам в отчетах.
        """
        )

        st.markdown("---")

        # Выдача прав доступа
        st.markdown("### Выдать права доступа к проекту")

        with st.form("grant_permission_form"):
            col1, col2 = st.columns(2)

            with col1:
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT id, username FROM users WHERE is_active = 1 ORDER BY username"
                )
                active_users_list = cursor.fetchall()
                conn.close()

                user_options = {f"{u[1]}": u[0] for u in active_users_list}
                selected_user_display = st.selectbox(
                    "Выберите пользователя", options=list(user_options.keys())
                )
                selected_user_id = user_options[selected_user_display]

            with col2:
                project_name = st.text_input(
                    "Название проекта *", help="Введите название проекта"
                )

            submitted = st.form_submit_button("Выдать права", type="primary")

            if submitted:
                if project_name:
                    if grant_project_access(
                        selected_user_id, project_name, user["username"]
                    ):
                        log_action(
                            user["username"],
                            "grant_project_access",
                            f"Выданы права доступа пользователю {selected_user_display} к проекту {project_name}",
                        )
                        st.success(
                            f"✅ Пользователю {selected_user_display} выданы права доступа к проекту {project_name}!"
                        )
                        st.rerun()
                    else:
                        st.warning(
                            "⚠️ Права доступа уже существуют или произошла ошибка"
                        )
                else:
                    st.warning("Введите название проекта")

        st.markdown("---")

        # Список прав доступа
        st.markdown("### Текущие права доступа к проектам")

        permissions = get_all_project_permissions()

        if permissions:
            # Группировка по проектам
            projects_dict = {}
            for perm in permissions:
                project = perm["project_name"]
                if project not in projects_dict:
                    projects_dict[project] = []
                projects_dict[project].append(perm)

            # Отображение по проектам
            for project_name, project_perms in sorted(projects_dict.items()):
                with st.expander(
                    f"📁 {project_name} ({len(project_perms)} пользователей)"
                ):
                    perms_data = []
                    for perm in project_perms:
                        perms_data.append(
                            {
                                "Пользователь": perm["username"],
                                "Роль": get_user_role_display(perm["role"]),
                                "Выдано": (
                                    perm["granted_at"] if perm["granted_at"] else "-"
                                ),
                                "Выдал": perm["granted_by"] or "-",
                                "Действие": f"revoke_{perm['user_id']}_{project_name}",
                            }
                        )

                    df_perms = pd.DataFrame(perms_data)
                    st.dataframe(
                        df_perms[["Пользователь", "Роль", "Выдано", "Выдал"]],
                        use_container_width=True,
                        hide_index=True,
                    )

                    # Кнопки отзыва прав
                    for perm in project_perms:
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            st.text(f"Пользователь: {perm['username']}")
                        with col2:
                            if st.button("Отозвать", key=f"revoke_{perm['id']}"):
                                if revoke_project_access(perm["user_id"], project_name):
                                    log_action(
                                        user["username"],
                                        "revoke_project_access",
                                        f'Отозваны права доступа пользователя {perm["username"]} к проекту {project_name}',
                                    )
                                    st.success(
                                        f"✅ Права доступа пользователя {perm['username']} к проекту {project_name} отозваны!"
                                    )
                                    st.rerun()
        else:
            st.info("Права доступа к проектам не выданы")

    # ==================== TAB 7: Фильтры по умолчанию ====================
    with tab7:
        st.subheader("Управление фильтрами по умолчанию")

        st.info(
            """
        Здесь можно настроить фильтры по умолчанию для каждой роли и каждого отчета.
        Фильтры можно настроить отдельно для каждого отчета или скопировать для группы отчетов.
        """
        )

        st.markdown("---")

        # Выбор режима работы
        mode = st.radio(
            "Режим работы",
            [
                "Настроить фильтры для роли и отчета",
                "Просмотр всех фильтров",
                "Копирование фильтров между ролями",
            ],
            horizontal=True,
        )

        st.markdown("---")

        if mode == "Настроить фильтры для роли и отчета":
            st.markdown("### Настройка фильтров")

            with st.form("filter_form"):
                col1, col2 = st.columns(2)

                with col1:
                    selected_role = st.selectbox(
                        "Роль *",
                        options=list(ROLES.keys()),
                        format_func=lambda x: ROLES[x],
                    )

                    selected_report = st.selectbox("Отчет *", options=AVAILABLE_REPORTS)

                with col2:
                    filter_key = st.text_input(
                        "Ключ фильтра *",
                        help="Например: selected_project, date_range, etc.",
                    )
                    filter_type = st.selectbox(
                        "Тип фильтра *",
                        options=list(FILTER_TYPES.keys()),
                        format_func=lambda x: FILTER_TYPES[x],
                    )

                filter_value = st.text_input(
                    "Значение фильтра",
                    help='Введите значение фильтра. Для select/multiselect используйте JSON формат: ["значение1", "значение2"]',
                )

                submitted = st.form_submit_button("Сохранить фильтр", type="primary")

                if submitted:
                    if filter_key and selected_role and selected_report:
                        if set_default_filter(
                            selected_role,
                            selected_report,
                            filter_key,
                            filter_value,
                            filter_type,
                            user["username"],
                        ):
                            log_action(
                                user["username"],
                                "set_default_filter",
                                f"Установлен фильтр {filter_key} для роли {get_user_role_display(selected_role)} в отчете {selected_report}",
                            )
                            st.success("✅ Фильтр успешно сохранен!")
                            st.rerun()
                        else:
                            st.error("❌ Ошибка при сохранении фильтра")
                    else:
                        st.warning("Заполните обязательные поля (отмечены *)")

            st.markdown("---")

            # Текущие фильтры для выбранной роли и отчета
            st.markdown("### Текущие фильтры")

            col1, col2 = st.columns(2)
            with col1:
                view_role = st.selectbox(
                    "Роль для просмотра",
                    options=["Все"] + list(ROLES.keys()),
                    format_func=lambda x: ROLES.get(x, x) if x != "Все" else x,
                    key="view_filter_role",
                )
            with col2:
                view_report = st.selectbox(
                    "Отчет для просмотра",
                    options=["Все"] + AVAILABLE_REPORTS,
                    key="view_filter_report",
                )

            filters = get_all_default_filters(
                role=None if view_role == "Все" else view_role,
                report_name=None if view_report == "Все" else view_report,
            )

            if filters:
                filters_data = []
                for f in filters:
                    filters_data.append(
                        {
                            "Роль": get_user_role_display(f["role"]),
                            "Отчет": f["report_name"],
                            "Ключ": f["filter_key"],
                            "Значение": f["filter_value"] or "-",
                            "Тип": FILTER_TYPES.get(f["filter_type"], f["filter_type"]),
                            "Обновлено": f["updated_at"] or "-",
                            "Обновил": f["updated_by"] or "-",
                        }
                    )

                df_filters = pd.DataFrame(filters_data)
                st.dataframe(df_filters, use_container_width=True, hide_index=True)

                # Удаление фильтров
                st.markdown("#### Удаление фильтра")
                with st.form("delete_filter_form"):
                    del_col1, del_col2, del_col3 = st.columns(3)
                    with del_col1:
                        del_role = st.selectbox(
                            "Роль",
                            options=list(ROLES.keys()),
                            format_func=lambda x: ROLES[x],
                            key="del_filter_role",
                        )
                    with del_col2:
                        del_report = st.selectbox(
                            "Отчет", options=AVAILABLE_REPORTS, key="del_filter_report"
                        )
                    with del_col3:
                        # Получаем фильтры для выбранной роли и отчета
                        role_filters = get_default_filters(del_role, del_report)
                        del_filter_key = st.selectbox(
                            "Ключ фильтра",
                            options=list(role_filters.keys()) if role_filters else [],
                            key="del_filter_key",
                        )

                    if st.form_submit_button("Удалить фильтр", type="primary"):
                        if del_filter_key:
                            if delete_default_filter(
                                del_role, del_report, del_filter_key
                            ):
                                log_action(
                                    user["username"],
                                    "delete_default_filter",
                                    f"Удален фильтр {del_filter_key} для роли {get_user_role_display(del_role)} в отчете {del_report}",
                                )
                                st.success("✅ Фильтр успешно удален!")
                                st.rerun()
                            else:
                                st.error("❌ Ошибка при удалении фильтра")
            else:
                st.info("Фильтры не найдены")

        elif mode == "Просмотр всех фильтров":
            st.markdown("### Все фильтры по умолчанию")

            all_filters = get_all_default_filters()

            if all_filters:
                # Группировка по ролям и отчетам
                filters_by_role_report = {}
                for f in all_filters:
                    key = (f["role"], f["report_name"])
                    if key not in filters_by_role_report:
                        filters_by_role_report[key] = []
                    filters_by_role_report[key].append(f)

                for (role, report), filters_list in sorted(
                    filters_by_role_report.items()
                ):
                    with st.expander(
                        f"📋 {get_user_role_display(role)} - {report} ({len(filters_list)} фильтров)"
                    ):
                        filters_data = []
                        for f in filters_list:
                            filters_data.append(
                                {
                                    "Ключ": f["filter_key"],
                                    "Значение": f["filter_value"] or "-",
                                    "Тип": FILTER_TYPES.get(
                                        f["filter_type"], f["filter_type"]
                                    ),
                                    "Обновлено": f["updated_at"] or "-",
                                    "Обновил": f["updated_by"] or "-",
                                }
                            )
                        df = pd.DataFrame(filters_data)
                        st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.info("Фильтры не настроены")

        elif mode == "Копирование фильтров между ролями":
            st.markdown("### Копирование фильтров")

            st.info(
                "Скопируйте все фильтры из одной роли в другую. Можно скопировать для конкретного отчета или для всех отчетов."
            )

            with st.form("copy_filters_form"):
                col1, col2 = st.columns(2)

                with col1:
                    source_role = st.selectbox(
                        "Исходная роль",
                        options=list(ROLES.keys()),
                        format_func=lambda x: ROLES[x],
                        key="copy_source_role",
                    )

                with col2:
                    target_role = st.selectbox(
                        "Целевая роль",
                        options=list(ROLES.keys()),
                        format_func=lambda x: ROLES[x],
                        key="copy_target_role",
                    )

                copy_report = st.selectbox(
                    "Отчет (оставьте 'Все' для копирования всех отчетов)",
                    options=["Все"] + AVAILABLE_REPORTS,
                    key="copy_report",
                )

                if st.form_submit_button("Копировать фильтры", type="primary"):
                    if source_role == target_role:
                        st.warning(
                            "⚠️ Исходная и целевая роли не могут быть одинаковыми"
                        )
                    else:
                        report_name = None if copy_report == "Все" else copy_report
                        if copy_filters_to_role(source_role, target_role, report_name):
                            log_action(
                                user["username"],
                                "copy_filters",
                                f"Скопированы фильтры из роли {get_user_role_display(source_role)} в роль {get_user_role_display(target_role)}"
                                + (
                                    f" для отчета {copy_report}"
                                    if report_name
                                    else " для всех отчетов"
                                ),
                            )
                            st.success(f"✅ Фильтры успешно скопированы!")
                            st.rerun()
                        else:
                            st.error("❌ Ошибка при копировании фильтров")
