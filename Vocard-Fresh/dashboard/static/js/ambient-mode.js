/**
 * Ambient Mode - Dynamic Color Glow Effect
 * Inspired by Pear Desktop's ambient-mode plugin
 * 
 * Extracts dominant color from album art and creates:
 * - Dynamic background color glow
 * - Subtle pulsing animation
 * - Immersive fullplayer experience
 */

(function () {
    'use strict';

    let lastImageSrc = null;
    let ambientCanvas = null;
    let animationId = null;
    let dominantColor = { r: 128, g: 128, b: 128 };

    // Create canvas for color sampling
    function createAmbientCanvas() {
        if (ambientCanvas) return ambientCanvas;

        ambientCanvas = document.createElement('canvas');
        ambientCanvas.width = 10;
        ambientCanvas.height = 10;
        ambientCanvas.style.display = 'none';
        document.body.appendChild(ambientCanvas);
        return ambientCanvas;
    }

    // Extract dominant color from image
    function extractDominantColor(img) {
        const canvas = createAmbientCanvas();
        const ctx = canvas.getContext('2d');

        try {
            // Draw scaled down image
            ctx.drawImage(img, 0, 0, 10, 10);
            const imageData = ctx.getImageData(0, 0, 10, 10).data;

            // Sample colors
            let r = 0, g = 0, b = 0, count = 0;

            for (let i = 0; i < imageData.length; i += 4) {
                // Skip dark/black pixels
                const brightness = (imageData[i] + imageData[i + 1] + imageData[i + 2]) / 3;
                if (brightness > 30 && brightness < 240) {
                    r += imageData[i];
                    g += imageData[i + 1];
                    b += imageData[i + 2];
                    count++;
                }
            }

            if (count > 0) {
                dominantColor = {
                    r: Math.round(r / count),
                    g: Math.round(g / count),
                    b: Math.round(b / count)
                };
            }

            return dominantColor;
        } catch (e) {
            // CORS error - use fallback
            return dominantColor;
        }
    }

    // Apply ambient glow to fullplayer
    function applyAmbientGlow(color) {
        const fullplayer = document.querySelector('.fullplayer-overlay');
        if (!fullplayer) return;

        // Set CSS custom properties for ambient color
        fullplayer.style.setProperty('--ambient-r', color.r);
        fullplayer.style.setProperty('--ambient-g', color.g);
        fullplayer.style.setProperty('--ambient-b', color.b);
        fullplayer.style.setProperty('--ambient-color', `rgb(${color.r}, ${color.g}, ${color.b})`);

        // Add ambient class to trigger CSS effects
        fullplayer.classList.add('ambient-active');
    }

    // Update ambient effect when album art changes
    function updateAmbientEffect() {
        const controllerImg = document.getElementById('controller-img');
        const fpArtwork = document.querySelector('.fp-artwork img');

        const img = fpArtwork || controllerImg;
        if (!img || !img.src || img.src === lastImageSrc) return;

        lastImageSrc = img.src;

        // Create a new image to avoid CORS issues
        const tempImg = new Image();
        tempImg.crossOrigin = 'anonymous';
        tempImg.onload = function () {
            const color = extractDominantColor(tempImg);
            applyAmbientGlow(color);
        };
        tempImg.onerror = function () {
            // Use existing image if anonymous fails
            const color = extractDominantColor(img);
            applyAmbientGlow(color);
        };
        tempImg.src = img.src;
    }

    // Start ambient effect loop
    function startAmbientLoop() {
        if (animationId) return;

        function loop() {
            updateAmbientEffect();
            animationId = setTimeout(loop, 1000); // Check every second
        }
        loop();
    }

    // Initialize
    function init() {
        // Wait for DOM
        setTimeout(() => {
            startAmbientLoop();

            // Also update when fullplayer opens
            const observer = new MutationObserver((mutations) => {
                mutations.forEach((mutation) => {
                    if (mutation.target.classList && mutation.target.classList.contains('fullplayer-overlay')) {
                        if (mutation.target.classList.contains('active')) {
                            updateAmbientEffect();
                        }
                    }
                });
            });

            const fullplayer = document.querySelector('.fullplayer-overlay');
            if (fullplayer) {
                observer.observe(fullplayer, { attributes: true, attributeFilter: ['class'] });
            }
        }, 1000);
    }

    // Run
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
