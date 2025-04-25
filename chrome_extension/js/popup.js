document.addEventListener('DOMContentLoaded', () => {
    console.log('[YT-RAG] Popup initialized');
    
    const indexButton = document.getElementById('indexButton');
    const searchQuery = document.getElementById('searchQuery');
    const searchButton = document.getElementById('searchButton');
    const indexStatus = document.getElementById('indexStatus');
    const searchStatus = document.getElementById('searchStatus');
    const resultsDiv = document.getElementById('results');
    const spinner = document.getElementById('searchSpinner');
    const waitingMessage = document.getElementById('waitingMessage');

    let currentTab = null;
    let statusCheckInterval = null;
    
    // Status colors for different states
    const statusColors = {
        pending: '#ffd700',        // Gold
        fetching_metadata: '#87ceeb', // Sky Blue
        fetching_transcript: '#98fb98', // Pale Green
        indexing: '#dda0dd',      // Plum
        completed: '#90ee90',      // Light Green
        failed: '#ff6b6b'         // Light Red
    };

    // Configure marked.js
    marked.setOptions({
        highlight: function(code, lang) {
            if (lang && hljs.getLanguage(lang)) {
                return hljs.highlight(code, { language: lang }).value;
            }
            return hljs.highlightAuto(code).value;
        },
        breaks: true,
        gfm: true
    });
    
    // Check if current page is a video
    console.log('[YT-RAG] Querying active tab');
    chrome.tabs.query({active: true, currentWindow: true}, (tabs) => {
        if (!tabs || !tabs[0]) {
            console.error('[YT-RAG] No active tab found');
            showStatus(indexStatus, "Error: Cannot access current tab", "error");
            return;
        }

        console.log('[YT-RAG] Active tab:', tabs[0].url);
        
        currentTab = tabs[0];
        const url = currentTab.url;
        if (url && url.includes('youtube.com/watch')) {
            console.log('[YT-RAG] Valid video detected, enabling button');
            indexButton.disabled = false;
            indexButton.dataset.url = url;
            showStatus(indexStatus, "Ready to index this video ✨", "success");
        } else {
            console.log('[YT-RAG] Not a valid video page');
            showStatus(indexStatus, "Please navigate to a YouTube video", "error");
        }
    });
    
    function updateStatusUI(status) {
        indexStatus.style.display = 'block';
        indexStatus.style.background = `linear-gradient(45deg, ${statusColors[status.status]}22, ${statusColors[status.status]}11)`;
        indexStatus.style.borderColor = statusColors[status.status];
        
        let statusText = status.message;
        if (status.status === 'indexing') {
            statusText += ` (${status.elapsed_seconds}s elapsed)`;
        }
        
        indexStatus.textContent = statusText;
        
        if (status.status === 'completed') {
            clearInterval(statusCheckInterval);
            setTimeout(() => {
                indexButton.disabled = false;
            }, 2000);
        } else if (status.status === 'failed') {
            clearInterval(statusCheckInterval);
            indexButton.disabled = false;
            if (status.error) {
                console.error('Indexing error:', status.error);
            }
        }
    }
    
    async function checkIndexingStatus(operationId) {
        try {
            const response = await fetch(`http://localhost:5000/indexing_status/${operationId}`);
            if (!response.ok) {
                throw new Error('Failed to fetch status');
            }
            const status = await response.json();
            updateStatusUI(status);
        } catch (error) {
            console.error('Error checking indexing status:', error);
            clearInterval(statusCheckInterval);
            indexButton.disabled = false;
            showStatus(indexStatus, "Error checking status", "error");
        }
    }
    
    // Handle indexing
    indexButton.addEventListener('click', async () => {
        const url = currentTab.url;
        if (!url) return;
        
        try {
            indexButton.disabled = true;
            showStatus(indexStatus, "Starting indexing operation...", "pending");
            
            const response = await fetch('http://localhost:5000/index_video', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ url })
            });
            
            const data = await response.json();
            
            if (response.ok) {
                // Start polling for status updates
                statusCheckInterval = setInterval(() => {
                    checkIndexingStatus(data.operation_id);
                }, 2000);
            } else {
                throw new Error(data.error || "Failed to index video");
            }
        } catch (error) {
            showStatus(indexStatus, `Error: ${error.message}`, "error");
            indexButton.disabled = false;
        }
    });
    
    // Handle search
    searchButton.addEventListener('click', async () => {
        const query = searchQuery.value.trim();
        if (!query) return;
        
        try {
            searchButton.disabled = true;
            resultsDiv.innerHTML = "";
            spinner.style.display = "block";
            waitingMessage.style.display = "block";
            waitingMessage.textContent = getRandomWaitingMessage();
            searchStatus.style.display = "none";
            
            const response = await fetch('http://localhost:5000/query', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ query })
            });
            
            const data = await response.json();
            
            if (response.ok && data.status === 'success') {
                resultsDiv.innerHTML = '';
                
                // Add the main answer section
                const answerDiv = document.createElement('div');
                answerDiv.className = 'main-answer';
                answerDiv.innerHTML = `
                    <h3>Answer:</h3>
                    <div class="answer-content">${marked.parse(data.answer)}</div>
                `;
                resultsDiv.appendChild(answerDiv);
                
                // Add sources section if available
                if (data.sources && data.sources.length > 0) {
                    const sourcesDiv = document.createElement('div');
                    sourcesDiv.className = 'sources-section';
                    sourcesDiv.innerHTML = '<h3>Sources:</h3>';
                    resultsDiv.appendChild(sourcesDiv);
                    
                    data.sources.forEach(source => {
                        const sourceDiv = document.createElement('div');
                        sourceDiv.className = 'source-item';
                        
                        const timestamp = Math.floor(source.timestamp);
                        const videoUrl = `${source.url}&t=${timestamp}s`;
                        
                        sourceDiv.innerHTML = `
                            <div class="source-text">${marked.parse(source.text)}</div>
                            <div class="source-link">
                                <a href="${videoUrl}" target="_blank">
                                    ${source.video_title} (${formatTime(timestamp)})
                                </a>
                            </div>
                            <div class="divider"></div>
                        `;
                        
                        sourcesDiv.appendChild(sourceDiv);
                    });
                }
                
                // Apply syntax highlighting
                document.querySelectorAll('pre code').forEach((block) => {
                    hljs.highlightElement(block);
                });
            } else {
                throw new Error(data.error || "Search failed");
            }
        } catch (error) {
            showStatus(searchStatus, `Error: ${error.message}`, "error");
        } finally {
            searchButton.disabled = false;
            spinner.style.display = "none";
            waitingMessage.style.display = "none";
        }
    });

    // Handle Enter key in search input
    searchQuery.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            searchButton.click();
        }
    });
});

function formatTime(seconds) {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = Math.floor(seconds % 60);
    return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
}

function showStatus(element, message, type) {
    element.textContent = message;
    element.className = `status ${type}`;
    element.style.display = "block";
    
    if (type === "success") {
        setTimeout(() => {
            element.style.display = "none";
        }, 3000);
    }
}

function getRandomWaitingMessage() {
    const messages = [
        "Searching through video transcripts... 🔍",
        "Processing your query... 💭",
        "Finding relevant moments... ⏳",
        "Analyzing video content... 🎥",
        "Looking for the perfect answer... 🎯",
        "Connecting the dots... 🔗",
        "Almost there... ✨"
    ];
    return messages[Math.floor(Math.random() * messages.length)];
} 