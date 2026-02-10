// Popup script for Verity Sniffer

document.addEventListener('DOMContentLoaded', async () => {
  // Load settings
  const settings = await chrome.storage.local.get(['apiUrl', 'model', 'checks', 'recentChecks']);
  
  if (settings.apiUrl) {
    document.getElementById('apiUrl').value = settings.apiUrl;
  }
  
  if (settings.model) {
    document.getElementById('modelSelect').value = settings.model;
  }
  
  // Update stats
  updateStats(settings.checks || []);
  
  // Show recent checks
  showRecentChecks(settings.recentChecks || []);
  
  // Save settings button
  document.getElementById('saveSettings').addEventListener('click', async () => {
    const apiUrl = document.getElementById('apiUrl').value;
    const model = document.getElementById('modelSelect').value;
    
    await chrome.storage.local.set({ apiUrl, model });
    
    // Visual feedback
    const btn = document.getElementById('saveSettings');
    btn.textContent = 'Saved!';
    btn.style.background = '#28a745';
    setTimeout(() => {
      btn.textContent = 'Save Settings';
      btn.style.background = '#1a73e8';
    }, 1500);
  });
  
  // Clear data
  document.getElementById('clearData').addEventListener('click', async (e) => {
    e.preventDefault();
    if (confirm('Clear all check history?')) {
      await chrome.storage.local.set({ checks: [], recentChecks: [] });
      updateStats([]);
      showRecentChecks([]);
    }
  });
});

function updateStats(checks) {
  const total = checks.length;
  const verified = checks.filter(c => c.verdict === 'TRUE' || c.verdict === 'verified').length;
  const flagged = checks.filter(c => c.verdict === 'FALSE' || c.verdict === 'flagged').length;
  
  document.getElementById('checksCount').textContent = total;
  document.getElementById('verifiedCount').textContent = verified;
  document.getElementById('flaggedCount').textContent = flagged;
}

function showRecentChecks(checks) {
  const container = document.getElementById('recentChecks');
  
  if (!checks || checks.length === 0) {
    container.innerHTML = '<p class="empty-state">No checks yet. Select text on any page and right-click → "Check with Verity"</p>';
    return;
  }
  
  // Show last 5 checks
  const recent = checks.slice(-5).reverse();
  
  container.innerHTML = recent.map(check => {
    const verdictClass = check.verdict?.toLowerCase() || 'uncertain';
    return `
      <div class="recent-item">
        <div class="text">"${truncate(check.text, 60)}"</div>
        <span class="verdict ${verdictClass}">${check.verdict || 'Unknown'}</span>
        <span class="confidence">(${check.confidence || 0}% confidence)</span>
      </div>
    `;
  }).join('');
}

function truncate(str, len) {
  if (!str) return '';
  return str.length > len ? str.substring(0, len) + '...' : str;
}
