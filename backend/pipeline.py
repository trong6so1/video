import os
import re
import asyncio
import subprocess
import uuid
import datetime
import urllib.parse
from pathlib import Path
from typing import Callable, Awaitable, Optional
import requests
from faster_whisper import WhisperModel
from deep_translator import GoogleTranslator
import edge_tts

ProgressCallback = Callable[[str, int, Optional[dict]], Awaitable[None]]

def extract_douyin_url(raw_text: str) -> str:
    """Trích xuất và chuẩn hóa link URL Douyin (bao gồm cả dạng jingxuan?modal_id= và shortlink)."""
    url_match = re.search(r'(https?://[^\s]+)', raw_text)
    if not url_match:
        raise ValueError("Không tìm thấy đường dẫn hợp lệ trong chuỗi nhập vào.")
    url = url_match.group(1).rstrip('/')
    
    # Chuẩn hóa nếu là URL chứa modal_id (VD: https://www.douyin.com/jingxuan?modal_id=7674948813861211430)
    parsed = urllib.parse.urlparse(url)
    qs = urllib.parse.parse_qs(parsed.query)
    modal_id = qs.get("modal_id", [None])[0]
    if modal_id:
        return f"https://www.douyin.com/video/{modal_id}"
        
    return url

def download_douyin_video(url: str, output_path: str):
    """Tải video Douyin bằng cách lấy dynamic ttwid và gọi API aweme/detail, fallback qua yt-dlp."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        "Referer": "https://www.douyin.com/",
        "Accept": "application/json, text/plain, */*",
    }
    
    # 1. Trích xuất aweme_id
    video_id = None
    parsed = urllib.parse.urlparse(url)
    id_match = re.search(r'/video/(\d+)', parsed.path)
    if id_match:
        video_id = id_match.group(1)
    else:
        # Nếu là link rút gọn hoặc dạng khác, resolve redirect
        try:
            r = requests.get(url, headers=headers, allow_redirects=True, timeout=10)
            id_match = re.search(r'/video/(\d+)', r.url)
            if id_match:
                video_id = id_match.group(1)
        except Exception:
            pass

    # 2. Thử tải trực tiếp qua aweme API với dynamic ttwid cookie
    if video_id:
        try:
            session = requests.Session()
            session.get("https://live.douyin.com/", headers=headers, timeout=10)
            ttwid = session.cookies.get("ttwid")
            cookies = {"ttwid": ttwid} if ttwid else {}
            
            api_url = f"https://www.douyin.com/aweme/v1/web/aweme/detail/?aweme_id={video_id}&device_platform=webapp&aid=6383&channel=channel_pc_web"
            res = session.get(api_url, headers=headers, cookies=cookies, timeout=10)
            if res.status_code == 200 and res.text:
                data = res.json()
                item = data.get("aweme_detail")
                if item:
                    play_urls = item.get("video", {}).get("play_addr", {}).get("url_list", [])
                    if play_urls:
                        # Tải video stream
                        stream_res = requests.get(play_urls[0], headers=headers, stream=True, timeout=30)
                        if stream_res.status_code == 200:
                            with open(output_path, "wb") as f:
                                for chunk in stream_res.iter_content(chunk_size=1024 * 1024):
                                    if chunk:
                                        f.write(chunk)
                            return
        except Exception as e:
            print(f"Fallback sang yt-dlp vì lỗi tải trực tiếp: {e}")

    # 3. Fallback dùng yt-dlp
    ytdlp_cmd = [
        "yt-dlp",
        url,
        "-o", output_path,
        "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "--merge-output-format", "mp4",
        "--no-playlist",
        "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    ]
    res = subprocess.run(ytdlp_cmd, capture_output=True, text=True)
    if res.returncode != 0 and not Path(output_path).exists():
        raise RuntimeError(f"Tải video thất bại: {res.stderr[:400]}")

def format_timestamp(seconds: float) -> str:
    """Chuyển đổi giây sang định dạng thời gian SRT HH:MM:SS,mmm."""
    td = datetime.timedelta(seconds=seconds)
    total_seconds = int(td.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60
    millis = int((seconds - int(seconds)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

def write_srt(segments: list, output_path: str):
    """Ghi danh sách segments ra file SRT chuẩn."""
    with open(output_path, "w", encoding="utf-8") as f:
        for idx, seg in enumerate(segments, start=1):
            start = format_timestamp(seg["start"])
            end = format_timestamp(seg["end"])
            text = seg["text"].strip()
            f.write(f"{idx}\n{start} --> {end}\n{text}\n\n")

async def run_pipeline(task_id: str, raw_input: str, voice: str, report_progress: ProgressCallback):
    task_dir = Path("workspace/tasks") / task_id
    task_dir.mkdir(parents=True, exist_ok=True)
    
    # Stage 1: 10% - Trích xuất URL Douyin sạch & Khởi tạo task directory
    await report_progress("Trích xuất URL Douyin sạch & Khởi tạo task directory", 10, None)
    clean_url = extract_douyin_url(raw_input)
    
    # Stage 2: 25% - Dùng yt-dlp tải video MP4 gốc (kèm fallback direct API)
    await report_progress("Tải video Douyin gốc", 25, {"clean_url": clean_url})
    raw_video_path = task_dir / "raw_video.mp4"
    
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, download_douyin_video, clean_url, str(raw_video_path))

    if not raw_video_path.exists():
        # Kiểm tra nếu tên file có dạng khác
        mp4_files = list(task_dir.glob("*.mp4"))
        if mp4_files:
            raw_video_path = mp4_files[0]
        else:
            raise RuntimeError("Không tìm thấy file video sau khi tải về.")

    # Stage 3: 40% - Dùng ffmpeg trích xuất audio_zh.wav (mono 16kHz)
    await report_progress("Tách âm thanh tiếng Trung (mono 16kHz)", 40, None)
    audio_zh_path = task_dir / "audio_zh.wav"
    ffmpeg_extract = [
        "ffmpeg", "-y",
        "-i", str(raw_video_path),
        "-vn",
        "-ac", "1",
        "-ar", "16000",
        str(audio_zh_path)
    ]
    process = await asyncio.create_subprocess_exec(
        *ffmpeg_extract,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    await process.communicate()
    if process.returncode != 0 or not audio_zh_path.exists():
        raise RuntimeError("Trích xuất audio thất bại.")

    # Stage 4: 60% - Chạy Whisper STT bóc tách phụ đề subtitle_zh.srt
    await report_progress("Chạy Whisper STT bóc tách phụ đề tiếng Trung", 60, None)
    
    def transcribe():
        model = WhisperModel("small", device="cpu", compute_type="int8")
        segments_raw, _ = model.transcribe(str(audio_zh_path), language="zh", vad_filter=True)
        seg_list = []
        for s in segments_raw:
            seg_list.append({
                "start": s.start,
                "end": s.end,
                "text": s.text.strip()
            })
        return seg_list

    loop = asyncio.get_event_loop()
    segments_zh = await loop.run_in_executor(None, transcribe)
    
    # Trường hợp không nhận diện được lời nói (ví dụ video chỉ có nhạc nền)
    if not segments_zh:
        segments_zh = [{"start": 0.0, "end": 2.0, "text": "大家好"}]

    subtitle_zh_path = task_dir / "subtitle_zh.srt"
    write_srt(segments_zh, str(subtitle_zh_path))

    # Stage 5: 75% - Dịch phụ đề sang tiếng Việt subtitle_vi.srt
    await report_progress("Dịch phụ đề sang tiếng Việt", 75, None)
    
    def translate_texts():
        segments_vi = []
        texts_to_translate = [seg["text"] for seg in segments_zh]
        
        # Dùng Google Translate API clients5 kết hợp fallback MyMemory
        translated_results = []
        for i in range(0, len(texts_to_translate), 20):
            chunk = texts_to_translate[i:i+20]
            combined = "\n===\n".join(chunk)
            chunk_translated = None
            try:
                url = "https://clients5.google.com/translate_a/t"
                params = {"client": "dict-chrome-ex", "sl": "zh-CN", "tl": "vi", "q": combined}
                r = requests.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
                if r.status_code == 200:
                    data = r.json()
                    res_str = data[0] if isinstance(data, list) else str(data)
                    parts = res_str.split("\n===\n")
                    if len(parts) == len(chunk):
                        chunk_translated = [p.strip() for p in parts]
            except Exception as e:
                print(f"Batch translate error: {e}")

            if not chunk_translated:
                # Fallback dịch từng câu
                chunk_translated = []
                for c in chunk:
                    if not c.strip():
                        chunk_translated.append("")
                        continue
                    trans_item = None
                    # Thử clients5
                    try:
                        r = requests.get("https://clients5.google.com/translate_a/t",
                                         params={"client": "dict-chrome-ex", "sl": "zh-CN", "tl": "vi", "q": c},
                                         headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
                        if r.status_code == 200:
                            data = r.json()
                            trans_item = data[0] if isinstance(data, list) else str(data)
                    except Exception:
                        pass
                    
                    # Thử MyMemory nếu vẫn chưa có
                    if not trans_item:
                        try:
                            from deep_translator import MyMemoryTranslator
                            m = MyMemoryTranslator(source="zh-CN", target="vi-VN")
                            trans_item = m.translate(c)
                        except Exception:
                            trans_item = c
                    
                    chunk_translated.append(trans_item or c)

            translated_results.extend(chunk_translated)

        for seg, trans_text in zip(segments_zh, translated_results):
            segments_vi.append({
                "start": seg["start"],
                "end": seg["end"],
                "text": trans_text or ""
            })
        return segments_vi

    loop = asyncio.get_event_loop()
    segments_vi = await loop.run_in_executor(None, translate_texts)
    subtitle_vi_path = task_dir / "subtitle_vi.srt"
    write_srt(segments_vi, str(subtitle_vi_path))

    # Stage 6: 85% - Dùng edge-tts tạo giọng lồng tiếng dub_vi.mp3
    await report_progress("Dùng Edge-TTS tạo giọng lồng tiếng tiếng Việt", 85, None)
    full_vi_text = " ".join([seg["text"] for seg in segments_vi if seg["text"]])
    if not full_vi_text.strip():
        full_vi_text = "Video không có phụ đề."

    dub_vi_path = task_dir / "dub_vi.mp3"
    selected_voice = voice if voice and "NamMinh" in voice else "vi-VN-NamMinhNeural"
    
    # Chia nhỏ văn bản thành các đoạn tối đa 600 ký tự để tránh lỗi websocket timeout của Edge-TTS
    words = full_vi_text.split()
    chunks = []
    current_chunk = []
    current_len = 0
    for w in words:
        if current_len + len(w) + 1 > 600:
            chunks.append(" ".join(current_chunk))
            current_chunk = [w]
            current_len = len(w)
        else:
            current_chunk.append(w)
            current_len += len(w) + 1
    if current_chunk:
        chunks.append(" ".join(current_chunk))

    # Tạo file audio cho từng chunk và nối lại bằng ffmpeg concat
    chunk_files = []
    for idx, chunk in enumerate(chunks):
        c_path = task_dir / f"chunk_{idx}.mp3"
        try:
            communicate = edge_tts.Communicate(chunk, selected_voice)
            await communicate.save(str(c_path))
            if c_path.exists() and c_path.stat().st_size > 0:
                chunk_files.append(c_path)
        except Exception as e:
            print(f"Error generating chunk {idx}: {e}")

    if not chunk_files:
        raise RuntimeError("Không thể tạo giọng đọc lồng tiếng qua Edge-TTS.")

    if len(chunk_files) == 1:
        chunk_files[0].rename(dub_vi_path)
    else:
        # Nối các file mp3
        concat_list = task_dir / "concat.txt"
        with open(concat_list, "w", encoding="utf-8") as f:
            for cf in chunk_files:
                f.write(f"file '{cf.name}'\n")
        ffmpeg_concat = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", str(concat_list),
            "-c", "copy",
            str(dub_vi_path)
        ]
        proc = await asyncio.create_subprocess_exec(*ffmpeg_concat)
        await proc.communicate()

    # Stage 7: 95% - Ghép audio lồng tiếng, burn hardsub vào output_vi.mp4
    await report_progress("Ghép audio lồng tiếng và nhúng phụ đề vào video", 95, None)
    output_vi_path = task_dir / "output_vi.mp4"
    
    # Burn hardsub và hòa âm: giảm nhẹ âm nền và lồng tiếng việt
    # Chuẩn hóa đường dẫn SRT để tránh escape issue với ffmpeg subtitles filter
    srt_escaped = str(subtitle_vi_path).replace("\\", "/").replace(":", "\\:")
    
    ffmpeg_merge = [
        "ffmpeg", "-y",
        "-i", str(raw_video_path),
        "-i", str(dub_vi_path),
        "-filter_complex",
        f"[0:v]subtitles='{srt_escaped}':force_style='FontSize=20,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1'[v];"
        f"[0:a]volume=0.2[a0];[1:a]volume=1.2[a1];[a0][a1]amix=inputs=2:duration=first[a]",
        "-map", "[v]",
        "-map", "[a]",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-c:a", "aac",
        "-shortest",
        str(output_vi_path)
    ]
    
    process = await asyncio.create_subprocess_exec(
        *ffmpeg_merge,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()
    
    # Fallback nếu burn subtitle filter gặp lỗi phông/filter
    if process.returncode != 0 or not output_vi_path.exists():
        ffmpeg_merge_simple = [
            "ffmpeg", "-y",
            "-i", str(raw_video_path),
            "-i", str(dub_vi_path),
            "-filter_complex", "[0:a]volume=0.2[a0];[1:a]volume=1.2[a1];[a0][a1]amix=inputs=2:duration=first[a]",
            "-map", "0:v",
            "-map", "[a]",
            "-c:v", "copy",
            "-c:a", "aac",
            "-shortest",
            str(output_vi_path)
        ]
        process_simple = await asyncio.create_subprocess_exec(
            *ffmpeg_merge_simple,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await process_simple.communicate()

    if not output_vi_path.exists():
        raise RuntimeError("Ghép video thành phẩm thất bại.")

    # Stage 8: 100% - Hoàn tất xử lý
    srt_content = subtitle_vi_path.read_text(encoding="utf-8")
    await report_progress("Hoàn tất quy trình dịch và lồng tiếng video", 100, {
        "video_url": f"/api/video/{task_id}",
        "srt_content": srt_content,
        "clean_url": clean_url
    })
