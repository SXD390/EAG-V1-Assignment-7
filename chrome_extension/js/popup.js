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
    const indexedVideosHeader = document.getElementById('indexedVideosHeader');
    const indexedVideosContent = document.getElementById('indexedVideosContent');
    const videoList = document.getElementById('videoList');

    let currentTab = null;
    let statusCheckInterval = null;
    let videosLoaded = false;
    
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
    
    // Load saved query if exists
    chrome.storage.local.get(['savedQuery'], (result) => {
        if (result.savedQuery) {
            searchQuery.value = result.savedQuery;
            console.log('[YT-RAG] Loaded saved query:', result.savedQuery);
        }
    });
    
    // Save query as user types
    searchQuery.addEventListener('input', () => {
        const query = searchQuery.value;
        chrome.storage.local.set({ savedQuery: query }, () => {
            console.log('[YT-RAG] Saved query:', query);
        });
    });
    
    // Check if there's an ongoing indexing operation
    chrome.storage.local.get(['ongoingOperation'], (result) => {
        if (result.ongoingOperation) {
            console.log('[YT-RAG] Found ongoing operation:', result.ongoingOperation);
            // Resume status checking
            statusCheckInterval = setInterval(() => {
                checkIndexingStatus(result.ongoingOperation.id);
            }, 2000);
            
            // Disable index button while operation is in progress
            indexButton.disabled = true;
            
            // Show last known status if available
            if (result.ongoingOperation.lastStatus) {
                updateStatusUI(result.ongoingOperation.lastStatus);
            } else {
                showStatus(indexStatus, "Checking operation status...", "pending");
            }
        }
    });
    
    // Handle collapsible section
    indexedVideosHeader.addEventListener('click', () => {
        const isOpen = indexedVideosContent.style.display === 'block';
        const toggleIcon = indexedVideosHeader.querySelector('.toggle-icon');
        
        if (isOpen) {
            indexedVideosContent.style.display = 'none';
            toggleIcon.style.transform = 'rotate(0deg)';
        } else {
            indexedVideosContent.style.display = 'block';
            toggleIcon.style.transform = 'rotate(180deg)';
            
            // Fetch videos if they haven't been loaded yet
            if (!videosLoaded) {
                fetchIndexedVideos();
            }
        }
    });
    
    // Fetch indexed videos
    async function fetchIndexedVideos() {
        try {
            const loadingIndicator = indexedVideosContent.querySelector('.loading-indicator');
            loadingIndicator.style.display = 'block';
            videoList.innerHTML = '';
            
            const response = await fetch('http://localhost:5000/list_indexed_videos');
            if (!response.ok) {
                throw new Error('Failed to fetch indexed videos');
            }
            
            const data = await response.json();
            
            if (response.ok && data.status === 'success') {
                loadingIndicator.style.display = 'none';
                
                if (data.videos && data.videos.length > 0) {
                    renderVideoList(data.videos);
                } else {
                    videoList.innerHTML = '<div class="no-videos">No videos have been indexed yet.</div>';
                }
                
                videosLoaded = true;
            } else {
                throw new Error(data.error || "Failed to load videos");
            }
        } catch (error) {
            console.error('Error fetching indexed videos:', error);
            videoList.innerHTML = `<div class="error-message">Error: ${error.message}</div>`;
            const loadingIndicator = indexedVideosContent.querySelector('.loading-indicator');
            loadingIndicator.style.display = 'none';
        }
    }
    
    // Render video list
    function renderVideoList(videos) {
        videoList.innerHTML = '';

        // Create wrapper
        const wrapper = document.createElement('div');
        wrapper.className = 'video-table-wrapper';

        // Create table
        const table = document.createElement('table');
        table.className = 'video-table';

        // Table header
        const thead = document.createElement('thead');
        const headerRow = document.createElement('tr');
        ['#', 'Title', 'Channel', 'Views', 'Duration'].forEach(col => {
            const th = document.createElement('th');
            th.textContent = col;
            headerRow.appendChild(th);
        });
        thead.appendChild(headerRow);
        table.appendChild(thead);

        // Table body
        const tbody = document.createElement('tbody');
        videos.forEach((video, index) => {
            const row = document.createElement('tr');

            // Number
            const numCell = document.createElement('td');
            numCell.textContent = index + 1;
            row.appendChild(numCell);

            // Title (clickable span)
            const titleCell = document.createElement('td');
            const titleSpan = document.createElement('span');
            titleSpan.className = 'video-title-table-link';
            titleSpan.textContent = video.title;
            titleSpan.tabIndex = 0;
            titleSpan.setAttribute('role', 'button');
            titleSpan.title = 'Open video in new tab';
            titleSpan.onclick = () => {
                window.open(video.url, '_blank');
            };
            titleSpan.onkeydown = (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    window.open(video.url, '_blank');
                }
            };
            titleCell.appendChild(titleSpan);
            row.appendChild(titleCell);

            // Channel
            const channelCell = document.createElement('td');
            channelCell.textContent = video.author;
            row.appendChild(channelCell);

            // Views
            const viewsCell = document.createElement('td');
            viewsCell.textContent = formatViews(video.views);
            row.appendChild(viewsCell);

            // Duration
            const durationCell = document.createElement('td');
            durationCell.textContent = formatTime(video.length);
            row.appendChild(durationCell);

            tbody.appendChild(row);
        });
        table.appendChild(tbody);
        wrapper.appendChild(table);
        videoList.appendChild(wrapper);
    }
    
    // Format view count
    function formatViews(views) {
        if (!views) return '0';
        
        if (views >= 1000000) {
            return (views / 1000000).toFixed(1) + 'M';
        } else if (views >= 1000) {
            return (views / 1000).toFixed(1) + 'K';
        } else {
            return views.toString();
        }
    }
    
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
            // Only enable the button if there's no ongoing operation
            chrome.storage.local.get(['ongoingOperation'], (result) => {
                if (!result.ongoingOperation) {
                    indexButton.disabled = false;
                    indexButton.dataset.url = url;
                    showStatus(indexStatus, "Ready to index this video ✨", "success");
                }
            });
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
        
        // Save the last status
        chrome.storage.local.get(['ongoingOperation'], (result) => {
            if (result.ongoingOperation) {
                const updatedOperation = {
                    ...result.ongoingOperation,
                    lastStatus: status
                };
                chrome.storage.local.set({ ongoingOperation: updatedOperation });
            }
        });
        
        if (status.status === 'completed' || status.status === 'failed') {
            clearInterval(statusCheckInterval);
            // Clear the ongoing operation from storage
            chrome.storage.local.remove('ongoingOperation', () => {
                console.log('[YT-RAG] Operation completed or failed, removed from storage');
            });
            
            setTimeout(() => {
                indexButton.disabled = false;
            }, 2000);
            
            // Refresh the video list if completed successfully
            if (status.status === 'completed' && videosLoaded) {
                setTimeout(() => {
                    fetchIndexedVideos();
                }, 1000);
            }
            
            if (status.status === 'failed' && status.error) {
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
            
            // Clear the ongoing operation on error
            chrome.storage.local.remove('ongoingOperation', () => {
                console.log('[YT-RAG] Error checking status, removed operation from storage');
            });
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
                // Save operation ID to Chrome storage
                const operation = {
                    id: data.operation_id,
                    startTime: Date.now(),
                    videoUrl: url
                };
                
                chrome.storage.local.set({ ongoingOperation: operation }, () => {
                    console.log('[YT-RAG] Saved operation to storage:', operation);
                });
                
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
    if (!seconds) return '0:00';
    
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = Math.floor(seconds % 60);
    
    if (minutes >= 60) {
        const hours = Math.floor(minutes / 60);
        const remainingMinutes = minutes % 60;
        return `${hours}:${remainingMinutes.toString().padStart(2, '0')}:${remainingSeconds.toString().padStart(2, '0')}`;
    }
    
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