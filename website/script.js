// OnyxPad Official Website - Interactive Script

document.addEventListener('DOMContentLoaded', () => {
  initThemeSwitcher();
  initTerminalSimulator();
});

// 1. Theme Gallery Switcher
function initThemeSwitcher() {
  const tabs = document.querySelectorAll('.theme-tab');
  const previewImg = document.getElementById('theme-preview-img');
  const themeNameLbl = document.getElementById('theme-name-lbl');

  const themeImages = {
    'dracula': {
      src: '../docs/screenshots/theme-dracula-default.png',
      name: 'Dracula Dark (Default)'
    },
    'matrix': {
      src: '../docs/screenshots/theme-matrix-green.png',
      name: 'Matrix Cyber Green'
    },
    'monokai': {
      src: '../docs/screenshots/theme-monokai.png',
      name: 'Monokai Pro'
    },
    'nord': {
      src: '../docs/screenshots/theme-nord.png',
      name: 'Nordic Frost'
    },
    'onedark': {
      src: '../docs/screenshots/theme-one-dark.png',
      name: 'Atom One Dark'
    },
    'solarized': {
      src: '../docs/screenshots/theme-solarized-dark.png',
      name: 'Solarized Dark'
    }
  };

  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      tabs.forEach(t => t.classList.remove('active'));
      tab.classList.add('active');

      const themeKey = tab.dataset.theme;
      if (themeImages[themeKey] && previewImg) {
        previewImg.src = themeImages[themeKey].src;
        if (themeNameLbl) {
          themeNameLbl.textContent = themeImages[themeKey].name;
        }
      }
    });
  });
}

// 2. Asciinema Live Terminal Simulator
function initTerminalSimulator() {
  const playBtn = document.getElementById('demo-play-btn');
  const terminalScreen = document.getElementById('terminal-screen');
  const progressBar = document.getElementById('demo-progress');

  if (!playBtn || !terminalScreen) return;

  const lines = [
    '<span style="color: #10b981;">PS C:\\Users\\OnyxPad&gt;</span> agy build --release',
    '<span style="color: #06b6d4;">[Asciinema Worker QThread]</span> Initializing thread pool...',
    '<span style="color: #a855f7;">[PTY Recorder]</span> Record session started (Ctrl+Shift+R)...',
    '<span style="color: #38bdf8;">✓ 162 unit tests passed in 21.8s</span>',
    '<span style="color: #f59e0b;">✓ Saved recording to session.cast (v2 spec)</span>',
    '<span style="color: #10b981;">PS C:\\Users\\OnyxPad&gt;</span> echo "OnyxPad is ready!"',
    'OnyxPad is ready!'
  ];

  let isPlaying = false;
  let currentLine = 0;
  let intervalId = null;

  playBtn.addEventListener('click', () => {
    if (isPlaying) {
      pause();
    } else {
      play();
    }
  });

  function play() {
    isPlaying = true;
    playBtn.innerHTML = '❚❚';
    if (currentLine >= lines.length) {
      currentLine = 0;
      terminalScreen.innerHTML = '';
    }

    intervalId = setInterval(() => {
      if (currentLine < lines.length) {
        terminalScreen.innerHTML += `<div>${lines[currentLine]}</div>`;
        currentLine++;
        const pct = (currentLine / lines.length) * 100;
        if (progressBar) progressBar.style.width = `${pct}%`;
      } else {
        pause();
      }
    }, 800);
  }

  function pause() {
    isPlaying = false;
    playBtn.innerHTML = '▶';
    if (intervalId) clearInterval(intervalId);
  }
}
