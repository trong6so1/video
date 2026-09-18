# 🎬 Douyin Scraper & Video Translator Fullstack

Hệ thống Full-stack tự động khám phá và cào video Douyin theo thể loại (Ẩm thực, Hài hước), bóc tách âm thanh, nhận diện phụ đề tiếng Trung, dịch thuật sang tiếng Việt, lồng tiếng AI đồng bộ khẩu hình và nhúng phụ đề vào video thành phẩm. Tích hợp stream tiến trình realtime qua Server-Sent Events (SSE), tự động Git commit file `.srt` và mở GitHub Issue báo cáo.

---

## 🚀 Tính năng nổi bật

1. **Khám phá video Douyin theo thể loại (Feed Explorer):**
   - Hỗ trợ xem danh mục video mẫu theo chủ đề: **Ẩm thực (美食)** và **Hài hước (搞笑)**.
   - Thẻ video hiển thị Thumbnail sắc nét, thời lượng, tiêu đề và tác giả.
   - Chỉ cần 1-click vào thẻ video là có thể kích hoạt quy trình dịch ngay lập tức.
2. **Chuẩn hóa URL Douyin đa năng:**
   - Xử lý mượt mà tất cả các dạng liên kết: link chia sẻ từ app, link rút gọn `v.douyin.com`, link `jingxuan?modal_id=...` sang định dạng chuẩn `https://www.douyin.com/video/<id>`.
3. **Pipeline xử lý đa phương tiện 8 giai đoạn (% SSE Realtime):**
   - Stream tiến trình trực quan từ `0%` đến `100%` về UI.
   - Trích xuất âm thanh mono 16kHz qua FFmpeg.
   - Nhận diện giọng nói STT tiếng Trung bằng Faster-Whisper.
   - Dịch thuật phụ đề ngữ nghĩa tiếng Việt chuẩn.
   - Tạo audio lồng tiếng Việt AI tự nhiên bằng Edge-TTS / gTTS.
   - Hòa âm giảm nhạc nền gốc và burn phụ đề vào video MP4 thành phẩm.
4. **Tự động hóa Git & Báo cáo GitHub Issue:**
   - Tự động lưu và commit file `subtitle_vi.srt` vào repo Git.
   - Tự động mở Issue báo cáo tiến độ và toàn văn phụ đề trên GitHub.

---

## 🛠️ Hướng dẫn cài đặt & Cấu hình

### 1. Cài đặt các gói phụ thuộc Python

```bash
pip install -r backend/requirements.txt
```

*(Yêu cầu hệ thống đã cài đặt sẵn công cụ `ffmpeg` và `git`)*

---

### 2. Cấu hình biến môi trường (`.env`)

Sao chép tệp mẫu `.env.example` thành `.env`:

```bash
cp .env.example .env
```

Nội dung cấu hình trong tệp `.env`:

| Biến môi trường | Ý nghĩa | Ví dụ giá trị |
| :--- | :--- | :--- |
| `GITHUB_REPO` | Tên repository trên GitHub để mở Issue báo cáo | `username/repository-name` |
| `GITHUB_TOKEN` | GitHub Personal Access Token có quyền ghi Issue | `ghp_xxxxxxxxxxxxxxxxxxxx` |
| `TARGET_VOICE` | Giọng đọc lồng tiếng mặc định (Edge-TTS) | `vi-VN-HoaiMyNeural` hoặc `vi-VN-NamMinhNeural` |
| `PORT` | Cổng dịch vụ Backend API | `8000` |

---

### 3. Hướng dẫn lấy GitHub Token & Cấu hình Repo

Để kích hoạt tính năng tự động tạo Issue báo cáo nghiệm thu sau khi hoàn thành dịch video:

1. **Lấy GitHub Personal Access Token (PAT):**
   - Truy cập GitHub: [https://github.com/settings/tokens](https://github.com/settings/tokens) (hoặc vào *Settings -> Developer settings -> Personal access tokens -> Tokens (classic)*).
   - Chọn **Generate new token (classic)**.
   - Đặt tên Note (ví dụ: `Douyin-Translator-App`).
   - Tích chọn quyền (Scope):
     - `repo` (Bao gồm full control: commit code, tạo và quản lý Issues).
   - Bấm **Generate token** và sao chép mã token bắt đầu bằng `ghp_...`.

2. **Điền vào file `.env`:**
   ```env
   GITHUB_REPO=your-github-username/your-repo-name
   GITHUB_TOKEN=ghp_yourGeneratedTokenHere
   TARGET_VOICE=vi-VN-HoaiMyNeural
   PORT=8000
   ```

*(Nếu chưa điền token, hệ thống vẫn thực hiện dịch video bình thường và ghi chú lại trong nhật ký).*

---

## 🖥️ Khởi chạy hệ thống

Khởi động Backend API Server (FastAPI + Uvicorn):

```bash
uvicorn backend.main:app --reload --port 8000
```

Truy cập giao diện Web trên trình duyệt:
👉 **[http://localhost:8000](http://localhost:8000)**

---

## 📁 Cấu trúc thư mục dự án

```text
├── backend/
│   ├── main.py             # FastAPI App, SSE routing & feed endpoint
│   ├── scraper.py          # Module cào danh sách video Douyin theo thể loại
│   ├── pipeline.py         # Pipeline xử lý đa phương tiện 8 giai đoạn & Git/Issue
│   └── requirements.txt    # Danh sách thư viện Python cần thiết
├── frontend/
│   ├── index.html          # Giao diện chính (Category bar, Grid, Form, Progress, Player)
│   ├── style.css           # Bảng phong cách hiện đại (Dark/Modern theme)
│   └── app.js              # Tương tác giao diện, gọi API feed và lắng nghe SSE
├── workspace/tasks/        # Thư mục lưu trữ tác vụ, video gốc, audio, sub và output
├── .env.example            # Tệp biến môi trường mẫu
├── .env                    # Tệp cấu hình biến môi trường cục bộ
└── README.md               # Tài liệu hướng dẫn sử dụng chi tiết
```

---

## 📊 Bảng tiến trình xử lý (% SSE Stream)

| Giai đoạn | Tiến độ | Tác vụ xử lý Backend |
| :---: | :---: | :--- |
| **Stage 1** | `10%` | Trích xuất URL Douyin sạch (`/video/<id>`) & khởi tạo task |
| **Stage 2** | `25%` | Tải video MP4 gốc bằng direct API / `yt-dlp` |
| **Stage 3** | `40%` | Trích xuất file âm thanh mono 16kHz `audio_zh.wav` qua FFmpeg |
| **Stage 4** | `60%` | Chạy Whisper STT bóc tách phụ đề tiếng Trung `subtitle_zh.srt` |
| **Stage 5** | `75%` | Dịch phụ đề sang tiếng Việt tự nhiên `subtitle_vi.srt` |
| **Stage 6** | `85%` | Tạo audio giọng đọc tiếng Việt `dub_vi.mp3` bằng TTS |
| **Stage 7** | `95%` | Hòa âm giọng đọc tiếng Việt và burn phụ đề vào `output_vi.mp4` |
| **Stage 8** | `100%` | Commit phụ đề lên Git, mở GitHub Issue và phát video trên UI |
