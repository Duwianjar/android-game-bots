#!/usr/bin/env python3
from telethon import TelegramClient
from telethon.tl.types import User
import asyncio
import sys

# Konfigurasi
api_id = 94575  # API ID public untuk testing
api_hash = 'a3406de8d171bb422bb6ddf3bbd800e2'  # API hash public
phone = '+6285157993801'
password = 'Mbahgawol01'  # 2FA password

client = TelegramClient('session_telegram', api_id, api_hash)

async def main():
    await client.start(
        phone=phone,
        password=lambda: password
    )
    
    print("Login berhasil!")
    print("\nMengambil chat dengan BotFather...")
    
    try:
        # Cari BotFather
        botfather = await client.get_entity('BotFather')
        
        # Ambil pesan terakhir dari BotFather
        messages = await client.get_messages(botfather, limit=20)
        
        print("\n" + "="*60)
        print("CHAT TERAKHIR DENGAN BOTFATHER:")
        print("="*60)
        
        for msg in reversed(messages):
            if msg.text:
                sender = "Anda" if msg.out else "BotFather"
                print(f"\n[{sender}]")
                print(msg.text)
                print("-"*60)
        
        print("\n" + "="*60)
        
    except Exception as e:
        print(f"Error: {e}")
    
    await client.disconnect()

if __name__ == '__main__':
    asyncio.run(main())
