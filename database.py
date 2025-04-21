import aiosqlite
from typing import Optional, List, Dict

class DataBase:
    """
    Асинхронный класс для работы с базой данных SQLite.
    
    Предоставляет удобный интерфейс для выполнения CRUD-операций,
    создания таблиц и управления транзакциями.
    
    Использование:
        async with DataBase("example.db") as db:
            await db.create_table("users", {"id": "INTEGER PRIMARY KEY", "name": "TEXT"})
            await db.insert("users", {"name": "Alice"})
            users = await db.find("users", {"name": "Alice"})
            print(users)
    """

    def __init__(self, db_name: str):
        self.db_name = db_name
        self.db = None

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, *args):
        await self.close()

    async def connect(self):
        self.db = await aiosqlite.connect(self.db_name)
        self.db.row_factory = aiosqlite.Row

    async def close(self):
        if self.db:
            await self.db.close()

    async def query(self, sql: str, params: tuple = ()) -> List[Dict]:
        """
        Выполняет SELECT-запрос и возвращает результат в виде списка словарей.
        
        :param sql: SQL-запрос (например, "SELECT * FROM users").
        :param params: Параметры запроса (например, (1,) для WHERE id = ?).
        :return: Список словарей с результатами запроса.
        """
        async with self.db.execute(sql, params) as cursor:
            return [dict(row) for row in await cursor.fetchall()]

    async def execute(self, sql: str, params: tuple = ()) -> None:
        """
        Выполняет запрос с изменением данных (INSERT, UPDATE, DELETE).
        Автоматически фиксирует изменения.
        
        :param sql: SQL-запрос (например, "DELETE FROM users WHERE id = ?").
        :param params: Параметры запроса (например, (1,) для WHERE id = ?).
        """
        await self.db.execute(sql, params)
        await self.db.commit()

    async def create_table(self, table: str, schema: dict) -> None:
        """
        Создаёт таблицу на основе переданной схемы.
        
        :param table: Имя таблицы (например, "users").
        :param schema: Словарь, где ключи — названия столбцов, значения — типы данных.
        """
        columns = [f"{name} {dtype}" for name, dtype in schema.items()]
        await self.execute(f"CREATE TABLE IF NOT EXISTS {table} ({', '.join(columns)})")

    async def insert(self, table: str, data: dict) -> None:
        """
        Вставляет запись в таблицу.
        
        :param table: Имя таблицы (например, "users").
        :param data: Словарь, где ключи — названия столбцов, значения — данные для вставки.
        """
        try:
            columns = ", ".join(data.keys())
            placeholders = ", ".join("?" * len(data))
            cursor = await self.db.execute(
                f"INSERT INTO {table} ({columns}) VALUES ({placeholders})",
                tuple(data.values())
            )
            await self.db.commit()
        except aiosqlite.IntegrityError:
            return

    async def get(self, table: str, where: Optional[Dict] = None) -> Optional[Dict]:
        """
        Получает одну запись из таблицы по условию.
        
        :param table: Имя таблицы (например, "users").
        :param where: Словарь условий (например, {"id": 1} для WHERE id = 1).
        :return: Словарь с данными записи или None, если запись не найдена.
        """
        conditions, params = self._prepare_conditions(where)
        query = f"SELECT * FROM {table} {conditions}"
        results = await self.query(query, params)
        return results[0] if results else None

    async def find(self, table: str, where: Optional[Dict] = None, add_query: str = '') -> List[Dict]:
        """
        Ищет все записи в таблице по условию.
        
        :param table: Имя таблицы (например, "users").
        :param where: Словарь условий (например, {"age": 30} для WHERE age = 30).
        :return: Список словарей с найденными записями.
        """
        conditions, params = self._prepare_conditions(where)
        query = f"SELECT * FROM {table} {conditions} {add_query}"
        return await self.query(query, params)

    async def update(self, table: str, data: dict, where: Optional[Dict] = None) -> None:
        """
        Обновляет записи в таблице.
        
        :param table: Имя таблицы (например, "users").
        :param data: Словарь с новыми данными (например, {"age": 31}).
        :param where: Словарь условий (например, {"id": 1} для WHERE id = 1).
        """
        set_clause = ", ".join([f"{k} = ?" for k in data.keys()])
        where_clause, where_params = self._prepare_conditions(where)
        params = tuple(data.values()) + where_params
        await self.execute(f"UPDATE {table} SET {set_clause} {where_clause}", params)

    async def delete(self, table: str, where: Optional[Dict] = None) -> None:
        """
        Удаляет записи из таблицы по условию.
        
        :param table: Имя таблицы (например, "users").
        :param where: Словарь условий (например, {"id": 1} для WHERE id = 1).
        """
        conditions, params = self._prepare_conditions(where)
        await self.execute(f"DELETE FROM {table} {conditions}", params)

    @staticmethod
    def _prepare_conditions(conditions: Optional[Dict]) -> tuple[str, tuple]:
        if not conditions:
            return "", ()
        clauses = [f"{k} = ?" for k in conditions.keys()]
        return f"WHERE {' AND '.join(clauses)}", tuple(conditions.values())
