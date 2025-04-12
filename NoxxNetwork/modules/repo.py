import asyncio
import random
from pyrogram import filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from config import IMG
from NoxxNetwork import NoxxBot


start_txt = """**
✪ 𝐖𝐞𝐥𝐜𝐨𝐦𝐞 𝐌𝐮𝐬𝐢𝐜 𝐖𝐨𝐫𝐥𝐝 𝐒𝐮𝐩𝐩𝐨𝐫𝐭 ✪

➲ ᴇᴀsʏ ᴅᴇᴘʟᴏʏᴍᴇɴᴛ ✰  
➲ ɴᴏ ʙᴀɴ ɪssᴜᴇs ✰  
➲ ᴜɴʟɪᴍɪᴛᴇᴅ ᴅʏɴᴏs ✰  
➲ 𝟸𝟺/𝟽 ʟᴀɢ-ғʀᴇᴇ ✰

► sᴇɴᴅ ᴀ sᴄʀᴇᴇɴsʜᴏᴛ ɪғ ʏᴏᴜ ғᴀᴄᴇ ᴀɴʏ ᴘʀᴏʙʟᴇᴍs!
**"""




@NoxxBot.on_cmd("repo")
async def repo(_, m: Message):
    buttons = [
        [ 
          InlineKeyboardButton("ᴀᴅᴅ ᴍᴇ", url=f"https://t.me/{Baby_ChatsBot.username}?startgroup=true")
        ],
        [
          InlineKeyboardButton("sᴛʏʟᴇs ᴅᴘᴢ", url="https://t.me/DPZ_STYLES_WORLD"),
          InlineKeyboardButton("Cʜᴀᴛᴢᴏɴᴇ", url="https://t.me/+gdo528FUAq84NTM1"),
          ],
               [
                InlineKeyboardButton("ᴏᴡɴᴇʀ", url="http://t.me/MR_ROCKY_TZ"),

],
[
              InlineKeyboardButton("ᴍᴜsɪᴄ ʙᴏᴛ", url=f"https://t.me/BabyMusicsBot"),
              InlineKeyboardButton("Chatabot", url=f"https://t.me/Baby_ChatsBot")
              ]]
    
    reply_markup = InlineKeyboardMarkup(buttons)
    
    await m.reply_photo(
        photo=random.choice(IMG),
        caption=start_txt,
        reply_markup=reply_markup
    )
