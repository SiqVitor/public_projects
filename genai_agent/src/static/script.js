document.addEventListener('DOMContentLoaded', () => {
    const chatForm = document.getElementById('chat-form');
    const userInput = document.getElementById('user-input');
    const chatWindow = document.getElementById('chat-window');
    const csvUpload = document.getElementById('csv-upload');
    const filePreview = document.getElementById('file-preview');
    const fileNameSpan = document.getElementById('file-name');
    const removeFileBtn = document.getElementById('remove-file');

    let currentFilePath = null;

    // --- Navigation Logic ---
    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const section = btn.dataset.section;
            document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            document.querySelectorAll('section').forEach(s => s.classList.remove('active-section'));
            document.getElementById(`${section}-section`).classList.add('active-section');

            if (section === 'dashboard') updateMetrics();
        });
    });

    // --- Chat & CSV Logic ---
    csvUpload.addEventListener('change', async (e) => {
        const file = e.target.files[0];
        if (!file) return;

        const formData = new FormData();
        formData.append('file', file);

        const res = await fetch('/upload', { method: 'POST', body: formData });
        const data = await res.json();

        currentFilePath = data.path;
        fileNameSpan.textContent = data.filename;
        filePreview.style.display = 'flex';
    });

    removeFileBtn.addEventListener('click', () => {
        currentFilePath = null;
        filePreview.style.display = 'none';
        csvUpload.value = '';
    });

    chatForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const text = userInput.value.trim();
        if (!text) return;

        addMessage(text, 'user');
        userInput.value = '';

        const formData = new FormData();
        formData.append('message', text);
        if (currentFilePath) formData.append('file_path', currentFilePath);

        const response = await fetch('/chat', { method: 'POST', body: formData });
        const reader = response.body.getReader();
        const decoder = new TextDecoder();

        const agentMsgDiv = addMessage('', 'agent');
        let fullText = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            fullText += decoder.decode(value);
            agentMsgDiv.textContent = fullText;
            chatWindow.scrollTop = chatWindow.scrollHeight;
        }
    });

    function addMessage(text, side) {
        const div = document.createElement('div');
        div.className = `message ${side}`;
        div.textContent = text;
        chatWindow.appendChild(div);
        chatWindow.scrollTop = chatWindow.scrollHeight;
        return div;
    }

    // --- Metrics & Simulation ---
    async function updateMetrics() {
        const res = await fetch('/metrics');
        const data = await res.json();

        const ml = data.ml_platform;
        const rt = data.realtime_ml;

        if (rt && rt.metrics && rt.metrics.p99) {
            document.getElementById('p99-latency').textContent = `${rt.metrics.p99.toFixed(2)} ms`;
        }

        if (ml && ml.registered_version) {
            document.getElementById('model-version').textContent = `v${ml.registered_version}`;
        }

        if (ml && ml.validation && ml.validation.checks) {
            const psiCheck = ml.validation.checks.find(c => c.check === "data_drift_psi");
            if (psiCheck) {
                const match = psiCheck.detail.match(/psi=([\d.]+)/);
                if (match) {
                    const psiValue = parseFloat(match[1]);
                    document.getElementById('psi-status').textContent = psiValue.toFixed(3);
                    document.getElementById('psi-status').style.color = psiValue < 0.2 ? '#4ade80' : '#fb7185';
                }
            }
        }
    }

    document.getElementById('run-ml-all').addEventListener('click', async () => {
        const logBox = document.getElementById('log-output');
        logBox.textContent = "[*] Fetching simulation stream...\n";

        try {
            const response = await fetch('/run-simulation');
            const reader = response.body.getReader();
            const decoder = new TextDecoder();

            logBox.textContent = ""; // Clear for real logs

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                logBox.textContent += decoder.decode(value);
                logBox.scrollTop = logBox.scrollHeight;
            }

            await updateMetrics();
        } catch (err) {
            logBox.textContent += `\n[ERROR] Simulation failed: ${err.message}`;
        }
    });
});
