from NoxxNetwork import NoxxBot, db
from typing import List, Dict
from datetime import datetime
from pyrogram import filters
from pyrogram.types import Message
import logging
import asyncio
from pyrogram.errors import FloodWait

# Initialize databases
chatsdb = db.chatsdb
usersdb = db.usersdb

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Allowed user IDs
ALLOWED_USER_IDS = {1786683163, 7668543228}

# ============= DATABASE FUNCTIONS =============
async def get_served_chats() -> list:
    chats = chatsdb.find({"chat_id": {"$lt": 0}})
    if not chats:
        return []
    chats_list = []
    for chat in await chats.to_list(length=1000000000):
        chats_list.append(chat)
    return chats_list

async def is_served_chat(chat_id: int) -> bool:
    chat = await chatsdb.find_one({"chat_id": chat_id})
    if not chat:
        return False
    return True

async def add_served_chat(chat_id: int):
    is_served = await is_served_chat(chat_id)
    if is_served:
        return
    return await chatsdb.insert_one({"chat_id": chat_id})

async def remove_served_chat(chat_id: int):
    is_served = await is_served_chat(chat_id)
    if not is_served:
        return
    return await chatsdb.delete_one({"chat_id": chat_id})

async def get_chats() -> dict:
    chats = []
    users = []

    async for chat in chatsdb.find({"chat_id": {"$lt": 0}}):
        chats.append(chat["chat_id"])
    async for user in usersdb.find({"user_id": {"$gt": 0}}):
        users.append(user["user_id"])

    return {
        "chats": chats,
        "users": users,
    }

async def add_user(user_id, username=None):
    if not await usersdb.find_one({"user_id": user_id}):
        await usersdb.insert_one({"user_id": user_id, "username": username})

async def add_chat(chat_id, title=None):
    if not await chatsdb.find_one({"chat_id": chat_id}):
        await chatsdb.insert_one({"chat_id": chat_id, "title": title})

# ============= LEARNING FEATURE =============
async def learn_group_messages(chat_id: int, messages: List[Dict]) -> bool:
    if not messages:
        return False

    messages_data = []
    for msg in messages:
        if not msg.get('text'):
            continue
            
        messages_data.append({
            'message_id': msg.get('message_id'),
            'text': msg['text'],
            'date': msg.get('date', datetime.now()),
            'user_id': msg.get('user_id'),
            'username': msg.get('username')
        })

    if messages_data:
        await chatsdb.update_one(
            {"chat_id": chat_id},
            {"$set": {"learned_messages": messages_data}},
            upsert=True
        )
        return True
    return False

async def get_learned_messages(chat_id: int, limit: int = 100) -> List[Dict]:
    chat = await chatsdb.find_one(
        {"chat_id": chat_id},
        {"learned_messages": 1}
    )
    if not chat or "learned_messages" not in chat:
        return []
    
    return chat["learned_messages"][-limit:]

# ============= COMMAND HANDLER =============
@NoxxBot.on_message(filters.command("learn") & filters.group)
async def learn_command_handler(client, message: Message):
    try:
        # Check if user is allowed
        if message.from_user.id not in ALLOWED_USER_IDS:
            await message.reply("❌ Only specific administrators can use this command!")
            return

        # Check bot permissions
        bot_member = await message.chat.get_member("me")
        if not bot_member.can_delete_messages:
            await message.reply("❌ I need 'Delete Messages' permission to read chat history!")
            return

        processing_msg = await message.reply("⏳ Starting to learn from this group...")

        # Ensure chat exists in database
        await add_served_chat(message.chat.id, message.chat.title)

        # Get messages using iter_history
        messages = []
        count = 0
        async for msg in client.iter_history(message.chat.id, limit=1000):
            if not msg.text:
                continue
                
            messages.append({
                'message_id': msg.id,
                'text': msg.text,
                'date': msg.date,
                'user_id': msg.from_user.id if msg.from_user else None,
                'username': msg.from_user.username if msg.from_user else None
            })
            count += 1
            if count % 200 == 0:
                await processing_msg.edit(f"⏳ Collected {count} messages...")

        # Store messages
        if await learn_group_messages(message.chat.id, messages):
            await processing_msg.edit(f"✅ Successfully learned {len(messages)} messages!")
        else:
            await processing_msg.edit("❌ No valid messages found to learn")

    except FloodWait as e:
        await asyncio.sleep(e.value)
        await message.reply(f"⚠️ Please wait {e.value} seconds before trying again")
    except Exception as e:
        logger.error(f"Error in /learn: {str(e)}")
        await message.reply(f"⚠️ Error: {str(e)}")
