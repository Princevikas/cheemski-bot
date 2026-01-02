/**
 * SquigglySlider - Android 13 Style Wavy Progress Bar
 * Converted from Saket Narayan's Kotlin implementation
 * https://github.com/saket/squiggly-slider
 * 
 * For Cheemski Dashboard Music Player
 */
class SquigglySlider {
    constructor(canvas, container, options = {}) {
        this.canvas = canvas;
        this.container = container;
        this.ctx = canvas.getContext('2d');

        // Progress value (0 to 1)
        this.progress = 0;

        // Wave parameters - based on Saket's defaults
        this.strokeWidth = options.strokeWidth || 4;
        this.wavelength = options.wavelength || Math.max(this.strokeWidth * 6, 16);
        this.amplitude = options.amplitude || Math.max(this.strokeWidth / 2, 2);
        this.segmentsPerWavelength = 10;

        // Animation
        this.animationProgress = 0;
        this.animationDuration = options.animationDuration || 4000; // 4 seconds like Saket's default
        this.animate = true;
        this.lastTime = 0;

        // Colors
        this.activeColor = options.activeColor || '#00ff88';
        this.inactiveColor = options.inactiveColor || 'rgba(255, 255, 255, 0.2)';
        this.thumbColor = options.thumbColor || '#ffffff';

        // Thumb
        this.thumbWidth = options.thumbWidth || Math.max(this.strokeWidth, 4);
        this.thumbHeight = options.thumbHeight || Math.max(this.strokeWidth * 4, 16);

        // State
        this.isDragging = false;
        this.isHovering = false;
        this.targetAmplitude = this.amplitude;
        this.currentAmplitude = this.amplitude;

        // Predictive smoothing state
        this.visualProgress = 0;
        this.anchorProgress = 0;
        this.anchorTime = 0;
        this.estimatedRate = 0;

        // Callbacks
        this.onSeek = options.onSeek || null;
        this.onSeekStart = options.onSeekStart || null;
        this.onSeekEnd = options.onSeekEnd || null;

        // Load saved settings
        this.loadSettings();

        this.init();
    }

    init() {
        this.resize();
        window.addEventListener('resize', () => this.resize());

        // Mouse events
        this.container.addEventListener('mousedown', (e) => this.onMouseDown(e));
        window.addEventListener('mousemove', (e) => this.onMouseMove(e));
        window.addEventListener('mouseup', () => this.onMouseUp());
        this.container.addEventListener('mouseenter', () => this.isHovering = true);
        this.container.addEventListener('mouseleave', () => this.isHovering = false);

        // Touch events for mobile/tablet
        this.container.addEventListener('touchstart', (e) => this.onTouchStart(e), { passive: false });
        window.addEventListener('touchmove', (e) => this.onTouchMove(e), { passive: false });
        window.addEventListener('touchend', () => this.onMouseUp());

        // Start animation loop
        this.animationLoop();
    }

    resize() {
        const rect = this.container.getBoundingClientRect();
        const dpr = window.devicePixelRatio || 1;

        this.canvas.width = rect.width * dpr;
        this.canvas.height = rect.height * dpr;

        this.ctx.scale(dpr, dpr);

        this.width = rect.width;
        this.height = rect.height;
    }

    onMouseDown(e) {
        this.isDragging = true;
        this.targetAmplitude = 0; // Flatten wave on drag (like Saket's implementation)
        if (this.onSeekStart) this.onSeekStart();
        this.updateProgressFromEvent(e);
    }

    onMouseMove(e) {
        if (this.isDragging) {
            this.updateProgressFromEvent(e);
        }
    }

    onMouseUp() {
        if (this.isDragging) {
            this.isDragging = false;
            this.targetAmplitude = this.amplitude; // Restore wave
            if (this.onSeekEnd) this.onSeekEnd(this.progress);
        }
    }

    onTouchStart(e) {
        e.preventDefault();
        this.isDragging = true;
        this.targetAmplitude = 0;
        if (this.onSeekStart) this.onSeekStart();
        this.updateProgressFromEvent(e.touches[0]);
    }

    onTouchMove(e) {
        if (this.isDragging) {
            e.preventDefault();
            this.updateProgressFromEvent(e.touches[0]);
        }
    }

