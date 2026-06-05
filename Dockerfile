# Sử dụng Python 3.12 phiên bản slim siêu nhẹ
FROM python:3.12-slim

# Cài đặt FFmpeg và các công cụ cần thiết trên hệ thống Linux
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg libsodium-dev build-essential && \
    rm -rf /var/lib/apt/lists/*

# Thiết lập thư mục làm việc trong container
WORKDIR /app

# Copy requirements.txt và cài đặt các thư viện Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy toàn bộ code vào trong container
COPY . .

# Chạy bot
CMD ["python", "bot.py"]
