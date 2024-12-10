import os
import asyncio
import traceback
from binascii import (
    Error
)
from pyrogram import (
    Client,
    enums,
    filters
)
from pyrogram.errors import (
    UserNotParticipant,
    FloodWait,
    QueryIdInvalid
)
from pyrogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
    Message
)
from configs import Config
from handlers.database import db
from handlers.add_user_to_db import add_user_to_database
from handlers.send_file import send_media_and_reply
from handlers.helpers import b64_to_str, str_to_b64
from handlers.check_user_status import handle_user_status
from handlers.force_sub_handler import (
    handle_force_sub,
    get_invite_link
)
from handlers.broadcast_handlers import main_broadcast_handler
from handlers.save_media import (get_short)

MediaList = {}

Bot = Client(
    name=Config.BOT_USERNAME,
    in_memory=True,
    bot_token=Config.BOT_TOKEN,
    api_id=Config.API_ID,
    api_hash=Config.API_HASH
)


@Bot.on_message(filters.private)
async def _(bot: Client, cmd: Message):
    await handle_user_status(bot, cmd)


@Bot.on_message(filters.command("start") & filters.private)
async def start(bot: Client, cmd: Message):

    if cmd.from_user.id in Config.BANNED_USERS:
        await cmd.reply_text("Sorry, You are banned.")
        return
    if Config.UPDATES_CHANNEL is not None:
        back = await handle_force_sub(bot, cmd)
        if back == 400:
            return

    usr_cmd = cmd.text.split("_", 1)[-1]
    if usr_cmd == "/start":
        await add_user_to_database(bot, cmd)
        await cmd.reply_text(
            Config.HOME_TEXT.format(cmd.from_user.first_name, cmd.from_user.id),
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton("·ᴜᴘᴅᴀᴛᴇꜱ ᴄʜᴀɴɴᴇʟ·", url="https://t.me/+Qi0jCnSsuFkwODA1"),
                        InlineKeyboardButton("·ꜱᴜᴘᴘᴏʀᴛ ɢʀᴏᴜᴘ·", url="https://t.me/+-CaYhSPW5VwzNjM1"),
                    ],
                    [

                        InlineKeyboardButton("ᴄʟᴏꜱᴇ 🚪", callback_data="closeMessage")
                    ]
                ]
            )
        )
    else:
        try:
            try:
                file_id = int(b64_to_str(usr_cmd).split("_")[-1])
            except (Error, UnicodeDecodeError):
                file_id = int(usr_cmd.split("_")[-1])
            GetMessage = await bot.get_messages(chat_id=Config.DB_CHANNEL, message_ids=file_id)
            message_ids = []
            if GetMessage.text:
                message_ids = GetMessage.text.split(" ")
                _response_msg = await cmd.reply_text(
                    text=f"**Total Files:** `{len(message_ids)}`",
                    quote=True,
                    disable_web_page_preview=True
                )
            else:
                message_ids.append(int(GetMessage.id))
            for i in range(len(message_ids)):
                await send_media_and_reply(bot, user_id=cmd.from_user.id, file_id=int(message_ids[i]))
        except Exception as err:
            await cmd.reply_text(f"Something went wrong!\n\n**Error:** `{err}`")


@Bot.on_message((filters.document | filters.video | filters.audio | filters.photo) & ~filters.chat(Config.DB_CHANNEL))
async def main(bot: Client, message: Message):

    if message.chat.type == enums.ChatType.PRIVATE:

        await add_user_to_database(bot, message)

        if Config.UPDATES_CHANNEL is not None:
            back = await handle_force_sub(bot, message)
            if back == 400:
                return

        if message.from_user.id in Config.BANNED_USERS:
            await message.reply_text("Sorry, You are banned!\n\nContact [Support Group](https://t.me/+kG9L8w7YAZsyMjE1)",
                                     disable_web_page_preview=True)
            return

        # Check if the user is the BOT_OWNER
        if message.from_user.id != Config.BOT_OWNER:
            await message.reply_text("Don't send direct messages, you are not the bot owner.")
            return 

        try:
            forwarded_msg = await message.forward(Config.DB_CHANNEL)
            file_er_id = str(forwarded_msg.id)
            await forwarded_msg.reply_text(
                f"#PRIVATE_FILE:\n\n[{message.from_user.first_name}](tg://user?id={message.from_user.id}) Got File Link!",
                disable_web_page_preview=True)
            share_link = f"https://telegram.me/{Config.BOT_USERNAME}?start=VJBotz_{str_to_b64(file_er_id)}"
            short_link = get_short(share_link)
            await message.reply(
                "**Your File Stored in my Database!**\n\n"
                f"Here is the Permanent Link of your file: <code>{short_link}</code> \n\n"
                "Just Click the link to get your file!",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("ᴏʀɪɢɪɴᴀʟ ʟɪɴᴋ", url=share_link),
                      InlineKeyboardButton("ꜱʜᴏʀᴛ ʟɪɴᴋ", url=short_link)]]
                ),
                disable_web_page_preview=True, quote=True
            )
        except FloodWait as sl:
            if sl.value > 45:
                print(f"Sleep of {sl.value}s caused by FloodWait ...")
                await asyncio.sleep(sl.value)
                await bot.send_message(
                    chat_id=int(Config.LOG_CHANNEL),
                    text="#FloodWait:\n"
                        f"Got FloodWait of `{str(sl.value)}s` from `{str(message.chat.id)}` !!",
                    disable_web_page_preview=True,
                    reply_markup=InlineKeyboardMarkup(
                        [
                            [InlineKeyboardButton("Ban User", callback_data=f"ban_user_{str(message.chat.id)}")]
                        ]
                    )
                )
                return

        elif message.chat.type == enums.ChatType.CHANNEL:
            if (message.chat.id == int(Config.LOG_CHANNEL)) or (message.chat.id == int(Config.UPDATES_CHANNEL)) or message.forward_from_chat or message.forward_from:
                return
            elif int(message.chat.id) in Config.BANNED_CHAT_IDS:
                await bot.leave_chat(message.chat.id)
                return
            else:
                pass

            try:
                forwarded_msg = await message.forward(Config.DB_CHANNEL)
                file_er_id = str(forwarded_msg.id)
                share_link = f"https://telegram.me/{Config.BOT_USERNAME}?start=VJBotz_{str_to_b64(file_er_id)}"
                CH_edit = await bot.edit_message_reply_markup(message.chat.id, message.id,
                                                              reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(
                                                                  "Get Sharable Link", url=share_link)]]))
                if message.chat.username:
                    await forwarded_msg.reply_text(
                        f"#CHANNEL_BUTTON:\n\n[{message.chat.title}](https://t.me/{message.chat.username}/{CH_edit.id}) Channel's Broadcasted File's Button Added!")
                else:
                    private_ch = str(message.chat.id)[4:]
                    await forwarded_msg.reply_text(
                        f"#
