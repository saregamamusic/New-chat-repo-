from NoxxNetwork import NoxxBot, db
from typing import List, Dict
from datetime import datetime
from pyrogram import filters
from pyrogram.types import Message
import logging
import asyncio

# Initialize databases
chatsdb = db.chatsdb
usersdb = db.usersdb

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============= DATABASE FUNCTIONS =============
async def is_served_chat(chat_id: int) -> bool:
    chat = await chatsdb.find_one({"chat_id": chat_id})
    return bool(chat)

async def add_served_chat(chat_id: int, title: str = None):
    if not await is_served_chat(chat_id):
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

# ============= LEARN COMMAND HANDLER =============
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

        processing_msg = await message.reply("⏳ Learning from last 1000 messages...")

        # Ensure chat is in database
        await add_served_chat(message.chat.id, message.chat.title)

        # Get messages
        messages = []
        count = 0
        async for msg in client.get_chat_history(message.chat.id, limit=1000):
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
            if count % 100 == 0:  # Update progress every 100 messages
                await processing_msg.edit(f"⏳ Learned {count} messages so far...")

        # Store messages
        if await learn_group_messages(message.chat.id, messages):
            await processing_msg.edit(f"✅ Successfully learned {len(messages)} messages!")
        else:
            await processing_msg.edit("❌ No valid messages found to learn")

    except FloodWait as e:
        await asyncio.sleep(e.value)
        await message.reply(f"⚠️ Please wait {e.value} seconds before trying again")
    except Exception as e:
        logger.error(f"Error in /learn: {str(e)}", exc_info=True)
        await message.reply(f"⚠️ Error: {str(e)}")
