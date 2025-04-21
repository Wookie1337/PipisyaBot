from database import DataBase
from dickmanager import DickManager

from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

from typing import Tuple


API_TOKEN = 'YOUR_BOT_API_TOKEN'


async def ensure_user_in_db(db: DataBase, table: str, user_id: int, first_name: str, username: str, url: str) -> None:
    await db.insert(table=table, data={"id": user_id, "firstname": first_name, "username": username, "url": url})

async def setup_group_table(db: DataBase, table: str, chat_id: int) -> None:
    await db.create_table(
        table   = f"group_{chat_id}",
        schema  = {
            "id":           "INTEGER    PRIMARY KEY",
            "firstname":    "TEXT       DEFAULT 'None'",
            "username":     "TEXT       DEFAULT 'None'",
            "url":          "TEXT       DEFAULT 'None'",
            "size":         "INTEGER    DEFAULT 0",
            "last_played":  "TEXT       DEFAULT '2000-01-01 00:00:00'"
        }
    )

async def init_func(db: DataBase, message: Message) -> Tuple[int, str, int, str, bool]:
    #? Инициализация стандартных переменных
    user_id     = message.from_user.id
    first_name  = message.from_user.first_name
    username    = message.from_user.username
    url         = message.from_user.url
    chat_id     = abs(message.chat.id)
    chat_type   = message.chat.type
    in_group    = False

    #? Добавление пользователя в базу данных
    await ensure_user_in_db(db, "users", user_id, first_name, username, url)

    #? Проверка на то, что бот в группе
    if chat_type in ["group", "supergroup"]:
        #? Инициализация таблицы для группы
        await setup_group_table(db, f"group_{chat_id}", chat_id)

        #? Установка id пользователя использовавшего команду
        await ensure_user_in_db(db, f"group_{chat_id}", user_id, first_name, username, url)

        in_group = True

    return (user_id, first_name, chat_id, chat_type, in_group)

async def main() -> None:
    bot = Bot(token=API_TOKEN)
    dp  = Dispatcher()

    keyboards = {
        "add_bot": InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Добавить бота в группу", url="http://t.me/testxdxdxdxdxdx_bot?startgroup=Lichka")]
            ]
        )
    }

    async with DataBase("test.db") as db:
        #? Инициализация таблицы для всех пользователей
        await db.create_table(
            table   = "users",
            schema  = {
                "id":           "INTEGER    PRIMARY KEY",
                "firstname":    "TEXT       DEFAULT 'None'",
                "username":     "TEXT       DEFAULT 'None'",
                "url":          "TEXT       DEFAULT 'None'",
                "size":         "INTEGER    DEFAULT 0",
                "groups":       "TEXT       DEFAULT '[]'"
            }
        )

        dick_mgr = DickManager(db)

        #? Обработка команды /start
        @dp.message(Command("start"))
        async def start_handler(message: Message):
            try:
                #? Инициализация стандартных настроек
                user_id, first_name, chat_id, chat_type, in_group = await init_func(db, message)

                await message.answer(f"""
                    \rПривет! я линейка — бот для чатов (групп) \

                    \nСмысл бота: бот работает только в чатах. Раз в 24 часа игрок может прописать команду /dick, где в ответ получит от бота рандомное число. \
                    \nРандом работает от -5 см до +10 см. \

                    \nЕсли у тебя есть вопросы — пиши команду: /help"""
                )

            except Exception as e:
                print(f"Ошибка в start_handler: {e}")
                await message.answer("Произошла ошибка. Пожалуйста, попробуйте позже!")


        #? Обработка команды /dick
        @dp.message(Command("dick"))
        async def dick_handler(message: Message):
            #? Инициализация стандартных настроек
            user_id, first_name, chat_id, chat_type, in_group = await init_func(db, message)
            username    = message.from_user.username
            url         = message.from_user.url

            if in_group:
                ret_msg = await dick_mgr.dick(user_id, f"[{username}]({url})", chat_id)
                await message.answer(ret_msg, parse_mode="Markdown")
            else:
                await message.answer(f"Я работаю только в чатах (группах)", reply_markup=keyboards["add_bot"])

        
        @dp.message(Command("global_top"))
        async def global_top_handler(message: Message):
            #? Инициализация стандартных настроек
            user_id, first_name, chat_id, chat_type, in_group = await init_func(db, message)

            if in_group:
                await message.answer(f"Данная команда доступна только в личке с ботом❗️")
            else:
                ret_msg = await dick_mgr.get_global_top()
                await message.answer(ret_msg, parse_mode="Markdown")

        
        @dp.message(Command("chat_top"))
        async def chat_top_handler(message: Message):
            #? Инициализация стандартных настроек
            user_id, first_name, chat_id, chat_type, in_group = await init_func(db, message)

            if in_group:
                ret_msg = await dick_mgr.get_chat_top(chat_id)
                await message.answer(ret_msg, parse_mode="Markdown")
            else:
                await message.answer(f"Я работаю только в чатах (группах)", reply_markup=keyboards["add_bot"])


        @dp.message(Command("help"))
        async def help_handler(message: Message):
            await message.answer("""
                  \rКоманды бота:\
                  \n/dick — Вырастить/уменьшить пипису\
                  \n/chat_top — Топ 10 пипис чата\
                  \n/global_top — Глобальный топ 10 игроков\

                  \nКонтакты:\
                  \nСоздатель — @wookie1337""")

        #? Начало работы бота
        updates = await bot.get_updates()
        if updates:
            last_update_id = updates[-1].update_id
            await bot.get_updates(offset=last_update_id + 1)
        await dp.start_polling(bot, drop_pending_updates=True)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
