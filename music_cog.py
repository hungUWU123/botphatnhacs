import asyncio
import discord
from discord.ext import commands
from discord import app_commands
import yt_dlp
import random
import os
import time

# Cấu hình yt-dlp tối ưu cho việc phát trực tiếp âm thanh (streaming)
ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,             # Bỏ qua playlist đi kèm trong watch link (ví dụ: YouTube Mix)
    'nocheckcertificate': True,
    'ignoreerrors': True,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',    # Ràng buộc IPv4
    'socket_timeout': 10,           # Timeout 10s để tránh treo
}

ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn',
}

ytdl = yt_dlp.YoutubeDL(ytdl_format_options)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')  # Link stream trực tiếp
        self.duration = data.get('duration')
        self.thumbnail = data.get('thumbnail')
        self.webpage_url = data.get('webpage_url')
        self.requester_name = data.get('requester_name', 'Hệ thống')
        self.requester_avatar = data.get('requester_avatar')

    @classmethod
    async def extract_song_metadata(cls, url, *, loop=None):
        """Trích xuất siêu nhanh thông tin bài hát (Metadata) sử dụng chế độ flat extraction."""
        loop = loop or asyncio.get_event_loop()
        
        # Nếu không phải link trực tiếp, thực hiện tìm kiếm trên YouTube
        if not url.startswith(('http://', 'https://')):
            search_query = f"ytsearch1:{url}"  # Chỉ lấy 1 kết quả tìm kiếm duy nhất để tối ưu tốc độ
        else:
            search_query = url

        # Cấu hình ytdl phẳng để tải metadata siêu tốc (không lấy link stream trực tiếp lúc này)
        flat_options = {**ytdl_format_options, 'extract_flat': True}
        flat_ytdl = yt_dlp.YoutubeDL(flat_options)

        print(f"[DEBUG] [YTDL] Bắt đầu trích xuất phẳng (flat) cho: {search_query}")
        data = await loop.run_in_executor(None, lambda: flat_ytdl.extract_info(search_query, download=False))
        print("[DEBUG] [YTDL] Trích xuất phẳng hoàn tất.")
        
        if data is None:
            return None

        # Nếu kết quả trả về là link tham chiếu phẳng (không có title/metadata trực tiếp)
        if data.get('_type') == 'url' or data.get('title') is None:
            webpage_url = data.get('webpage_url') or data.get('url') or url
            print(f"[DEBUG] [YTDL] Phát hiện link tham chiếu phẳng. Tiến hành phân giải thông tin chi tiết: {webpage_url}")
            data = await loop.run_in_executor(None, lambda: ytdl.extract_info(webpage_url, download=False))
            print("[DEBUG] [YTDL] Phân giải chi tiết hoàn tất.")
            
        if data is None:
            return None

        # Xử lý danh sách phát hoặc kết quả tìm kiếm
        if 'entries' in data:
            entries = [entry for entry in data['entries'] if entry is not None]
            if not entries:
                return None
            
            # Nếu là tìm kiếm, chỉ lấy kết quả đầu tiên
            if not url.startswith(('http://', 'https://')) or 'ytsearch' in data.get('extractor_key', '').lower():
                entry = entries[0]
                video_id = entry.get('id') or entry.get('url')
                video_url = f"https://www.youtube.com/watch?v={video_id}" if video_id and not video_id.startswith('http') else video_id
                
                return {
                    'title': entry.get('title', 'Không rõ tên'),
                    'webpage_url': video_url,
                    'duration': int(entry.get('duration')) if entry.get('duration') is not None else None,
                    'thumbnail': entry.get('thumbnails', [{}])[0].get('url') if entry.get('thumbnails') else None,
                }
            else:
                # Đây là một playlist thực sự (chạy flat cực nhanh)
                playlist_songs = []
                for entry in entries:
                    video_id = entry.get('id') or entry.get('url')
                    video_url = f"https://www.youtube.com/watch?v={video_id}" if video_id and not video_id.startswith('http') else video_url
                    playlist_songs.append({
                        'title': entry.get('title', 'Không rõ tên'),
                        'webpage_url': video_url,
                        'duration': int(entry.get('duration')) if entry.get('duration') is not None else None,
                        'thumbnail': entry.get('thumbnails', [{}])[0].get('url') if entry.get('thumbnails') else None,
                    })
                return playlist_songs

        # Bài hát đơn lẻ từ URL trực tiếp
        return {
            'title': data.get('title', 'Không rõ tên'),
            'webpage_url': data.get('webpage_url') or url,
            'duration': int(data.get('duration')) if data.get('duration') is not None else None,
            'thumbnail': data.get('thumbnail'),
        }

    @classmethod
    async def create_source(cls, song_data, *, loop=None, volume=0.5):
        """Phân giải link stream âm thanh thực tế ngay trước khi phát nhạc (Lazy Loading)."""
        loop = loop or asyncio.get_event_loop()
        webpage_url = song_data.get('webpage_url')
        
        print(f"[DEBUG] [YTDL] Phân giải stream URL cho bài: {song_data.get('title')}")
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(webpage_url, download=False))
        print("[DEBUG] [YTDL] Phân giải stream hoàn tất.")
        
        if 'entries' in data:
            data = data['entries'][0]
            
        full_data = {**song_data, **data}
        # Đảm bảo duration là int
        dur = full_data.get('duration')
        if dur is not None:
            full_data['duration'] = int(dur)
            
        filename = full_data['url']
        
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=full_data, volume=volume)


