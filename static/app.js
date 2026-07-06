document.addEventListener('DOMContentLoaded', () => {
  // DOM Elements
  const modeBtns = document.querySelectorAll('.mode-btn');
  const runBtn = document.getElementById('run-triage-btn');
  const runBtnText = runBtn.querySelector('.btn-text');
  const loader = runBtn.querySelector('.loader');
  const errorBox = document.getElementById('error-box');
  const errorMsg = document.getElementById('error-msg');
  const consoleOutput = document.getElementById('console-output');
  const clearConsoleBtn = document.getElementById('clear-console-btn');
  const reportOutput = document.getElementById('report-output');
  const agentStatus = document.getElementById('agent-status');
  const agentStatusText = agentStatus.querySelector('.status-text');
  
  const metricEmails = document.getElementById('metric-emails').querySelector('.metric-value');
  const metricEvents = document.getElementById('metric-events').querySelector('.metric-value');
  const metricDrafts = document.getElementById('metric-drafts').querySelector('.metric-value');

  let activeMode = 'mock'; // Default mode

  // Toggle Mode Selector
  modeBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      modeBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      activeMode = btn.getAttribute('data-mode');
      addLog(`[System] Mode switched to: ${activeMode.toUpperCase()}`);
    });
  });

  // Clear logs button
  clearConsoleBtn.addEventListener('click', () => {
    consoleOutput.innerHTML = '';
    addLog('[System] Logs cleared.');
  });

  // Main trigger: Run Triage Agent
  runBtn.addEventListener('click', async () => {
    // Set UI to loading state
    runBtn.disabled = true;
    loader.classList.remove('hidden');
    runBtnText.textContent = 'Executing Agent...';
    errorBox.classList.add('hidden');
    
    // Update status badge
    updateStatus('running', 'Processing');
    
    addLog(`[System] Starting triage loop in ${activeMode.toUpperCase()} mode...`);
    addLog(`[System] Launching ADK Runner subprocess and local FastMCP server...`);
    
    try {
      const response = await fetch(`/api/run-triage?mode=${activeMode}`);
      const data = await response.json();
      
      // Update UI with logs
      if (data.logs && data.logs.length > 0) {
        data.logs.forEach(line => addLog(line));
      }
      
      if (data.success) {
        updateStatus('success', 'Completed');
        addLog('[System] Triage completed successfully.');
        
        // Render Markdown report
        if (data.summary) {
          reportOutput.innerHTML = `<div class="rendered-md">${marked.parse(data.summary)}</div>`;
          // Extract metrics from the summary text
          parseAndSetMetrics(data.summary);
        } else {
          reportOutput.innerHTML = `
            <div class="empty-report-state">
              <div class="empty-icon">⚠️</div>
              <h3>Empty Report</h3>
              <p>Triage finished but no report summary was returned by the agent.</p>
            </div>`;
        }
      } else {
        updateStatus('error', 'Failed');
        addLog(`[Error] ${data.error}`, 'error');
        showError(data.error);
      }
      
    } catch (err) {
      updateStatus('error', 'Failed');
      addLog(`[Error] Network request failed: ${err.message}`, 'error');
      showError(err.message);
    } finally {
      // Restore UI elements
      runBtn.disabled = false;
      loader.classList.add('hidden');
      runBtnText.textContent = 'Run Triage Agent';
    }
  });

  // Helper function to append logs in console
  function addLog(text, forceType = null) {
    const line = document.createElement('div');
    line.classList.add('log-line');
    
    // Classify line type for colors
    if (forceType) {
      line.classList.add(`${forceType}-line`);
    } else if (text.startsWith('[System]')) {
      line.classList.add('system-line');
    } else if (text.startsWith('[Tool Call]') || text.startsWith('[Tool Error]')) {
      line.classList.add('tool-line');
    } else if (text.startsWith('[MOCK')) {
      line.classList.add('mock-line');
    } else if (text.startsWith('[ERROR') || text.startsWith('[API ERROR]')) {
      line.classList.add('error-line');
    } else if (text.startsWith('[API]')) {
      line.classList.add('success-line');
    }
    
    line.textContent = text;
    consoleOutput.appendChild(line);
    // Scroll to bottom
    consoleOutput.scrollTop = consoleOutput.scrollHeight;
  }

  // Update Status Badge UI
  function updateStatus(statusClass, label) {
    agentStatus.className = `status-badge ${statusClass}`;
    agentStatusText.textContent = label;
  }

  // Show Error Box
  function showError(msg) {
    errorMsg.textContent = msg;
    errorBox.classList.remove('hidden');
  }

  // Parse metrics from the agent output and update cards
  function parseAndSetMetrics(summaryText) {
    // Regex looking for the specific instructions pattern:
    // 'You had X emails. I drafted Y replies for urgent meetings, scheduled Z events...'
    // Supports singular/plural variations.
    const regex = /You had (\d+) emails?\. I drafted (\d+) repl(?:ies|y) for urgent meetings, scheduled (\d+) events?/i;
    const match = summaryText.match(regex);
    
    if (match) {
      const emailsCount = match[1];
      const draftsCount = match[2];
      const eventsCount = match[3];
      
      animateNumber(metricEmails, parseInt(emailsCount));
      animateNumber(metricEvents, parseInt(eventsCount));
      animateNumber(metricDrafts, parseInt(draftsCount));
    } else {
      // Fallback: search counts of keywords only in the non-table description text preceding the table
      const lines = summaryText.split('\n');
      let textHeader = '';
      for (const line of lines) {
        const trimmed = line.trim();
        if (trimmed && !trimmed.startsWith('|')) {
          textHeader += ' ' + trimmed;
        } else if (trimmed.startsWith('|')) {
          break;
        }
      }
      
      const emailMatch = textHeader.match(/(\d+)\s+emails?/i) || textHeader.match(/had\s+(\d+)/i);
      const draftMatch = textHeader.match(/(\d+)\s+repl(?:ies|y)/i) || textHeader.match(/drafted\s+(\d+)/i);
      const eventMatch = textHeader.match(/(\d+)\s+events?/i) || textHeader.match(/scheduled\s+(\d+)/i);
      
      const emailsCount = emailMatch ? parseInt(emailMatch[1]) : 0;
      const draftsCount = draftMatch ? parseInt(draftMatch[1]) : 0;
      const eventsCount = eventMatch ? parseInt(eventMatch[1]) : 0;
      
      animateNumber(metricEmails, emailsCount);
      animateNumber(metricEvents, eventsCount);
      animateNumber(metricDrafts, draftsCount);
    }
  }

  // Number animation helper for premium feel
  function animateNumber(element, targetVal) {
    let current = 0;
    const duration = 800; // ms
    const stepTime = Math.abs(Math.floor(duration / targetVal)) || 50;
    
    if (targetVal === 0) {
      element.textContent = '0';
      return;
    }
    
    const timer = setInterval(() => {
      current += 1;
      element.textContent = current;
      if (current >= targetVal) {
        clearInterval(timer);
        element.textContent = targetVal;
      }
    }, stepTime);
  }
});
