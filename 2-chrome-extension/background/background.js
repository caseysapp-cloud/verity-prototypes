// Background service worker for Verity Sniffer

// Create context menu on install
chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: 'verity-check',
    title: 'Check with Verity 🔍',
    contexts: ['selection']
  });
});

// Handle context menu click
chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  if (info.menuItemId === 'verity-check' && info.selectionText) {
    const data = {
      text: info.selectionText,
      url: info.pageUrl,
      context: ''
    };
    
    try {
      const result = await analyzeText(data);
      
      // Send result to content script
      chrome.tabs.sendMessage(tab.id, {
        action: 'showResult',
        result: result
      });
      
      // Save to history
      await saveCheck(data.text, result);
    } catch (err) {
      chrome.tabs.sendMessage(tab.id, {
        action: 'showResult',
        result: { error: err.message }
      });
    }
  }
});

// Handle messages from content script
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'analyze') {
    analyzeText(request.data)
      .then(async (result) => {
        await saveCheck(request.data.text, result);
        sendResponse(result);
      })
      .catch(err => {
        sendResponse({ error: err.message });
      });
    return true; // Keep channel open for async response
  }
  
  if (request.action === 'feedback') {
    saveFeedback(request.data);
    sendResponse({ success: true });
  }
});

// Analyze text via API
async function analyzeText(data) {
  const settings = await chrome.storage.local.get(['apiUrl', 'model']);
  const apiUrl = settings.apiUrl || 'http://localhost:8000';
  const model = settings.model || 'gpt-4o';
  
  const response = await fetch(`${apiUrl}/analyze`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      text: data.text,
      url: data.url,
      context: data.context,
      model: model
    })
  });
  
  if (!response.ok) {
    const error = await response.text();
    throw new Error(`API error: ${response.status} - ${error}`);
  }
  
  return response.json();
}

// Save check to history
async function saveCheck(text, result) {
  const storage = await chrome.storage.local.get(['checks', 'recentChecks']);
  const checks = storage.checks || [];
  const recentChecks = storage.recentChecks || [];
  
  const check = {
    text: text.substring(0, 100),
    verdict: result.fact_check?.verdict || 'Unknown',
    confidence: result.fact_check?.confidence || 0,
    timestamp: Date.now()
  };
  
  checks.push(check);
  recentChecks.push(check);
  
  // Keep only last 100 checks
  if (checks.length > 100) checks.shift();
  if (recentChecks.length > 10) recentChecks.shift();
  
  await chrome.storage.local.set({ checks, recentChecks });
}

// Save feedback
async function saveFeedback(data) {
  const storage = await chrome.storage.local.get(['feedback']);
  const feedback = storage.feedback || [];
  
  feedback.push({
    text: data.text,
    feedback: data.feedback,
    result: data.result,
    timestamp: Date.now()
  });
  
  // Keep only last 50 feedback entries
  if (feedback.length > 50) feedback.shift();
  
  await chrome.storage.local.set({ feedback });
}
