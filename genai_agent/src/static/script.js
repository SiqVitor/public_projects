document.addEventListener('DOMContentLoaded', async () => {
    // Background Interaction
    document.addEventListener('mousemove', (e) => {
        const x = (e.clientX / window.innerWidth) * 100;
        const y = (e.clientY / window.innerHeight) * 100;
        document.body.style.setProperty('--mouse-x', `${x}%`);
        document.body.style.setProperty('--mouse-y', `${y}%`);
    });

    const chatForm = document.getElementById('chat-form');
    const userInput = document.getElementById('user-input');

    // Auto-resize textarea
    userInput.addEventListener('input', () => {
        userInput.style.height = 'auto';
        userInput.style.height = userInput.scrollHeight + 'px';
    });

    // Handle Shift+Enter for new line, Enter for submit (Desktop only)
    userInput.addEventListener('keydown', (e) => {
        const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);

        if (e.key === 'Enter') {
            if (isMobile) {
                // On mobile, Enter always inserts newline
                return;
            }

            if (!e.shiftKey) {
                e.preventDefault();
                chatForm.dispatchEvent(new Event('submit'));
            }
        }
    });

    const chatWindow = document.getElementById('chat-window');
    const csvUpload = document.getElementById('csv-upload');
    const filePreview = document.getElementById('file-preview');
    const fileNameSpan = document.getElementById('file-name');
    const removeFileBtn = document.getElementById('remove-file');
    const typingIndicator = document.getElementById('typing-indicator');
    const sendBtn = document.getElementById('send-btn');
    const sendLabel = document.getElementById('send-label');
    const cancelLabel = document.getElementById('cancel-label');
    const attachLabel = document.getElementById('attach-label');
    const errorToast = document.getElementById('error-toast');
    const errorMessage = document.getElementById('error-message');

    let currentFilePath = null;
    let isProcessing = false;
    let abortController = null;

    // Reset session on page load
    fetch('/reset', { method: 'POST' });

    // --- File Handling (CSV/PDF) ---
    csvUpload.addEventListener('change', async (e) => {
        if (isProcessing) return;
        const file = e.target.files[0];
        if (!file) return;

        const formData = new FormData();
        formData.append('file', file);

        try {
            const res = await fetch('/upload', { method: 'POST', body: formData });
            const data = await res.json();

            currentFilePath = data.path;
            fileNameSpan.textContent = data.filename;
            filePreview.style.display = 'block';

            // Adjust icon for PDF
            const fileIcon = filePreview.querySelector('.file-icon');
            if (file.name.endsWith('.pdf')) {
                fileIcon.textContent = 'PDF:';
            } else {
                fileIcon.textContent = 'Data:';
            }
        } catch (err) {
            console.error("Upload failed", err);
        }
    });

    removeFileBtn.addEventListener('click', () => {
        if (isProcessing) return;
        currentFilePath = null;
        filePreview.style.display = 'none';
        csvUpload.value = '';
    });

    // --- Chat Intelligence ---
    chatForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        if (isProcessing) {
            if (abortController) abortController.abort();
            return;
        }

        const text = userInput.value.trim();
        if (!text) return;

        hideError();
        setLoadingState(true);
        addMessage(text, 'user');
        userInput.value = '';
        userInput.style.height = 'auto';

        abortController = new AbortController();
        const formData = new FormData();
        formData.append('message', text);
        if (currentFilePath) formData.append('file_path', currentFilePath);

        try {
            const response = await fetch('/chat', {
                method: 'POST',
                body: formData,
                signal: abortController.signal
            });

            if (response.status === 429) {
                const reader = response.body.getReader();
                const { value } = await reader.read();
                const errText = new TextDecoder().decode(value).replace("ERROR: ", "");
                showError(errText);
                chatWindow.lastElementChild.remove(); // Remove the user message if it failed
                return;
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();

            const agentMsgDiv = addMessage('', 'agent');
            let fullText = '';

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                let chunk = decoder.decode(value);

                // Signal Detection for Session Warning
                if (chunk.includes("[[TOKEN_WARNING]]")) {
                    showError("Session limit approaching. Consider resetting the chat for optimal performance.");
                    chunk = chunk.replace("[[TOKEN_WARNING]]", "");
                }

                if (chunk.startsWith("ERROR: ")) {
                    showError(chunk.replace("ERROR: ", ""));
                    agentMsgDiv.remove();
                    break;
                }

                // Typewriter Logic
                // We split the chunk into characters and append them one by one
                // utilizing a small delay to create the effect.
                for (const char of chunk) {
                    fullText += char;
                    agentMsgDiv.innerHTML = formatAIResponse(fullText);
                    scrollToBottom();
                    // 5ms delay per character implies ~200 chars/sec (fast but readable)
                    // Adjust this value to change typing speed
                    await new Promise(resolve => setTimeout(resolve, 5));
                }
            }
        } catch (err) {
            if (err.name === 'AbortError') {
                addMessage('_Response cancelled._', 'system-msg');
            } else {
                showError('Connection lost. Please try again.');
            }
        } finally {
            setLoadingState(false);
            abortController = null;
        }
    });

    function setLoadingState(loading) {
        isProcessing = loading;
        if (loading) {
            typingIndicator.classList.add('active');
            userInput.disabled = true;
            sendLabel.style.display = 'none';
            cancelLabel.style.display = 'inline';
            sendBtn.classList.add('cancel-state');
            attachLabel.style.opacity = '0.3';
            attachLabel.style.pointerEvents = 'none';
        } else {
            typingIndicator.classList.remove('active');
            userInput.disabled = false;
            sendLabel.style.display = 'inline';
            cancelLabel.style.display = 'none';
            sendBtn.classList.remove('cancel-state');
            attachLabel.style.opacity = '1';
            attachLabel.style.pointerEvents = 'auto';
            userInput.focus();
        }
        scrollToBottom();
    }

    function showError(msg) {
        errorMessage.textContent = msg;
        errorToast.style.display = 'block';
        setTimeout(hideError, 8000);
    }

    function hideError() {
        errorToast.style.display = 'none';
    }

    function addMessage(text, side) {
        const div = document.createElement('div');
        div.className = `message ${side}`;
        div.innerHTML = formatAIResponse(text);
        chatWindow.appendChild(div);
        scrollToBottom();
        return div;
    }

    function scrollToBottom() {
        chatWindow.scrollTo({ top: chatWindow.scrollHeight, behavior: 'smooth' });
    }

    function formatAIResponse(text) {
        if (!text) return '...';
        return text
            .replace(/\n/g, '<br>')
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/`(.*?)`/g, '<code style="background: rgba(255,255,255,0.1); padding: 2px 4px; border-radius: 4px;">$1</code>');
    }
});
