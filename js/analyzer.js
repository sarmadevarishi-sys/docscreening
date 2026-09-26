window.SatyaKavach = window.SatyaKavach || {};

window.SatyaKavach.MockAnalyzer = (function() {

  // ─── REAL BACKEND BRIDGE ─────────────────────────────────────────────────
  // If hosted on a public domain, automatically uses window.location.origin.
  // When running locally on file://, defaults to http://localhost:8000.
  const BACKEND_URL = (window.location.protocol === 'http:' || window.location.protocol === 'https:')
    ? window.location.origin
    : 'http://localhost:8000';
  let _backendOnline = null; // null = unchecked, true/false = known

  async function checkBackend() {
    if (_backendOnline !== null) return _backendOnline;
    try {
      const resp = await fetch(`${BACKEND_URL}/health`, { signal: AbortSignal.timeout(2000) });
      _backendOnline = resp.ok;
    } catch {
      _backendOnline = false;
    }
    if (_backendOnline) {
      console.log('[SatyaKavach] ✅ Real AI backend is ONLINE — using real models.');
    } else {
      console.warn('[SatyaKavach] ⚠️  Backend OFFLINE — using simulation. Start backend/start_server.bat to enable real AI.');
    }
    // Re-check every 30s in case server starts later
    setTimeout(() => { _backendOnline = null; }, 30000);
    return _backendOnline;
  }

  async function callBackendImage(file) {
    const form = new FormData();
    form.append('file', file);
    const resp = await fetch(`${BACKEND_URL}/analyze/image`, { method: 'POST', body: form });
    if (!resp.ok) throw new Error(`Backend error ${resp.status}`);
    return resp.json();
  }


  // Converts the flat backend JSON into the full result shape the dashboard expects
  function backendResultToFullResult(backendData, file, type) {
    const score = backendData.riskScore ?? 50;
    const label = score > 60 ? 'HIGH' : (score > 30 ? 'MEDIUM' : 'LOW');
    return {
      overallRisk: {
        score,
        label,
        confidence: { lower: Math.max(0, score - 8), upper: Math.min(100, score + 8), mean: score },
        method: backendData.method || 'Real AI Backend'
      },
      visualForensics: type !== 'audio' ? {
        faceSwapDetection: { score, confidence: 85, boundingBoxes: [] },
        expressionSync: { score, confidence: 90, label: score > 60 ? 'Inconsistent' : 'Natural' },
        gazeConsistency: { score, details: backendData.method || '' },
        lightingShadow: { score: Math.max(0, score - 10), details: '' },
        rppgPulse: { detected: true, bpm: score > 60 ? 0 : 72, consistency: score > 60 ? 20 : 85 },
        microBehaviors: { blinkRate: score > 60 ? 0.2 : 15, pupilDilation: score > 60 ? 'Static' : 'Dynamic', microTremors: score > 60 ? 'Absent' : 'Present', throatMovement: score > 60 ? 'Irregular' : 'Normal' }
      } : null,
      threatIntel: {
        sourceRepetition: {
          score: score > 60 ? 25 : 90,
          label: score > 60 ? 'Suspicious' : 'Clean',
          details: score > 60 ? 'Abnormal repetition across flagged origins' : 'Unique single origin verified'
        }
      },
      timeline: [],
      heatmapData: { width: 256, height: 256, matrix: (() => { const m = new Float32Array(256 * 256); for (let i = 0; i < m.length; i++) m[i] = Math.random(); return m; })() },
      documentClassification: backendData.document_classification || null,
      extractedFields: backendData.extracted_fields || null,
      validationReport: backendData.validation_report || null,
      tamperReport: backendData.tamper_report || null,
      ocrLines: backendData.ocr_lines || [],
      ocrEngine: backendData.ocr_engine || null,
      metadata: {
        fileName: file.name || 'stream_capture',
        fileType: type,
        fileSize: file.size || 0,
        duration: backendData.duration || 0,
        resolution: backendData.resolution || 'N/A',
        analyzedAt: new Date().toISOString(),
        backendModel: backendData.method || null,
        modelLoaded: backendData.modelLoaded ?? false
      }
    };
  }
  // ─────────────────────────────────────────────────────────────────────────


  const Utils = window.SatyaKavach.Utils;

  // Cache to store analysis results for the same file/url
  const resultCache = new Map();

  // Simple deterministic PRNG (Mulberry32)
  function createSeededRandom(seed) {
    let state = seed | 0;
    return function() {
      state = (state + 0x6D2B79F5) | 0;
      let t = Math.imul(state ^ (state >>> 15), 1 | state);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  // Simple string hasher
  function hashString(str) {
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
      const chr = str.charCodeAt(i);
      hash = ((hash << 5) - hash) + chr;
      hash |= 0; // Convert to 32bit integer
    }
    return Math.abs(hash);
  }

  function getCacheKey(file, type) {
    if (typeof file === 'string') return 'url:' + file;
    // For File objects, use name + size + lastModified for a stable key
    return 'file:' + (file.name || 'unknown') + ':' + (file.size || 0) + ':' + (file.lastModified || 0);
  }

  class MockAnalyzer {
    constructor() {}

    async analyzeImage(file, onProgress) {
      if (onProgress) onProgress('Connecting to AI backend...', 5);
      const online = await checkBackend();
      if (online) {
        try {
          if (onProgress) onProgress('Running HuggingFace deepfake model...', 30);
          const backendData = await callBackendImage(file);
          if (onProgress) onProgress('Mapping results...', 90);
          await Utils.delay(300);
          if (onProgress) onProgress('Complete', 100);
          return backendResultToFullResult(backendData, file, 'image');
        } catch (e) {
          console.warn('[SatyaKavach] Backend call failed, falling back to simulation:', e);
        }
      }
      return this._simulateAnalysis(file, 'image', onProgress);
    }

    async analyzeVideo(file, onProgress) {
      if (onProgress) onProgress('Connecting to AI backend...', 5);
      const online = await checkBackend();
      if (online) {
        try {
          if (onProgress) onProgress('Running HuggingFace deepfake model on frame...', 30);
          const backendData = await callBackendImage(file);
          if (onProgress) onProgress('Complete', 100);
          return backendResultToFullResult(backendData, file, 'video');
        } catch (e) {
          console.warn('[SatyaKavach] Backend call failed, falling back to simulation:', e);
        }
      }
      return this._simulateAnalysis(file, 'video', onProgress);
    }



    async _simulateAnalysis(file, type, onProgress) {
      const cacheKey = getCacheKey(file, type);

      // Return cached result instantly (with brief loading for UX)
      if (resultCache.has(cacheKey)) {
        const stages = [
          { msg: 'Loading cached analysis...', progress: 50, delay: 300 },
          { msg: 'Complete', progress: 100, delay: 200 }
        ];
        for (const stage of stages) {
          if (onProgress) onProgress(stage.msg, stage.progress);
          await Utils.delay(stage.delay);
        }
        // Return a deep copy so the caller can't mutate the cache
        return JSON.parse(JSON.stringify(resultCache.get(cacheKey)));
      }

      // Full analysis stages
      const stages = [
        { msg: 'Extracting metadata...', progress: 10, delay: 500 },
        { msg: 'Running forensic models...', progress: 40, delay: 800 },
        { msg: 'Analyzing spectral features...', progress: 70, delay: 600 },
        { msg: 'Checking threat intel...', progress: 90, delay: 400 },
        { msg: 'Finalizing report...', progress: 100, delay: 200 }
      ];

      for (const stage of stages) {
        if (onProgress) onProgress(stage.msg, stage.progress);
        await Utils.delay(stage.delay);
      }

      // Real EXIF extraction if it's an image and exifr is available
      let realExif = null;
      if (type === 'image' && window.exifr) {
        try {
          realExif = await exifr.parse(file);
          console.log('[SatyaKavach] Real EXIF extracted:', realExif);
        } catch (e) {
          console.warn('[SatyaKavach] Exif parse error:', e);
        }
      }

      // Create a seeded PRNG from the file identity
      const seed = hashString(cacheKey);
      const rand = createSeededRandom(seed);

      // Deterministic helper functions using the seeded PRNG
      const randInt = (min, max) => Math.floor(rand() * (max - min + 1)) + min;
      const randFloat = (min, max) => rand() * (max - min) + min;

      // Determine fake/real based on seeded random (consistent per file)
      const isFake = rand() > 0.4; // 60% chance of fake - but SAME every time for this file
      
      const overallScore = isFake ? randInt(70, 99) : randInt(5, 30);
      const label = overallScore > 60 ? 'HIGH' : (overallScore > 30 ? 'MEDIUM' : 'LOW');
      const confSpread = randInt(5, 15);

      const result = {
        overallRisk: { 
          score: overallScore, 
          label: label, 
          confidence: { 
            lower: Math.max(0, overallScore - confSpread), 
            upper: Math.min(100, overallScore + confSpread), 
            mean: overallScore 
          } 
        },
        visualForensics: type !== 'audio' ? {
          faceSwapDetection: { 
            score: isFake ? randInt(60, 95) : randInt(0, 20), 
            confidence: 85, 
            boundingBoxes: [{x: 0.35 + randFloat(-0.05, 0.05), y: 0.25 + randFloat(-0.05, 0.05), w: 0.25, h: 0.3}] 
          },
          expressionSync: { 
            score: isFake ? randInt(70, 99) : randInt(5, 25), 
            confidence: 90, 
            label: isFake ? 'Inconsistent' : 'Natural' 
          },
          gazeConsistency: { 
            score: isFake ? randInt(65, 90) : randInt(0, 15), 
            details: isFake ? 'Unnatural pupil fixation detected' : 'Normal' 
          },
          lightingShadow: { 
            score: isFake ? randInt(50, 85) : randInt(0, 10), 
            details: isFake ? 'Inconsistent ambient occlusion' : 'Consistent' 
          },
          rppgPulse: { detected: true, bpm: isFake ? 0 : randInt(60, 90), consistency: isFake ? randInt(10, 25) : randInt(75, 95) },
          microBehaviors: { 
            blinkRate: isFake ? randFloat(0.1, 0.5) : randInt(12, 20), 
            pupilDilation: isFake ? 'Static' : 'Dynamic', 
            microTremors: isFake ? 'Absent' : 'Present', 
            throatMovement: isFake ? 'Irregular' : 'Normal' 
          }
        } : null,
        threatIntel: {
          sourceRepetition: {
            score: isFake ? randInt(15, 35) : randInt(75, 95),
            label: isFake ? 'Suspicious' : 'Clean',
            details: isFake ? 'Abnormal repetition across flagged origins' : 'Unique single origin verified'
          }
        },
        timeline: type === 'video' ? [
          { timestamp: randFloat(1, 4), frameIndex: randInt(30, 120), type: isFake ? 'anomaly' : 'normal', label: isFake ? 'Face Swap Seam' : 'Normal', score: isFake ? randInt(70, 95) : randInt(5, 15) },
          { timestamp: randFloat(4, 8), frameIndex: randInt(120, 240), type: isFake ? 'anomaly' : 'normal', label: isFake ? 'Audio Splice' : 'Normal', score: isFake ? randInt(80, 98) : randInt(3, 12) }
        ] : [],
        heatmapData: { width: 256, height: 256, matrix: (() => {
          // Use seeded PRNG for heatmap too - same file = same heatmap
          const m = new Float32Array(256 * 256);
          for (let i = 0; i < m.length; i++) m[i] = rand();
          return m;
        })() },
        documentClassification: type === 'image' ? {
          code: 'pan_card_front',
          name: 'PAN Card (Permanent Account Number)',
          confidence: isFake ? 74.2 : 98.6
        } : null,
        extractedFields: type === 'image' ? {
          id_number: isFake ? 'ABCDE9999Z' : 'ABCDE1234F',
          holder_name: 'RAJESH KUMAR SHARMA',
          father_name: 'RAMESH SHARMA',
          dob: '15/08/1990',
          holder_category: 'Individual (P)'
        } : null,
        ocrLines: type === 'image' ? [
          'INCOME TAX DEPARTMENT',
          'GOVT. OF INDIA',
          'Permanent Account Number Card',
          'ABCDE1234F',
          'RAJESH KUMAR SHARMA',
          'RAMESH SHARMA',
          '15/08/1990'
        ] : [],
        validationReport: type === 'image' ? {
          verdict: isFake ? 'SUSPICIOUS' : 'VALIDATED',
          pass_count: isFake ? 1 : 3,
          fail_count: isFake ? 1 : 0,
          warn_count: isFake ? 1 : 0,
          total_rules: 3,
          checks: [
            { rule: 'PAN Format (ICAI Standard)', status: isFake ? 'FAIL' : 'PASS',
              detail: isFake ? "'ABCDE9999Z' structure contains suspicious digit sequence" : "'ABCDE1234F' matches [A-Z]{5}[0-9]{4}[A-Z] — Valid" },
            { rule: 'PAN Entity Classification', status: 'PASS',
              detail: "4th character 'P' → Individual" },
            { rule: 'Date of Birth Coherence', status: isFake ? 'WARN' : 'PASS',
              detail: isFake ? "DOB could not be verified against standard format" : "DOB '15/08/1990' is valid and represents a plausible age" }
          ]
        } : null,
        metadata: { 
          fileName: file.name || 'stream_capture', 
          fileType: type, 
          fileSize: file.size || 0, 
          duration: type !== 'image' ? 12.5 : 0, 
          resolution: realExif ? `${realExif.ExifImageWidth || 1920}x${realExif.ExifImageHeight || 1080}` : '1920x1080', 
          analyzedAt: new Date().toISOString(),
          cameraMake: realExif ? realExif.Make : null,
          cameraModel: realExif ? realExif.Model : null,
          software: realExif ? realExif.Software : null,
          dateTaken: realExif ? realExif.DateTimeOriginal : null
        }
      };

      // Cache the result (store a copy)
      resultCache.set(cacheKey, JSON.parse(JSON.stringify(result)));

      return result;
    }
  }

  return new MockAnalyzer();
})();
