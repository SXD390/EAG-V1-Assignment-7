document.addEventListener('DOMContentLoaded', () => {
    const indexButton = document.getElementById('indexButton');
    const searchQuery = document.getElementById('searchQuery');
    const searchButton = document.getElementById('searchButton');
    const indexStatus = document.getElementById('indexStatus');
    const searchStatus = document.getElementById('searchStatus');
    const resultsDiv = document.getElementById('results');
    const spinner = document.getElementById('searchSpinner');
    const waitingMessage = document.getElementById('waitingMessage');

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
    chrome.tabs.query({active: true, currentWindow: true}, (tabs) => {
        chrome.tabs.sendMessage(tabs[0].id, {action: "checkVideo"}, (response) => {
            if (response && response.isVideo) {
                indexButton.disabled = false;
                indexButton.dataset.url = response.url;
            }
        });
    });
    
    // Handle indexing
    indexButton.addEventListener('click', async () => {
        const url = indexButton.dataset.url;
        if (!url) return;
        
        try {
            indexButton.disabled = true;
            showStatus(indexStatus, "Indexing video...", "pending");
            
            const response = await fetch('http://localhost:5000/index_video', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ url })
            });
            
            const data = await response.json();
            
            if (response.ok) {
                showStatus(indexStatus, "Video indexed successfully! ✨", "success");
            } else {
                throw new Error(data.error || "Failed to index video");
            }
        } catch (error) {
            showStatus(indexStatus, `Error: ${error.message}`, "error");
        } finally {
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
            
            const response = await fetch('http://localhost:5000/query', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ query })
            });
            
            const data = await response.json();
            
            if (response.ok) {
                // Render markdown content
                const answer = marked.parse(data.answer);
                const sources = data.sources.map(source => `
                    <div class="source">
                        <a href="${source.url}" target="_blank">
                            ${source.video_title} (${formatTime(source.timestamp)})
                        </a>
                    </div>
                `).join('');
                
                resultsDiv.innerHTML = `
                    <div class="answer">${answer}</div>
                    <h4>Sources:</h4>
                    ${sources}
                `;

                // Initialize syntax highlighting
                document.querySelectorAll('pre code').forEach((block) => {
                    hljs.highlightBlock(block);
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
    const remainingSeconds = seconds % 60;
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