    updateProgressFromEvent(e) {
        const rect = this.container.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const newProgress = Math.max(0, Math.min(1, x / rect.width));

        // Immediate update during drag
        this.progress = newProgress;
        this.visualProgress = newProgress;
        this.lastReceivedValue = newProgress;
        this.lastChangeTime = performance.now();
        this.anchorProgress = newProgress; // Keep for compatibility if used elsewhere
        this.anchorTime = performance.now();
        this.estimatedRate = 0; // Reset rate during seek

        if (this.onSeek) this.onSeek(newProgress);
    }

    setPlaying(isPlaying) {
        this.isPlaying = isPlaying;
        if (!isPlaying) {
            this.estimatedRate = 0;
        }
    }

    setProgress(value) {
        if (!this.isDragging) {
            const now = performance.now();
            const constrainedValue = Math.max(0, Math.min(1, value));

            // Initialize if first run
            if (this.lastReceivedValue === undefined) {
                this.lastReceivedValue = constrainedValue;
                this.lastChangeTime = now;
                this.visualProgress = constrainedValue;
                this.progress = constrainedValue;
                this.anchorProgress = constrainedValue;
                this.anchorTime = now;
                return;
            }

            // Detect change (server update step)
            // We use a small threshold to detect actual step vs floating point noise
            const diff = constrainedValue - this.lastReceivedValue;

            if (Math.abs(diff) > 0.0001) {
                // Value changed! This marks a "step" from the server.
                const dt = now - this.lastChangeTime;

                // If the step happened reasonably closely to expected (e.g. ~1s)
                // We use this to calculate the playback rate.
                if (dt > 200 && diff > 0 && diff < 0.1) {
                    const instantaneousRate = diff / dt;

                    // Smooth the rate
                    if (this.estimatedRate === 0) {
                        this.estimatedRate = instantaneousRate;
                    } else {
                        // Trust the new rate more if it's consistent
                        this.estimatedRate = (this.estimatedRate * 0.6) + (instantaneousRate * 0.4);
                    }

                    // Allow slight drift to keep it smooth, but correct if huge
                    const drift = this.visualProgress - constrainedValue;
                    if (Math.abs(drift) > 0.1) {
                        // Too much drift vs the server value, snap to it
                        this.visualProgress = constrainedValue;
                    }
                } else if (Math.abs(diff) > 0.1) {
                    // Large jump (seek), reset everything
                    this.visualProgress = constrainedValue;
                    this.estimatedRate = 0;
                }

                // Update anchor
                this.lastReceivedValue = constrainedValue;
                this.lastChangeTime = now;
                this.anchorProgress = constrainedValue;
                this.anchorTime = now;
            } else {
                // Value hasn't changed. 
                // If it's been too long without a change (> 2.0s), assume stalled/paused
                if (now - this.lastChangeTime > 2000) {
                    this.estimatedRate = 0;
                }
            }

            this.progress = constrainedValue;
        }
    }

    setAnimate(value) {
        this.animate = value;
    }

    setColor(color) {
        this.activeColor = color;
        this.saveSettings();
    }

    saveSettings() {
        try {
            localStorage.setItem('squigglySliderSettings', JSON.stringify({
                wavelength: this.wavelength,
                amplitude: this.amplitude,
                activeColor: this.activeColor
            }));
        } catch (e) { }
    }

    loadSettings() {
        try {
            const saved = localStorage.getItem('squigglySliderSettings');
            if (saved) {
                const settings = JSON.parse(saved);
                this.wavelength = settings.wavelength || this.wavelength;
                this.amplitude = settings.amplitude || this.amplitude;
                this.activeColor = settings.activeColor || this.activeColor;
            }
        } catch (e) { }
    }

