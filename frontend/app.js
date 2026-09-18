// Navbar Tabs
const navTabExplore = document.getElementById('navTabExplore');
const navTabTranslate = document.getElementById('navTabTranslate');
const navProcessBadge = document.getElementById('navProcessBadge');

// Screens
const screenExplore = document.getElementById('screenExplore');
const screenTranslate = document.getElementById('screenTranslate');

// Screen 1: Feed Elements
const videoGrid = document.getElementById('videoGrid');
const catButtons = document.querySelectorAll('.cat-btn');

// Screen 2: Translation Elements
const translateForm = document.getElementById('translateForm');
const douyinUrlInput = document.getElementById('douyinUrlInput');
const voiceSelect = document.getElementById('voiceSelect');
const submitBtn = document.getElementById('submitBtn');
const btnText = submitBtn.querySelector('.btn-text');
const spinner = submitBtn.querySelector('.spinner');

// Video Banner
const selectedVideoBanner = document.getElementById('selectedVideoBanner');
const bannerThumb = document.getElementById('bannerThumb');
const bannerTitle = document.getElementById('bannerTitle');
const bannerUrl = document.getElementById('bannerUrl');

// Progress Elements
const progressSection = document.getElementById('progressSection');
const stepLabel = document.getElementById('stepLabel');
const percentLabel = document.getElementById('percentLabel');
const progressBar = document.getElementById('progressBar');
const logContent = document.getElementById('logContent');
const stageItems = document.querySelectorAll('.stage-item');

// Preview Elements
const previewSection = document.getElementById('previewSection');
const videoPlayer = document.getElementById('videoPlayer');
const downloadBtn = document.getElementById('downloadBtn');
const gitReportText = document.getElementById('gitReportText');
const toggleSubBtn = document.getElementById('toggleSubBtn');
const subContainer = document.getElementById('subContainer');
const subText = document.getElementById('subText');

let currentEventSource = null;
let activeCategory = 'food';

// 1. Chuyển đổi giữa 2 màn hình chính qua Navbar
function switchMainScreen(screen) {
  if (screen === 'explore') {
    navTabExplore.classList.add('active');
    navTabTranslate.classList.remove('active');
    screenExplore.classList.add('active');
    screenTranslate.classList.remove('active');
  } else {
    navTabTranslate.classList.add('active');
    navTabExplore.classList.remove('active');
    screenTranslate.classList.add('active');
    screenExplore.classList.remove('active');
  }
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

// 2. Tải danh sách video từ Backend API
async function loadFeed(category) {
  videoGrid.innerHTML = '<div class="grid-loading">⏳ Đang nạp danh sách video từ Douyin...</div>';
  try {
    const res = await fetch(`/api/feed?category=${encodeURIComponent(category)}`);
    if (!res.ok) throw new Error('Không thể tải danh sách video.');
    const data = await res.json();
    renderGrid(data.videos || []);
  } catch (err) {
    videoGrid.innerHTML = `<div class="grid-loading" style="color: #ef4444;">⚠️ Lỗi: ${err.message}</div>`;
  }
}

// 3. Render danh sách thẻ video ra Grid ở Màn hình 1
function renderGrid(videos) {
  if (!videos || videos.length === 0) {
    videoGrid.innerHTML = '<div class="grid-loading">Không có video nào trong danh mục này.</div>';
    return;
  }

  videoGrid.innerHTML = videos.map(v => `
    <div class="video-card" data-url="${escapeHtml(v.url)}" data-title="${escapeHtml(v.title)}" data-thumb="${escapeHtml(v.thumbnail)}">
      <div class="thumb-box">
        <img class="thumb-img" src="${escapeHtml(v.thumbnail)}" alt="${escapeHtml(v.title)}" loading="lazy" onerror="this.src='https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=400'">
        <span class="badge-dur">${v.duration || '01:00'}</span>
        <span class="badge-hot">🔥 ${escapeHtml(v.hot_info || 'Hot')}</span>
        <div class="play-hint">▶</div>
      </div>
      <div class="card-body">
        <h4 class="card-title-vi" title="${escapeHtml(v.title)}">${escapeHtml(v.title)}</h4>
        <div class="card-title-zh" title="${escapeHtml(v.original_title || '')}">${escapeHtml(v.original_title || '')}</div>
        <div class="card-footer">
          <span class="card-author">${escapeHtml(v.author || '@Douyin')}</span>
          <span class="card-action-btn">Dịch ngay ⚡</span>
        </div>
      </div>
    </div>
  `).join('');

  // Gắn sự kiện click vào thẻ video: Chuyển sang Màn hình 2 & Bắt đầu dịch
  videoGrid.querySelectorAll('.video-card').forEach(card => {
    card.addEventListener('click', () => {
      const url = card.getAttribute('data-url');
      const title = card.getAttribute('data-title');
      const thumb = card.getAttribute('data-thumb');

      // Điền URL vào ô input ở Màn hình 2
      douyinUrlInput.value = url;

      // Cập nhật banner video
      bannerThumb.src = thumb || 'https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=400';
      bannerTitle.textContent = title || 'Video Douyin';
      bannerUrl.textContent = url;
      selectedVideoBanner.style.display = 'block';

      // Chuyển sang MÀN HÌNH 2
      switchMainScreen('translate');

      // Kích hoạt dịch ngay lập tức
      startTranslation(url, voiceSelect.value);
    });
  });
}

function selectCategory(category) {
  activeCategory = category;
  catButtons.forEach(b => {
    b.classList.toggle('active', b.getAttribute('data-category') === category);
  });
  loadFeed(category);
}

function escapeHtml(str) {
  if (!str) return '';
  return str.replace(/[&<>"']/g, m => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;'
  })[m]);
}

