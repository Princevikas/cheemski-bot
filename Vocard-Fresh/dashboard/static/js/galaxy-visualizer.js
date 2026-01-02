/**
 * Galaxy Visualizer - Beat-reactive particle background for fullplayer
 * Creates a starfield that reacts to music playback
 */

class GalaxyVisualizer {
    constructor(canvasId) {
        this.canvas = document.getElementById(canvasId);
        if (!this.canvas) {
            console.error(`Canvas ${canvasId} not found`);
            return;
        }

        this.ctx = this.canvas.getContext('2d');
        this.particles = [];
        this.beatDetector = new BeatDetector(120); // Default 120 BPM
        this.isPlaying = false;
        this.volume = 1.0;
        this.currentPosition = 0;

        // Visual settings
        this.particleCount = 800;
        this.baseRotationSpeed = 0.0002;
        this.colors = [
            'rgba(138, 43, 226, ', // Purple
            'rgba(75, 0, 130, ',   // Indigo
            'rgba(255, 255, 255, ', // White
            'rgba(30, 144, 255, ', // Blue
        ];

        this.init();
        this.resize();
        this.animate();

        // Handle window resize
        window.addEventListener('resize', () => this.resize());
    }

    init() {
        this.createParticles();
    }

    resize() {
        this.canvas.width = this.canvas.offsetWidth;
        this.canvas.height = this.canvas.offsetHeight;
        this.centerX = this.canvas.width / 2;
        this.centerY = this.canvas.height / 2;
    }

    createParticles() {
        this.particles = [];
        for (let i = 0; i < this.particleCount; i++) {
            // Create particles in a spiral galaxy formation
            const angle = Math.random() * Math.PI * 2;
            const distance = Math.random() * Math.min(this.canvas.width, this.canvas.height);
            const speed = 0.5 + Math.random() * 1.5;

            this.particles.push({
                angle: angle,
                distance: distance,
                baseDistance: distance,
                size: Math.random() * 2 + 0.5,
                baseSize: Math.random() * 2 + 0.5,
                speed: speed,
                opacity: Math.random() * 0.8 + 0.2,
                colorIndex: Math.floor(Math.random() * this.colors.length),
                pulseOffset: Math.random() * Math.PI * 2,
            });
        }
    }

    update(position, volume, isPlaying, bpm) {
        this.currentPosition = position || 0;
        this.volume = Math.max(0.1, Math.min(1.0, volume || 0.5));
        this.isPlaying = isPlaying;

        if (bpm && bpm !== this.beatDetector.bpm) {
            this.beatDetector.setBPM(bpm);
        }

        // Get beat information
        const beatIntensity = this.beatDetector.getBeatIntensity(this.currentPosition);
        const beatPhase = this.beatDetector.getBeatPhase(this.currentPosition);

        // Update each particle
        this.particles.forEach((particle, index) => {
            // Rotate particles
            const rotationSpeed = this.baseRotationSpeed * particle.speed * (this.isPlaying ? 1 : 0.2);
            particle.angle += rotationSpeed * this.volume;

            // Pulse size on beat
            const pulseFactor = 1 + beatIntensity * 0.5 * this.volume;
            particle.size = particle.baseSize * pulseFactor;

            // Wave effect based on beat divisions
            const wave = Math.sin(beatPhase * Math.PI * 2 + particle.pulseOffset) * 0.1;
            particle.distance = particle.baseDistance * (1 + wave * this.volume);

            // Fade opacity on beat
            particle.opacity = 0.3 + beatIntensity * 0.5;
        });
    }

    draw() {
        // Clear canvas with trail effect
        this.ctx.fillStyle = 'rgba(0, 0, 0, 0.05)';
        this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);

        // Draw particles
        this.particles.forEach(particle => {
            const x = this.centerX + Math.cos(particle.angle) * particle.distance;
            const y = this.centerY + Math.sin(particle.angle) * particle.distance;

            // Draw particle with glow
            const color = this.colors[particle.colorIndex];
            const opacity = particle.opacity;

            // Glow effect
            this.ctx.shadowBlur = 15 * this.volume;
            this.ctx.shadowColor = color + opacity + ')';

            // Draw particle
            this.ctx.fillStyle = color + opacity + ')';
            this.ctx.beginPath();
            this.ctx.arc(x, y, particle.size, 0, Math.PI * 2);
            this.ctx.fill();
        });

        // Reset shadow
        this.ctx.shadowBlur = 0;
    }

    animate() {
        this.draw();
        requestAnimationFrame(() => this.animate());
    }

    // Public methods to control visualizer
    setPlaybackState(position, volume, isPlaying, bpm) {
        this.update(position, volume, isPlaying, bpm);
    }

    destroy() {
        window.removeEventListener('resize', () => this.resize());
        this.particles = [];
    }
}

// Export for global use
window.GalaxyVisualizer = GalaxyVisualizer;
