/**
 * Visualizer Manager - Manages multiple visualizer effects
 * Allows switching between different visualization styles
 */

class VisualizerManager {
    constructor(canvasId) {
        this.canvas = document.getElementById(canvasId);
        if (!this.canvas) {
            console.error(`Canvas ${canvasId} not found`);
            return;
        }

        this.ctx = this.canvas.getContext('2d');
        this.beatDetector = new BeatDetector(120);

        this.currentEffect = 0;
        this.effects = [
            new GalaxyEffect(this.canvas, this.ctx),
            new CircularWaveEffect(this.canvas, this.ctx),
            new ShaderTunnelEffect(this.canvas, this.ctx),
            new GeometricShapesEffect(this.canvas, this.ctx),
            new WaveformRingsEffect(this.canvas, this.ctx)
        ];

        this.isPlaying = false;
        this.volume = 1.0;
        this.currentPosition = 0;

        this.init();
    }

    init() {
        this.resize();
        this.animate();
        window.addEventListener('resize', () => this.resize());
    }

    resize() {
        this.canvas.width = this.canvas.offsetWidth;
        this.canvas.height = this.canvas.offsetHeight;
        this.effects.forEach(effect => effect.resize?.(this.canvas.width, this.canvas.height));
    }

    update(position, volume, isPlaying, bpm) {
        this.currentPosition = position || 0;
        this.volume = Math.max(0.1, Math.min(1.0, volume || 0.5));
        this.isPlaying = isPlaying;

        if (bpm && bpm !== this.beatDetector.bpm) {
            this.beatDetector.setBPM(bpm);
        }

        const beatIntensity = this.beatDetector.getBeatIntensity(this.currentPosition);
        const beatPhase = this.beatDetector.getBeatPhase(this.currentPosition);

        // Update current effect
        const effect = this.effects[this.currentEffect];
        if (effect && effect.update) {
            effect.update({
                position: this.currentPosition,
                volume: this.volume,
                isPlaying: this.isPlaying,
                beatIntensity,
                beatPhase
            });
        }
    }

    draw() {
        // Clear with fade effect
        this.ctx.fillStyle = 'rgba(0, 0, 0, 0.1)';
        this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);

        // Draw current effect
        const effect = this.effects[this.currentEffect];
        if (effect && effect.draw) {
            effect.draw();
        }
    }

    animate() {
        this.draw();
        requestAnimationFrame(() => this.animate());
    }

    // Switch to next effect
    nextEffect() {
        this.currentEffect = (this.currentEffect + 1) % this.effects.length;
        console.log(`Switched to effect: ${this.effects[this.currentEffect].constructor.name}`);
    }

    // Switch to previous effect
    prevEffect() {
        this.currentEffect = (this.currentEffect - 1 + this.effects.length) % this.effects.length;
        console.log(`Switched to effect: ${this.effects[this.currentEffect].constructor.name}`);
    }

    setPlaybackState(position, volume, isPlaying, bpm) {
        this.update(position, volume, isPlaying, bpm);
    }

    destroy() {
        window.removeEventListener('resize', () => this.resize());
        this.effects.forEach(effect => effect.destroy?.());
    }
}

// Export
window.VisualizerManager = VisualizerManager;
