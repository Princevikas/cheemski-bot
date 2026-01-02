/**
 * Mobile Mini Player Enhancements
 * 
 * Features:
 * 1. Initialize mini squiggly progress bar
 * 2. Mini player tap → opens fullplayer overlay
 * 3. Syncs mini progress with main position bar
 */

(function () {
    'use strict';

    let miniSlider = null;

    // Only run on mobile portrait
    function isMobilePortrait() {
        return window.innerWidth <= 480;
    }

    // ========================================
    // MINI SQUIGGLY PROGRESS BAR
    // ========================================
    function initMiniSquigglySlider() {
        if (!isMobilePortrait()) return;

        const canvas = document.getElementById('mini-squiggly-canvas');
        const container = document.getElementById('mini-progress-container');

        if (!canvas || !container) return;
        if (miniSlider) return; // Already initialized

        // Use the MiniSquigglySlider class from squiggly-slider.js
        if (typeof MiniSquigglySlider !== 'undefined') {
            miniSlider = new MiniSquigglySlider(canvas, container);
            syncMiniProgress();
        }
    }

    // Sync mini slider with main position bar
    function syncMiniProgress() {
        const positionBar = document.getElementById('position-bar');
        if (!positionBar || !miniSlider) return;

        function update() {
            if (!miniSlider) return;
            const max = parseFloat(positionBar.max) || 500;
            const value = parseFloat(positionBar.value) || 0;
            const progress = value / max;
            miniSlider.setProgress(progress);
        }

        // Update on position change
        positionBar.addEventListener('input', update);

        // Poll every 200ms to catch programmatic updates
        setInterval(update, 200);
        update();
    }

    // ========================================
    // MINI PLAYER TAP → FULLPLAYER
    // ========================================
    function initMiniPlayerTap() {
        const controlContainer = document.querySelector('.control-container');

        if (!controlContainer) return;

        // Tap on mini player opens fullplayer (except for buttons)
        controlContainer.addEventListener('click', function (e) {
            if (!isMobilePortrait()) return;

            // Don't trigger if clicking on a button or interactive element
            const target = e.target;
            if (target.closest('#play-pause-btn') ||
                target.closest('#mobile-play-pause-btn') ||
                target.closest('#toggle-queue-view') ||
                target.closest('.btn') ||
                target.closest('#mini-squiggly-canvas')) {
                return;
            }

            // Open fullplayer using the existing function from action.js
            if (typeof openFullPlayer === 'function') {
                openFullPlayer();
            }
        });
    }

    // ========================================
    // MOBILE PLAY BUTTON SYNC
    // ========================================
    function initMobilePlayButton() {
        const mobilePlayBtn = document.getElementById('mobile-play-btn');
        const mainPlayBtn = document.getElementById('play-pause-btn');

        if (!mobilePlayBtn || !mainPlayBtn) return;

        // Click mobile button → trigger main button
        mobilePlayBtn.addEventListener('click', function (e) {
            e.stopPropagation();
            mainPlayBtn.click();
        });

        // Sync state from main button
        function syncState() {
            mobilePlayBtn.textContent = mainPlayBtn.textContent;
        }

        // Observe main button changes
        const observer = new MutationObserver(syncState);
        observer.observe(mainPlayBtn, {
            childList: true,
            characterData: true,
            subtree: true
        });

        // Initial sync
        syncState();
    }

    // ========================================
    // INIT
    // ========================================
    function init() {
        setTimeout(function () {
            initMiniSquigglySlider();
            initMobilePlayButton();
            initMiniPlayerTap();
        }, 500); // Wait for squiggly-slider.js to load
    }

    // Run on DOMContentLoaded
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // Re-init on resize
    let resizeTimeout;
    window.addEventListener('resize', function () {
        clearTimeout(resizeTimeout);
        resizeTimeout = setTimeout(function () {
            if (isMobilePortrait() && !miniSlider) {
                initMiniSquigglySlider();
            }
        }, 250);
    });

})();
