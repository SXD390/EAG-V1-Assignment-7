// Simple markdown parser implementation
const simpleMarkdown = {
  options: {
    highlight: null
  },
  
  setOptions: function(opts) {
    if (opts && opts.highlight) {
      this.options.highlight = opts.highlight;
    }
    return this;
  },
  
  parse: function(text) {
    if (!text) return '';
    
    // Convert headers
    text = text.replace(/^### (.*$)/gm, '<h3>$1</h3>');
    text = text.replace(/^## (.*$)/gm, '<h2>$1</h2>');
    text = text.replace(/^# (.*$)/gm, '<h1>$1</h1>');
    
    // Convert bold
    text = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    
    // Convert italic
    text = text.replace(/\*(.*?)\*/g, '<em>$1</em>');
    
    // Convert inline code
    text = text.replace(/`(.*?)`/g, '<code>$1</code>');
    
    // Convert code blocks
    text = text.replace(/```([\s\S]*?)```/g, (match, code) => {
      // If highlight function is provided, use it
      if (this.options.highlight) {
        try {
          const highlighted = this.options.highlight(code);
          return `<pre><code>${highlighted}</code></pre>`;
        } catch (e) {
          console.error('Error highlighting code:', e);
        }
      }
      return '<pre><code>' + code.trim() + '</code></pre>';
    });
    
    // Convert links
    text = text.replace(/\[(.*?)\]\((.*?)\)/g, '<a href="$2">$1</a>');
    
    // Convert lists
    text = text.replace(/^\s*[-*+]\s+(.*)/gm, '<li>$1</li>');
    text = text.replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>');
    
    // Convert paragraphs
    text = text.replace(/^(?!<[houil])\s*([^\n]+)\s*$/gm, '<p>$1</p>');
    
    return text;
  }
};

// Make it available globally
window.marked = {
  setOptions: function(opts) {
    return simpleMarkdown.setOptions(opts);
  },
  parse: function(text) {
    return simpleMarkdown.parse(text);
  }
}; 