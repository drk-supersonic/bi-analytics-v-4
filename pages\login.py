"""
Страница авторизации
"""

import sys
import os

# Добавляем родительскую директорию в путь для импорта
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from auth import (
    authenticate,
    generate_reset_token,
    reset_password,
    verify_reset_token,
    init_db,
    get_user_by_username,
)

# Инициализация базы данных
init_db()

# Настройка страницы
st.set_page_config(
    page_title="Авторизация - BI Analytics",
    page_icon="🔐",
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items={"Get Help": None, "Report a bug": None, "About": None},
)

# Стили для темной темы
st.markdown(
    """
    <style>
    /* Фон приложения - новый цвет */
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
    
    /* Основной контент - белый текст */
    .main .block-container,
    .main .element-container,
    .main h1, .main h2, .main h3, .main h4, .main h5, .main h6,
    .main p, .main span, .main div,
    .main label {
        color: #ffffff !important;
    }
    
    /* Скрываем боковую панель на странице входа */
    .stSidebar {
        display: none !important;
    }
    [data-testid="stSidebar"] {
        display: none !important;
    }
    /* Скрываем стандартную навигацию */
    [data-testid="stSidebarNav"] {
        display: none !important;
    }
    
    /* Контейнер для формы авторизации - делаем еще шире */
    .main .block-container {
        max-width: 1500px !important;
        width: 100% !important;
        padding-top: 3rem !important;
        padding-bottom: 3rem !important;
    }
    
    /* Переопределяем все возможные ограничения ширины */
    .main > div {
        max-width: 1500px !important;
        width: 100% !important;
    }
    
    /* Контейнер для формы входа - расширяем */
    form[data-testid="stForm"] {
        max-width: 1500px !important;
        width: 100% !important;
        margin: 0 auto !important;
    }
    
    /* Убеждаемся, что все элементы формы используют доступную ширину */
    .stForm {
        max-width: 1500px !important;
        width: 100% !important;
    }
    
    .stForm > div {
        max-width: 1500px !important;
        width: 100% !important;
    }
    
    /* Переопределяем внутренние контейнеры Streamlit */
    [data-testid="stForm"] {
        max-width: 1500px !important;
        width: 100% !important;
    }
    
    [data-testid="stForm"] > div {
        max-width: 1500px !important;
        width: 100% !important;
    }
    
    
    /* Стилизация полей ввода - подсветка для видимости на темном фоне */
    .stTextInput > div > div > input,
    .stTextInput > div > div > input:focus,
    input[type="text"],
    input[type="password"],
    input[type="email"] {
        background-color: #2a2a3a !important;
        color: #ffffff !important;
        border: 1px solid #4a5568 !important;
        border-radius: 4px !important;
        padding: 0.5rem !important;
    }
    .stTextInput > div > div > input:focus,
    input[type="text"]:focus,
    input[type="password"]:focus,
    input[type="email"]:focus {
        border-color: #1f77b4 !important;
        box-shadow: 0 0 0 2px rgba(31, 119, 180, 0.2) !important;
        outline: none !important;
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
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        box-sizing: border-box !important;
        white-space: nowrap !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
        line-height: 1 !important;
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
    /* Кнопки primary - фон цвета основного фона */
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
    /* Кнопки secondary - фон цвета основного фона */
    .stButton > button[kind="secondary"] {
        background-color: #12385C !important;
        color: #ffffff !important;
        border: 1px solid rgba(255, 255, 255, 0.3) !important;
    }
    .stButton > button[kind="secondary"]:hover {
        background-color: rgba(18, 56, 92, 0.9) !important;
        border-color: rgba(255, 255, 255, 0.5) !important;
        color: #ffffff !important;
    }
    </style>
""",
    unsafe_allow_html=True,
)

# Если уже авторизован, перенаправляем
if st.session_state.get("authenticated", False):
    st.success("Вы уже авторизованы!")
    if st.button("Перейти к панели"):
        st.switch_page("project_visualization_app.py")
    st.stop()

# Определяем режим: вход или восстановление пароля
if "reset_mode" not in st.session_state:
    st.session_state.reset_mode = False
if "reset_token" not in st.session_state:
    st.session_state.reset_token = None

# Заголовок страницы (всегда показывается)
st.markdown(
    """
    <div style="text-align: center; margin-bottom: 2rem;">
        <h1 style="color: #ffffff; font-size: 3rem; margin-bottom: 0.5rem;">🔐</h1>
        <h1 style="color: #ffffff; font-size: 2rem; margin-bottom: 0.5rem;">BI Analytics</h1>
        <p style="color: #a0a0a0; font-size: 1.1rem;">Войдите в систему для доступа к панели аналитики</p>
    </div>
""",
    unsafe_allow_html=True,
)

# Форма без контейнера

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

    new_password = st.text_input("Новый пароль", type="password", key="new_password")
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

# Режим запроса восстановления пароля
elif st.session_state.reset_mode:
    st.subheader("Восстановление пароля")

    tab1, tab2 = st.tabs(["По имени пользователя", "По токену"])

    with tab1:
        username = st.text_input("Введите имя пользователя", key="reset_username")

        col1, col2 = st.columns(2)

        with col1:
            if st.button("Создать токен восстановления", type="primary"):
                if username:
                    user = get_user_by_username(username)
                    if user:
                        token = generate_reset_token(username)
                        if token:
                            # В реальном приложении здесь должна быть отправка email
                            # Для демонстрации показываем токен
                            st.success("✅ Токен восстановления создан!")
                            st.info(f"**Токен восстановления:** `{token}`")
                            st.warning(
                                "⚠️ В реальном приложении токен будет отправлен на email пользователя"
                            )
                            st.info(
                                "Для демонстрации скопируйте токен и используйте вкладку 'По токену'"
                            )

                            # Сохраняем токен в сессии для перехода к следующему шагу
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
        token_input = st.text_input("Введите токен восстановления", key="token_input")

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

# Режим входа
else:
    # Форма входа
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
            if st.form_submit_button("❓ Забыли пароль?", use_container_width=True):
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
                    st.switch_page("project_visualization_app.py")
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
