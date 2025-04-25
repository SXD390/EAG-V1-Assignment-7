// Simple syntax highlighter implementation
const simpleHighlight = {
  highlightAll: function() {
    document.querySelectorAll('pre code').forEach((block) => {
      // Add a basic highlighting class
      block.classList.add('highlighted');
      
      const code = block.textContent;
      
      // Simple syntax highlighting for common programming elements
      let highlighted = code
        // Highlight strings
        .replace(/(["'])(.*?)\1/g, '<span class="string">$1$2$1</span>')
        // Highlight numbers
        .replace(/\b(\d+)\b/g, '<span class="number">$1</span>')
        // Highlight keywords
        .replace(/\b(function|return|if|else|for|while|var|let|const)\b/g, '<span class="keyword">$1</span>')
        // Highlight comments
        .replace(/(\/\/.*$)/gm, '<span class="comment">$1</span>')
        .replace(/(\/\*[\s\S]*?\*\/)/g, '<span class="comment">$1</span>');
      
      block.innerHTML = highlighted;
    });
  }
};

// Make it available globally
window.hljs = {
  highlightAll: simpleHighlight.highlightAll
}; 