    animationLoop(timestamp = 0) {
        const deltaTime = timestamp - this.lastTime;
        this.lastTime = timestamp;

        // Smooth animation progress (0 to 1, loops continuously)
        if (this.animate && deltaTime > 0 && deltaTime < 100) {
            this.animationProgress += deltaTime / this.animationDuration;
            if (this.animationProgress >= 1) {
                this.animationProgress -= 1;
            }

            // Smooth interpolation for the slider progress (Snail-like motion)
            if (!this.isDragging && this.estimatedRate > 0) {
                // Predict progress based on estimated rate
                // We add a tiny bit of progress each frame
                this.visualProgress += this.estimatedRate * deltaTime;

                // Clamp to prevent overshooting too much (drift correction)
                // If we are way ahead of target (which is the last anchor), wait.
                // Actually, anchorProgress IS the last known position. We should ALWAYS be ahead of it if playing.
                // But if we get too far ahead (e.g. stalled update), slow down.
                const projectedDrift = this.visualProgress - this.anchorProgress;
                if (projectedDrift > 0.05 && this.estimatedRate > 0) {
                    // Dragging too far ahead, slow down slightly
                    this.visualProgress -= projectedDrift * 0.05;
                }
            } else if (!this.isDragging) {
                // Fallback: If no rate known, soft lerp to target
                const diff = this.progress - this.visualProgress;
                if (Math.abs(diff) > 0.0001) {
                    this.visualProgress += diff * 0.1;
                } else {
                    this.visualProgress = this.progress;
                }
            }

            this.visualProgress = Math.max(0, Math.min(1, this.visualProgress));

            // Smooth amplitude transition (spring-like)
            const amplitudeDiff = this.targetAmplitude - this.currentAmplitude;
            this.currentAmplitude += amplitudeDiff * 0.1;
        }

        this.draw();
        requestAnimationFrame((t) => this.animationLoop(t));
    }

    draw() {
        const ctx = this.ctx;
        const centerY = this.height / 2;
        // USE VISUAL PROGRESS HERE
        const progressX = this.visualProgress * this.width;

        // Clear canvas
        ctx.clearRect(0, 0, this.width, this.height);

        // Constants from Saket's code
        const TwoPi = 2 * Math.PI;

        // Draw inactive track (flat line from progress to end)
        ctx.beginPath();
        ctx.strokeStyle = this.inactiveColor;
        ctx.lineWidth = this.strokeWidth;
        ctx.lineCap = 'round';
        ctx.moveTo(progressX, centerY);
        ctx.lineTo(this.width, centerY);
        ctx.stroke();

        // Draw active track (squiggly line from start to progress)
        if (progressX > 0) {
            const waveStartX = this.strokeWidth / 2;
            const waveEndX = Math.max(progressX - (this.strokeWidth / 2), waveStartX);

            const segmentWidth = this.wavelength / this.segmentsPerWavelength;
            const numOfPoints = Math.ceil((waveEndX - waveStartX) / segmentWidth) + 1;

            ctx.beginPath();
            ctx.strokeStyle = this.activeColor;
            ctx.lineWidth = this.strokeWidth;
            ctx.lineCap = 'round';
            ctx.lineJoin = 'round';

            let pointX = waveStartX;
            const waveLengthPx = waveEndX - waveStartX;

            for (let point = 0; point < numOfPoints; point++) {
                const proportionOfWavelength = (pointX - waveStartX) / this.wavelength;
                const radiansX = proportionOfWavelength * TwoPi + (TwoPi * this.animationProgress);

                // Taper amplitude: 0 at start, full at end (thumb)
                // Use power function for smoother, more "snake-like" tail
                const progressFactor = waveLengthPx > 0 ? (pointX - waveStartX) / waveLengthPx : 0;
                const taperedAmplitude = this.currentAmplitude * Math.pow(progressFactor, 1.5);

                const offsetY = centerY + (Math.sin(radiansX) * taperedAmplitude);

                if (point === 0) {
                    ctx.moveTo(pointX, offsetY);
                } else {
                    ctx.lineTo(pointX, offsetY);
                }
                pointX = Math.min(pointX + segmentWidth, waveEndX);
            }

            ctx.stroke();
        }

        // Draw thumb (rectangular like Saket's, at center Y)
        const thumbX = progressX;
        const thumbY = centerY;

        // Thumb glow on hover/drag
        if (this.isHovering || this.isDragging) {
            ctx.beginPath();
            ctx.roundRect(
                thumbX - this.thumbWidth / 2 - 4,
                thumbY - this.thumbHeight / 2 - 4,
                this.thumbWidth + 8,
                this.thumbHeight + 8,
                4
            );
            ctx.fillStyle = 'rgba(0, 255, 136, 0.2)';
            ctx.fill();
        }

        // Draw rounded rectangle thumb
        ctx.beginPath();
        ctx.roundRect(
            thumbX - this.thumbWidth / 2,
            thumbY - this.thumbHeight / 2,
            this.thumbWidth,
            this.thumbHeight,
            4
        );
        ctx.fillStyle = this.thumbColor;
        ctx.shadowColor = 'rgba(0, 0, 0, 0.3)';
        ctx.shadowBlur = 4;
        ctx.shadowOffsetY = 1;
        ctx.fill();

        // Reset shadow
        ctx.shadowColor = 'transparent';
        ctx.shadowBlur = 0;
        ctx.shadowOffsetY = 0;
    }

