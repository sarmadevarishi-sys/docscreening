window.SatyaKavach = window.SatyaKavach || {};

window.SatyaKavach.WaveformRenderer = class WaveformRenderer {
  constructor() {
    this.audioContext = null;
    this.analyser = null;
    this.buffer = null;
    this.isSyntheticView = false;
  }

  _ensureAudioContext() {
    if (!this.audioContext) {
      this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
      this.analyser = this.audioContext.createAnalyser();
    }
  }

  async loadAudio(fileUrl) {
    // In a real app we'd fetch and decode the audio file.
    // For demo, we just simulate successful loading.
    return new Promise(resolve => setTimeout(resolve, 500));
  }

  renderWaveform(canvas, mockData = null) {
    const ctx = canvas.getContext('2d');
    const w = canvas.width;
    const h = canvas.height;
    ctx.clearRect(0, 0, w, h);
    
    // Grid
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.07)';
    ctx.lineWidth = 1;
    ctx.beginPath();
    for(let i=0; i<h; i+=20) { ctx.moveTo(0, i); ctx.lineTo(w, i); }
    for(let i=0; i<w; i+=50) { ctx.moveTo(i, 0); ctx.lineTo(i, h); }
    ctx.stroke();

    const data = mockData || this.generateMockWaveform(1000, 44100);
    
    ctx.beginPath();
    ctx.strokeStyle = this.isSyntheticView ? '#ff3366' : '#00d4ff';
    ctx.lineWidth = 1.5;
    
    const sliceWidth = w * 1.0 / data.length;
    let x = 0;
    
    for(let i = 0; i < data.length; i++) {
      const v = data[i];
      const y = (v + 1) / 2 * h;
      
      if(i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
      
      x += sliceWidth;
    }
    ctx.stroke();
    
    // Labels
    ctx.fillStyle = '#666680';
    ctx.font = "10px 'JetBrains Mono', monospace";
    ctx.fillText("1.0", 4, 12);
    ctx.fillText("-1.0", 4, h - 4);
  }

  renderSpectrogram(canvas) {
    const ctx = canvas.getContext('2d');
    const w = canvas.width;
    const h = canvas.height;
    const imgData = this.generateMockSpectrogram(w, h);
    ctx.putImageData(imgData, 0, 0);
  }

  highlightSyntheticRegions(canvas, regions) {
    const ctx = canvas.getContext('2d');
    const w = canvas.width;
    const h = canvas.height;
    
    regions.forEach(region => {
      const startX = region.startNorm * w; // startNorm is 0.0 to 1.0
      const widthX = (region.endNorm - region.startNorm) * w;
      
      ctx.fillStyle = 'rgba(255, 51, 102, 0.15)';
      ctx.fillRect(startX, 0, widthX, h);
      
      ctx.strokeStyle = '#ff3366';
      ctx.lineWidth = 2;
      ctx.strokeRect(startX, 0, widthX, h);
      
      // Label
      ctx.fillStyle = '#ff3366';
      ctx.fillRect(startX, 0, ctx.measureText(region.type).width + 16, 20);
      ctx.fillStyle = '#fff';
      ctx.font = "10px 'JetBrains Mono', monospace";
      ctx.fillText(`${region.type.toUpperCase()} (${(region.confidence*100).toFixed(1)}%)`, startX + 8, 14);
    });
  }

  drawPhaseDiscontinuities(canvas, points) {
    const ctx = canvas.getContext('2d');
    const h = canvas.height;
    const w = canvas.width;
    
    ctx.strokeStyle = '#ffaa00';
    ctx.lineWidth = 1;
    ctx.setLineDash([4, 4]);
    
    points.forEach(p => {
      const x = p * w;
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, h);
      ctx.stroke();
    });
    ctx.setLineDash([]);
  }

  generateMockWaveform(length, sampleRate) {
    const data = new Float32Array(length);
    for(let i=0; i<length; i++) {
      // Simulate speech envelope with noise
      const envelope = Math.sin(i / length * Math.PI) * Math.sin(i * 0.05);
      data[i] = envelope * 0.5 + (Math.random() * 0.2 - 0.1);
    }
    return data;
  }

  generateMockSpectrogram(w, h) {
    const imgData = new ImageData(w, h);
    for(let x=0; x<w; x++) {
      for(let y=0; y<h; y++) {
        const i = (y * w + x) * 4;
        const val = Math.random() * 255 * (1 - y/h); // lower freq = higher intensity
        
        // Heatmap colors for spectrogram
        imgData.data[i] = val > 128 ? 255 : 0; // R
        imgData.data[i+1] = val > 64 ? val : 0; // G
        imgData.data[i+2] = val < 128 ? 255-val : 0; // B
        imgData.data[i+3] = 255;
      }
    }
    return imgData;
  }

  renderDualView(waveformCanvas, spectrogramCanvas) {
    this.renderWaveform(waveformCanvas);
    this.renderSpectrogram(spectrogramCanvas);
  }
  
  toggleColorCoding() {
    this.isSyntheticView = !this.isSyntheticView;
  }
};
