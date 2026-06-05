# 🎵 Bot Discord Phát Nhạc (Discord Music Bot)

Đây là mã nguồn một Bot Discord phát nhạc hiện đại, sử dụng Python với thư viện `discord.py` và `yt-dlp` để lấy luồng âm thanh chất lượng cao trực tiếp từ YouTube, SoundCloud, Spotify, v.v.

Bot được tích hợp sẵn hệ thống tự động tải xuống công cụ giải mã âm thanh **FFmpeg Essentials** dành cho hệ điều hành Windows, giúp bạn chạy bot vô cùng nhanh chóng mà không cần cài đặt FFmpeg thủ công vào hệ thống.

---

## ✨ Tính năng chính

- 🚀 **Hỗ trợ Slash Commands (`/`)**: Các lệnh trực quan, hiện đại, có gợi ý nhập liệu.
- 🎵 **Phát nhạc đa nền tảng**: Phát trực tiếp từ link YouTube, SoundCloud, Spotify hoặc tìm kiếm trực tiếp bằng từ khóa (ví dụ: `/play son tung mtp`).
- 📜 **Hàng chờ nhạc (Queue)**: Xem danh sách bài hát kế tiếp, thêm nhạc tự động.
- 🔁 **Chế độ Lặp lại (Loop)**: Tùy chỉnh không lặp, lặp 1 bài đang phát hoặc lặp lại toàn bộ hàng chờ.
- 🔀 **Trộn bài (Shuffle)**: Trộn ngẫu nhiên danh sách hàng chờ.
- 🔊 **Điều khiển âm lượng (Volume)**: Tăng giảm âm lượng phát nhạc trực tiếp bằng lệnh `/volume`.
- 🔋 **Tự động ngắt kết nối**: Bot tự động rời kênh voice sau 3 phút nếu không có nhạc phát hoặc không có người trong phòng để tiết kiệm băng thông.

---

## 🛠️ Hướng dẫn cài đặt và chạy Bot

### Bước 1: Tạo Bot trên Discord Developer Portal
1. Truy cập [Discord Developer Portal](https://discord.com/developers/applications).
2. Nhấn nút **New Application** và đặt tên cho Bot của bạn.
3. Vào tab **Bot** (bên menu trái) -> Nhấn **Add Bot** hoặc **Reset Token** để lấy chuỗi **Token**. Lưu lại token này.
4. Cuộn xuống phần **Privileged Gateway Intents** và kích hoạt (Bật màu xanh) các quyền sau:
   - **Presence Intent**
   - **Server Members Intent**
   - **Message Content Intent** (bắt buộc)
5. Lưu lại cấu hình (**Save Changes**).

### Bước 2: Cài đặt thư viện Python
Mở Command Prompt hoặc PowerShell tại thư mục chứa code và chạy lệnh:
```bash
pip install -r requirements.txt
```

### Bước 3: Cấu hình Token
1. Mở file `.env` bằng Notepad hoặc trình biên soạn code.
2. Thay thế dòng `your_discord_bot_token_here` bằng chuỗi Token bạn đã copy ở Bước 1.
   ```env
   DISCORD_TOKEN=MTAyNDM5... (Token thật của bạn)
   ```
3. Lưu và đóng file lại.

### Bước 4: Mời Bot vào Server của bạn
1. Tại [Discord Developer Portal](https://discord.com/developers/applications), truy cập tab **OAuth2** -> **URL Generator**.
2. Trong phần **Scopes**, tích chọn: `bot` và `applications.commands`.
3. Trong phần **Bot Permissions**, tích chọn:
   - **Send Messages**
   - **Embed Links**
   - **Connect** (Voice)
   - **Speak** (Voice)
4. Copy đường dẫn được tạo ở dưới cùng và dán vào trình duyệt để mời Bot vào máy chủ Discord của bạn.

### Bước 5: Chạy Bot
Chạy bot bằng lệnh:
```bash
python bot.py
```
> **Lưu ý**: Lần đầu chạy bot sẽ tự động tải FFmpeg (khoảng 90MB) từ trang chủ Gyan.dev và giải nén vào thư mục bot. Quá trình này có thể mất từ 10 - 30 giây tùy tốc độ mạng của bạn. Khi bot hiển thị `🌟 Bot đã sẵn sàng nhận lệnh từ người dùng!` nghĩa là đã hoàn tất.

---

## 🎮 Danh sách lệnh Slash Commands (`/`)

| Lệnh | Mô tả |
| :--- | :--- |
| `/join` | Mời bot vào kênh thoại bạn đang đứng. |
| `/play <tên_bài_hoặc_link>` | Tìm kiếm nhạc hoặc phát trực tiếp từ URL và đưa vào hàng chờ. |
| `/pause` | Tạm dừng phát nhạc. |
| `/resume` | Tiếp tục phát nhạc đang bị tạm dừng. |
| `/skip` | Bỏ qua bài hát hiện tại. |
| `/stop` | Dừng nhạc hoàn toàn, xóa hàng chờ và ngắt kết nối bot. |
| `/queue` | Hiển thị hàng chờ các bài hát tiếp theo. |
| `/nowplaying` | Hiển thị chi tiết bài hát đang được phát. |
| `/volume <0-100>` | Điều chỉnh âm lượng phát nhạc. |
| `/loop <chế_độ>` | Lặp bài hát hiện tại / Lặp toàn bộ hàng chờ / Tắt lặp lại. |
| `/shuffle` | Trộn ngẫu nhiên danh sách hàng chờ. |

---

## ⚠️ Giải quyết một số lỗi thường gặp

1. **Lỗi `OpusNotLoaded` hoặc không nghe thấy âm thanh**:
   Bot tự động cài đặt gói mã hóa âm thanh `PyNaCl` đi kèm trong `requirements.txt`. Đảm bảo rằng bạn đã cài đặt đủ các thư viện và file `ffmpeg.exe` + `ffprobe.exe` đã nằm trong thư mục bot sau lần chạy đầu tiên.
   
2. **Lỗi lệnh Slash không hiển thị ngay lập tức**:
   Khi bạn chạy bot lần đầu tiên, bot sẽ đồng bộ các lệnh slash của mình. Đôi khi có thể mất vài phút để Discord cập nhật trên thiết bị của bạn. Hãy thử khởi động lại ứng dụng Discord trên máy tính hoặc điện thoại nếu không thấy hiển thị.

3. **Lỗi liên quan đến `yt-dlp` (không tải được video YouTube)**:
   Nếu YouTube cập nhật thuật toán làm bot không phát được nhạc, hãy cập nhật `yt-dlp` lên bản mới nhất bằng cách chạy:
   ```bash
   pip install --upgrade yt-dlp
   ```
