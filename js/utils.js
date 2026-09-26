window.SatyaKavach = window.SatyaKavach || {};

window.SatyaKavach.Utils = (function() {
  const $ = selector => document.querySelector(selector);
  const $$ = selector => document.querySelectorAll(selector);

  function createElement(tag, classes = [], attrs = {}) {
    const el = document.createElement(tag);
    if (typeof classes === 'string') classes = classes.split(' ').filter(Boolean);
    if (classes.length) el.classList.add(...classes);
    for (const [key, value] of Object.entries(attrs)) {
      if (key.startsWith('data-')) {
        el.setAttribute(key, value);
      } else {
        el[key] = value;
      }
    }
    return el;
  }

  function formatPercent(value, decimals = 1) {
    return Number(value).toFixed(decimals) + '%';
  }

  function formatConfidence(value) {
    if (value >= 85) return { label: 'HIGH', color: '#ff3366', class: 'confidence-high' };
    if (value >= 50) return { label: 'MEDIUM', color: '#ffaa00', class: 'confidence-medium' };
    return { label: 'LOW', color: '#00e676', class: 'confidence-low' };
  }

  function randomInRange(min, max) {
    return Math.random() * (max - min) + min;
  }

  function randomInt(min, max) {
    return Math.floor(randomInRange(min, max + 1));
  }

  function delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  function debounce(fn, ms) {
    let timer;
    return function(...args) {
      clearTimeout(timer);
      timer = setTimeout(() => fn.apply(this, args), ms);
    };
  }

  function throttle(fn, ms) {
    let lastTime = 0;
    return function(...args) {
      const now = Date.now();
      if (now - lastTime >= ms) {
        lastTime = now;
        fn.apply(this, args);
      }
    };
  }

  function animateValue(el, start, end, duration) {
    if (!el) return;
    const range = end - start;
    let current = start;
    const increment = end > start ? 1 : -1;
    const stepTime = Math.abs(Math.floor(duration / range));
    if (stepTime === 0) { el.textContent = end; return; }
    const timer = setInterval(function() {
      current += increment;
      el.textContent = current;
      if (current === end) {
        clearInterval(timer);
      }
    }, stepTime);
  }

  function generateId() {
    return Math.random().toString(36).substring(2, 9);
  }

  function detectFileType(file) {
    const type = file.type;
    if (type.startsWith('image/')) return { type: 'image', format: type.split('/')[1] };
    if (type.startsWith('video/')) return { type: 'video', format: type.split('/')[1] };
    if (type.startsWith('audio/')) return { type: 'audio', format: type.split('/')[1] };
    return { type: 'unknown', format: '' };
  }

  function detectPlatform(url) {
    if (url.includes('youtube.com') || url.includes('youtu.be')) return 'YouTube';
    if (url.includes('twitter.com') || url.includes('x.com')) return 'Twitter';
    if (url.includes('tiktok.com')) return 'TikTok';
    if (url.includes('instagram.com')) return 'Instagram';
    return 'Unknown';
  }

  function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  }

  function formatDuration(seconds) {
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m}:${s < 10 ? '0' : ''}${s}`;
  }

  function clamp(value, min, max) {
    return Math.min(Math.max(value, min), max);
  }

  function lerp(a, b, t) {
    return a + (b - a) * clamp(t, 0, 1);
  }

  function hexToRgba(hex, alpha = 1) {
    const r = parseInt(hex.slice(1, 3), 16);
    const g = parseInt(hex.slice(3, 5), 16);
    const b = parseInt(hex.slice(5, 7), 16);
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
  }

  return {
    $, $$, createElement, formatPercent, formatConfidence,
    randomInRange, randomInt, delay, debounce, throttle,
    animateValue, generateId, detectFileType, detectPlatform,
    formatFileSize, formatDuration, clamp, lerp, hexToRgba
  };
})();