// 4. Bắt đầu dịch video & Lắng nghe SSE
async function startTranslation(douyinUrl, voice) {
  if (!douyinUrl || !douyinUrl.trim()) return;

  // Cập nhật trạng thái UI
  submitBtn.disabled = true;
  btnText.textContent = 'Đang xử lý...';
  spinner.style.display = 'inline-block';
  navProcessBadge.style.display = 'inline-block';
  progressSection.style.display = 'block';
  previewSection.style.display = 'none';
  logContent.innerHTML = '';
  setProgress(0, 'Đang gửi yêu cầu khởi tạo task...');

  if (currentEventSource) {
    currentEventSource.close();
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
    appendLog(`Đã khởi tạo Task ID: ${taskId}`);

    // Kết nối SSE
    listenSSE(taskId);

  } catch (err) {
    alert(`Lỗi: ${err.message}`);
    submitBtn.disabled = false;
    btnText.textContent = 'Bắt đầu chuyển ngữ ⚡';
    spinner.style.display = 'none';
    navProcessBadge.style.display = 'none';
  }
}

// 5. Kết nối SSE để theo dõi tiến trình 0% -> 100%
function listenSSE(taskId) {
  currentEventSource = new EventSource(`/api/progress/${taskId}`);

  currentEventSource.onmessage = (e) => {
    try {
      const payload = JSON.parse(e.data);
      const { percent, step, status, data, error } = payload;

      setProgress(percent, step);

      if (status === 'completed') {
        currentEventSource.close();
        submitBtn.disabled = false;
        btnText.textContent = 'Bắt đầu chuyển ngữ ⚡';
        spinner.style.display = 'none';
        navProcessBadge.style.display = 'none';

        // Hiển thị khung thành phẩm video
        const videoUrl = data && data.video_url ? data.video_url : `/api/video/${taskId}`;
        videoPlayer.src = videoUrl;
        downloadBtn.href = videoUrl;
        previewSection.style.display = 'block';

        // Ghi nội dung phụ đề
        if (data && data.srt_content) {
          subText.textContent = data.srt_content;
        }

        // Báo cáo Git / GitHub Issue
        if (data && data.git_report) {
          const report = data.git_report;
          if (report.issue_url) {
            gitReportText.innerHTML = `Đã tự động tạo Issue nghiệm thu: <a href="${report.issue_url}" target="_blank" style="color: #60a5fa; text-decoration: underline;">Xem Issue trên GitHub ↗</a>`;
          } else if (report.git_committed) {
            gitReportText.textContent = 'Đã tự động commit file phụ đề .srt vào Git repository.';
          } else {
            gitReportText.textContent = report.notes.join(' | ') || 'Hoàn tất quy trình xử lý.';
          }
        }

        videoPlayer.load();
        videoPlayer.play().catch(() => {});
        appendLog('🎉 Pipeline hoàn tất 100%! Video đã sẵn sàng phát.');
        previewSection.scrollIntoView({ behavior: 'smooth' });
      }

      if (status === 'failed') {
        currentEventSource.close();
        submitBtn.disabled = false;
        btnText.textContent = 'Bắt đầu chuyển ngữ ⚡';
        spinner.style.display = 'none';
        navProcessBadge.style.display = 'none';
        appendLog(`❌ Thất bại: ${error || step}`);
        alert(`Quá trình xử lý thất bại: ${error || step}`);
      }
    } catch (err) {
      console.error('Lỗi parse SSE:', err);
    }
  };

  currentEventSource.onerror = (err) => {
    console.warn('Đóng kết nối SSE.', err);
  };
}

function setProgress(percent, step) {
  progressBar.style.width = `${percent}%`;
  percentLabel.textContent = `${percent}%`;
  stepLabel.textContent = step;

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

  appendLog(`${step} (${percent}%)`);
}

function appendLog(message) {
  const time = new Date().toLocaleTimeString();
  const line = document.createElement('div');
  line.textContent = `[${time}] ${message}`;
  logContent.appendChild(line);
  logContent.scrollTop = logContent.scrollHeight;
}

function toggleSubtitle() {
  if (subContainer.style.display === 'none') {
    subContainer.style.display = 'block';
    toggleSubBtn.textContent = 'Ẩn nội dung phụ đề ▲';
  } else {
    subContainer.style.display = 'none';
    toggleSubBtn.textContent = '📝 Xem nội dung phụ đề tiếng Việt (.srt)';
  }
}

// Form Submit Event ở Màn hình 2
translateForm.addEventListener('submit', (e) => {
  e.preventDefault();
  const url = douyinUrlInput.value.trim();
  const voice = voiceSelect.value;
  
  bannerThumb.src = 'https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=400';
  bannerTitle.textContent = 'Video tùy chỉnh';
  bannerUrl.textContent = url;
  selectedVideoBanner.style.display = 'block';

  startTranslation(url, voice);
});

// Khởi chạy khi tải trang
document.addEventListener('DOMContentLoaded', () => {
  loadFeed('food');
});
