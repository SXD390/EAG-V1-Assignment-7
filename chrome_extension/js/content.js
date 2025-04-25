// Listen for messages from the popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "checkVideo") {
        const videoId = extractVideoId(window.location.href);
        sendResponse({ 
            isVideo: !!videoId,
            videoId: videoId,
            url: window.location.href
        });
    }
});

// Extract video ID from URL
function extractVideoId(url) {
    const patterns = [
        /(?:v=|\/)([0-9A-Za-z_-]{11}).*/,
        /(?:youtu\.be\/)([0-9A-Za-z_-]{11})/
    ];
    
    for (const pattern of patterns) {
        const match = url.match(pattern);
        if (match) {
            return match[1];
        }
    }
    return null;
} 