// Fullplayer Sync - Makes fullplayer functional and synced with main player
(function () {
    'use strict';

    const fp = {
        // Elements
        artwork: document.getElementById('fp-artwork-img'),
        title: document.getElementById('fp-title'),
        artist: document.getElementById('fp-artist'),
        squigglyCanvas: document.getElementById('fp-squiggly-canvas'),
        currentTime: document.getElementById('fp-current-time'),
        duration: document.getElementById('fp-duration'),

        // Buttons
        playBtn: document.getElementById('fp-play-btn'),
        prevBtn: document.getElementById('fp-prev-btn'),
        nextBtn: document.getElementById('fp-next-btn'),
        shuffleBtn: document.getElementById('fp-shuffle-btn'),
        repeatBtn: document.getElementById('fp-repeat-btn'),

        // State
        isDragging: false,
        squigglySlider: null
    };

    // Initialize Squiggly Progress Slider when ready
    function initSquigglySlider() {
        if (!fp.squigglyCanvas || fp.squigglySlider) return;

        // Wait for SquigglySlider to be available
        if (typeof window.SquigglySlider === 'undefined') {
            setTimeout(initSquigglySlider, 100);
            return;
        }

        try {
            fp.squigglySlider = new window.SquigglySlider(fp.squigglyCanvas, {
                onSeek: (progress) => {
                    if (window.player && window.player.duration) {
                        const seekTime = (progress / 100) * window.player.duration;
                        window.player.currentTime = seekTime;
                    }
                }
            });
            console.log('Fullplayer squiggly slider initialized');
        } catch (e) {
            console.error('Failed to initialize fullplayer squiggly slider:', e);
        }
    }

    // Start initialization
    setTimeout(initSquigglySlider, 500);

    // Update progress bar
    function updateProgress() {
        if (!window.player || fp.isDragging) return;

        const currentTime = window.player.currentTime || 0;
        const duration = window.player.duration || 0;

        if (duration > 0) {
            const progress = (currentTime / duration) * 100;
            if (fp.squigglySlider) {
                fp.squigglySlider.setProgress(progress);
            }
        }

        // Update time displays
        if (fp.currentTime) {
            fp.currentTime.textContent = formatTime(currentTime);
        }
        if (fp.duration) {
            fp.duration.textContent = formatTime(duration);
        }
    }

    // Format time helper
    function formatTime(seconds) {
        if (!seconds || isNaN(seconds)) return '0:00';
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    }

    // Sync fullplayer with main player
    function syncFullplayer() {
        if (typeof player === 'undefined') return;

        const track = player.currentTrack;
        if (!track) return;

        // Update artwork
        const controllerImg = document.getElementById('controller-img');
        if (fp.artwork && controllerImg) {
            fp.artwork.src = controllerImg.src || track.artworkUrl || '';
        }

        // Update title and artist
        if (fp.title) fp.title.textContent = track.title || 'Unknown Track';
        if (fp.artist) fp.artist.textContent = track.author || 'Unknown Artist';

        // Update progress
        updateProgress();

        // Update play/pause button state
        const mainPlayBtn = document.getElementById('play-pause-btn');
        if (fp.playBtn && mainPlayBtn) {
            const isPaused = mainPlayBtn.textContent.trim() === 'play_circle';
            fp.playBtn.querySelector('.material-symbols-outlined').textContent =
                isPaused ? 'play_arrow' : 'pause';
        }

        // Update shuffle state
        const mainShuffleBtn = document.getElementById('shuffle-btn');
        if (fp.shuffleBtn && mainShuffleBtn) {
            fp.shuffleBtn.classList.toggle('active', mainShuffleBtn.classList.contains('active'));
        }

        // Update repeat state
        const mainRepeatBtn = document.getElementById('repeat-btn');
        if (fp.repeatBtn && mainRepeatBtn) {
            const repeatText = mainRepeatBtn.textContent.trim();
            fp.repeatBtn.querySelector('.material-symbols-outlined').textContent = repeatText;
            fp.repeatBtn.classList.toggle('active', repeatText !== 'repeat');
        }
    }

    // Wire up fullplayer controls
    function initFullplayerControls() {
        // Play/Pause
        const mainPlayBtn = document.getElementById('play-pause-btn');
        if (fp.playBtn && mainPlayBtn) {
            fp.playBtn.addEventListener('click', () => {
                mainPlayBtn.click();
                setTimeout(syncFullplayer, 100);
            });
        }

        // Previous
        const mainPrevBtn = document.getElementById('back-btn');
        if (fp.prevBtn && mainPrevBtn) {
            fp.prevBtn.addEventListener('click', () => mainPrevBtn.click());
        }

        // Next/Skip
        const mainNextBtn = document.getElementById('skip-btn');
        if (fp.nextBtn && mainNextBtn) {
            fp.nextBtn.addEventListener('click', () => mainNextBtn.click());
        }

        // Shuffle
        const mainShuffleBtn = document.getElementById('shuffle-btn');
        if (fp.shuffleBtn && mainShuffleBtn) {
            fp.shuffleBtn.addEventListener('click', () => {
                mainShuffleBtn.click();
                setTimeout(syncFullplayer, 100);
            });
        }

        // Repeat
        const mainRepeatBtn = document.getElementById('repeat-btn');
        if (fp.repeatBtn && mainRepeatBtn) {
            fp.repeatBtn.addEventListener('click', () => {
                mainRepeatBtn.click();
                setTimeout(syncFullplayer, 100);
            });
        }
    }

    let updateInterval = null;

    // Start continuous sync when fullplayer is active
    function startFullplayerSync() {
        if (updateInterval) return;

        syncFullplayer();
        updateInterval = setInterval(syncFullplayer, 500);
    }

    // Stop sync when fullplayer is closed
    function stopFullplayerSync() {
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
                        startFullplayerSync();
                    } else {
                        stopFullplayerSync();
                    }
                }
            });
        });

        observer.observe(fullplayer, { attributes: true, attributeFilter: ['class'] });

        // Also sync when opened
        if (fullplayer.classList.contains('active')) {
            startFullplayerSync();
        }
    }

    // Initialize
    function init() {
        setTimeout(() => {
            initFullplayerControls();
            initFullplayerMonitor();
        }, 1000);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
