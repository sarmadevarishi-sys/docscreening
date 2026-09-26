window.SatyaKavach = window.SatyaKavach || {};

window.SatyaKavach.ProvenanceTree = class ProvenanceTree {
  constructor() {}

  render(container, provenanceData) {
    container.innerHTML = '';
    container.style.display = 'flex';
    container.style.flexDirection = 'column';
    container.style.alignItems = 'center';
    container.style.gap = '16px';
    container.style.padding = '24px';
    container.style.fontFamily = "'Inter', sans-serif";

    provenanceData.forEach((node, index) => {
      const isLast = index === provenanceData.length - 1;
      
      const el = document.createElement('div');
      el.style.width = '100%';
      el.style.maxWidth = '400px';
      el.style.backgroundColor = '#1e1e36';
      el.style.border = '1px solid rgba(255,255,255,0.07)';
      el.style.borderRadius = '8px';
      el.style.padding = '16px';
      el.style.position = 'relative';
      el.style.opacity = '0';
      el.style.transform = 'translateY(10px)';
      el.style.transition = 'all 0.3s ease-out';
      
      // Status coloring
      let statusColor = '#00e676'; // verified
      if (node.status === 'tampered') statusColor = '#ff3366';
      if (node.status === 'missing') statusColor = '#ffaa00';
      
      el.style.borderLeft = `4px solid ${statusColor}`;

      el.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: flex-start;">
          <div>
            <div style="color: #e8e8f0; font-weight: 600; font-size: 14px; margin-bottom: 4px;">
              ${this.getIcon(node.type)} ${node.title}
            </div>
            <div style="color: #8888aa; font-size: 12px;">${node.subtitle}</div>
          </div>
          ${this.renderC2PABadge(node.status)}
        </div>
        <div style="margin-top: 12px; font-family: 'JetBrains Mono', monospace; font-size: 10px; color: #666680; display: none;" class="meta-details">
          ${Object.entries(node.metadata).map(([k,v]) => `<div><span style="color:#8888aa">${k}:</span> ${v}</div>`).join('')}
        </div>
        <div style="margin-top: 12px; font-size: 11px; color: #666680; text-align: right;">
          ${node.timestamp}
        </div>
      `;

      // Expand details on click
      el.style.cursor = 'pointer';
      el.addEventListener('click', () => {
        const details = el.querySelector('.meta-details');
        details.style.display = details.style.display === 'none' ? 'block' : 'none';
      });

      container.appendChild(el);

      // Animate in
      setTimeout(() => {
        el.style.opacity = '1';
        el.style.transform = 'translateY(0)';
      }, index * 150);

      if (!isLast) {
        const connector = document.createElement('div');
        connector.style.width = '2px';
        connector.style.height = '24px';
        
        // Dashed line if the next node breaks the chain
        if (provenanceData[index+1].status === 'tampered' || provenanceData[index+1].status === 'missing') {
          connector.style.borderLeft = `2px dashed ${statusColor}`;
        } else {
          connector.style.backgroundColor = statusColor;
        }
        
        connector.style.opacity = '0';
        connector.style.transition = 'opacity 0.3s ease-out';
        
        container.appendChild(connector);
        setTimeout(() => { connector.style.opacity = '1'; }, index * 150 + 100);
      }
    });
  }

  getIcon(type) {
    const icons = {
      'CAPTURE': '📷',
      'EDIT': '✂️',
      'EXPORT': '📤',
      'DISTRIBUTE': '🌐',
      'TAMPER': '⚠️'
    };
    return icons[type] || '📄';
  }

  renderC2PABadge(status) {
    if (status === 'verified') {
      return `<span style="background: rgba(0, 230, 118, 0.1); color: #00e676; border: 1px solid #00e676; padding: 2px 6px; border-radius: 4px; font-size: 10px; font-weight: bold;">C2PA ✓</span>`;
    } else if (status === 'tampered') {
      return `<span style="background: rgba(255, 51, 102, 0.1); color: #ff3366; border: 1px solid #ff3366; padding: 2px 6px; border-radius: 4px; font-size: 10px; font-weight: bold;">C2PA ✗</span>`;
    } else {
      return `<span style="background: rgba(255, 170, 0, 0.1); color: #ffaa00; border: 1px solid #ffaa00; padding: 2px 6px; border-radius: 4px; font-size: 10px; font-weight: bold;">NO SIG</span>`;
    }
  }

  generateMockProvenance(scenario) {
    const base = [
      {
        type: 'CAPTURE',
        title: 'Sony Alpha 7 IV',
        subtitle: 'Original Capture',
        status: 'verified',
        timestamp: '2023-10-12T14:32:00Z',
        metadata: { 'Hardware': 'ILCE-7M4', 'Lens': 'FE 24-70mm F2.8 GM', 'Location': '34.0522° N, 118.2437° W' }
      }
    ];

    if (scenario === 'authentic') {
      return [...base, {
        type: 'EDIT',
        title: 'Adobe Photoshop 2024',
        subtitle: 'Color Correction',
        status: 'verified',
        timestamp: '2023-10-13T09:15:00Z',
        metadata: { 'Tool': 'Camera Raw', 'Actions': 'Exposure, Contrast' }
      }, {
        type: 'EXPORT',
        title: 'Export to Web',
        subtitle: 'JPEG Compression',
        status: 'verified',
        timestamp: '2023-10-13T09:20:00Z',
        metadata: { 'Format': 'image/jpeg', 'Quality': '85' }
      }];
    } else if (scenario === 'tampered') {
      return [...base, {
        type: 'EDIT',
        title: 'Adobe Premiere Pro',
        subtitle: 'Sequence Edit',
        status: 'verified',
        timestamp: '2023-10-14T11:00:00Z',
        metadata: { 'Codec': 'H.264', 'Bitrate': '50Mbps' }
      }, {
        type: 'TAMPER',
        title: 'DeepFaceLab (Detected)',
        subtitle: 'AI Face Swap',
        status: 'tampered',
        timestamp: 'Unknown',
        metadata: { 'Model': 'DFL SAEHD', 'Confidence': '98.7%', 'Artifacts': 'Spatial Seam, Blending' }
      }, {
        type: 'DISTRIBUTE',
        title: 'Social Media Platform',
        subtitle: 'Uploaded via Web',
        status: 'missing',
        timestamp: '2023-10-15T18:45:00Z',
        metadata: { 'Source': 'Web Browser', 'Stripped': 'EXIF, C2PA' }
      }];
    }
    return base;
  }
};
