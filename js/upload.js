window.SatyaKavach = window.SatyaKavach || {};

window.SatyaKavach.UploadManager = (function() {
  const Utils = window.SatyaKavach.Utils;

  class UploadManager {
    constructor(dropZoneSelector, options = {}) {
      this.dropZone = Utils.$(dropZoneSelector);
      this.options = options;
      this.callbacks = {
        'file-selected': [],
        'analysis-start': [],
        'analysis-progress': [],
        'analysis-complete': []
      };
      
      this.init();
    }

    init() {
      if (!this.dropZone) return;
      
      this.dropZone.addEventListener('dragenter', this.handleDragEnter.bind(this));
      this.dropZone.addEventListener('dragover', this.handleDragOver.bind(this));
      this.dropZone.addEventListener('dragleave', this.handleDragLeave.bind(this));
      this.dropZone.addEventListener('drop', this.handleDrop.bind(this));
      
      const fileInput = Utils.$('#file-upload-input');
      if (fileInput) {
        fileInput.addEventListener('change', (e) => {
          if (e.target.files.length > 0) {
            this.processFile(e.target.files[0]);
          }
        });
      }
    }

    on(event, callback) {
      if (this.callbacks[event]) {
        this.callbacks[event].push(callback);
      }
    }

    emit(event, data) {
      if (this.callbacks[event]) {
        this.callbacks[event].forEach(cb => cb(data));
      }
    }

    handleDragEnter(e) {
      e.preventDefault();
      e.stopPropagation();
      this.dropZone.classList.add('drag-active');
    }

    handleDragOver(e) {
      e.preventDefault();
      e.stopPropagation();
      this.dropZone.classList.add('drag-active');
    }

    handleDragLeave(e) {
      e.preventDefault();
      e.stopPropagation();
      if (!this.dropZone.contains(e.relatedTarget)) {
        this.dropZone.classList.remove('drag-active');
      }
    }

    handleDrop(e) {
      e.preventDefault();
      e.stopPropagation();
      this.dropZone.classList.remove('drag-active');
      
      if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
        this.processFile(e.dataTransfer.files[0]);
      } else {
        const text = e.dataTransfer.getData('text');
        if (text && text.startsWith('http')) {
          this.processUrl(text);
        }
      }
    }

    async processFile(file) {
      window._lastUploadedDocFile = file;
      this.emit('file-selected', { file });
      const typeInfo = Utils.detectFileType(file);
      
      if (typeInfo.type === 'unknown') {
        alert("Unsupported file type");
        return;
      }
      
      this.emit('analysis-start', { file, type: typeInfo.type });
      
      let result;
      const progressCb = (stage, percent) => {
        this.emit('analysis-progress', { stage, percent });
      };

      try {
        if (typeInfo.type === 'image') {
          result = await window.SatyaKavach.MockAnalyzer.analyzeImage(file, progressCb);
        } else if (typeInfo.type === 'video') {
          result = await window.SatyaKavach.MockAnalyzer.analyzeVideo(file, progressCb);
        } else if (typeInfo.type === 'audio') {
          result = await window.SatyaKavach.MockAnalyzer.analyzeAudio(file, progressCb);
        }
        this.emit('analysis-complete', { result });
      } catch (err) {
        console.error("Analysis failed", err);
      }
    }

    async processUrl(url) {
      const platform = Utils.detectPlatform(url);
      this.emit('analysis-start', { url, type: 'url', platform });
      
      const progressCb = (stage, percent) => {
        this.emit('analysis-progress', { stage, percent });
      };

      try {
        const result = await window.SatyaKavach.MockAnalyzer.analyzeUrl(url, progressCb);
        this.emit('analysis-complete', { result });
      } catch (err) {
        console.error("Analysis failed", err);
      }
    }
  }

  return UploadManager;
})();
