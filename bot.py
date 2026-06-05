import os
import sys
import discord
from discord.ext import commands
from dotenv import load_dotenv
import asyncio

# Tránh lỗi mã hóa Unicode trên Windows terminal
if sys.version_info >= (3, 7):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Tự động tải và cài đặt FFmpeg nếu chưa có
from ffmpeg_setup import setup_ffmpeg
setup_ffmpeg()

# Load token từ file .env
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# Cấu hình Intents cho bot
intents = discord.Intents.default()
intents.message_content = True  # Bật Message Content Intent (nếu cần xử lý prefix commands)
intents.voice_states = True     # Bắt buộc để phát nhạc qua voice channels
intents.guilds = True           # Cần thiết để quản lý các guild (server)

# Khởi tạo bot với prefix tạm thời (slash commands vẫn là chính)
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print("=" * 40)
    print(f"🤖 Bot đang hoạt động với tên: {bot.user.name}")
    print(f"🆔 ID của Bot: {bot.user.id}")
    print("=" * 40)
    
    # Thiết lập trạng thái hoạt động của bot
    await bot.change_presence(activity=discord.Activity(
        type=discord.ActivityType.listening, 
        name="/play để nghe nhạc"
    ))
    
    # Tải Cog nhạc
    try:
        await bot.load_extension("music_cog")
        print("🎵 Đã tải thành công Music Cog.")
    except Exception as e:
        print(f"❌ Không thể tải Music Cog: {e}")

    # Đồng bộ hóa slash commands toàn cầu
    print("🔄 Đang đồng bộ hóa Slash Commands với Discord...")
    try:
        synced = await bot.tree.sync()
        print(f"✅ Đã đồng bộ thành công {len(synced)} slash commands.")
    except Exception as e:
        print(f"❌ Lỗi đồng bộ slash commands: {e}")
    
    print("=" * 40)
    print("🌟 Bot đã sẵn sàng nhận lệnh từ người dùng!")
    print("=" * 40)

def run_web_server():
    from http.server import BaseHTTPRequestHandler, HTTPServer
    import threading

    class KeepAliveHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write("Bot nhạc đang hoạt động ổn định!".encode('utf-8'))

        def log_message(self, format, *args):
            return

    port = int(os.getenv("PORT", 8080))
    try:
        server = HTTPServer(('0.0.0.0', port), KeepAliveHandler)
        print(f"📡 Keep-alive web server đã khởi chạy tại cổng {port}")
        threading.Thread(target=server.serve_forever, daemon=True).start()
    except Exception as e:
        print(f"⚠️ Không thể khởi động keep-alive web server: {e}")

def main():
    if not TOKEN or TOKEN == "your_discord_bot_token_here":
        print("[LỖI THIẾT LẬP]")
        print("Vui lòng mở file `.env` và thay thế 'your_discord_bot_token_here' bằng Discord Bot Token thực tế của bạn.")
        print("Sau đó chạy lại bot.")
        return
        
    # Chạy keep-alive web server (hỗ trợ Render)
    run_web_server()
        
    try:
        bot.run(TOKEN)
    except discord.errors.LoginFailure:
        print("[LỖI ĐĂNG NHẬP] Token Discord của bạn không hợp lệ. Vui lòng kiểm tra lại file `.env`.")
    except Exception as e:
        print(f"[LỖI HỆ THỐNG] Không thể khởi chạy bot: {e}")

if __name__ == "__main__":
    main()
