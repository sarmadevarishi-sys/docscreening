window.SatyaKavach = window.SatyaKavach || {};

window.SatyaKavach.TextAnalyzer = (function() {
  const Utils = window.SatyaKavach.Utils;

  class TextAnalyzer {
    analyze(text) {
      if (!text) {
        return { originalText: '', annotations: [], score: 0, classification: 'None', recommendedAction: 'No text provided.' };
      }

      const annotations = [];
      let score = 0;
      let hasSuspiciousUrl = false;

      // Comprehensive Cyber Scam & Phishing Indicators
      const indicators = [
        // 1. Suspicious URLs, Shorteners, IP links, and Unknown TLDs
        {
          pattern: /(https?:\/\/[^\s]+|www\.[^\s]+|[a-zA-Z0-9-]+\.(xyz|top|click|link|site|online|vip|info|work|tech|cc|tk|ml|ga|cf|gq|club|space|biz|download|fun|monster|bid|icu|beauty|monster|pw)\/[^\s]*|\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\/[^\s]*|(bit\.ly|tinyurl|t\.co|lnkd\.in|goo\.gl|ow\.ly|is\.gd|cutt\.ly|rebrand\.ly)\/[a-zA-Z0-9_-]+)/ig,
          type: 'suspicious_url',
          weight: 45
        },
        // 2. High Urgency & Pressure Tactics
        {
          pattern: /\b(act now|limited time|immediate|immediately|expire|expires|expiring|last chance|urgent|urgently|suspended within|account locked|final warning|action required)\b/ig,
          type: 'urgency',
          weight: 25
        },
        // 3. Impersonation of Banks, Government, Police, Tech Giants
        {
          pattern: /\b(irs|fbi|police|sbi|hdfc|icici|axis|pnb|paytm|phonepe|gpay|bank|support|security|wallet|helpdesk|customer care|service team|customs|fedex|dhl|postal|telecom)\b/ig,
          type: 'impersonation',
          weight: 30
        },
        // 4. Financial & Greed Hooks (Lottery, Prizes, Transfers, Refunds)
        {
          pattern: /\b(won|lottery|prize|reward|cashback|transfer|deposited|credited|refund|account suspended|blocked|unauthorized transaction|earn daily|income|investment|profit|bitcoin|crypto)\b/ig,
          type: 'financial',
          weight: 35
        },
        // 5. Phishing Tricks (Verify, Update Payment, Click Here, OTP, Login)
        {
          pattern: /\b(verify your|click here|update payment|login|sign in|confirm details|share otp|share pin|kyc update|pan link|aadhaar update|claim now)\b/ig,
          type: 'phishing',
          weight: 35
        }
      ];

      indicators.forEach(ind => {
        let match;
        // Reset regex state
        ind.pattern.lastIndex = 0;
        while ((match = ind.pattern.exec(text)) !== null) {
          annotations.push({
            start: match.index,
            end: match.index + match[0].length,
            type: ind.type,
            matched: match[0]
          });
          score += ind.weight;
          if (ind.type === 'suspicious_url') {
            hasSuspiciousUrl = true;
          }
        }
      });

      // Compound boost: If message contains a link AND any phishing/urgency/financial trigger, boost score heavily
      if (hasSuspiciousUrl && (score >= 35 || annotations.length >= 2)) {
        score = Math.max(score + 35, 88);
      }

      score = Utils.clamp(score, 0, 100);

      let classification = 'Clean / Safe';
      if (score >= 60) classification = 'Phishing / Cyber Scam';
      else if (score >= 30) classification = 'Suspicious Message';

      let recommendedAction = 'Message appears clean. Exercise standard caution.';
      if (score >= 60) {
        recommendedAction = '⚠️ CRITICAL: Cyber Scam / Phishing attempt identified! Do NOT click any links, do NOT reply, and do NOT share any OTP or personal credentials.';
      } else if (score >= 30) {
        recommendedAction = '⚡ WARNING: Message contains suspicious elements. Verify the sender independently before taking action.';
      }

      return {
        originalText: text,
        annotations,
        score,
        classification,
        recommendedAction
      };
    }

    renderHighlightedText(container, text, annotations) {
      if (!container) return;
      container.innerHTML = '';
      let currentIndex = 0;

      // Filter and sort non-overlapping annotations
      const sorted = [...annotations].sort((a, b) => a.start - b.start);

      sorted.forEach(ann => {
        if (ann.start >= currentIndex) {
          if (ann.start > currentIndex) {
            container.appendChild(document.createTextNode(text.substring(currentIndex, ann.start)));
          }
          const span = Utils.createElement('span', ['highlight', `highlight-${ann.type}`], {
            textContent: text.substring(ann.start, ann.end)
          });
          container.appendChild(span);
          currentIndex = ann.end;
        }
      });

      if (currentIndex < text.length) {
        container.appendChild(document.createTextNode(text.substring(currentIndex)));
      }
    }
  }

  return new TextAnalyzer();
})();
