const setupPanel = document.getElementById('setup-panel');
const hudPanel = document.getElementById('hud-panel');
const scriptInput = document.getElementById('script-input');
const speedSlider = document.getElementById('speed-slider');
const speedLabel = document.getElementById('speed-label');
const fontSlider = document.getElementById('font-slider');
const fontLabel = document.getElementById('font-label');
const btnVoiceToggle = document.getElementById('btn-voice-toggle');
const btnStart = document.getElementById('btn-start');

const scriptDisplay = document.getElementById('script-display');
const hudProgress = document.getElementById('hud-progress');
const hudWpm = document.getElementById('hud-wpm');
const btnPlayPause = document.getElementById('btn-play-pause');
const btnSlower = document.getElementById('btn-slower');
const btnFaster = document.getElementById('btn-faster');
const btnExit = document.getElementById('btn-exit');
const voiceIndicator = document.getElementById('voice-indicator');

let scrollPos = 0;
let isPlaying = false;
let animFrame = null;
let lastTimestamp = null;
let speed = 40;
let voiceSyncEnabled = false;
let recognition = null;
let wordCount = 0;
let sessionStartTime = null;
let wordsSpoken = 0;

// ── Setup controls ──

speedSlider.addEventListener('input', () => {
  speed = parseInt(speedSlider.value);
  speedLabel.textContent = speed;
});

fontSlider.addEventListener('input', () => {
  const size = fontSlider.value;
  fontLabel.textContent = size + 'px';
  if (scriptDisplay) scriptDisplay.style.fontSize = size + 'px';
});

btnVoiceToggle.addEventListener('click', () => {
  voiceSyncEnabled = !voiceSyncEnabled;
  btnVoiceToggle.textContent = voiceSyncEnabled ? 'ON' : 'OFF';
  btnVoiceToggle.className = 'toggle-btn ' + (voiceSyncEnabled ? 'on' : 'off');
});

btnStart.addEventListener('click', startPresentation);

// ── Presentation ──

function buildScript(text) {
  scriptDisplay.innerHTML = '';
  const paras = text.split(/\n+/).filter(p => p.trim());
  wordCount = paras.join(' ').split(/\s+/).length;
  paras.forEach(para => {
    const p = document.createElement('p');
    p.textContent = para;
    scriptDisplay.appendChild(p);
  });
  scriptDisplay.style.fontSize = fontSlider.value + 'px';
}

function startPresentation() {
  const text = scriptInput.value.trim();
  if (!text) return;

  buildScript(text);
  scrollPos = 0;
  scriptDisplay.style.transform = 'translateY(0px)';
  setupPanel.classList.add('hidden');
  hudPanel.classList.remove('hidden');

  isPlaying = true;
  sessionStartTime = Date.now();
  btnPlayPause.textContent = '⏸ Pause';

  if (voiceSyncEnabled) startVoiceSync();
  requestAnimationFrame(scrollLoop);
}

function scrollLoop(timestamp) {
  if (!isPlaying) {
    lastTimestamp = null;
    return;
  }

  if (lastTimestamp !== null) {
    const delta = (timestamp - lastTimestamp) / 1000;
    scrollPos += speed * delta;
    const maxScroll = scriptDisplay.scrollHeight;
    if (scrollPos >= maxScroll) {
      scrollPos = maxScroll;
      isPlaying = false;
      btnPlayPause.textContent = '▶ Done';
    }
    scriptDisplay.style.transform = `translateY(-${scrollPos}px)`;
    updateProgress();
    highlightActiveParagraph();
  }

  lastTimestamp = timestamp;
  animFrame = requestAnimationFrame(scrollLoop);
}

function updateProgress() {
  const max = scriptDisplay.scrollHeight;
  const pct = Math.min(100, Math.round((scrollPos / max) * 100));
  hudProgress.textContent = pct + '%';

  if (sessionStartTime && wordsSpoken > 0) {
    const mins = (Date.now() - sessionStartTime) / 60000;
    hudWpm.textContent = Math.round(wordsSpoken / mins) + ' WPM';
  }
}

function highlightActiveParagraph() {
  const paras = scriptDisplay.querySelectorAll('p');
  const viewportMid = scrollPos + window.innerHeight / 2;

  paras.forEach(p => {
    const top = p.offsetTop;
    const bottom = top + p.offsetHeight;
    if (viewportMid >= top && viewportMid < bottom) {
      p.className = 'active-para';
    } else if (p.offsetTop + p.offsetHeight < viewportMid) {
      p.className = 'past-para';
    } else {
      p.className = '';
    }
  });
}

// ── HUD controls ──

btnPlayPause.addEventListener('click', () => {
  if (!isPlaying) {
    isPlaying = true;
    btnPlayPause.textContent = '⏸ Pause';
    requestAnimationFrame(scrollLoop);
  } else {
    isPlaying = false;
    btnPlayPause.textContent = '▶ Resume';
    cancelAnimationFrame(animFrame);
  }
});

btnSlower.addEventListener('click', () => {
  speed = Math.max(10, speed - 10);
  speedSlider.value = speed;
  speedLabel.textContent = speed;
});

btnFaster.addEventListener('click', () => {
  speed = Math.min(120, speed + 10);
  speedSlider.value = speed;
  speedLabel.textContent = speed;
});

btnExit.addEventListener('click', () => {
  isPlaying = false;
  cancelAnimationFrame(animFrame);
  stopVoiceSync();
  hudPanel.classList.add('hidden');
  setupPanel.classList.remove('hidden');
  scrollPos = 0;
});

// ── Voice Sync ──

function startVoiceSync() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) return;

  recognition = new SpeechRecognition();
  recognition.continuous = true;
  recognition.interimResults = true;
  recognition.lang = 'en-US';

  let lastWordCount = 0;

  recognition.onresult = (e) => {
    let interim = '';
    for (let i = e.resultIndex; i < e.results.length; i++) {
      if (e.results[i].isFinal) {
        const words = e.results[i][0].transcript.trim().split(/\s+/).length;
        wordsSpoken += words;
        const ratio = wordsSpoken / wordCount;
        const targetScroll = ratio * scriptDisplay.scrollHeight;
        const diff = targetScroll - scrollPos;
        // Gently nudge speed toward where the speaker is
        if (Math.abs(diff) > 50) {
          speed = Math.max(10, Math.min(120, speed + Math.sign(diff) * 5));
        }
      }
    }
  };

  recognition.onerror = () => {};
  recognition.start();
  voiceIndicator.classList.remove('hidden');
}

function stopVoiceSync() {
  if (recognition) {
    recognition.stop();
    recognition = null;
  }
  voiceIndicator.classList.add('hidden');
}

// ── Keyboard shortcuts ──

document.addEventListener('keydown', (e) => {
  if (hudPanel.classList.contains('hidden')) return;
  if (e.code === 'Space') {
    e.preventDefault();
    btnPlayPause.click();
  } else if (e.code === 'ArrowUp') {
    btnSlower.click();
  } else if (e.code === 'ArrowDown') {
    btnFaster.click();
  } else if (e.code === 'Escape') {
    btnExit.click();
  }
});
