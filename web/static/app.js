// Soniox Microphone Transcription - Client-side JavaScript

class MicrophoneTranscriber {
    constructor() {
        this.ws = null;
        this.audioContext = null;
        this.mediaStream = null;
        this.processor = null;
        this.isRecording = false;
        this.startTime = null;
        this.totalBytesSent = 0;
        this.wordCount = 0;
        this.transcriptionBuffer = [];

        // Get DOM elements
        this.deviceSelect = document.getElementById('deviceSelect');
        this.startBtn = document.getElementById('startBtn');
        this.stopBtn = document.getElementById('stopBtn');
        this.refreshDevices = document.getElementById('refreshDevices');
        this.clearBtn = document.getElementById('clearBtn');
        this.copyBtn = document.getElementById('copyBtn');
        this.statusIndicator = document.getElementById('statusIndicator');
        this.statusText = document.getElementById('statusText');
        this.transcriptionOutput = document.getElementById('transcriptionOutput');
        this.durationEl = document.getElementById('duration');
        this.wordCountEl = document.getElementById('wordCount');
        this.dataSentEl = document.getElementById('dataSent');
        this.audioCanvas = document.getElementById('audioCanvas');

        // Set up canvas for visualisation
        this.canvasCtx = this.audioCanvas.getContext('2d');
        this.canvasCtx.fillStyle = '#1e293b';
        this.canvasCtx.fillRect(0, 0, this.audioCanvas.width, this.audioCanvas.height);

        // Bind event handlers
        this.startBtn.addEventListener('click', () => this.startRecording());
        this.stopBtn.addEventListener('click', () => this.stopRecording());
        this.refreshDevices.addEventListener('click', () => this.loadDevices());
        this.clearBtn.addEventListener('click', () => this.clearTranscription());
        this.copyBtn.addEventListener('click', () => this.copyTranscription());

        // Initialise
        this.loadDevices();
        this.updateStatus('Ready', false);
    }

    async loadDevices() {
        try {
            const response = await fetch('/api/devices');
            const data = await response.json();

            this.deviceSelect.innerHTML = '';

            if (data.error) {
                this.deviceSelect.innerHTML = `<option value="">Error: ${data.error}</option>`;
                return;
            }

            if (data.devices.length === 0) {
                this.deviceSelect.innerHTML = '<option value="">No microphones found</option>';
                return;
            }

            data.devices.forEach(device => {
                const option = document.createElement('option');
                option.value = device.index;
                option.textContent = `${device.name} (${device.channels} channels)`;
                this.deviceSelect.appendChild(option);
            });

        } catch (error) {
            console.error('Failed to load devices:', error);
            this.deviceSelect.innerHTML = '<option value="">Failed to load devices</option>';
        }
    }

