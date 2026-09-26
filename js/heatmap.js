window.SatyaKavach = window.SatyaKavach || {};

window.SatyaKavach.HeatmapRenderer = class HeatmapRenderer {
  constructor(canvas) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
    this.canvas.style.transition = 'opacity 0.3s ease-in-out';
    this.lut = this.generateThermalLUT();
    this.animationFrame = null;
    this.pulsePhase = 0;
  }

  // Always read live dimensions from the canvas element
  get width() { return this.canvas.width; }
  get height() { return this.canvas.height; }

  generateThermalLUT() {
    // 0.0 = #0044ff, 0.25 = #00ddff, 0.5 = #00ff88, 0.75 = #ffcc00, 1.0 = #ff2200
    const lut = new Uint8ClampedArray(256 * 4);
    const stops = [
      { v: 0, r: 0, g: 68, b: 255, a: 0 },
      { v: 64, r: 0, g: 221, b: 255, a: 102 },
      { v: 128, r: 0, g: 255, b: 136, a: 153 },
      { v: 192, r: 255, g: 204, b: 0, a: 204 },
      { v: 255, r: 255, g: 34, b: 0, a: 242 }
    ];

    for (let i = 0; i < 256; i++) {
      let s1 = stops[0], s2 = stops[stops.length - 1];
      for (let j = 0; j < stops.length - 1; j++) {
        if (i >= stops[j].v && i <= stops[j + 1].v) {
          s1 = stops[j];
          s2 = stops[j + 1];
          break;
        }
      }
      const t = (i - s1.v) / (s2.v - s1.v || 1);
      lut[i * 4] = s1.r + t * (s2.r - s1.r);
      lut[i * 4 + 1] = s1.g + t * (s2.g - s1.g);
      lut[i * 4 + 2] = s1.b + t * (s2.b - s1.b);
      lut[i * 4 + 3] = s1.a + t * (s2.a - s1.a);
    }
    return lut;
  }

  renderHeatmap(matrix, matrixWidth, matrixHeight, opacity = 1.0) {
    this.clear();
    this.ctx.globalAlpha = opacity;
    
    const imgData = this.ctx.createImageData(matrixWidth, matrixHeight);
    for (let i = 0; i < matrix.length; i++) {
      const val = Math.max(0, Math.min(255, Math.floor(matrix[i] * 255)));
      imgData.data[i * 4] = this.lut[val * 4];
      imgData.data[i * 4 + 1] = this.lut[val * 4 + 1];
      imgData.data[i * 4 + 2] = this.lut[val * 4 + 2];
      imgData.data[i * 4 + 3] = this.lut[val * 4 + 3];
    }
    
    const tempCanvas = document.createElement('canvas');
    tempCanvas.width = matrixWidth;
    tempCanvas.height = matrixHeight;
    tempCanvas.getContext('2d').putImageData(imgData, 0, 0);
    
    // Scale up using canvas context
    this.ctx.imageSmoothingEnabled = true;
    this.ctx.imageSmoothingQuality = 'high';
    this.ctx.drawImage(tempCanvas, 0, 0, this.width, this.height);
    this.ctx.globalAlpha = 1.0;
  }

  generateMockHeatmap(width, height, faceRegions) {
    const matrix = new Float32Array(width * height);
    for(let y = 0; y < height; y++) {
      for(let x = 0; x < width; x++) {
        let val = Math.random() * 0.15; // Noise
        
        faceRegions.forEach(region => {
          const dx = (x - region.x) / region.radiusX;
          const dy = (y - region.y) / region.radiusY;
          const distSq = dx*dx + dy*dy;
          
          if (distSq < 1.5) {
            let intensity = Math.exp(-distSq * 2.5);
            // Simulate jawline/seam artifacts typical in face swaps
            if (distSq > 0.7 && distSq < 1.2) intensity += 0.5;
            val += intensity * region.intensity;
          }
        });
        matrix[y * width + x] = Math.min(1.0, val);
      }
    }
    return matrix;
  }

  drawBoundingBoxes(boxes) {
    this.ctx.lineWidth = 2;
    this.ctx.font = "12px 'Inter', sans-serif";
    boxes.forEach(box => {
      this.ctx.strokeStyle = box.tampered ? '#ff3366' : '#00e676';
      this.ctx.strokeRect(box.x, box.y, box.w, box.h);
      
      const textWidth = this.ctx.measureText(box.label).width;
      this.ctx.fillStyle = box.tampered ? 'rgba(255, 51, 102, 0.9)' : 'rgba(0, 230, 118, 0.9)';
      this.ctx.fillRect(box.x, box.y - 22, textWidth + 12, 22);
      
      this.ctx.fillStyle = '#fff';
      this.ctx.fillText(box.label, box.x + 6, box.y - 7);
    });
  }

  drawLandmarks(points) {
    this.ctx.fillStyle = '#00d4ff';
    points.forEach(pt => {
      this.ctx.beginPath();
      this.ctx.arc(pt.x, pt.y, 1.5, 0, Math.PI * 2);
      this.ctx.fill();
    });
  }

  clear() {
    this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
  }

  toggle(visible) {
    this.opacity = visible ? 1 : 0;
    this.canvas.style.opacity = this.opacity;
  }

  renderRPPGMask(width, height) {
    const w = width || this.canvas.width;
    const h = height || this.canvas.height;
    const drawPulse = () => {
      this.ctx.clearRect(0, 0, w, h);
      this.pulsePhase += 0.08;
      const intensity = (Math.sin(this.pulsePhase) + 1) / 2 * 0.4 + 0.1;
      
      // Mock skin overlay pulse
      this.ctx.fillStyle = `rgba(0, 255, 136, ${intensity})`;
      this.ctx.beginPath();
      this.ctx.ellipse(w/2, h/2 - 20, w/4, h/3, 0, 0, Math.PI*2);
      this.ctx.fill();
      
      this.animationFrame = requestAnimationFrame(drawPulse);
    };
    drawPulse();
  }
  
  stopRPPGMask() {
    if (this.animationFrame) {
      cancelAnimationFrame(this.animationFrame);
      this.animationFrame = null;
    }
    this.clear();
  }
  
  renderLegend(x, y, w, h) {
    const gradient = this.ctx.createLinearGradient(x, y, x + w, y);
    gradient.addColorStop(0, '#0044ff');
    gradient.addColorStop(0.25, '#00ddff');
    gradient.addColorStop(0.5, '#00ff88');
    gradient.addColorStop(0.75, '#ffcc00');
    gradient.addColorStop(1, '#ff2200');
    
    this.ctx.fillStyle = gradient;
    this.ctx.fillRect(x, y, w, h);
    
    this.ctx.fillStyle = '#e8e8f0';
    this.ctx.font = "10px 'JetBrains Mono', monospace";
    this.ctx.fillText("0.0 (Authentic)", x, y + h + 14);
    this.ctx.textAlign = "right";
    this.ctx.fillText("1.0 (Manipulated)", x + w, y + h + 14);
    this.ctx.textAlign = "left"; // reset
  }
};