class GuildMusicState:
    """Quản lý trạng thái phát nhạc độc lập cho mỗi Guild (Server)."""
    def __init__(self, bot, guild):
        self.bot = bot
        self.guild = guild
        self.queue = []  # Danh sách các bài hát trong hàng chờ
        self.current = None  # Bài hát đang phát (đối tượng YTDLSource)
        self.voice_client = None
        self.volume = 0.5  # Âm lượng mặc định (50%)
        self.loop_mode = "none"  # "none", "song", "queue"
        self.play_next_song = asyncio.Event()
        self.audio_player_task = None
        
        # Theo dõi thời gian phát nhạc để vẽ progress bar
        self.start_time = None
        self.paused_time = 0
        self.total_paused = 0

    def start_audio_player(self):
        if self.audio_player_task is None or self.audio_player_task.done():
            self.audio_player_task = self.bot.loop.create_task(self.audio_player_loop())

    async def audio_player_loop(self):
        while True:
            self.play_next_song.clear()

            if not self.voice_client or not self.voice_client.is_connected():
                print("[DEBUG] [Player Loop] Mất kết nối voice. Dừng phát.")
                break

            # Kiểm tra xem có bài hát nào không
            if not self.queue and self.current is None:
                try:
                    print("[DEBUG] [Player Loop] Hàng chờ trống. Đợi nhạc mới trong 3 phút...")
                    await asyncio.wait_for(self.wait_for_queue(), timeout=180.0)
                except asyncio.TimeoutError:
                    print("[DEBUG] [Player Loop] Quá 3 phút không hoạt động. Rời kênh thoại.")
                    if self.voice_client:
                        await self.voice_client.disconnect()
                    break

            if not self.voice_client or not self.voice_client.is_connected():
                break

            # Xác định bài hát tiếp theo
            if self.loop_mode == "song" and self.current:
                print(f"[DEBUG] [Player Loop] Lặp lại bài hát hiện tại: {self.current.title}")
                # Tạo lại AudioSource từ metadata hiện có để phát lại
                try:
                    self.current = await YTDLSource.create_source(self.current.data, loop=self.bot.loop, volume=self.volume)
                except Exception as e:
                    print(f"[DEBUG] [Player Loop] Lỗi lặp bài hát: {e}")
                    self.current = None
                    continue
            else:
                if self.loop_mode == "queue" and self.current:
                    # Đưa bài hát vừa phát xong về cuối hàng chờ
                    self.queue.append(self.current.data)

                if self.queue:
                    next_song_data = self.queue.pop(0)
                    try:
                        print(f"[DEBUG] [Player Loop] Lấy bài hát tiếp theo: {next_song_data.get('title')}")
                        # Phân giải stream URL thực tế ngay trước khi phát (Tránh link hết hạn)
                        self.current = await YTDLSource.create_source(next_song_data, loop=self.bot.loop, volume=self.volume)
                    except Exception as e:
                        print(f"[DEBUG] [Player Loop] Lỗi phân giải hoặc khởi tạo bài hát: {e}")
                        self.current = None
                        continue
                else:
                    self.current = None
                    continue

            # Thiết lập bộ đếm thời gian phát nhạc
            self.start_time = time.time()
            self.paused_time = 0
            self.total_paused = 0

            # Bắt đầu phát bài hát
            print(f"[DEBUG] [Player Loop] Gọi voice_client.play() bài: {self.current.title}")
            try:
                self.voice_client.play(self.current, after=lambda e: self.bot.loop.call_soon_threadsafe(self.play_next_song.set))
            except Exception as e:
                print(f"[DEBUG] [Player Loop] Lỗi khi phát nhạc: {e}")
                self.current = None
                continue
            
            # Chờ bài hát phát xong
            await self.play_next_song.wait()
            print("[DEBUG] [Player Loop] Đã phát xong bài hát.")

        self.current = None
        self.queue.clear()

    async def wait_for_queue(self):
        while not self.queue and self.voice_client and self.voice_client.is_connected():
            await asyncio.sleep(1)

    def skip(self):
        if self.voice_client and self.voice_client.is_playing():
            self.voice_client.stop()

    def stop(self):
        self.queue.clear()
        self.current = None
        if self.voice_client:
            self.voice_client.stop()

    def get_elapsed_time(self):
        if not self.current or not self.start_time:
            return 0
        if self.voice_client and self.voice_client.is_paused():
            elapsed = self.paused_time - self.start_time - self.total_paused
        else:
            elapsed = time.time() - self.start_time - self.total_paused
        return max(0, int(elapsed))

    def get_progress_bar(self):
        duration = self.current.duration
        if not duration:
            return "🔴 **Phát trực tiếp**"
        
        elapsed = self.get_elapsed_time()
        elapsed = min(elapsed, duration)
        
        bar_length = 15
        filled = int((elapsed / duration) * bar_length)
        bar = "▬" * filled + "🔘" + "▬" * (bar_length - filled - 1)
        
        elapsed_str = f"{int(elapsed) // 60}:{int(elapsed) % 60:02d}"
        duration_str = f"{int(duration) // 60}:{int(duration) % 60:02d}"
        
        return f"`{elapsed_str}` {bar} `{duration_str}`"


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.states = {}

    def get_state(self, guild):
        if guild.id not in self.states:
            self.states[guild.id] = GuildMusicState(self.bot, guild)
        return self.states[guild.id]

    async def cog_unload(self):
        for state in self.states.values():
            state.stop()
            if state.voice_client:
                await state.voice_client.disconnect()

    @app_commands.command(name="join", description="Mời bot vào kênh thoại của bạn.")
    async def join(self, interaction: discord.Interaction):
        if not interaction.user.voice:
            embed = discord.Embed(description="❌ Bạn cần tham gia vào một kênh thoại trước!", color=0xe74c3c)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        channel = interaction.user.voice.channel
        state = self.get_state(interaction.guild)

        if interaction.guild.voice_client:
            await interaction.guild.voice_client.move_to(channel)
        else:
            state.voice_client = await channel.connect()

        state.start_audio_player()
        
        embed = discord.Embed(
            title="🔊 Đã Kết Nối",
            description=f"Đã kết nối vào kênh thoại **{channel.name}** thành công!",
            color=0x3498db
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="play", description="Phát nhạc từ link YouTube/SoundCloud hoặc tìm kiếm tên bài hát.")
    @app_commands.describe(nhac="Tên bài hát hoặc đường dẫn (URL)")
    async def play(self, interaction: discord.Interaction, nhac: str):
        await interaction.response.defer()

        # Kiểm tra xem người dùng có ở trong kênh thoại không
        if not interaction.user.voice:
            embed = discord.Embed(description="❌ Bạn cần tham gia vào một kênh thoại trước!", color=0xe74c3c)
            await interaction.followup.send(embed=embed)
            return

        channel = interaction.user.voice.channel
        state = self.get_state(interaction.guild)

        # Kết nối tới voice channel nếu chưa kết nối
        if not interaction.guild.voice_client:
            print(f"[DEBUG] [Play Cmd] Đang kết nối tới kênh thoại: {channel.name}...")
            try:
                state.voice_client = await asyncio.wait_for(channel.connect(timeout=20.0), timeout=25.0)
                print("[DEBUG] [Play Cmd] Đã kết nối kênh thoại thành công.")
            except asyncio.TimeoutError:
                print("[DEBUG] [Play Cmd] Lỗi: Kết nối kênh thoại quá thời gian (Timeout).")
                embed = discord.Embed(description="❌ Lỗi: Kết nối tới kênh thoại bị quá thời gian (Timeout). Vui lòng kiểm tra quyền hạn của Bot.", color=0xe74c3c)
                await interaction.followup.send(embed=embed)
                return
            except Exception as e:
                print(f"[DEBUG] [Play Cmd] Lỗi kết nối kênh thoại: {e}")
                embed = discord.Embed(description=f"❌ Không thể kết nối tới kênh thoại: {e}", color=0xe74c3c)
                await interaction.followup.send(embed=embed)
                return
            state.start_audio_player()
        else:
            state.voice_client = interaction.guild.voice_client
            state.start_audio_player()

        try:
            # Lưu thông tin người yêu cầu
            requester_name = interaction.user.display_name
            requester_avatar = interaction.user.display_avatar.url if interaction.user.display_avatar else None

            # Tìm kiếm nhạc phẳng (Chạy siêu tốc)
            print(f"[DEBUG] [Play Cmd] Bắt đầu trích xuất phẳng cho: {nhac}")
            result = await YTDLSource.extract_song_metadata(nhac, loop=self.bot.loop)
            print("[DEBUG] [Play Cmd] Trích xuất phẳng hoàn tất.")
            
            if result is None:
                embed = discord.Embed(description="❌ Không tìm thấy bài hát nào hoặc định dạng không hỗ trợ.", color=0xe74c3c)
                await interaction.followup.send(embed=embed)
                return

            if isinstance(result, list):
                # Thêm playlist flat vào hàng chờ
                for entry in result:
                    entry_copy = entry.copy()
                    entry_copy['requester_name'] = requester_name
                    entry_copy['requester_avatar'] = requester_avatar
                    state.queue.append(entry_copy)
                
                embed = discord.Embed(
                    title="📂 Đã Thêm Playlist",
                    description=f"Đã thêm **{len(result)}** bài hát vào hàng chờ (chế độ tải nhanh).",
                    color=0x3498db
                )
                await interaction.followup.send(embed=embed)
            else:
                # Thêm bài hát đơn lẻ flat vào hàng chờ
                song_data = result.copy()
                song_data['requester_name'] = requester_name
                song_data['requester_avatar'] = requester_avatar
                
                state.queue.append(song_data)
                
                duration = song_data.get('duration')
                duration_str = f"{int(duration) // 60}:{int(duration) % 60:02d}" if duration else "Không rõ"
                
                embed = discord.Embed(color=0x2ecc71)
                
                # Hiển thị phản hồi nhanh dựa trên việc phát nhạc
                is_currently_playing = state.voice_client.is_playing() or state.voice_client.is_paused() or state.current is not None
                
                if is_currently_playing:
                    embed.title = "➕ Đã Thêm Vào Hàng Chờ"
                    embed.description = f"[**{song_data.get('title')}**]({song_data.get('webpage_url')})"
                    embed.add_field(name="⏱️ Thời lượng", value=duration_str, inline=True)
                    embed.add_field(name="⏳ Vị trí trong hàng", value=f"`#{len(state.queue)}`", inline=True)
                else:
                    embed.title = "🎵 Bắt Đầu Phát Nhạc"
                    embed.description = f"[**{song_data.get('title')}**]({song_data.get('webpage_url')})"
                    embed.add_field(name="⏱️ Thời lượng", value=duration_str, inline=True)
                    
                if song_data.get('thumbnail'):
                    embed.set_thumbnail(url=song_data.get('thumbnail'))
                
                embed.set_footer(text=f"Yêu cầu bởi: {requester_name}", icon_url=requester_avatar)
                await interaction.followup.send(embed=embed)

        except Exception as e:
            print(f"[DEBUG] [Play Cmd] Lỗi trong quá trình xử lý lệnh: {e}")
            embed = discord.Embed(description=f"❌ Đã xảy ra lỗi khi xử lý bài hát: {e}", color=0xe74c3c)
            await interaction.followup.send(embed=embed)

    @app_commands.command(name="pause", description="Tạm dừng nhạc đang phát.")
    async def pause(self, interaction: discord.Interaction):
        state = self.get_state(interaction.guild)
        if not state.voice_client or not state.voice_client.is_playing():
            embed = discord.Embed(description="❌ Hiện tại không có nhạc nào đang phát.", color=0xe74c3c)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        state.voice_client.pause()
        state.paused_time = time.time()
        
        embed = discord.Embed(
            title="⏸️ Đã Tạm Dừng",
            description=f"Tạm dừng bài: **{state.current.title}**",
            color=0xe67e22
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="resume", description="Tiếp tục phát bài nhạc đang tạm dừng.")
    async def resume(self, interaction: discord.Interaction):
        state = self.get_state(interaction.guild)
        if not state.voice_client or not state.voice_client.is_paused():
            embed = discord.Embed(description="❌ Nhạc không ở trạng thái tạm dừng.", color=0xe74c3c)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        state.voice_client.resume()
        state.total_paused += time.time() - state.paused_time
        state.paused_time = 0
        
        embed = discord.Embed(
            title="▶️ Tiếp Tục Phát",
            description=f"Đang phát lại bài: **{state.current.title}**",
            color=0x2ecc71
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="skip", description="Bỏ qua bài hát hiện tại.")
    async def skip(self, interaction: discord.Interaction):
        state = self.get_state(interaction.guild)
        if not state.voice_client or (not state.voice_client.is_playing() and not state.voice_client.is_paused()):
            embed = discord.Embed(description="❌ Không có bài hát nào đang phát để bỏ qua.", color=0xe74c3c)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        title = state.current.title if state.current else "Bài hát hiện tại"
        state.skip()
        
        embed = discord.Embed(
            title="⏭️ Đã Bỏ Qua",
            description=f"Đã bỏ qua bài hát: **{title}**",
            color=0x3498db
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="stop", description="Dừng phát nhạc, xóa hàng chờ và rời kênh thoại.")
    async def stop(self, interaction: discord.Interaction):
        state = self.get_state(interaction.guild)
        state.stop()
        
        if state.voice_client:
            await state.voice_client.disconnect()
            state.voice_client = None
            
            embed = discord.Embed(
                title="⏹️ Đã Dừng Nhạc",
                description="Đã dừng phát nhạc, xóa sạch hàng chờ và rời khỏi kênh thoại.",
                color=0xe74c3c
            )
            await interaction.response.send_message(embed=embed)
        else:
            embed = discord.Embed(description="❌ Bot hiện tại không có ở trong kênh thoại.", color=0xe74c3c)
            await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="queue", description="Hiển thị danh sách các bài hát trong hàng chờ.")
    async def queue(self, interaction: discord.Interaction):
        state = self.get_state(interaction.guild)
        if not state.queue and not state.current:
            embed = discord.Embed(description="📂 Hàng chờ hiện đang trống. Hãy thêm nhạc bằng lệnh `/play`", color=0x3498db)
            await interaction.response.send_message(embed=embed)
            return

        embed = discord.Embed(title="🎶 Danh Sách Hàng Chờ Nhạc", color=0x3498db)
        
        # Bài đang phát
        if state.current:
            duration = state.current.duration
            duration_str = f"{int(duration) // 60}:{int(duration) % 60:02d}" if duration else "Phát trực tiếp"
            embed.description = f"**🔥 Đang Phát:**\n[**{state.current.title}**]({state.current.webpage_url}) | `{duration_str}`\n\n**⌛ Hàng Đợi Kế Tiếp:**\n"
        else:
            embed.description = "**⌛ Hàng Đợi Kế Tiếp:**\n"

        # Danh sách chờ (tối đa hiển thị 10 bài để tránh quá dài)
        queue_list = ""
        for i, song_data in enumerate(state.queue[:10], start=1):
            title = song_data.get('title')
            url = song_data.get('webpage_url')
            dur = song_data.get('duration')
            dur_str = f"{int(dur) // 60}:{int(dur) % 60:02d}" if dur else "Không rõ"
            queue_list += f"`{i:02d}.` [**{title}**]({url}) | `{dur_str}` (Yêu cầu bởi: *{song_data.get('requester_name')}*)\n"

        if not state.queue:
            queue_list = "*Không có bài hát nào tiếp theo. Hãy thêm nhạc bằng lệnh `/play`*"

        embed.description += queue_list

        if len(state.queue) > 10:
            embed.description += f"\n*...và còn {len(state.queue) - 10} bài hát khác trong danh sách.*"
            
        loop_status = "Tắt"
        if state.loop_mode == "song":
            loop_status = "Lặp bài hiện tại"
        elif state.loop_mode == "queue":
            loop_status = "Lặp toàn bộ hàng chờ"
            
        embed.set_footer(
            text=f"Tổng số: {len(state.queue)} bài | Âm lượng: {int(state.volume * 100)}% | Lặp: {loop_status}",
            icon_url=self.bot.user.display_avatar.url if self.bot.user.display_avatar else None
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="nowplaying", description="Hiển thị bài hát hiện đang phát.")
    async def nowplaying(self, interaction: discord.Interaction):
        state = self.get_state(interaction.guild)
        if not state.current:
            embed = discord.Embed(description="❌ Hiện tại không có bài hát nào đang phát.", color=0xe74c3c)
            await interaction.response.send_message(embed=embed)
            return

        embed = discord.Embed(
            title="🎵 Đang Phát",
            description=f"[**{state.current.title}**]({state.current.webpage_url})",
            color=0x2ecc71
        )
        if state.current.thumbnail:
            embed.set_thumbnail(url=state.current.thumbnail)
        
        # Thêm progress bar động
        progress_bar = state.get_progress_bar()
        embed.add_field(name="⏳ Tính Trạng", value=progress_bar, inline=False)
        
        # Cấu hình lặp lại
        loop_status = "Tắt"
        if state.loop_mode == "song":
            loop_status = "🔂 Lặp bài hiện tại"
        elif state.loop_mode == "queue":
            loop_status = "🔁 Lặp toàn bộ hàng chờ"
            
        embed.add_field(name="🔄 Chế Độ Lặp", value=loop_status, inline=True)
        embed.add_field(name="🔊 Âm Lượng", value=f"{int(state.volume * 100)}%", inline=True)
        
        embed.set_footer(text=f"Yêu cầu bởi: {state.current.requester_name}", icon_url=state.current.requester_avatar)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="volume", description="Điều chỉnh âm lượng nhạc (0 - 100).")
    @app_commands.describe(muc_do="Mức âm lượng từ 0 đến 100")
    async def volume(self, interaction: discord.Interaction, muc_do: int):
        state = self.get_state(interaction.guild)
        if muc_do < 0 or muc_do > 100:
            embed = discord.Embed(description="❌ Vui lòng nhập mức âm lượng hợp lệ từ 0 đến 100.", color=0xe74c3c)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        state.volume = muc_do / 100
        if state.current:
            state.current.volume = state.volume
        
        # Biểu tượng âm lượng tương ứng
        vol_icon = "🔈" if muc_do == 0 else "🔉" if muc_do < 50 else "🔊"
        embed = discord.Embed(
            title=f"{vol_icon} Điều Chỉnh Âm Lượng",
            description=f"Đã thay đổi âm lượng phát nhạc thành **{muc_do}%**.",
            color=0xf1c40f
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="loop", description="Điều chỉnh chế độ lặp lại nhạc.")
    @app_commands.choices(che_do=[
        app_commands.Choice(name="Tắt lặp lại", value="none"),
        app_commands.Choice(name="Lặp lại bài hát hiện tại", value="song"),
        app_commands.Choice(name="Lặp lại toàn bộ hàng chờ", value="queue")
    ])
    async def loop(self, interaction: discord.Interaction, che_do: app_commands.Choice[str]):
        state = self.get_state(interaction.guild)
        state.loop_mode = che_do.value
        
        color_map = {"none": 0xe74c3c, "song": 0x9b59b6, "queue": 0x9b59b6}
        embed = discord.Embed(color=color_map.get(state.loop_mode, 0x9b59b6))
        
        if state.loop_mode == "none":
            embed.title = "🔄 Đã Tắt Lặp Lại"
            embed.description = "Chế độ phát nhạc bình thường (không lặp lại)."
        elif state.loop_mode == "song":
            embed.title = "🔂 Lặp Bài Hiện Tại"
            embed.description = "Sẽ phát đi phát lại bài hát đang phát."
        elif state.loop_mode == "queue":
            embed.title = "🔁 Lặp Toàn Bộ Hàng Chờ"
            embed.description = "Khi phát hết hàng chờ, danh sách sẽ được bắt đầu lại từ đầu."
            
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="shuffle", description="Trộn ngẫu nhiên danh sách hàng chờ.")
    async def shuffle(self, interaction: discord.Interaction):
        state = self.get_state(interaction.guild)
        if not state.queue:
            embed = discord.Embed(description="❌ Hàng chờ hiện đang trống, không thể trộn bài.", color=0xe74c3c)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        random.shuffle(state.queue)
        embed = discord.Embed(
            title="🔀 Trộn Bài Hát",
            description="Đã trộn ngẫu nhiên toàn bộ danh sách hàng chờ nhạc thành công!",
            color=0x9b59b6
        )
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(Music(bot))
