import os
import sys
import urllib.request
import zipfile
import shutil
import time

# Tránh lỗi mã hóa Unicode trên Windows terminal
if sys.version_info >= (3, 7):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

FFMPEG_ZIP_URL = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
ZIP_FILE_NAME = "ffmpeg_temp.zip"
TARGET_FILES = ["ffmpeg.exe", "ffprobe.exe"]

def is_ffmpeg_installed():
    if os.path.exists("ffmpeg.exe") and os.path.exists("ffprobe.exe"):
        return True
    
    ffmpeg_in_path = shutil.which("ffmpeg")
    ffprobe_in_path = shutil.which("ffprobe")
    return ffmpeg_in_path is not None and ffprobe_in_path is not None

def download_file_resilient(url, filename, retries=8):
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url)
            downloaded = 0
            
            # Kiểm tra xem có file tải dở không để tiếp tục tải (Resume)
            if os.path.exists(filename):
                downloaded = os.path.getsize(filename)
                
            if downloaded > 0:
                req.add_header('Range', f'bytes={downloaded}-')
                mode = 'ab'
                print(f"\n[FFmpeg] Phát hiện file tải dở. Tiếp tục tải từ {downloaded / (1024*1024):.1f} MB...")
            else:
                mode = 'wb'
            
            # Thêm User-Agent giả lập trình duyệt để tránh bị chặn chặn
            req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)')
            
            with urllib.request.urlopen(req, timeout=15) as response:
                # Kiểm tra mã trạng thái HTTP (206 là Partial Content - được hỗ trợ resume)
                status = response.status if hasattr(response, 'status') else 200
                
                content_len = int(response.headers.get('content-length', 0))
                if mode == 'ab' and status == 206:
                    total_size = content_len + downloaded
                else:
                    # Nếu server không hỗ trợ resume (không trả về 206) hoặc file mới từ đầu
                    if mode == 'ab' and status != 206:
                        # Server không cho resume, ghi đè lại từ đầu
                        mode = 'wb'
                        downloaded = 0
                    total_size = content_len
                
                chunk_size = 512 * 1024  # 512 KB mỗi chunk
                with open(filename, mode) as f:
                    while True:
                        chunk = response.read(chunk_size)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            percent = min(100, downloaded * 100 / total_size)
                            sys.stdout.write(f"\rĐang tải FFmpeg: {percent:.1f}% ({downloaded / (1024*1024):.1f} MB / {total_size / (1024*1024):.1f} MB)")
                        else:
                            sys.stdout.write(f"\rĐang tải FFmpeg: {downloaded / (1024*1024):.1f} MB")
                        sys.stdout.flush()
            print("\n[FFmpeg] Tải xuống tệp hoàn tất!")
            return True
            
        except urllib.error.HTTPError as e:
            # Nếu gặp lỗi HTTP 416 (Range Not Satisfiable), có thể file cục bộ đã tải xong hoặc bị hỏng, xóa đi tải lại
            if e.code == 416:
                print(f"\n[FFmpeg] Lỗi Range. Xóa tệp tạm và thử tải lại từ đầu...")
                if os.path.exists(filename):
                    os.remove(filename)
            else:
                print(f"\n[FFmpeg] Lỗi HTTP {e.code} ở lần thử {attempt + 1}: {e.reason}")
            time.sleep(3)
        except Exception as e:
            print(f"\n[FFmpeg] Lỗi ở lần thử {attempt + 1}: {e}")
            time.sleep(3)
            
    return False

def setup_ffmpeg():
    if is_ffmpeg_installed():
        print("[FFmpeg] FFmpeg và FFprobe đã được tìm thấy. Bỏ qua tải xuống.")
        return True
    
    # Không tải Windows binaries trên các hệ điều hành khác (như Linux/Render)
    if sys.platform != "win32":
        print("[FFmpeg] Phát hiện hệ điều hành không phải Windows (như Linux/Render).")
        print("[FFmpeg] Bỏ qua tải bản Windows cục bộ. Vui lòng đảm bảo FFmpeg đã được cài đặt trên hệ thống.")
        return False
        
    print("[FFmpeg] Không tìm thấy FFmpeg cục bộ hoặc trong hệ thống.")
    print(f"[FFmpeg] Bắt đầu tải FFmpeg Essentials từ: {FFMPEG_ZIP_URL}")
    
    # Thực hiện tải file có resume
    if not download_file_resilient(FFMPEG_ZIP_URL, ZIP_FILE_NAME):
        print("[FFmpeg] Lỗi tải FFmpeg sau nhiều lần thử lại.")
        return False
        
    try:
        print("[FFmpeg] Bắt đầu giải nén...")
        
        extracted_count = 0
        with zipfile.ZipFile(ZIP_FILE_NAME, 'r') as zip_ref:
            for file_info in zip_ref.infolist():
                filename = os.path.basename(file_info.filename)
                if filename in TARGET_FILES:
                    # Đọc file nhị phân từ zip và lưu trực tiếp ra thư mục hiện tại
                    with zip_ref.open(file_info) as source, open(filename, 'wb') as target:
                        shutil.copyfileobj(source, target)
                    print(f"[FFmpeg] Đã giải nén: {filename}")
                    extracted_count += 1
        
        # Xóa file zip tạm
        if os.path.exists(ZIP_FILE_NAME):
            os.remove(ZIP_FILE_NAME)
            
        if extracted_count == len(TARGET_FILES):
            print("[FFmpeg] Cài đặt FFmpeg hoàn tất thành công!")
            return True
        else:
            print("[FFmpeg] Cảnh báo: Không tìm thấy đầy đủ ffmpeg.exe và ffprobe.exe trong file zip.")
            return False
            
    except Exception as e:
        print(f"\n[FFmpeg] Đã xảy ra lỗi khi giải nén: {e}")
        if os.path.exists(ZIP_FILE_NAME):
            os.remove(ZIP_FILE_NAME)
        return False

if __name__ == "__main__":
    setup_ffmpeg()
