// Listen for messages from the popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    console.log('[YT-RAG] Content script received message:', request);
    
    if (request.action === "checkVideo") {
        const url = window.location.href;
        console.log('[YT-RAG] Current URL:', url);
        
        const videoId = extractVideoId(url);
        console.log('[YT-RAG] Extracted video ID:', videoId);
        
        const response = { 
            isVideo: !!videoId,
            videoId: videoId,
            url: url
        };
        console.log('[YT-RAG] Sending response:', response);
        
        sendResponse(response);
        return true; // Required for async response
    }
});

// Extract video ID from URL
function extractVideoId(url) {
    console.log('[YT-RAG] Attempting to extract video ID from:', url);
    
    const patterns = [
        /(?:v=|\/)([0-9A-Za-z_-]{11}).*/,
        /(?:youtu\.be\/)([0-9A-Za-z_-]{11})/
    ];
    
    for (const pattern of patterns) {
        console.log('[YT-RAG] Trying pattern:', pattern);
        const match = url.match(pattern);
        if (match) {
            console.log('[YT-RAG] Found match:', match[1]);
            return match[1];
        }
    }
    console.log('[YT-RAG] No video ID found');
    return null;
} 