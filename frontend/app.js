const form = document.getElementById('translateForm');
const douyinUrlInput = document.getElementById('douyinUrl');
const voiceSelect = document.getElementById('voiceSelect');
const submitBtn = document.getElementById('submitBtn');
const btnText = submitBtn.querySelector('.btn-text');
const spinner = submitBtn.querySelector('.spinner');

const progressSection = document.getElementById('progressSection');
const stepLabel = document.getElementById('stepLabel');
const percentLabel = document.getElementById('percentLabel');
const progressBar = document.getElementById('progressBar');
const logContent = document.getElementById('logContent');
const stageItems = document.querySelectorAll('.stage-item');

const previewSection = document.getElementById('previewSection');
const videoPlayer = document.getElementById('videoPlayer');
const downloadBtn = document.getElementById('downloadBtn');

let eventSource = null;

function appendLog(message) {
  const time = new Date().toLocaleTimeString();
  const line = document.createElement('div');
  line.textContent = `[${time}] ${message}`;
  logContent.appendChild(line);
  logContent.scrollTop = logContent.scrollHeight;
}

function updateStageItems(percent) {
  stageItems.forEach(item => {
    const stage = parseInt(item.getAttribute('data-stage'), 10);
    if (percent >= stage) {
      item.classList.add('completed');
      item.classList.remove('active');
    } else if (percent > stage - 15 && percent < stage) {
      item.classList.add('active');
      item.classList.remove('completed');
    } else {
      item.classList.remove('active', 'completed');
    }
  });
}

function setProgress(percent, step) {
  progressBar.style.width = `${percent}%`;
  percentLabel.textContent = `${percent}%`;
  stepLabel.textContent = step;
  updateStageItems(percent);
  appendLog(`${step} (${percent}%)`);
}

form.addEventListener('submit', async (e) => {
  e.preventDefault();
  
  const douyinUrl = douyinUrlInput.value.trim();
  const voice = voiceSelect.value;
  if (!douyinUrl) return;

  // Reset UI
  submitBtn.disabled = true;
  btnText.textContent = 'Đang xử lý...';
  spinner.style.display = 'inline-block';
  progressSection.style.display = 'block';
  previewSection.style.display = 'none';
  logContent.innerHTML = '';
  setProgress(0, 'Đang gửi yêu cầu...');

  if (eventSource) {
    eventSource.close();
  }

  try {
    const res = await fetch('/api/translate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        douyin_url: douyinUrl,
        target_voice: voice
      })
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Không thể tạo task.');
    }

    const data = await res.json();
    const taskId = data.task_id;
    appendLog(`Đã tạo task ID: ${taskId}`);

    // Kết nối SSE để nhận tiến trình thực tế
    connectSSE(taskId);

  } catch (err) {
    alert(`Lỗi: ${err.message}`);
    submitBtn.disabled = false;
    btnText.textContent = 'Bắt đầu chuyển ngữ';
    spinner.style.display = 'none';
  }
});

function connectSSE(taskId) {
  eventSource = new EventSource(`/api/progress/${taskId}`);

  eventSource.onmessage = (e) => {
    try {
      const payload = JSON.parse(e.data);
      const { percent, step, status, data, error } = payload;

      setProgress(percent, step);

      if (status === 'completed') {
        eventSource.close();
        submitBtn.disabled = false;
        btnText.textContent = 'Bắt đầu chuyển ngữ';
        spinner.style.display = 'none';

        // Hiển thị khung xem trước video
        const videoUrl = data && data.video_url ? data.video_url : `/api/video/${taskId}`;
        videoPlayer.src = videoUrl;
        downloadBtn.href = videoUrl;
        previewSection.style.display = 'block';
        videoPlayer.load();
        videoPlayer.play().catch(() => {});
        appendLog('✅ Video hoàn thành! Bạn có thể xem trước hoặc tải về.');
      }

      if (status === 'failed') {
        eventSource.close();
        submitBtn.disabled = false;
        btnText.textContent = 'Bắt đầu chuyển ngữ';
        spinner.style.display = 'none';
        appendLog(`❌ Thất bại: ${error || step}`);
        alert(`Quá trình xử lý bị lỗi: ${error || step}`);
      }
    } catch (err) {
      console.error('Lỗi parse SSE event:', err);
    }
  };

  eventSource.onerror = (err) => {
    console.warn('Mất kết nối SSE hoặc pipeline đã đóng.', err);
  };
}
