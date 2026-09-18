---
name: douyin-scraper-and-translator-fullstack
description: Hệ thống Full-stack tự động cào video Douyin theo thể loại, hiển thị dạng Grid trên UI, chọn hoặc dán link bất kỳ để dịch sang tiếng Việt, lồng tiếng TTS, stream tiến trình % realtime qua SSE, commit Git và mở GitHub Issue.
triggers:
  - build douyin app
  - setup douyin translator
  - run douyin translator fullstack
  - crawl and translate douyin
---

# Douyin Scraper & Video Translation Fullstack Skill

## Vai trò & Nhiệm vụ
Bạn là một Full-stack Media & Automation Agent. Bạn có nhiệm vụ thiết kế, lập trình và vận hành hệ thống gồm:
1. **Scraper Engine:** Thu thập danh sách video Douyin theo danh mục/thể loại (tiêu đề, ảnh bìa thumbnail, URL gốc, ID).
2. **Frontend App:**
   - **Trang Khám phá (Feed Mode):** Hiển thị danh mục thể loại (Ẩm thực, Hài hước, v.v.) và danh sách video dạng lưới (Grid cards).
   - **Trang Dịch thuật (Translate Mode):** Kích hoạt khi bấm vào một video hoặc dán link thủ công. Hiển thị tiến trình % chuyển động mượt qua Server-Sent Events (SSE), nhật ký trạng thái từng bước và trình phát video tiếng Việt sau khi hoàn thành.
3. **Backend API Pipeline:** Điều phối tuần tự các bước: chuẩn hóa URL Douyin, tải video (yt-dlp), tách âm thanh (ffmpeg), nhận diện chữ (whisper), dịch phụ đề, lồng tiếng (edge-tts) và ghép video.
4. **Git & Issue Management:** Tự động commit file phụ đề và mở Issue báo cáo trên GitHub repository.

---

## Nguyên tắc vận hành cốt lõi (Human-in-the-loop & Error Prevention)
1. **Xác nhận từng bước:** Trước khi cài đặt thư viện, tạo/sửa file code, khởi động server hoặc đẩy code lên Git, Agent PHẢI dừng lại hỏi xác nhận của người dùng: *"Tôi chuẩn bị thực hiện [Tên bước]. Bạn có đồng ý tiếp tục không?"*.
2. **Chuẩn hóa link Douyin:** URL đầu vào có thể là dạng copy từ app, link rút gọn `v.douyin.com`, hoặc link web chứa query `jingxuan?modal_id=...`. Backend BẮT BUỘC phải quy đổi tất cả về định dạng chuẩn `https://www.douyin.com/video/<modal_id_hoặc_video_id>` trước khi chuyển qua `yt-dlp` để tránh lỗi Unsupported URL.
3. **An toàn Git:** Không commit file media nhị phân nặng (`.mp4`, `.wav`, `.mp3`). Chỉ commit mã nguồn, cấu hình và file phụ đề (`.srt`).

---

## Bảng trọng số tiến trình Backend (% Stream qua SSE)

| Giai đoạn | Tiến độ | Tác vụ xử lý Backend |
| :--- | :--- | :--- |
| **Stage 1** | `10%` | Phân tích cú pháp, chuyển đổi link về dạng `/video/<id>` & tạo task workspace |
| **Stage 2** | `25%` | Tải video MP4 gốc bằng `yt-dlp` |
| **Stage 3** | `40%` | Trích xuất file âm thanh mono 16kHz `audio_zh.wav` bằng `ffmpeg` |
| **Stage 4** | `60%` | Dùng Whisper phiên âm giọng nói sang phụ đề tiếng Trung `subtitle_zh.srt` |
| **Stage 5** | `75%` | Dịch phụ đề sang tiếng Việt tự nhiên, chuẩn timeline `subtitle_vi.srt` |
| **Stage 6** | `85%` | Tạo audio giọng đọc tiếng Việt `dub_vi.mp3` bằng `edge-tts` |
| **Stage 7** | `95%` | Dùng FFmpeg hạ âm lượng gốc, chèn voice tiếng Việt và burn phụ đề vào `output_vi.mp4` |
| **Stage 8** | `100%` | Commit phụ đề lên Git, mở GitHub Issue và kích hoạt video player trên UI |

---

## Quy trình thực thi chi tiết

