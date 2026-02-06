"""
Модуль для логирования действий пользователей
"""
import sqlite3
from datetime import datetime
from typing import Optional, List, Dict
from auth import DB_PATH, init_db

# Инициализация таблицы логов
def init_log_table():
    """Инициализация таблицы логов действий пользователей"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_activity_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            action TEXT NOT NULL,
            details TEXT,
            ip_address TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

# Инициализируем таблицу при импорте модуля
init_db()
init_log_table()


def log_action(username: str, action: str, details: Optional[str] = None, ip_address: Optional[str] = None):
    """
    Логирование действия пользователя
    
    Args:
        username: Имя пользователя
        action: Тип действия (например, 'login', 'logout', 'change_role')
        details: Дополнительные детали действия
        ip_address: IP-адрес пользователя
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO user_activity_logs (username, action, details, ip_address, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (username, action, details, ip_address, datetime.now().isoformat()))
        conn.commit()
        conn.close()
    except Exception as e:
        # Логируем ошибку, но не прерываем выполнение
        print(f"Ошибка при логировании действия: {e}")


def get_logs(limit: int = 100, username: Optional[str] = None, action: Optional[str] = None) -> List[Dict]:
    """
    Получение логов действий пользователей
    
    Args:
        limit: Максимальное количество записей
        username: Фильтр по имени пользователя
        action: Фильтр по типу действия
    
    Returns:
        Список словарей с логами
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        query = "SELECT id, username, action, details, ip_address, created_at FROM user_activity_logs WHERE 1=1"
        params = []
        
        if username:
            query += " AND username = ?"
            params.append(username)
        
        if action:
            query += " AND action = ?"
            params.append(action)
        
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        # Преобразуем в список словарей
        logs = []
        for row in rows:
            logs.append({
                'id': row[0],
                'username': row[1],
                'action': row[2],
                'details': row[3],
                'ip_address': row[4],
                'created_at': row[5]
            })
        
        return logs
    except Exception as e:
        print(f"Ошибка при получении логов: {e}")
        return []


def get_logs_count(username: Optional[str] = None, action: Optional[str] = None) -> int:
    """
    Получение количества логов
    
    Args:
        username: Фильтр по имени пользователя
        action: Фильтр по типу действия
    
    Returns:
        Количество записей
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        query = "SELECT COUNT(*) FROM user_activity_logs WHERE 1=1"
        params = []
        
        if username:
            query += " AND username = ?"
            params.append(username)
        
        if action:
            query += " AND action = ?"
            params.append(action)
        
        cursor.execute(query, params)
        count = cursor.fetchone()[0]
        conn.close()
        
        return count
    except Exception as e:
        print(f"Ошибка при подсчете логов: {e}")
        return 0

