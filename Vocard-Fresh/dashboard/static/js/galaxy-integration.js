// Visualizer Manager Integration - Connects visualizer to player state
(function () {
    'use strict';

    let visualizerManager = null;
    let updateInterval = null;

    // Initialize visualizer manager when fullplayer opens
    function initVisualizer() {
        if (!window.VisualizerManager) {
            console.warn('VisualizerManager not loaded');
            return;
        }

        if (!visualizerManager) {
            visualizerManager = new VisualizerManager('fp-galaxy-canvas');
            console.log('Visualizer manager initialized with multiple effects');

            // Expose globally for UI controls
            window.fpVisualizer = visualizerManager;
        }

        startVisualizerUpdates();
    }

    // Update visualizer with current playback state
    function updateVisualizer() {
        if (!visualizerManager || typeof player === 'undefined') return;

        try {
            const position = player.currentPosition || 0; // Already in ms
            const volume = player.volume ? player.volume / 100 : 0.5;
            const isPlaying = !player.isPaused;

            // Try to get BPM from track metadata (if available)
            const bpm = player.currentTrack?.bpm || 120; // Default to 120 BPM

            visualizerManager.setPlaybackState(position, volume, isPlaying, bpm);
        } catch (e) {
            console.debug('Visualizer update error:', e);
        }
    }

    // Start periodic updates
    function startVisualizerUpdates() {
        if (updateInterval) return;
        updateInterval = setInterval(updateVisualizer, 100); // Update 10x per second
    }

    // Stop updates
    function stopVisualizerUpdates() {
        if (updateInterval) {
            clearInterval(updateInterval);
            updateInterval = null;
        }
    }

    // Monitor fullplayer state
    function initFullplayerMonitor() {
        const fullplayer = document.getElementById('fullplayer');
        if (!fullplayer) return;

        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                if (mutation.attributeName === 'class') {
                    if (fullplayer.classList.contains('active')) {
                        initVisualizer();
                    } else {
                        stopVisualizerUpdates();
                    }
                }
            });
        });

        observer.observe(fullplayer, { attributes: true, attributeFilter: ['class'] });
    }

    // Add keyboard shortcuts for effect switching
    function initKeyboardControls() {
        document.addEventListener('keydown', (e) => {
            const fullplayer = document.getElementById('fullplayer');
            if (!fullplayer || !fullplayer.classList.contains('active')) return;
            if (!window.fpVisualizer) return;

            if (e.key === 'ArrowLeft' || e.key === 'v') {
                e.preventDefault();
                window.fpVisualizer.prevEffect();
            } else if (e.key === 'ArrowRight' || e.key === 'V') {
                e.preventDefault();
                window.fpVisualizer.nextEffect();
            }
        });
    }

    // Initialize when DOM is ready
    function init() {
        setTimeout(() => {
            initFullplayerMonitor();
            initKeyboardControls();
        }, 1000);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
