/**
 * Audio Visualizer for Fullplayer
 * Inspired by Pear Desktop's visualizer plugin
 * 
 * Creates animated audio visualization using Web Audio API
 */

(function () {
    'use strict';

    let visualizerCanvas = null;
    let visualizerCtx = null;
    let animationId = null;
    let audioContext = null;
    let analyser = null;
    let dataArray = null;
    let bufferLength = 0;

    // Create visualizer canvas
    function createVisualizerCanvas() {
        // Check if canvas already exists
        visualizerCanvas = document.getElementById('fp-visualizer-canvas');
        if (visualizerCanvas) return visualizerCanvas;

        // Create canvas
        visualizerCanvas = document.createElement('canvas');
        visualizerCanvas.id = 'fp-visualizer-canvas';
        visualizerCanvas.style.position = 'absolute';
        visualizerCanvas.style.top = '0';
        visualizerCanvas.style.left = '0';
        visualizerCanvas.style.width = '100%';
        visualizerCanvas.style.height = '100%';
        visualizerCanvas.style.pointerEvents = 'none';
        visualizerCanvas.style.opacity = '0.3';
        visualizerCanvas.style.zIndex = '1';

        // Add to fullplayer
        const fullplayer = document.querySelector('.fullplayer-overlay');
        if (fullplayer) {
            fullplayer.appendChild(visualizerCanvas);
        }

        visualizerCtx = visualizerCanvas.getContext('2d');
        resizeCanvas();
        window.addEventListener('resize', resizeCanvas);

        return visualizerCanvas;
    }

    function resizeCanvas() {
        if (!visualizerCanvas) return;
        const dpr = window.devicePixelRatio || 1;
        visualizerCanvas.width = window.innerWidth * dpr;
        visualizerCanvas.height = window.innerHeight * dpr;
        visualizerCtx.scale(dpr, dpr);
    }

    // Initialize audio analyzer (simplified - no actual audio connection)
    // This creates a visual effect without needing audio access
    function initSimulatedVisualizer() {
        bufferLength = 64;
        dataArray = new Uint8Array(bufferLength);

        // Simulate audio data with smooth random values
        let phase = 0;
        setInterval(() => {
            const bassBoost = Math.sin(phase) * 50 + 128;
            for (let i = 0; i < bufferLength; i++) {
                const freq = i / bufferLength;
                const amplitude = Math.sin(phase + freq * 10) * 50 + bassBoost;
                dataArray[i] = Math.max(0, Math.min(255, amplitude + (Math.random() * 20 - 10)));
            }
            phase += 0.05;
        }, 50);
    }

    // Draw frequency bars visualization
    function drawBars() {
        if (!visualizerCtx || !dataArray) return;

        const width = window.innerWidth;
        const height = window.innerHeight;

        visualizerCtx.clearRect(0, 0, width, height);

        const barWidth = (width / bufferLength) * 2;
        let barHeight;
        let x = 0;

        // Get ambient color if available
        const fullplayer = document.querySelector('.fullplayer-overlay');
        const r = fullplayer ? fullplayer.style.getPropertyValue('--ambient-r') || 100 : 100;
        const g = fullplayer ? fullplayer.style.getPropertyValue('--ambient-g') || 255 : 255;
        const b = fullplayer ? fullplayer.style.getPropertyValue('--ambient-b') || 136 : 136;

        for (let i = 0; i < bufferLength; i++) {
            barHeight = (dataArray[i] / 255) * height * 0.4;

            // Create gradient for bars
            const gradient = visualizerCtx.createLinearGradient(0, height - barHeight, 0, height);
            gradient.addColorStop(0, `rgba(${r}, ${g}, ${b}, 0.8)`);
            gradient.addColorStop(1, `rgba(${r}, ${g}, ${b}, 0.3)`);

            visualizerCtx.fillStyle = gradient;
            visualizerCtx.fillRect(x, height - barHeight, barWidth, barHeight);

            x += barWidth + 2;
        }
    }

    // Draw waveform visualization
    function drawWaveform() {
        if (!visualizerCtx || !dataArray) return;

        const width = window.innerWidth;
        const height = window.innerHeight;

        visualizerCtx.clearRect(0, 0, width, height);

        // Get ambient color
        const fullplayer = document.querySelector('.fullplayer-overlay');
        const r = fullplayer ? fullplayer.style.getPropertyValue('--ambient-r') || 100 : 100;
        const g = fullplayer ? fullplayer.style.getPropertyValue('--ambient-g') || 255 : 255;
        const b = fullplayer ? fullplayer.style.getPropertyValue('--ambient-b') || 136 : 136;

        visualizerCtx.lineWidth = 3;
        visualizerCtx.strokeStyle = `rgba(${r}, ${g}, ${b}, 0.6)`;
        visualizerCtx.beginPath();

        const sliceWidth = width / bufferLength;
        let x = 0;

        for (let i = 0; i < bufferLength; i++) {
            const v = dataArray[i] / 128.0;
            const y = v * height / 3 + height / 2;

            if (i === 0) {
                visualizerCtx.moveTo(x, y);
            } else {
                visualizerCtx.lineTo(x, y);
            }

            x += sliceWidth;
        }

        visualizerCtx.stroke();
    }

    // Animation loop
    function animate() {
        drawBars(); // Can switch to drawWaveform() for different effect
        animationId = requestAnimationFrame(animate);
    }

    // Start visualizer
    function startVisualizer() {
        if (animationId) return; // Already running

        createVisualizerCanvas();
        initSimulatedVisualizer();
        animate();
    }

    // Stop visualizer
    function stopVisualizer() {
        if (animationId) {
            cancelAnimationFrame(animationId);
            animationId = null;
        }
        if (visualizerCtx && visualizerCanvas) {
            visualizerCtx.clearRect(0, 0, visualizerCanvas.width, visualizerCanvas.height);
        }
    }

    // Monitor fullplayer state
    function initVisualizerMonitor() {
        const fullplayer = document.getElementById('fullplayer');
        if (!fullplayer) return;

        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                if (mutation.attributeName === 'class') {
                    if (fullplayer.classList.contains('active')) {
                        setTimeout(startVisualizer, 300); // Delay for smooth transition
                    } else {
                        stopVisualizer();
                    }
                }
            });
        });

        observer.observe(fullplayer, { attributes: true, attributeFilter: ['class'] });

        // Start if already open
        if (fullplayer.classList.contains('active')) {
            startVisualizer();
        }
    }

    // Initialize
    function init() {
        setTimeout(() => {
            initVisualizerMonitor();
        }, 1000);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
