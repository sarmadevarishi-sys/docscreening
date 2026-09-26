window.SatyaKavach = window.SatyaKavach || {};

window.SatyaKavach.Dashboard = (function() {
  const Utils = window.SatyaKavach.Utils;

  class Dashboard {
    constructor(containerSelector) {
      this.container = Utils.$(containerSelector);
    }

    render(analysisResult) {
      if (!this.container) return;
      this.container.innerHTML = '';
      
      const r = analysisResult;
      
      // Header & Overall Risk
      const header = Utils.createElement('div', 'dashboard-header');
      const scoreDiv = Utils.createElement('div', 'risk-score-container');
      const conf = Utils.formatConfidence(r.overallRisk.score);
      scoreDiv.innerHTML = `
        <h2 class="section-title">Forensic Risk Assessment</h2>
        <div class="score-display">
          <div class="score-number ${conf.class}" id="risk-score-num">0</div>
          <div class="score-label ${conf.class}">${conf.label} RISK</div>
        </div>
        <div class="confidence-bar-container">
          <div class="confidence-track">
            <div class="confidence-range" style="left: ${r.overallRisk.confidence.lower}%; width: ${r.overallRisk.confidence.upper - r.overallRisk.confidence.lower}%"></div>
            <div class="confidence-pin" style="left: ${r.overallRisk.confidence.mean}%"></div>
          </div>
          <div class="confidence-labels">
            <span>0</span>
            <span>Confidence Interval</span>
            <span>100</span>
          </div>
        </div>
      `;
      header.appendChild(scoreDiv);
      this.container.appendChild(header);

      Utils.animateValue(scoreDiv.querySelector('#risk-score-num'), 0, r.overallRisk.score, 1000);

      // Dedicated Document Screening & OCR Extraction Card (Module 1)
      if (r.documentClassification) {
        this.container.appendChild(this._createDocumentSection(r));
      }

      // Document Standard & Rule Validation Card (Module 2)
      if (r.validationReport) {
        this.container.appendChild(this._createValidationSection(r.validationReport));
      }

      // Module 4: Biometric Verification Booth (Person vs Document Matching)
      this.container.appendChild(this._createBiometricSection(r));

      // Sections mapping
      const sectionsMap = [
        { title: 'File Metadata', key: 'metadata' },
        { title: 'Visual Forensics', key: 'visualForensics' },
        { title: 'Threat Intelligence', key: 'threatIntel' }
      ];

      sectionsMap.forEach(sec => {
        if (r[sec.key]) {
          this.container.appendChild(this._createSection(sec.title, r[sec.key]));
        }
      });
    }

    _createSection(title, data) {
      const section = Utils.createElement('div', 'dashboard-section');
      const header = Utils.createElement('div', 'section-header');
      header.innerHTML = `<h3>${title}</h3><span class="collapse-icon">▼</span>`;
      
      const content = Utils.createElement('div', 'section-content');
      
      header.addEventListener('click', () => {
        content.classList.toggle('collapsed');
        header.querySelector('.collapse-icon').style.transform = content.classList.contains('collapsed') ? 'rotate(-90deg)' : 'rotate(0deg)';
      });
      section.appendChild(header);

      for (const [key, val] of Object.entries(data)) {
        if (key === 'c2pa' || key === 'deviceId' || key === 'editHistory' || key === 'timeline' || key === 'heatmapData') continue; // Handle nested objects separately if needed, simplified for now
        
        const row = Utils.createElement('div', 'metric-row');
        // format key from camelCase to Title Case
        const formattedKey = key.replace(/([A-Z])/g, ' $1').replace(/^./, str => str.toUpperCase());
        const label = Utils.createElement('div', 'metric-label', { textContent: formattedKey });
        
        let valueStr = '';
        let confClass = '';
        if (typeof val === 'object' && val !== null) {
          if (val.score !== undefined) {
             valueStr = `${val.score}%`;
             if(val.label) valueStr += ` (${val.label})`;
             if(val.details) valueStr += ` - ${val.details}`;
             const isTrustMetric = key.toLowerCase().includes('reput') || key.toLowerCase().includes('repet') || val.label === 'Clean' || val.label === 'Suspicious';
             if (isTrustMetric) {
               confClass = val.score >= 60 ? 'confidence-low' : (val.score >= 40 ? 'confidence-medium' : 'confidence-high');
             } else {
               confClass = Utils.formatConfidence(val.score).class;
             }
          } else if (val.matched !== undefined) {
             valueStr = val.matched ? 'MATCHED' : 'CLEAN';
             if(val.name) valueStr += ` (${val.name})`;
             confClass = val.matched ? 'text-danger' : 'text-success';
          } else {
             valueStr = JSON.stringify(val);
          }
        } else {
          valueStr = val.toString();
        }

        const value = Utils.createElement('div', 'metric-value', { textContent: valueStr });
        if (confClass) value.classList.add(confClass);

        row.appendChild(label);
        row.appendChild(value);
        content.appendChild(row);
      }
      section.appendChild(content);
      return section;
    }

    _createDocumentSection(r) {
      const doc = r.documentClassification;
      const fields = r.extractedFields || {};
      const section = Utils.createElement('div', 'dashboard-section document-identity-section');
      
      const isHighConf = (doc.confidence || 0) >= 60;
      const badgeClass = isHighConf ? 'badge-success' : 'badge-warning';
      const icon = doc.code && doc.code.includes('passport') ? '🛂' : '🪪';

      const header = Utils.createElement('div', 'section-header doc-card-header');
      header.innerHTML = `
        <div style="display:flex; align-items:center; gap:8px;">
          <span style="font-size:18px;">${icon}</span>
          <h3 style="margin:0; font-size:14px; font-weight:700; color:var(--accent-cyan);">Document Identification &amp; OCR</h3>
        </div>
        <span class="badge ${badgeClass}">${doc.confidence ? doc.confidence + '%' : 'Identified'}</span>
      `;
      section.appendChild(header);

      const content = Utils.createElement('div', 'section-content doc-card-body');
      
      // Main Document Banner
      const banner = Utils.createElement('div', 'doc-banner');
      banner.style.cssText = 'background: rgba(0, 212, 255, 0.08); border: 1px solid rgba(0, 212, 255, 0.25); border-radius: var(--radius-sm); padding: 12px; margin-bottom: 12px; display: flex; justify-content: space-between; align-items: center;';
      banner.innerHTML = `
        <div>
          <div style="font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; color: var(--text-secondary, #666);">Detected Document Standard</div>
          <div style="font-size: 16px; font-weight: 700; color: var(--text-primary, #1d1d1f); margin-top: 2px;">${doc.name || 'Indian Identity Document'}</div>
        </div>
        <span class="badge ${badgeClass}" style="padding: 4px 8px; font-size: 11px;">${isHighConf ? '✓ Layout Verified' : '⚠ Layout Review'}</span>
      `;
      content.appendChild(banner);

      // Extracted Fields Table
      const fieldKeys = Object.keys(fields);
      if (fieldKeys.length > 0) {
        const fieldsTitle = Utils.createElement('div', 'metric-label', { textContent: 'EXTRACTED IDENTITY PARAMETERS' });
        fieldsTitle.style.cssText = 'font-weight: 600; font-size: 11px; color: var(--accent-cyan); margin-bottom: 8px; letter-spacing: 0.5px;';
        content.appendChild(fieldsTitle);

        const labelMap = {
          id_number: 'Document ID / Number',
          holder_name: 'Full Name',
          father_name: 'Father\'s Name',
          relative_name: 'Relative\'s Name',
          dob: 'Date of Birth',
          gender: 'Gender',
          pincode: 'PIN Code',
          expiry_date: 'Date of Expiry',
          date_of_issue: 'Date of Issue',
          place_of_issue: 'Place of Issue',
          nationality: 'Nationality',
          holder_category: 'PAN Category',
          validity_expiry: 'Validity',
          surname: 'Surname',
          given_names: 'Given Names'
        };

        for (const [k, v] of Object.entries(fields)) {
          if (k === 'document_id_label' || k === 'mrz_raw' || k === 'mrz_detected' || !v) continue;
          const row = Utils.createElement('div', 'metric-row');
          row.style.cssText = 'padding: 6px 0; border-bottom: 1px solid var(--border-subtle);';
          const labelText = labelMap[k] || k.replace(/_/g, ' ').toUpperCase();
          const label = Utils.createElement('div', 'metric-label', { textContent: labelText });
          const value = Utils.createElement('div', 'metric-value font-mono', { textContent: v });
          value.style.cssText = 'color: var(--accent-cyan, #0066cc); font-weight: 700;';
          row.appendChild(label);
          row.appendChild(value);
          content.appendChild(row);
        }
      }

      // OCR Raw Text Snippet
      if (r.ocrLines && r.ocrLines.length > 0) {
        const ocrDetails = Utils.createElement('details', 'ocr-raw-container');
        ocrDetails.style.cssText = 'margin-top: 12px; font-size: 11px; background: rgba(0,0,0,0.3); border-radius: var(--radius-sm); padding: 8px; border: 1px solid var(--border-subtle);';
        const summary = Utils.createElement('summary', '', { textContent: `🔍 View Extracted OCR Text Lines (${r.ocrLines.length} segments)` });
        summary.style.cssText = 'cursor: pointer; color: var(--text-secondary); font-weight: 500;';
        const rawBox = Utils.createElement('div', 'ocr-raw-box font-mono');
        rawBox.style.cssText = 'margin-top: 8px; max-height: 120px; overflow-y: auto; color: var(--text-muted); font-size: 10px; line-height: 1.5; white-space: pre-wrap;';
        rawBox.textContent = r.ocrLines.join('\n');
        ocrDetails.appendChild(summary);
        ocrDetails.appendChild(rawBox);
        content.appendChild(ocrDetails);
      }

      section.appendChild(content);
      return section;
    }

    _createValidationSection(report) {
      const { checks = [], verdict = 'INCONCLUSIVE', pass_count = 0, fail_count = 0, warn_count = 0, total_rules = 0 } = report;

      // Verdict styling map
      const verdictMap = {
        VALIDATED:    { class: 'badge-success', icon: '✅', label: 'VALIDATED',    color: '#00e676' },
        SUSPICIOUS:   { class: 'badge-warning', icon: '⚠️', label: 'SUSPICIOUS',   color: '#ffaa00' },
        INVALID:      { class: 'badge-danger',  icon: '❌', label: 'INVALID',      color: '#ff3366' },
        INCONCLUSIVE: { class: 'badge-warning', icon: '🔍', label: 'INCONCLUSIVE', color: '#ffaa00' },
        UNVERIFIABLE: { class: 'badge-danger',  icon: '🚫', label: 'UNVERIFIABLE', color: '#ff3366' },
        ERROR:        { class: 'badge-warning', icon: '⚡', label: 'ERROR',        color: '#888888' }
      };
      const v = verdictMap[verdict] || verdictMap['INCONCLUSIVE'];

      const section = Utils.createElement('div', 'dashboard-section');

      const header = Utils.createElement('div', 'section-header');
      header.innerHTML = `
        <div style="display:flex; align-items:center; gap:8px;">
          <span style="font-size:16px;">📋</span>
          <h3 style="margin:0; font-size:14px; font-weight:700; color:#c8b6ff;">Document Standard Validation</h3>
        </div>
        <span class="badge ${v.class}" style="font-size:11px;">${v.icon} ${v.label}</span>
      `;
      section.appendChild(header);

      const content = Utils.createElement('div', 'section-content');

      // Verdict summary bar
      const summaryBar = Utils.createElement('div', 'validation-summary-bar');
      summaryBar.style.cssText = `
        background: rgba(200,182,255,0.07);
        border: 1px solid rgba(200,182,255,0.2);
        border-radius: var(--radius-sm);
        padding: 10px 14px;
        margin-bottom: 12px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 12px;
      `;
      summaryBar.innerHTML = `
        <div>
          <div style="font-size:11px; color:var(--text-muted); text-transform:uppercase; letter-spacing:0.5px;">Ruleset Verdict</div>
          <div style="font-size:15px; font-weight:700; color:${v.color}; margin-top:2px;">${v.icon} ${v.label}</div>
        </div>
        <div style="display:flex; gap:16px; font-size:12px;">
          <div style="text-align:center;">
            <div style="font-size:18px; font-weight:700; color:#00e676;">${pass_count}</div>
            <div style="color:var(--text-muted);">PASS</div>
          </div>
          <div style="text-align:center;">
            <div style="font-size:18px; font-weight:700; color:#ff3366;">${fail_count}</div>
            <div style="color:var(--text-muted);">FAIL</div>
          </div>
          <div style="text-align:center;">
            <div style="font-size:18px; font-weight:700; color:#ffaa00;">${warn_count}</div>
            <div style="color:var(--text-muted);">WARN</div>
          </div>
        </div>
      `;
      content.appendChild(summaryBar);

      // Individual check rows
      const statusConfig = {
        PASS: { icon: '✅', color: '#00e676', bg: 'rgba(0,230,118,0.06)' },
        FAIL: { icon: '❌', color: '#ff3366', bg: 'rgba(255,51,102,0.08)' },
        WARN: { icon: '⚠️', color: '#ffaa00', bg: 'rgba(255,170,0,0.06)' }
      };

      for (const chk of checks) {
        const sc = statusConfig[chk.status] || statusConfig['WARN'];
        const row = Utils.createElement('div', 'validation-check-row');
        row.style.cssText = `
          padding: 8px 10px;
          border-radius: var(--radius-sm);
          margin-bottom: 6px;
          background: ${sc.bg};
          border-left: 3px solid ${sc.color};
        `;
        row.innerHTML = `
          <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:8px;">
            <div style="font-size:12px; font-weight:600; color:var(--text-primary);">${sc.icon} ${chk.rule}</div>
            <span style="font-size:10px; font-weight:700; color:${sc.color}; white-space:nowrap;">${chk.status}</span>
          </div>
          <div style="font-size:11px; color:var(--text-muted); margin-top:3px;">${chk.detail}</div>
        `;
        content.appendChild(row);
      }

      section.appendChild(content);
      return section;
    }

    _createBiometricSection(r) {
      const section = Utils.createElement('div', 'dashboard-section biometric-section');
      const header = Utils.createElement('div', 'section-header');
      header.innerHTML = `
        <div style="display:flex; align-items:center; gap:8px;">
          <span style="font-size:16px;">👤</span>
          <h3 style="margin:0; font-size:14px; font-weight:700; color:var(--text-primary);">Biometric Verification Booth</h3>
        </div>
        <span class="badge badge-warning" id="bio-status-badge" style="font-size:11px;">Awaiting Live Face</span>
      `;
      section.appendChild(header);

      const content = Utils.createElement('div', 'section-content');
      
      // Extract document photo base64 if available
      const docCropBase64 = r.tamperReport?.photo_splice?.details?.face_crop_base64 || null;
      const docImgSrc = docCropBase64 ? `data:image/jpeg;base64,${docCropBase64}` : null;

      content.innerHTML = `
        <div style="background:rgba(0,102,204,0.04); border:1px solid rgba(0,102,204,0.15); border-radius:var(--radius-sm); padding:12px; margin-bottom:12px;">
          <div style="font-size:11px; text-transform:uppercase; letter-spacing:0.5px; color:var(--text-secondary); margin-bottom:10px; font-weight:700;">
            1:1 Identity Matching (Document Photo vs Physical Carrier)
          </div>
          
          <div style="display:grid; grid-template-columns: 1fr 1fr; gap:12px; margin-bottom:12px;">
            <!-- Left: Document Photo -->
            <div style="background:var(--bg-elevated); border:1px solid var(--border-subtle); border-radius:var(--radius-sm); padding:10px; text-align:center;">
              <div style="font-size:10px; color:var(--text-muted); font-weight:bold; margin-bottom:6px; text-transform:uppercase;">1. Document Card Photo</div>
              <div style="width:110px; height:130px; margin:0 auto; background:rgba(0,0,0,0.05); border-radius:6px; overflow:hidden; display:flex; align-items:center; justify-content:center; border:1px solid var(--border-medium);">
                ${docImgSrc ? `<img id="doc-card-photo" src="${docImgSrc}" style="width:100%; height:100%; object-fit:cover;" alt="Card Photo"/>` : `<span style="font-size:10px; color:var(--text-muted);">Auto-Cropped from ID</span>`}
              </div>
            </div>

            <!-- Right: Live Booth Camera / Selfie -->
            <div style="background:var(--bg-elevated); border:1px solid var(--border-subtle); border-radius:var(--radius-sm); padding:10px; text-align:center;">
              <div style="font-size:10px; color:var(--text-muted); font-weight:bold; margin-bottom:6px; text-transform:uppercase;">2. Live Booth Face</div>
              <div style="width:110px; height:130px; margin:0 auto; background:rgba(0,0,0,0.05); border-radius:6px; overflow:hidden; position:relative; display:flex; align-items:center; justify-content:center; border:1px solid var(--border-medium);">
                <video id="booth-webcam-video" autoplay playsinline muted style="width:100%; height:100%; object-fit:cover; display:none;"></video>
                <img id="booth-face-preview" style="width:100%; height:100%; object-fit:cover; display:none;" alt="Live Face"/>
                <canvas id="booth-webcam-canvas" style="display:none;"></canvas>
                <div id="booth-camera-placeholder" style="font-size:10px; color:var(--text-muted); padding:6px;">
                  📷 Camera Offline
                </div>
              </div>
            </div>
          </div>

          <!-- Controls -->
          <div style="display:flex; gap:8px; justify-content:center; flex-wrap:wrap; margin-bottom:8px;">
            <button class="btn btn-outline" id="btn-start-camera" style="font-size:11px; padding:6px 12px;">
              📷 Start Booth Camera
            </button>
            <button class="btn btn-primary" id="btn-capture-face" style="font-size:11px; padding:6px 12px; display:none;">
              📸 Capture Live Face
            </button>
            <label class="btn btn-ghost" style="font-size:11px; padding:6px 12px; cursor:pointer; margin:0;">
              📁 Upload Selfie
              <input type="file" id="input-selfie-upload" accept="image/*" style="display:none;">
            </label>
          </div>

          <!-- Live Result Verdict Bar -->
          <div id="bio-verdict-box" style="display:none; background:var(--bg-card); border-radius:6px; padding:10px; border:1px solid var(--border-subtle); margin-top:8px;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
              <div>
                <div style="font-size:10px; color:var(--text-muted); text-transform:uppercase; font-weight:700;">Biometric Verification Result</div>
                <div id="bio-verdict-title" style="font-size:14px; font-weight:800; margin-top:2px;">—</div>
              </div>
              <div style="text-align:right;">
                <div id="bio-match-score" style="font-size:18px; font-weight:900;">—</div>
                <div style="font-size:9px; color:var(--text-muted);">MATCH SCORE</div>
              </div>
            </div>
            <div id="bio-verdict-desc" style="font-size:11px; color:var(--text-secondary); margin-top:6px; line-height:1.4;"></div>
          </div>
        </div>
      `;

      // Attach event listeners after append
      setTimeout(() => {
        this._initBoothEvents(content, r);
      }, 50);

      section.appendChild(content);
      return section;
    }

    _initBoothEvents(container, r) {
      const video = container.querySelector('#booth-webcam-video');
      const canvas = container.querySelector('#booth-webcam-canvas');
      const preview = container.querySelector('#booth-face-preview');
      const placeholder = container.querySelector('#booth-camera-placeholder');
      const btnStartCam = container.querySelector('#btn-start-camera');
      const btnCapture = container.querySelector('#btn-capture-face');
      const inputUpload = container.querySelector('#input-selfie-upload');
      const verdictBox = container.querySelector('#bio-verdict-box');
      const verdictTitle = container.querySelector('#bio-verdict-title');
      const matchScore = container.querySelector('#bio-match-score');
      const verdictDesc = container.querySelector('#bio-verdict-desc');
      const statusBadge = document.querySelector('#bio-status-badge');

      let currentStream = null;
      let capturedLiveBlob = null;

      // 1. Start Webcam
      if (btnStartCam) {
        btnStartCam.addEventListener('click', async () => {
          try {
            if (currentStream) {
              currentStream.getTracks().forEach(t => t.stop());
            }
            currentStream = await navigator.mediaDevices.getUserMedia({ video: { width: 480, height: 480, facingMode: 'user' } });
            video.srcObject = currentStream;
            video.style.display = 'block';
            if (placeholder) placeholder.style.display = 'none';
            if (preview) preview.style.display = 'none';
            btnCapture.style.display = 'inline-flex';
            btnStartCam.textContent = '🔄 Switch Camera';
          } catch (err) {
            alert('Could not access booth camera: ' + err.message + '. Please use "Upload Selfie" instead.');
          }
        });
      }

      // 2. Capture Snapshot
      if (btnCapture) {
        btnCapture.addEventListener('click', () => {
          if (!video || !video.videoWidth) return;
          canvas.width = video.videoWidth;
          canvas.height = video.videoHeight;
          const ctx = canvas.getContext('2d');
          ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

          canvas.toBlob((blob) => {
            capturedLiveBlob = blob;
            preview.src = URL.createObjectURL(blob);
            preview.style.display = 'block';
            video.style.display = 'none';
            if (currentStream) {
              currentStream.getTracks().forEach(t => t.stop());
              currentStream = null;
            }
            btnStartCam.textContent = '📷 Retake Photo';
            btnCapture.style.display = 'none';
            this._runFaceVerification(capturedLiveBlob, container, r);
          }, 'image/jpeg', 0.95);
        });
      }

      // 3. Upload File Fallback
      if (inputUpload) {
        inputUpload.addEventListener('change', (e) => {
          if (e.target.files && e.target.files[0]) {
            const file = e.target.files[0];
            capturedLiveBlob = file;
            preview.src = URL.createObjectURL(file);
            preview.style.display = 'block';
            if (video) video.style.display = 'none';
            if (placeholder) placeholder.style.display = 'none';
            if (currentStream) {
              currentStream.getTracks().forEach(t => t.stop());
              currentStream = null;
            }
            btnStartCam.textContent = '📷 Open Camera';
            btnCapture.style.display = 'none';
            this._runFaceVerification(capturedLiveBlob, container, r);
          }
        });
      }
    }

    async _runFaceVerification(liveBlob, container, r) {
      const verdictBox = container.querySelector('#bio-verdict-box');
      const verdictTitle = container.querySelector('#bio-verdict-title');
      const matchScore = container.querySelector('#bio-match-score');
      const verdictDesc = container.querySelector('#bio-verdict-desc');
      const statusBadge = document.querySelector('#bio-status-badge');

      if (!verdictBox) return;
      verdictBox.style.display = 'block';
      verdictTitle.textContent = 'Analyzing Biometrics...';
      verdictTitle.style.color = 'var(--text-primary)';
      matchScore.textContent = '...';
      verdictDesc.textContent = 'Aligning facial landmarks and comparing deep biometric vectors via SFace neural engine...';

      try {
        const formData = new FormData();

        // Get document image from active file or data URI
        const docCropBase64 = r.tamperReport?.photo_splice?.details?.face_crop_base64;
        if (docCropBase64) {
          // Convert base64 to Blob
          const byteChars = atob(docCropBase64);
          const byteNums = new Array(byteChars.length);
          for (let i = 0; i < byteChars.length; i++) byteNums[i] = byteChars.charCodeAt(i);
          const byteArray = new Uint8Array(byteNums);
          formData.append('doc_file', new Blob([byteArray], { type: 'image/jpeg' }), 'doc_face.jpg');
        } else if (window._lastUploadedDocFile) {
          formData.append('doc_file', window._lastUploadedDocFile);
        } else {
          throw new Error('No document photo available to compare.');
        }

        formData.append('live_file', liveBlob, 'live_face.jpg');

        const baseUrl = (window.location.protocol === 'http:' || window.location.protocol === 'https:')
          ? window.location.origin
          : 'http://localhost:8000';

        const resp = await fetch(`${baseUrl}/verify/face`, {
          method: 'POST',
          body: formData
        });

        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const data = await resp.json();

        const isMatch = data.match;
        const color = isMatch ? '#00e676' : '#ff3366';

        verdictTitle.textContent = data.verdict_text || (isMatch ? 'IDENTITY CONFIRMED' : 'IMPERSONATION ALERT');
        verdictTitle.style.color = color;
        matchScore.textContent = `${data.match_score}%`;
        matchScore.style.color = color;
        verdictDesc.textContent = data.explanation || '';

        if (statusBadge) {
          statusBadge.textContent = isMatch ? '✓ Verified Person' : '⚠ Impersonation Risk';
          statusBadge.className = isMatch ? 'badge badge-success' : 'badge badge-danger';
        }

      } catch (err) {
        console.error('Face verification failed:', err);
        verdictTitle.textContent = 'Comparison Failed';
        verdictTitle.style.color = 'var(--accent-red)';
        matchScore.textContent = '0%';
        verdictDesc.textContent = `Could not complete 1:1 face verification (${err.message}). Ensure backend is running.`;
      }
    }

    clear() {
      if (this.container) this.container.innerHTML = '';
    }

    showLoading() {
      if (this.container) {
        this.container.innerHTML = '<div class="loading-skeleton"><div class="pulse">Extracting Forensics...</div></div>';
      }
    }
  }

  return Dashboard;
})();
