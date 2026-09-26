window.SatyaKavach = window.SatyaKavach || {};

window.SatyaKavach.FrameSlider = class FrameSlider {
  constructor(container, videoElement) {
    this.container = container;
    this.video = videoElement;
    this.duration = 0;
    this.fps = 30;
    this.markers = [];
    this.currentFrame = 0;
    this.totalFrames = 0;
    this.callbacks = [];
    
    this.buildUI();
    this.bindEvents();
  }

  buildUI() {
    this.container.innerHTML = `
      <div class="frame-slider-wrapper" style="display: flex; flex-direction: column; gap: 8px; width: 100%;">
        <div class="slider-controls" style="display: flex; justify-content: space-between; align-items: center; color: #8888aa; font-family: 'JetBrains Mono', monospace; font-size: 12px;">
          <div class="time-display">00:00.00</div>
          <div class="playback-controls">
            <button class="btn-play" style="background: none; border: 1px solid rgba(255,255,255,0.14); color: #e8e8f0; padding: 4px 12px; border-radius: 6px; cursor: pointer;">Play</button>
            <select class="speed-select" style="background: #181830; color: #e8e8f0; border: 1px solid rgba(255,255,255,0.14); border-radius: 4px;">
              <option value="0.25">0.25x</option>
              <option value="0.5">0.5x</option>
              <option value="1" selected>1x</option>
              <option value="2">2x</option>
            </select>
          </div>
          <div class="frame-display">Frame 0 / 0</div>
        </div>
        <div style="position: relative; height: 32px;">
          <canvas class="timeline-canvas" style="position: absolute; top: 0; left: 0; width: 100%; height: 8px; border-radius: 4px;"></canvas>
          <input type="range" class="frame-range" min="0" max="100" value="0" style="position: absolute; top: 0; left: 0; width: 100%; height: 8px; opacity: 0; cursor: pointer;">
          <div class="thumb-indicator" style="position: absolute; top: -4px; left: 0; width: 4px; height: 16px; background: #00d4ff; box-shadow: 0 0 8px #00d4ff; border-radius: 2px; pointer-events: none; transition: left 0.1s linear;"></div>
          <canvas class="markers-canvas" style="position: absolute; top: 12px; left: 0; width: 100%; height: 20px;"></canvas>
        </div>
      </div>
    `;
    
    this.timeDisplay = this.container.querySelector('.time-display');
    this.frameDisplay = this.container.querySelector('.frame-display');
    this.rangeInput = this.container.querySelector('.frame-range');
    this.thumbIndicator = this.container.querySelector('.thumb-indicator');
    this.timelineCanvas = this.container.querySelector('.timeline-canvas');
    this.markersCanvas = this.container.querySelector('.markers-canvas');
    this.playBtn = this.container.querySelector('.btn-play');
    this.speedSelect = this.container.querySelector('.speed-select');
    
    // Resize canvases
    const rect = this.container.getBoundingClientRect();
    this.timelineCanvas.width = rect.width || 800;
    this.markersCanvas.width = rect.width || 800;
  }

  bindEvents() {
    this.rangeInput.addEventListener('input', (e) => {
      this.seekToFrame(parseInt(e.target.value, 10));
    });
    
    document.addEventListener('keydown', (e) => {
      if (e.code === 'Space') {
        e.preventDefault();
        this.togglePlay();
      } else if (e.code === 'ArrowRight') {
        const step = e.shiftKey ? 10 : 1;
        this.seekToFrame(Math.min(this.totalFrames, this.currentFrame + step));
      } else if (e.code === 'ArrowLeft') {
        const step = e.shiftKey ? 10 : 1;
        this.seekToFrame(Math.max(0, this.currentFrame - step));
      }
    });

    this.playBtn.addEventListener('click', () => this.togglePlay());
    this.speedSelect.addEventListener('change', (e) => {
      if (this.video) this.video.playbackRate = parseFloat(e.target.value);
    });

    if (this.video) {
      this.video.addEventListener('timeupdate', () => {
        if (!this.video.paused) {
          const frame = Math.floor(this.video.currentTime * this.fps);
          this.updateState(frame);
        }
      });
    }
  }

  init(duration, fps = 30, timelineMarkers = []) {
    this.duration = duration;
    this.fps = fps;
    this.totalFrames = Math.floor(duration * fps);
    this.markers = timelineMarkers;
    
    this.rangeInput.max = this.totalFrames;
    this.updateState(0);
    
    this.renderTimeline();
    this.renderMarkers();
  }

  renderTimeline() {
    const ctx = this.timelineCanvas.getContext('2d');
    const w = this.timelineCanvas.width;
    const h = this.timelineCanvas.height;
    
    ctx.fillStyle = '#1e1e36';
    ctx.fillRect(0, 0, w, h);
    
    this.markers.forEach(m => {
      const x = (m.timestamp / this.duration) * w;
      const width = Math.max(2, (1 / this.duration) * w * 5); // 5 frames wide
      
      ctx.fillStyle = m.type === 'anomaly' ? '#ff3366' : 
                      m.type === 'suspicious' ? '#ffaa00' : '#00e676';
      ctx.fillRect(x - width/2, 0, width, h);
    });
  }

  renderMarkers() {
    const ctx = this.markersCanvas.getContext('2d');
    const w = this.markersCanvas.width;
    const h = this.markersCanvas.height;
    ctx.clearRect(0, 0, w, h);
    
    ctx.font = "10px 'Inter', sans-serif";
    ctx.textAlign = "center";
    
    this.markers.forEach(m => {
      const x = (m.timestamp / this.duration) * w;
      
      ctx.fillStyle = m.type === 'anomaly' ? '#ff3366' : 
                      m.type === 'suspicious' ? '#ffaa00' : '#00e676';
      
      // Marker dot
      ctx.beginPath();
      ctx.arc(x, 4, 3, 0, Math.PI * 2);
      ctx.fill();
      
      // Label
      ctx.fillStyle = '#8888aa';
      ctx.fillText(m.label, x, 18);
    });
  }

  seekToFrame(frameIndex) {
    this.updateState(frameIndex);
    if (this.video) {
      this.video.currentTime = frameIndex / this.fps;
    }
  }

  seekToTimestamp(seconds) {
    this.seekToFrame(Math.floor(seconds * this.fps));
  }

  updateState(frameIndex) {
    this.currentFrame = frameIndex;
    this.rangeInput.value = frameIndex;
    
    const pct = (frameIndex / this.totalFrames) * 100;
    this.thumbIndicator.style.left = `calc(${pct}% - 2px)`;
    
    this.frameDisplay.textContent = `Frame ${this.currentFrame} / ${this.totalFrames}`;
    
    const time = this.currentFrame / this.fps;
    const mins = Math.floor(time / 60).toString().padStart(2, '0');
    const secs = Math.floor(time % 60).toString().padStart(2, '0');
    const ms = Math.floor((time % 1) * 100).toString().padStart(2, '0');
    this.timeDisplay.textContent = `${mins}:${secs}.${ms}`;
    
    this.callbacks.forEach(cb => cb(this.currentFrame, time));
  }

  onFrameChange(callback) {
    this.callbacks.push(callback);
  }

  togglePlay() {
    if (this.video) {
      if (this.video.paused) {
        this.video.play();
        this.playBtn.textContent = 'Pause';
      } else {
        this.video.pause();
        this.playBtn.textContent = 'Play';
      }
    }
  }
};