    async startRecording() {
        try {
            this.updateStatus('Requesting microphone access...', false);

            // Get microphone access
            this.mediaStream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true,
                    sampleRate: 16000,
                    channelCount: 1
                }
            });

            this.updateStatus('Connecting to server...', false);

            // Create WebSocket connection
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.host}/ws/transcribe`;
            this.ws = new WebSocket(wsUrl);

            this.ws.onopen = () => {
                this.updateStatus('Connected', true);
                this.setupAudioProcessing();
            };

            this.ws.onmessage = (event) => {
                this.handleTranscription(JSON.parse(event.data));
            };

            this.ws.onerror = (error) => {
                console.error('WebSocket error:', error);
                this.updateStatus('Connection error', false);
                this.stopRecording();
            };

            this.ws.onclose = () => {
                this.updateStatus('Disconnected', false);
            };

        } catch (error) {
            console.error('Failed to start recording:', error);
            alert(`Failed to access microphone: ${error.message}`);
            this.stopRecording();
        }
    }

    setupAudioProcessing() {
        try {
            // Create audio context
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)({
                sampleRate: 16000
            });

            const source = this.audioContext.createMediaStreamSource(this.mediaStream);

            // Create audio worklet processor for capturing audio
            this.processor = this.audioContext.createScriptProcessor(4096, 1, 1);

            this.processor.onaudioprocess = (event) => {
                if (!this.isRecording) return;

                const inputData = event.inputBuffer.getChannelData(0);

                // Convert float32 to int16 PCM
                const pcmData = this.float32ToInt16(inputData);

                // Send to server
                if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                    this.ws.send(pcmData);
                    this.totalBytesSent += pcmData.byteLength;
                    this.updateStats();
                }

                // Visualise audio level
                this.visualiseAudio(inputData);
            };

            source.connect(this.processor);
            this.processor.connect(this.audioContext.destination);

            // Start recording
            this.isRecording = true;
            this.startTime = Date.now();
            this.startBtn.disabled = true;
            this.stopBtn.disabled = false;
            this.updateStatus('Recording...', true);

            // Start duration timer
            this.durationInterval = setInterval(() => this.updateStats(), 1000);

        } catch (error) {
            console.error('Failed to set up audio processing:', error);
            this.stopRecording();
        }
    }

    float32ToInt16(float32Array) {
        const int16Array = new Int16Array(float32Array.length);
        for (let i = 0; i < float32Array.length; i++) {
            const s = Math.max(-1, Math.min(1, float32Array[i]));
            int16Array[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
        }
        return int16Array.buffer;
    }

    visualiseAudio(audioData) {
        // Calculate RMS (root mean square) for audio level
        let sum = 0;
        for (let i = 0; i < audioData.length; i++) {
            sum += audioData[i] * audioData[i];
        }
        const rms = Math.sqrt(sum / audioData.length);
        const level = Math.min(1, rms * 10); // Scale up for visibility

        // Draw on canvas
        const width = this.audioCanvas.width;
        const height = this.audioCanvas.height;

        this.canvasCtx.fillStyle = '#1e293b';
        this.canvasCtx.fillRect(0, 0, width, height);

        const barHeight = level * height;
        const gradient = this.canvasCtx.createLinearGradient(0, height - barHeight, 0, height);
        gradient.addColorStop(0, '#2563eb');
        gradient.addColorStop(1, '#7c3aed');

        this.canvasCtx.fillStyle = gradient;
        this.canvasCtx.fillRect(0, height - barHeight, width, barHeight);
    }

    stopRecording() {
        this.isRecording = false;

        // Stop duration timer
        if (this.durationInterval) {
            clearInterval(this.durationInterval);
        }

        // Close WebSocket
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }

        // Stop audio processing
        if (this.processor) {
            this.processor.disconnect();
            this.processor = null;
        }

        if (this.audioContext) {
            this.audioContext.close();
            this.audioContext = null;
        }

        // Stop media stream
        if (this.mediaStream) {
            this.mediaStream.getTracks().forEach(track => track.stop());
            this.mediaStream = null;
        }

        // Reset UI
        this.startBtn.disabled = false;
        this.stopBtn.disabled = true;
        this.updateStatus('Stopped', false);

        // Clear canvas
        this.canvasCtx.fillStyle = '#1e293b';
        this.canvasCtx.fillRect(0, 0, this.audioCanvas.width, this.audioCanvas.height);
    }

    handleTranscription(message) {
        if (message.type === 'error') {
            console.error('Transcription error:', message.message);
            alert(`Error: ${message.message}`);
            this.stopRecording();
            return;
        }

        if (message.type === 'ready') {
            console.log('Server ready to receive audio');
            return;
        }

        if (message.type === 'token') {
            // Add token to buffer
            this.transcriptionBuffer.push({
                text: message.text,
                isFinal: message.is_final,
                confidence: message.confidence
            });

            // Update word count
            if (message.is_final) {
                this.wordCount += message.text.trim().split(/\s+/).length;
            }

            // Render transcription
            this.renderTranscription();
            this.updateStats();
        }
    }

    renderTranscription() {
        // Clear placeholder
        if (this.transcriptionBuffer.length > 0) {
            this.transcriptionOutput.innerHTML = '';
        }

        // Group tokens by final/partial
        let html = '';
        let currentSentence = '';

        for (const token of this.transcriptionBuffer) {
            if (token.isFinal) {
                currentSentence += token.text + ' ';
            } else {
                if (currentSentence) {
                    html += `<span class="token final">${currentSentence}</span>`;
                    currentSentence = '';
                }
                html += `<span class="token partial">${token.text} </span>`;
            }
        }

        if (currentSentence) {
            html += `<span class="token final">${currentSentence}</span>`;
        }

        this.transcriptionOutput.innerHTML = html;

        // Auto-scroll to bottom
        this.transcriptionOutput.scrollTop = this.transcriptionOutput.scrollHeight;
    }

    clearTranscription() {
        this.transcriptionBuffer = [];
        this.wordCount = 0;
        this.transcriptionOutput.innerHTML = '<p class="placeholder">Your transcription will appear here...</p>';
        this.updateStats();
    }

    copyTranscription() {
        const text = this.transcriptionBuffer
            .filter(t => t.isFinal)
            .map(t => t.text)
            .join(' ')
            .trim();

        if (!text) {
            alert('Nothing to copy!');
            return;
        }

        navigator.clipboard.writeText(text).then(() => {
            this.copyBtn.textContent = '✓ Copied!';
            setTimeout(() => {
                this.copyBtn.textContent = '📋 Copy';
            }, 2000);
        }).catch(error => {
            console.error('Failed to copy:', error);
            alert('Failed to copy to clipboard');
        });
    }

    updateStatus(text, isRecording) {
        this.statusText.textContent = text;
        this.statusIndicator.className = 'status-indicator';

        if (isRecording) {
            this.statusIndicator.classList.add('recording');
        } else if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.statusIndicator.classList.add('connected');
        }
    }

    updateStats() {
        // Duration
        if (this.startTime) {
            const elapsed = Math.floor((Date.now() - this.startTime) / 1000);
            const minutes = Math.floor(elapsed / 60);
            const seconds = elapsed % 60;
            this.durationEl.textContent = `${minutes}:${seconds.toString().padStart(2, '0')}`;
        }

        // Word count
        this.wordCountEl.textContent = this.wordCount.toString();

        // Data sent
        const kb = (this.totalBytesSent / 1024).toFixed(1);
        this.dataSentEl.textContent = `${kb} KB`;
    }
}

// Initialise app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new MicrophoneTranscriber();
});