    destroy() {
        window.removeEventListener('resize', () => this.resize());
        window.removeEventListener('mousemove', (e) => this.onMouseMove(e));
        window.removeEventListener('mouseup', () => this.onMouseUp());
        window.removeEventListener('touchmove', (e) => this.onTouchMove(e));
        window.removeEventListener('touchend', () => this.onMouseUp());
    }
}

// Export for use in the dashboard
if (typeof window !== 'undefined') {
    window.SquigglySlider = SquigglySlider;
}

/**
 * SquigglyVolumeSlider - Parabolic Arc Volume Slider with Squiggly Animation
 * Uses same wave physics as SquigglySlider but on a curved path
 */
class SquigglyVolumeSlider {
    constructor(canvas, container, options = {}) {
        this.canvas = canvas;
        this.container = container;
        this.ctx = canvas.getContext('2d');

        // Volume (0 to 100)
        this.volume = options.initialVolume || 50;
        this.lastVolume = this.volume; // For mute toggle

        // Curve control points (Quadratic Bezier) - spans wider for easier interaction
        this.curveStart = { x: 8, y: 42 };
        this.curveControl = { x: 75, y: 8 };
        this.curveEnd = { x: 142, y: 42 };

        // Wave parameters
        this.strokeWidth = options.strokeWidth || 4;
        this.wavelength = options.wavelength || 14;
        this.amplitude = options.amplitude || 3;
        this.segmentsPerWavelength = 8;

        // Animation
        this.animationProgress = 0;
        this.animationDuration = options.animationDuration || 3000;
        this.animate = true;
        this.lastTime = 0;

        // Colors
        this.activeColor = options.activeColor || '#00ff88';
        this.inactiveColor = options.inactiveColor || 'rgba(255, 255, 255, 0.2)';
        this.thumbColor = options.thumbColor || '#ffffff';

        // Circular Thumb
        this.thumbRadius = options.thumbRadius || 8;

        // State
        this.isDragging = false;
        this.isHovering = false;
        this.isMuted = false;
        this.targetAmplitude = this.amplitude;
        this.currentAmplitude = this.amplitude;

        // Callbacks
        this.onChange = options.onChange || null;
        this.onMuteToggle = options.onMuteToggle || null;

        // Label element
        this.labelElement = options.labelElement || null;
        this.muteButton = options.muteButton || null;

        this.init();
    }

