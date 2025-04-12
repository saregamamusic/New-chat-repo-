from NoxxNetwork import db
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

# ============= ORIGINAL DATABASE FUNCTIONS =============
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
    """
    Store messages directly in the chat's document
    """
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
    """
    Get learned messages from chat document
    """
    chat = await chatsdb.find_one(
        {"chat_id": chat_id},
        {"learned_messages": 1}
    )
    if not chat or "learned_messages" not in chat:
        return []
    
    return chat["learned_messages"][-limit:]

async def process_learn_command(chat_id: int, admin_id: int, client) -> str:
    """
    Handle /learn command (updated for chatsdb storage)
    """
    if not await is_served_chat(chat_id):
        return "❌ Please add this group to database first using /addchat"
    
    try:
        # Get last 1000 messages
        messages = []
        count = 0
        async for message in client.get_chat_history(chat_id, limit=1000):
            if not message.text:
                continue
                
            messages.append({
                'message_id': message.id,
                'text': message.text,
                'date': message.date,
                'user_id': message.from_user.id if message.from_user else None,
                'username': message.from_user.username if message.from_user else None
            })
            count += 1
            if count % 200 == 0:  # Update progress every 200 messages
                await client.send_message(
                    chat_id=admin_id,
                    text=f"⏳ Collected {count} messages so far..."
                )
        
        # Store in the same chat document
        success = await learn_group_messages(chat_id, messages)
        
        if success:
            return f"✅ {len(messages)} messages successfully learned and stored!"
        return "❌ No valid messages found to learn"
            
    except FloodWait as e:
        await asyncio.sleep(e.value)
        return f"⚠️ Please wait {e.value} seconds before trying again"
    except Exception as e:
        logger.error(f"Error in process_learn_command: {str(e)}", exc_info=True)
        return f"⚠️ Error: {str(e)}"

# ============= COMMAND HANDLER =============
@NoxxBot.on_message(filters.command("learn") & filters.group)
async def learn_command_handler(client, message: Message):
    try:
        # Check admin status
        user = await message.chat.get_member(message.from_user.id)
        if user.status not in ("creator", "administrator"):
            await message.reply("❌ Only admins can use this command!")
            return

        # Check bot permissions
        bot_member = await message.chat.get_member("me")
        if not bot_member.can_delete_messages:
            await message.reply("❌ I need 'Delete Messages' permission to read chat history!")
            return

        processing_msg = await message.reply("⏳ Starting to learn from this group...")

        result = await process_learn_command(
            chat_id=message.chat.id,
            admin_id=message.from_user.id,
            client=client
        )

        await processing_msg.edit(result)

    except Exception as e:
        logger.error(f"Error in learn_command_handler: {str(e)}")
        await message.reply(f"⚠️ An error occurred: {str(e)}")
