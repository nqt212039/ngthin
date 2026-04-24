# bot.py (đã sửa lỗi cú pháp)

# Giả sử bạn đang dùng discord.py
import discord
from discord.ext import commands

TOKEN = "YOUR_TOKEN_HERE"

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Bot đã đăng nhập: {bot.user}")

# Sửa lỗi ở đây: thêm dấu phẩy đúng cú pháp
bot.run(TOKEN)