    init() {
        this.resize();
        window.addEventListener('resize', () => this.resize());

        // Mouse events
        this.container.addEventListener('mousedown', (e) => this.onMouseDown(e));
        window.addEventListener('mousemove', (e) => this.onMouseMove(e));
        window.addEventListener('mouseup', () => this.onMouseUp());
        this.container.addEventListener('mouseenter', () => this.isHovering = true);
        this.container.addEventListener('mouseleave', () => this.isHovering = false);

        // Touch events
        this.container.addEventListener('touchstart', (e) => this.onTouchStart(e), { passive: false });
        window.addEventListener('touchmove', (e) => this.onTouchMove(e), { passive: false });
        window.addEventListener('touchend', () => this.onMouseUp());

        // Mute button
        if (this.muteButton) {
            this.muteButton.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                this.toggleMute();
            });
        }

        // Start animation
        this.animationLoop();
        this.updateLabel();
    }

    resize() {
        const rect = this.container.getBoundingClientRect();
        const dpr = window.devicePixelRatio || 1;

        this.canvas.width = rect.width * dpr;
        this.canvas.height = rect.height * dpr;
        this.ctx.scale(dpr, dpr);

        this.width = rect.width;
        this.height = rect.height;

        // Scale curve to canvas
        const scaleX = this.width / 150;
        const scaleY = this.height / 50;
        this.scaledStart = { x: this.curveStart.x * scaleX, y: this.curveStart.y * scaleY };
        this.scaledControl = { x: this.curveControl.x * scaleX, y: this.curveControl.y * scaleY };
        this.scaledEnd = { x: this.curveEnd.x * scaleX, y: this.curveEnd.y * scaleY };
    }

    // Quadratic Bezier point at t
    getPointOnCurve(t) {
        const inv = 1 - t;
        return {
            x: inv * inv * this.scaledStart.x + 2 * inv * t * this.scaledControl.x + t * t * this.scaledEnd.x,
            y: inv * inv * this.scaledStart.y + 2 * inv * t * this.scaledControl.y + t * t * this.scaledEnd.y
        };
    }

    // Normal vector at t (perpendicular to tangent)
    getNormalAtT(t) {
        const inv = 1 - t;
        // Tangent = derivative of bezier
        const tx = 2 * inv * (this.scaledControl.x - this.scaledStart.x) + 2 * t * (this.scaledEnd.x - this.scaledControl.x);
        const ty = 2 * inv * (this.scaledControl.y - this.scaledStart.y) + 2 * t * (this.scaledEnd.y - this.scaledControl.y);
        const len = Math.sqrt(tx * tx + ty * ty);
        // Normal is perpendicular (-ty, tx)
        return { x: -ty / len, y: tx / len };
    }

    onMouseDown(e) {
        this.isDragging = true;
        this.targetAmplitude = 0;
        this.updateVolumeFromEvent(e);
    }

    onMouseMove(e) {
        if (this.isDragging) {
            this.updateVolumeFromEvent(e);
        }
    }

    onMouseUp() {
        if (this.isDragging) {
            this.isDragging = false;
            this.targetAmplitude = this.amplitude;
            // Only send volume change when drag ends
            if (this.onChange) this.onChange(this.volume);
        }
    }

    onTouchStart(e) {
        e.preventDefault();
        this.isDragging = true;
        this.targetAmplitude = 0;
        this.updateVolumeFromEvent(e.touches[0]);
    }

    onTouchMove(e) {
        if (this.isDragging) {
            e.preventDefault();
            this.updateVolumeFromEvent(e.touches[0]);
        }
    }

    updateVolumeFromEvent(e) {
        const rect = this.container.getBoundingClientRect();
        const x = e.clientX - rect.left;

        // Map click to curve's X span (with padding for easier min/max)
        const curveStartX = this.scaledStart.x;
        const curveEndX = this.scaledEnd.x;
        const curveWidth = curveEndX - curveStartX;

        // Calculate progress based on curve position, not container
        let progress = (x - curveStartX) / curveWidth;

        // Add some tolerance at edges for easier 0% and 100%
        if (progress < 0.05) progress = 0;
        if (progress > 0.95) progress = 1;

        progress = Math.max(0, Math.min(1, progress));
        const newVolume = Math.round(progress * 100);

        // Only update visual if volume changed (don't call onChange - that happens on mouseup)
        if (newVolume !== this.volume) {
            this.volume = newVolume;

            if (this.volume > 0) {
                this.isMuted = false;
                this.lastVolume = this.volume;
            }

            this.updateLabel();
        }
    }

    setVolume(val) {
        this.volume = Math.max(0, Math.min(100, val));
        if (this.volume > 0) {
            this.lastVolume = this.volume;
            this.isMuted = false;
        }
        this.updateLabel();
        // Force immediate visual update
        if (this.draw) this.draw();
    }

    toggleMute() {
        if (this.isMuted || this.volume === 0) {
            // Unmute
            this.volume = this.lastVolume || 50;
            this.isMuted = false;
        } else {
            // Mute
            this.lastVolume = this.volume;
            this.volume = 0;
            this.isMuted = true;
        }
        this.updateLabel();
        if (this.onChange) this.onChange(this.volume);
        if (this.onMuteToggle) this.onMuteToggle(this.isMuted);
    }

    updateLabel() {
        if (this.labelElement) {
            this.labelElement.innerText = `Vol: ${this.volume}%`;
        }
        // Update mute button icon
        if (this.muteButton) {
            if (this.volume === 0) {
                this.muteButton.innerText = 'volume_off';
            } else if (this.volume < 50) {
                this.muteButton.innerText = 'volume_down';
            } else {
                this.muteButton.innerText = 'volume_up';
            }
        }
    }

    animationLoop(timestamp = 0) {
        const deltaTime = timestamp - this.lastTime;
        this.lastTime = timestamp;

        if (this.animate && deltaTime > 0 && deltaTime < 100) {
            this.animationProgress += deltaTime / this.animationDuration;
            if (this.animationProgress >= 1) this.animationProgress -= 1;

            // Smooth amplitude
            const diff = this.targetAmplitude - this.currentAmplitude;
            this.currentAmplitude += diff * 0.1;
        }

        this.draw();
        requestAnimationFrame((t) => this.animationLoop(t));
    }

    draw() {
        const ctx = this.ctx;
        const progress = this.volume / 100;
        const TwoPi = 2 * Math.PI;

        ctx.clearRect(0, 0, this.width, this.height);

        const segments = 60;

        // Draw inactive track (full curve, no wave)
        ctx.beginPath();
        ctx.strokeStyle = this.inactiveColor;
        ctx.lineWidth = this.strokeWidth;
        ctx.lineCap = 'round';
        ctx.moveTo(this.scaledStart.x, this.scaledStart.y);
        ctx.quadraticCurveTo(this.scaledControl.x, this.scaledControl.y, this.scaledEnd.x, this.scaledEnd.y);
        ctx.stroke();

        // Draw active track (squiggly up to progress)
        if (progress > 0) {
            ctx.beginPath();
            ctx.strokeStyle = this.activeColor;
            ctx.lineWidth = this.strokeWidth;
            ctx.lineCap = 'round';
            ctx.lineJoin = 'round';

            const activeSegments = Math.ceil(segments * progress);

            for (let i = 0; i <= activeSegments; i++) {
                const t = i / segments;
                const pt = this.getPointOnCurve(t);
                const normal = this.getNormalAtT(t);

                // Taper amplitude (snake tail effect)
                const taper = Math.pow(t / progress, 1.5);
                const amp = this.currentAmplitude * taper;

                // Wave offset
                const wave = Math.sin((t / progress) * 15 + TwoPi * this.animationProgress) * amp;

                const x = pt.x + normal.x * wave;
                const y = pt.y + normal.y * wave;

                if (i === 0) {
                    ctx.moveTo(x, y);
                } else {
                    ctx.lineTo(x, y);
                }
            }
            ctx.stroke();
        }

        // Draw circular thumb
        const thumbT = progress;
        const thumbPt = this.getPointOnCurve(thumbT);
        const thumbNormal = this.getNormalAtT(thumbT);
        const thumbWave = Math.sin(15 + TwoPi * this.animationProgress) * this.currentAmplitude;
        const thumbX = thumbPt.x + thumbNormal.x * thumbWave;
        const thumbY = thumbPt.y + thumbNormal.y * thumbWave;

        // Glow on hover/drag
        if (this.isHovering || this.isDragging) {
            ctx.beginPath();
            ctx.arc(thumbX, thumbY, this.thumbRadius + 4, 0, TwoPi);
            ctx.fillStyle = 'rgba(0, 255, 136, 0.3)';
            ctx.fill();
        }

        // Thumb circle
        ctx.beginPath();
        ctx.arc(thumbX, thumbY, this.thumbRadius, 0, TwoPi);
        ctx.fillStyle = this.thumbColor;
        ctx.shadowColor = 'rgba(0, 255, 136, 0.5)';
        ctx.shadowBlur = 6;
        ctx.fill();

        // Thumb border
        ctx.strokeStyle = this.activeColor;
        ctx.lineWidth = 2;
        ctx.stroke();

        // Reset shadow
        ctx.shadowColor = 'transparent';
        ctx.shadowBlur = 0;

        // Draw volume percentage on canvas (positioned below the arc)
        ctx.font = 'bold 11px Arial, sans-serif';
        ctx.fillStyle = '#00ff88';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'top';
        ctx.fillText(`${this.volume}%`, this.width / 2, this.height - 12);
    }

    destroy() {
        window.removeEventListener('resize', () => this.resize());
        window.removeEventListener('mousemove', (e) => this.onMouseMove(e));
        window.removeEventListener('mouseup', () => this.onMouseUp());
    }
}

