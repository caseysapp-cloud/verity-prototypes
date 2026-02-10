// Content script for Verity Sniffer
// Handles text selection and displays inline results

(function() {
  'use strict';
  
  let tooltip = null;
  let currentSelection = null;
  
  // Create floating button for text selection
  const floatingBtn = document.createElement('div');
  floatingBtn.id = 'verity-float-btn';
  floatingBtn.innerHTML = '🔍 Check';
  floatingBtn.style.display = 'none';
  document.body.appendChild(floatingBtn);
  
  // Show button on text selection
  document.addEventListener('mouseup', (e) => {
    setTimeout(() => {
      const selection = window.getSelection();
      const text = selection.toString().trim();
      
      if (text.length > 10 && text.length < 2000) {
        currentSelection = {
          text: text,
          url: window.location.href,
          context: getContext(selection)
        };
        
        // Position button near selection
        const range = selection.getRangeAt(0);
        const rect = range.getBoundingClientRect();
        
        floatingBtn.style.display = 'block';
        floatingBtn.style.left = (rect.left + window.scrollX + rect.width / 2 - 40) + 'px';
        floatingBtn.style.top = (rect.top + window.scrollY - 40) + 'px';
      } else {
        floatingBtn.style.display = 'none';
        currentSelection = null;
      }
    }, 10);
  });
  
  // Hide button on click elsewhere
  document.addEventListener('mousedown', (e) => {
    if (e.target !== floatingBtn && !e.target.closest('#verity-tooltip')) {
      floatingBtn.style.display = 'none';
      hideTooltip();
    }
  });
  
  // Handle floating button click
  floatingBtn.addEventListener('click', async (e) => {
    e.preventDefault();
    e.stopPropagation();
    
    if (currentSelection) {
      floatingBtn.innerHTML = '⏳ Checking...';
      floatingBtn.style.pointerEvents = 'none';
      
      try {
        const result = await analyzeText(currentSelection);
        showTooltip(result, floatingBtn.style.left, floatingBtn.style.top);
      } catch (err) {
        showTooltip({ error: err.message }, floatingBtn.style.left, floatingBtn.style.top);
      }
      
      floatingBtn.innerHTML = '🔍 Check';
      floatingBtn.style.pointerEvents = 'auto';
      floatingBtn.style.display = 'none';
    }
  });
  
  // Get surrounding context
  function getContext(selection) {
    try {
      const node = selection.anchorNode;
      if (node && node.parentElement) {
        const parent = node.parentElement.closest('p, div, article, section');
        if (parent) {
          return parent.textContent.substring(0, 500);
        }
      }
    } catch (e) {}
    return '';
  }
  
  // Analyze text via background script
  async function analyzeText(data) {
    return new Promise((resolve, reject) => {
      chrome.runtime.sendMessage(
        { action: 'analyze', data: data },
        (response) => {
          if (chrome.runtime.lastError) {
            reject(new Error(chrome.runtime.lastError.message));
          } else if (response.error) {
            reject(new Error(response.error));
          } else {
            resolve(response);
          }
        }
      );
    });
  }
  
  // Show result tooltip
  function showTooltip(result, left, top) {
    hideTooltip();
    
    tooltip = document.createElement('div');
    tooltip.id = 'verity-tooltip';
    
    if (result.error) {
      tooltip.innerHTML = `
        <div class="verity-header verity-error">
          <span class="verity-icon">⚠️</span>
          <span class="verity-title">Error</span>
          <button class="verity-close">×</button>
        </div>
        <div class="verity-body">
          <p>${result.error}</p>
        </div>
      `;
    } else {
      const verdictClass = getVerdictClass(result.fact_check?.verdict);
      const verdictIcon = getVerdictIcon(result.fact_check?.verdict);
      
      tooltip.innerHTML = `
        <div class="verity-header ${verdictClass}">
          <span class="verity-icon">${verdictIcon}</span>
          <span class="verity-title">${result.fact_check?.verdict || 'Unknown'}</span>
          <span class="verity-confidence">${result.fact_check?.confidence || 0}%</span>
          <button class="verity-close">×</button>
        </div>
        <div class="verity-body">
          <div class="verity-warning">⚠️ AI analysis may contain errors</div>
          
          <div class="verity-section">
            <h4>Fact Check</h4>
            <p>${result.fact_check?.explanation || 'No explanation provided'}</p>
          </div>
          
          ${result.ai_likelihood > 0.5 ? `
            <div class="verity-section verity-ai-warning">
              <h4>🤖 AI Content Detected (${Math.round(result.ai_likelihood * 100)}%)</h4>
              <p>${(result.ai_signals || []).join(', ') || 'Possible AI-generated content'}</p>
            </div>
          ` : ''}
          
          ${result.bias?.detected ? `
            <div class="verity-section verity-bias">
              <h4>📊 Bias Detected: ${result.bias.direction}</h4>
              <p>${(result.bias.indicators || []).join(', ')}</p>
            </div>
          ` : ''}
          
          ${result.fact_check?.sources?.length > 0 ? `
            <div class="verity-section">
              <h4>Sources</h4>
              <ul class="verity-sources">
                ${result.fact_check.sources.map(s => `
                  <li>
                    ${s.url ? `<a href="${s.url}" target="_blank">${s.title || s.url}</a>` : s.title || s}
                  </li>
                `).join('')}
              </ul>
            </div>
          ` : ''}
          
          ${result.warnings?.length > 0 ? `
            <div class="verity-section verity-warnings">
              <h4>⚠️ Warnings</h4>
              <ul>
                ${result.warnings.map(w => `<li>${w}</li>`).join('')}
              </ul>
            </div>
          ` : ''}
          
          <div class="verity-feedback">
            <span>Was this helpful?</span>
            <button class="verity-feedback-btn" data-feedback="yes">👍</button>
            <button class="verity-feedback-btn" data-feedback="no">👎</button>
          </div>
        </div>
      `;
    }
    
    // Parse position
    const leftNum = parseInt(left);
    const topNum = parseInt(top);
    
    tooltip.style.left = leftNum + 'px';
    tooltip.style.top = (topNum + 30) + 'px';
    
    document.body.appendChild(tooltip);
    
    // Close button
    tooltip.querySelector('.verity-close').addEventListener('click', hideTooltip);
    
    // Feedback buttons
    tooltip.querySelectorAll('.verity-feedback-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const feedback = e.target.dataset.feedback;
        chrome.runtime.sendMessage({
          action: 'feedback',
          data: { text: currentSelection?.text, feedback, result }
        });
        e.target.parentElement.innerHTML = 'Thanks for your feedback!';
      });
    });
  }
  
  function hideTooltip() {
    if (tooltip) {
      tooltip.remove();
      tooltip = null;
    }
  }
  
  function getVerdictClass(verdict) {
    if (!verdict) return 'verity-unknown';
    const v = verdict.toLowerCase();
    if (v.includes('true') || v === 'verified') return 'verity-true';
    if (v.includes('false') || v === 'flagged') return 'verity-false';
    if (v.includes('partial')) return 'verity-partial';
    return 'verity-unknown';
  }
  
  function getVerdictIcon(verdict) {
    if (!verdict) return '❓';
    const v = verdict.toLowerCase();
    if (v.includes('true') || v === 'verified') return '✅';
    if (v.includes('false') || v === 'flagged') return '❌';
    if (v.includes('partial')) return '⚠️';
    return '❓';
  }
  
  // Listen for context menu results
  chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === 'showResult') {
      const selection = window.getSelection();
      if (selection.rangeCount > 0) {
        const range = selection.getRangeAt(0);
        const rect = range.getBoundingClientRect();
        showTooltip(request.result, 
          (rect.left + window.scrollX) + 'px', 
          (rect.top + window.scrollY) + 'px'
        );
      }
    }
  });
})();