### Bước 1: Khởi tạo cấu trúc dự án & Môi trường
* **Hỏi xác nhận:** *"Tôi chuẩn bị tạo khung thư mục dự án và tệp requirements.txt (FastAPI, yt-dlp, whisper, edge-tts, playwright). Bạn có đồng ý bắt đầu không?"*
* **Cấu trúc thư mục:**
  ```text
  ├── backend/
  │   ├── main.py          # FastAPI app, SSE stream & routing
  │   ├── scraper.py       # Module cào danh sách video theo thể loại
  │   ├── pipeline.py      # Pipeline xử lý media từ 0% -> 100%
  │   └── requirements.txt
  ├── frontend/
  │   ├── index.html       # UI chứa thanh thể loại, grid video, progress bar & video player
  │   ├── style.css        # Giao diện responsive tối ưu hiển thị
  │   └── app.js           # Xử lý tương tác tab, gọi API và lắng nghe SSE
  └── workspace/tasks/     # Thư mục chứa dữ liệu tạm và output
Bước 2: Xây dựng Module Scraper (backend/scraper.py)
Hỏi xác nhận: "Tôi chuẩn bị tạo script bóc tách danh sách video Douyin theo thể loại (Ẩm thực, Hài hước...). Bạn có đồng ý không?"

Chức năng:

Nhận tên thể loại hoặc từ khóa.

Sử dụng Playwright hoặc HTTP client lấy danh sách video: Thumbnail, Tiêu đề, Tác giả, và chuẩn hóa link thành https://www.douyin.com/video/<video_id>.

Cache kết quả tạm thời để UI load nhanh.

Bước 3: Xây dựng Backend API & Pipeline (backend/main.py, backend/pipeline.py)
Hỏi xác nhận: "Tôi chuẩn bị viết mã nguồn Backend với các endpoint: /api/feed, /api/translate, /api/progress/{task_id} và /api/video/{task_id}. Tiếp tục nhé?"

Yêu cầu kỹ thuật:

clean_douyin_url(): Tự động tách modal_id từ link jingxuan?modal_id=... thành link video trực tiếp.

Quản lý trạng thái bằng generator hoặc queue để stream trực tiếp sự kiện Server-Sent Events (SSE) theo cấu trúc: data: {"percent": 40, "step": "Đang tách âm thanh tiếng Trung..."}\n\n.

Phục vụ file video hoàn thiện qua endpoint static hoặc streaming response.

Bước 4: Xây dựng Giao diện Frontend (frontend/index.html, frontend/app.js)
Hỏi xác nhận: "Tôi chuẩn bị thiết kế giao diện Frontend gồm thanh danh mục, lưới video card, khung nhập URL trực tiếp và thanh tiến trình %. Bạn có đồng ý không?"

Thành phần giao diện:

Category Bar: Các nút chọn danh mục để lọc video.

Video Grid: Mỗi thẻ hiển thị thumbnail, tên video. Khi nhấp vào thẻ, tự động lấy URL và chuyển sang chế độ dịch.

Direct URL Input: Cho phép dán link Douyin bất kỳ nếu không muốn chọn từ grid.

Progress Container: Thanh tiến trình hiển thị phần trăm trực quan, dòng chữ hiển thị bước hiện tại.

Result Area: Nhúng thẻ <video controls> tự động nạp nguồn khi tiến trình chạm mốc 100%.

Bước 5: Khởi chạy và Kiểm thử
Hỏi xác nhận: "Tôi chuẩn bị chạy server Backend bằng Uvicorn trên cổng 8000 để chạy thử nghiệm. Bạn có muốn bắt đầu không?"

Lệnh shell:

Bash
uvicorn backend.main:app --reload --port 8000
Bước 6: Git Commit & Nghiệm thu GitHub Issue
Hỏi xác nhận: "Video đã chuyển ngữ hoàn tất. Tôi chuẩn bị commit phụ đề tiếng Việt lên Git và tạo Issue nghiệm thu trên GitHub repo <OWNER/REPO>. Bạn có đồng ý không?"

Thực thi:

Commit file .srt qua công cụ shell:

Bash
git add workspace/tasks/<TASK_ID>/*.srt
git commit -m "feat(douyin): complete translation for task <TASK_ID>"
git push origin HEAD
Tạo GitHub Issue thông qua tool mcp-github:

Title: [Completed] Douyin Translation - Task <TASK_ID>

Body: Báo cáo thời gian xử lý, URL nguồn đã chuẩn hóa, đường dẫn file xuất bản và toàn văn nội dung subtitle_vi.srt.