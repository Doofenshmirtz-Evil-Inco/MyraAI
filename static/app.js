let ws; let recognition; let isListening = false;
function initWebSocket() {
    ws = new WebSocket((window.location.protocol === 'https:' ? 'wss:' : 'ws:') + '//' + window.location.host + '/ws/log');
    ws.onopen = () => document.getElementById('connectionStatus').innerText = 'Connected';
    ws.onmessage = (e) => { const d = JSON.parse(e.data); if (d.status === 'success') document.getElementById('statusText').innerText = 'Logged: ' + d.entry.Title; };
    ws.onclose = () => setTimeout(initWebSocket, 3000);
}
initWebSocket();
function toggleRecording() {
    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
        alert("Speech recognition not supported. Use Chrome/Edge.");
        return;
    }
    if (isListening) stopListening(); else startListening();
}
function startListening() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    recognition = new SpeechRecognition();
    recognition.continuous = true; recognition.interimResults = true; recognition.lang = 'en-US';
    recognition.onstart = () => { isListening = true; document.getElementById('statusText').innerText = "Listening..."; };
    recognition.onresult = (event) => {
        const result = event.results[event.results.length - 1];
        const transcript = result[0].transcript.trim();
        document.getElementById('liveTranscript').innerText = transcript || 'Listening...';
        if (result.isFinal && transcript && ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ transcript: transcript }));
        }
    };
    recognition.onerror = (e) => { if (e.error === 'not-allowed') document.getElementById('statusText').innerText = "Mic denied"; };
    recognition.onend = () => { if (isListening) { try { recognition.start(); } catch (e) {} } else { document.getElementById('statusText').innerText = "Stopped"; } };
    recognition.start();
}
function stopListening() { isListening = false; if (recognition) recognition.stop(); document.getElementById('statusText').innerText = "Stopped"; }