// Export
if (typeof window !== 'undefined') {
    window.SquigglyVolumeSlider = SquigglyVolumeSlider;
}

/**
 * MiniSquigglySlider - Compact progress bar for mobile mini player
 * Display-only version (no interaction), syncs with main slider
 */
class MiniSquigglySlider {
    constructor(canvas, container, options = {}) {
        this.canvas = canvas;
        this.container = container;
        this.ctx = canvas.getContext('2d');

        // Progress value (0 to 1)
        this.progress = 0;

        // Wave parameters - smaller for compact display
        this.strokeWidth = options.strokeWidth || 3;
        this.wavelength = options.wavelength || 12;
        this.amplitude = options.amplitude || 4;
        this.segmentsPerWavelength = 8;

        // Animation
        this.animationProgress = 0;
        this.animationDuration = options.animationDuration || 3000;
        this.lastTime = 0;

        // Colors
        this.activeColor = options.activeColor || '#00ff88';
        this.inactiveColor = options.inactiveColor || 'rgba(255, 255, 255, 0.15)';

        // Load saved color
        this.loadSettings();

        this.init();
    }

    init() {
        this.resize();
        window.addEventListener('resize', () => this.resize());
        this.animationLoop();
    }

    loadSettings() {
        try {
            const saved = localStorage.getItem('squigglySliderSettings');
            if (saved) {
                const settings = JSON.parse(saved);
                this.activeColor = settings.activeColor || this.activeColor;
            }
        } catch (e) { }
    }

