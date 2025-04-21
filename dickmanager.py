import ast
import random

from typing import Optional, Dict
from datetime import datetime, timedelta
from database import DataBase

class DickManager:
    CONFIG = {
        "delay": timedelta(hours=24, minutes=0, seconds=0),
        "time": {"h": 24, "m": 0, "s": 0},
        "max": 10,
        "min": -5,
        "date_format": "%Y-%m-%d %H:%M:%S",
        "messages": {
            "yes": (
                "{username}, твой писюн {state} на {add_size} см.\n"
                "Теперь он равен {size} см.\n"
                "Ты занимаешь {top} место в топе.\n"
                "Следующая попытка через — {h}ч. {m}м. {s}с."
            ),
            "no": (
                "{username}, ты уже играл.\n"
                "Твой писюн равен {size} см.\n"
                "Ты занимаешь {top} место в топе.\n"
                "Следующая попытка через — {h}ч. {m}м. {s}с."
            )
        }
    }

    def __init__(self, database: DataBase):
        self.db = database
        self.data = None


    async def get_data(self, table: str, user_id: int) -> Optional[Dict]:
        data = await self.db.get(
            table = table,
            where = {"id": user_id}
        )
        return data
    
    
    async def add_group(self, groups: list, user_id: int, chat_id: int):
        if chat_id in groups: return
        groups.append(chat_id)
        await self.db.update(
            table   = "users",
            data    = {"groups": str(groups)},
            where   = {"id": user_id}
        )


    async def get_time_next_play(self, last_played) -> Dict[str, int]:
        now = datetime.now()
        delta = now - last_played
        delay = self.CONFIG["delay"]
        
        remaining = delay - delta
        if remaining.total_seconds() <= 0:
            return {"h": 0, "m": 0, "s": 0}

        total_seconds = int(remaining.total_seconds())
        h, rem = divmod(total_seconds, 3600)
        m, s = divmod(rem, 60)
        
        return {"h": h, "m": m, "s": s}
    

    async def get_top(self, table: str) -> str:
        TOP_HEADER = "Топ 10 игроков\n\n"
        
        data = await self.db.find(
            table=table,
            add_query="ORDER BY size DESC LIMIT 10"
        )
        if not data:
            return "Список топ игроков пуст."
        
        lines = [
            f"{n}) [{user['username']}]({user['url']}) — {user['size']} см."
            for n, user in enumerate(data, start=1)
        ]
        
        return TOP_HEADER + "\n".join(lines)


    async def get_n_top(self, user_id: int, chat_id: int) -> int:
        data = await self.db.find(
            table = f"group_{chat_id}",
            add_query = "ORDER BY size DESC"
        )
        if not data:
            return 0
        for index, user in enumerate(data, start=1):
            if user["id"] == user_id:
                return index
            

    async def get_global_top(self) -> str:
        return await self.get_top("users")

    async def get_chat_top(self, chat_id) -> str:
        return await self.get_top(f"group_{chat_id}")
    
    
    async def dick(self, user_id, username, chat_id) -> str:
        self.data = {
            "users": await self.get_data("users", user_id),
            "group": await self.get_data(f"group_{chat_id}", user_id)
        }

        last_played =  datetime.strptime(self.data["group"]["last_played"], self.CONFIG["date_format"])
        format_data = {"username": username, "size": self.data["group"]["size"], "top": await self.get_n_top(user_id, chat_id)}
        groups = ast.literal_eval(self.data["users"]["groups"])

        await self.add_group(groups, user_id, chat_id)

        if (datetime.now() - last_played) > self.CONFIG["delay"]:
            while (random_size := random.randint(self.CONFIG["min"], self.CONFIG["max"])) == 0:
                continue
            
            new_size = self.data["group"]["size"] + random_size
            if new_size < 0: new_size = 0

            self.data["group"]["size"] = new_size
            self.data["group"]["last_played"] = datetime.strftime(datetime.now(), self.CONFIG["date_format"])

            await self.db.update(
                table   = f"group_{chat_id}",
                data    = self.data["group"],
                where   = {"id": user_id}
            )
            
            format_data["state"]    = "вырос"       if random_size > 0 else "сократился"
            format_data["size"]     = new_size
            format_data["add_size"] = random_size   if random_size > 0 else abs(random_size)
            format_data["top"]      = await self.get_n_top(user_id, chat_id)

            dick_sizes = []
            for chat_id in groups:
                data = await self.db.get(f"group_{chat_id}", {"id": user_id})
                if (value := data["size"]) != None:
                    dick_sizes.append(value)
            
            await self.db.update(
                table   = "users",
                data    = {"size": max(dick_sizes)},
                where   = {"id": user_id}
            )

            return self.CONFIG["messages"]["yes"].format(
                **format_data,
                **self.CONFIG["time"]
            )
        
        else:
            return self.CONFIG["messages"]["no"].format(
                **format_data,
                **await self.get_time_next_play(last_played)
            )
            
