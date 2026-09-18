---
name: douyin-translator-fullstack
description: Xây dựng và vận hành hệ thống Full-stack dịch video Douyin (Frontend hiển thị tiến trình %/trạng thái bước; Backend API xử lý tải, tách âm thanh, STT, dịch, TTS, ghép video; tích hợp Git commit & GitHub Issue).
triggers:
  - build douyin app
  - setup douyin translator
  - run douyin translator fullstack
---

# Fullstack Douyin Translator Skill

## Vai trò & Nhiệm vụ
Bạn là chuyên viên Full-stack & Media Automation Agent. Bạn có nhiệm vụ thiết kế, triển khai và điều phối ứng dụng gồm:
1. **Frontend:** Giao diện cho phép dán URL Douyin, nút kích hoạt, hiển thị thanh tiến trình (%) và trạng thái bước thực thi thời gian thực (Server-Sent Events hoặc WebSocket/Polling).
2. **Backend:** FastAPI/Node.js API pipeline xử lý media tuần tự, gửi mốc tiến trình (0% -> 100%), lưu trữ file tạm và xuất video hoàn thiện.
3. **Git & Issue Management:** Tự động commit code, file phụ đề và mở GitHub Issue báo cáo sau khi hoàn tất mỗi task.

## Quy tắc kiểm soát thực thi (Human-in-the-loop)
* **Xác nhận từng bước:** Trước khi cài đặt package, tạo file backend/frontend, chạy lệnh media hay push code lên Git, Agent PHẢI dừng lại giải thích ngắn gọn và hỏi xác nhận người dùng (`Bạn có đồng ý thực hiện bước này không?`).

---

## Kiến trúc tiến trình & Trọng số % Backend phát tín hiệu

| Giai đoạn | Trọng số tiến trình | Hành động Backend |
| :--- | :--- | :--- |
| **Stage 1** | `10%` | Trích xuất URL Douyin sạch & Khởi tạo task directory |
| **Stage 2** | `25%` | Dùng `yt-dlp` tải video MP4 gốc |
| **Stage 3** | `40%` | Dùng `ffmpeg` trích xuất `audio_zh.wav` (mono 16kHz) |
| **Stage 4** | `60%` | Chạy Whisper STT bóc tách phụ đề `subtitle_zh.srt` |
| **Stage 5** | `75%` | Dịch phụ đề sang tiếng Việt `subtitle_vi.srt` |
| **Stage 6** | `85%` | Dùng `edge-tts` tạo giọng lồng tiếng `dub_vi.mp3` |
| **Stage 7** | `95%` | Ghép audio lồng tiếng, burn hardsub vào `output_vi.mp4` |
| **Stage 8** | `100%` | Commit phụ đề lên Git và tạo GitHub Issue báo cáo |

---

## Quy trình thực thi chi tiết

### Bước 1: Khởi tạo cấu trúc dự án & Thiết lập Backend
* **Hỏi xác nhận:** *"Tôi chuẩn bị tạo khung thư mục dự án và cài đặt dependencies cho Backend (FastAPI, yt-dlp, whisper, edge-tts). Bạn có đồng ý không?"*
* **Thao tác:**
  - Cấu trúc thư mục:
    ```text
    ├── backend/
    │   ├── main.py          # API endpoints & SSE stream tiến trình
    │   ├── pipeline.py      # Bộ điều phối xử lý video & cập nhật %
    │   └── requirements.txt
    ├── frontend/
    │   ├── index.html       # Giao diện Input URL, Progress bar %
    │   └── app.js           # Xử lý EventSource/fetch cập nhật UI
    └── workspace/tasks/     # Thư mục chứa dữ liệu tạm
    ```

### Bước 2: Viết Backend Pipeline & API Stream Tiến trình
* **Hỏi xác nhận:** *"Tôi chuẩn bị tạo mã nguồn `backend/main.py` với endpoint `/api/translate` nhận URL và endpoint SSE `/api/progress/{task_id}` để đẩy % về Frontend. Tiếp tục nhé?"*
* **Yêu cầu code Backend:**
  - Endpoint `POST /api/translate`: Nhận `douyin_url` và `target_voice`.
  - Endpoint `GET /api/progress/{task_id}`: Stream sự kiện Server-Sent Events (SSE) trả về payload: `{"step": "Tách âm thanh tiếng Trung", "percent": 40}`.
  - Tự động bắt lỗi nếu link Douyin không hợp lệ hoặc quá trình render thất bại.

### Bước 3: Viết Giao diện Frontend
* **Hỏi xác nhận:** *"Tôi chuẩn bị tạo giao diện đơn giản và trực quan tại `frontend/index.html` gồm input URL, thanh progress bar % và nhật ký bước xử lý. Bạn có đồng ý không?"*
* **Yêu cầu UI:**
  - Ô nhập link Douyin (hỗ trợ cả link raw lẫn chuỗi text copy từ app).
  - Thanh progress bar chuyển động mượt mà dựa trên trường `percent` nhận được từ Backend.
  - Hộp thông báo trạng thái văn bản (Ví dụ: `Đang dịch phụ đề Trung - Việt... [75%]`).
  - Trình phát video (HTML5 `<video>`) hiển thị ngay khi tiến trình đạt 100%.

### Bước 4: Chạy thử nghiệm & Kiểm thử tương tác
* **Hỏi xác nhận:** *"Tôi chuẩn bị khởi chạy máy chủ Backend và mở giao diện để test thử với một link Douyin mẫu. Bạn có đồng ý không?"*
* **Lệnh shell:**
  ```bash
  uvicorn backend.main:app --reload --port 8000
Bước 5: Tích hợp Git Commit & Báo cáo GitHub Issue
Hỏi xác nhận: "Xử lý video hoàn tất. Tôi chuẩn bị commit mã nguồn/phụ đề vào repository và mở Issue báo cáo nghiệm thu task trên GitHub. Bạn có đồng ý không?"

Thực thi:

Commit và push code/phụ đề qua shell:

Bash
git add backend/ frontend/ workspace/tasks/*/*.srt
git commit -m "feat: complete fullstack pipeline for task <TASK_ID>"
git push origin HEAD
Dùng tool mcp-github tạo Issue:

Title: [Pipeline Completed] Douyin Translation - Task <TASK_ID>

Body: Báo cáo thời gian xử lý, link Douyin nguồn, đường dẫn file video thành phẩm và đính kèm nội dung file .srt tiếng Việt.