    resize() {
        const rect = this.container.getBoundingClientRect();
        const dpr = window.devicePixelRatio || 1;

        this.canvas.width = rect.width * dpr;
        this.canvas.height = rect.height * dpr;
        this.ctx.scale(dpr, dpr);

        this.width = rect.width;
        this.height = rect.height;
    }

    setProgress(value) {
        this.progress = Math.max(0, Math.min(1, value));
    }

    animationLoop(timestamp = 0) {
        const deltaTime = timestamp - this.lastTime;
        this.lastTime = timestamp;

        if (deltaTime > 0 && deltaTime < 100) {
            this.animationProgress += deltaTime / this.animationDuration;
            if (this.animationProgress >= 1) {
                this.animationProgress -= 1;
            }
        }

        this.draw();
        requestAnimationFrame((t) => this.animationLoop(t));
    }

    draw() {
        const ctx = this.ctx;
        const centerY = this.height / 2;
        const progressX = this.progress * this.width;
        const padding = 8;

        // Clear
        ctx.clearRect(0, 0, this.width, this.height);

        const TwoPi = 2 * Math.PI;

        // Draw inactive track (flat line)
        ctx.beginPath();
        ctx.strokeStyle = this.inactiveColor;
        ctx.lineWidth = this.strokeWidth;
        ctx.lineCap = 'round';
        ctx.moveTo(progressX, centerY);
        ctx.lineTo(this.width - padding, centerY);
        ctx.stroke();

        // Draw active track (squiggly)
        if (progressX > padding) {
            const waveStartX = padding;
            const waveEndX = Math.max(progressX, waveStartX + 1);

            const segmentWidth = this.wavelength / this.segmentsPerWavelength;
            const numOfPoints = Math.ceil((waveEndX - waveStartX) / segmentWidth) + 1;

            ctx.beginPath();
            ctx.strokeStyle = this.activeColor;
            ctx.lineWidth = this.strokeWidth;
            ctx.lineCap = 'round';
            ctx.lineJoin = 'round';

            let pointX = waveStartX;
            const waveLengthPx = waveEndX - waveStartX;

            for (let point = 0; point < numOfPoints; point++) {
                const proportionOfWavelength = (pointX - waveStartX) / this.wavelength;
                const radiansX = proportionOfWavelength * TwoPi + (TwoPi * this.animationProgress);

                // Taper amplitude: starts small, grows toward thumb
                const progressFactor = waveLengthPx > 0 ? (pointX - waveStartX) / waveLengthPx : 0;
                const taperedAmplitude = this.amplitude * Math.pow(progressFactor, 1.5);

                const offsetY = centerY + (Math.sin(radiansX) * taperedAmplitude);

                if (point === 0) {
                    ctx.moveTo(pointX, offsetY);
                } else {
                    ctx.lineTo(pointX, offsetY);
                }
                pointX = Math.min(pointX + segmentWidth, waveEndX);
            }

            ctx.stroke();

            // Small dot at progress position
            ctx.beginPath();
            ctx.arc(progressX, centerY, 4, 0, TwoPi);
            ctx.fillStyle = this.activeColor;
            ctx.fill();
        }
    }

    destroy() {
        window.removeEventListener('resize', () => this.resize());
    }
}

// Export
if (typeof window !== 'undefined') {
    window.MiniSquigglySlider = MiniSquigglySlider;
}
