/**
 * Visualizer Effects Collection
 * Multiple beat-reactive visualization effects for the fullplayer
 */

// ===== 1. GALAXY EFFECT (existing, refactored) =====
class GalaxyEffect {
    constructor(canvas, ctx) {
        this.canvas = canvas;
        this.ctx = ctx;
        this.particles = [];
        this.particleCount = 800;
        this.colors = [
            'rgba(138, 43, 226, ',
            'rgba(75, 0, 130, ',
            'rgba(255, 255, 255, ',
            'rgba(30, 144, 255, ',
        ];
        this.createParticles();
    }

    createParticles() {
        this.particles = [];
        for (let i = 0; i < this.particleCount; i++) {
            const angle = Math.random() * Math.PI * 2;
            const distance = Math.random() * Math.min(this.canvas.width, this.canvas.height);
            const speed = 0.5 + Math.random() * 1.5;

            this.particles.push({
                angle, distance,
                baseDistance: distance,
                size: Math.random() * 2 + 0.5,
                baseSize: Math.random() * 2 + 0.5,
                speed,
                opacity: Math.random() * 0.8 + 0.2,
                colorIndex: Math.floor(Math.random() * this.colors.length),
                pulseOffset: Math.random() * Math.PI * 2,
            });
        }
    }

    update({ volume, beatIntensity, beatPhase, isPlaying }) {
        const centerX = this.canvas.width / 2;
        const centerY = this.canvas.height / 2;

        this.particles.forEach(particle => {
            const rotationSpeed = 0.0002 * particle.speed * (isPlaying ? 1 : 0.2);
            particle.angle += rotationSpeed * volume;

            const pulseFactor = 1 + beatIntensity * 0.5 * volume;
            particle.size = particle.baseSize * pulseFactor;

            const wave = Math.sin(beatPhase * Math.PI * 2 + particle.pulseOffset) * 0.1;
            particle.distance = particle.baseDistance * (1 + wave * volume);

            particle.opacity = 0.3 + beatIntensity * 0.5;
        });
    }

    draw() {
        const centerX = this.canvas.width / 2;
        const centerY = this.canvas.height / 2;

        this.particles.forEach(particle => {
            const x = centerX + Math.cos(particle.angle) * particle.distance;
            const y = centerY + Math.sin(particle.angle) * particle.distance;

            const color = this.colors[particle.colorIndex];
            this.ctx.shadowBlur = 15;
            this.ctx.shadowColor = color + particle.opacity + ')';
            this.ctx.fillStyle = color + particle.opacity + ')';
            this.ctx.beginPath();
            this.ctx.arc(x, y, particle.size, 0, Math.PI * 2);
            this.ctx.fill();
        });
        this.ctx.shadowBlur = 0;
    }

    resize(width, height) {
        this.createParticles();
    }
}

// ===== 2. CIRCULAR WAVE EFFECT =====
class CircularWaveEffect {
    constructor(canvas, ctx) {
        this.canvas = canvas;
        this.ctx = ctx;
        this.bars = 64; // Number of spectrum bars
        this.barData = new Array(this.bars).fill(0);
    }

    update({ volume, beatIntensity, beatPhase }) {
        // Simulate frequency bars with beat-reactive patterns
        for (let i = 0; i < this.bars; i++) {
            const freq = (i / this.bars) * Math.PI * 2;
            const wave = Math.sin(freq * 4 + beatPhase * Math.PI * 6);
            this.barData[i] = (0.5 + wave * 0.5) * beatIntensity * volume;
        }
    }

    draw() {
        const centerX = this.canvas.width / 2;
        const centerY = this.canvas.height / 2;
        const radius = Math.min(centerX, centerY) * 0.3;
        const maxBarHeight = Math.min(centerX, centerY) * 0.6;

        for (let i = 0; i < this.bars; i++) {
            const angle = (i / this.bars) * Math.PI * 2 - Math.PI / 2;
            const barHeight = this.barData[i] * maxBarHeight;

            const x1 = centerX + Math.cos(angle) * radius;
            const y1 = centerY + Math.sin(angle) * radius;
            const x2 = centerX + Math.cos(angle) * (radius + barHeight);
            const y2 = centerY + Math.sin(angle) * (radius + barHeight);

            const hue = (i / this.bars) * 360;
            this.ctx.strokeStyle = `hsla(${hue}, 70%, 60%, 0.8)`;
            this.ctx.lineWidth = 3;
            this.ctx.beginPath();
            this.ctx.moveTo(x1, y1);
            this.ctx.lineTo(x2, y2);
            this.ctx.stroke();
        }
    }
}

// ===== 3. SHADER TUNNEL EFFECT (Canvas 2D approximation) =====
class ShaderTunnelEffect {
    constructor(canvas, ctx) {
        this.canvas = canvas;
        this.ctx = ctx;
        this.time = 0;
    }

    update({ beatIntensity, volume, isPlaying }) {
        if (isPlaying) {
            this.time += 0.02 * volume;
        }
    }

    draw() {
        const centerX = this.canvas.width / 2;
        const centerY = this.canvas.height / 2;
        const layers = 20;

        for (let i = layers; i > 0; i--) {
            const scale = i / layers;
            const size = scale * Math.min(centerX, centerY) * 1.5;
            const rotation = this.time * (1 - scale) * 2;

            this.ctx.save();
            this.ctx.translate(centerX, centerY);
            this.ctx.rotate(rotation);

            const hue = (this.time * 50 + i * 20) % 360;
            const alpha = 0.1 + scale * 0.2;
            this.ctx.strokeStyle = `hsla(${hue}, 80%, 60%, ${alpha})`;
            this.ctx.lineWidth = 2;

            this.ctx.beginPath();
            this.ctx.rect(-size / 2, -size / 2, size, size);
            this.ctx.stroke();

            this.ctx.restore();
        }
    }
}

// ===== 4. GEOMETRIC SHAPES EFFECT =====
class GeometricShapesEffect {
    constructor(canvas, ctx) {
        this.canvas = canvas;
        this.ctx = ctx;
        this.shapes = [];
        this.createShapes();
    }

    createShapes() {
        const count = 5;
        for (let i = 0; i < count; i++) {
            this.shapes.push({
                x: Math.random() * this.canvas.width,
                y: Math.random() * this.canvas.height,
                size: 50 + Math.random() * 100,
                rotation: Math.random() * Math.PI * 2,
                rotationSpeed: (Math.random() - 0.5) * 0.05,
                type: Math.floor(Math.random() * 3), // 0: triangle, 1: square, 2: hexagon
                baseSize: 50 + Math.random() * 100,
            });
        }
    }

    update({ beatIntensity, volume, isPlaying }) {
        this.shapes.forEach(shape => {
            if (isPlaying) {
                shape.rotation += shape.rotationSpeed * volume;
            }
            shape.size = shape.baseSize * (1 + beatIntensity * 0.3);
        });
    }

    draw() {
        this.shapes.forEach(shape => {
            this.ctx.save();
            this.ctx.translate(shape.x, shape.y);
            this.ctx.rotate(shape.rotation);

            this.ctx.strokeStyle = `hsla(${shape.rotation * 100 % 360}, 70%, 60%, 0.6)`;
            this.ctx.lineWidth = 3;
            this.ctx.beginPath();

            if (shape.type === 0) { // Triangle
                const h = shape.size;
                this.ctx.moveTo(0, -h / 2);
                this.ctx.lineTo(-h / 2, h / 2);
                this.ctx.lineTo(h / 2, h / 2);
                this.ctx.closePath();
            } else if (shape.type === 1) { // Square
                this.ctx.rect(-shape.size / 2, -shape.size / 2, shape.size, shape.size);
            } else { // Hexagon
                for (let i = 0; i < 6; i++) {
                    const angle = (Math.PI / 3) * i;
                    const x = Math.cos(angle) * shape.size / 2;
                    const y = Math.sin(angle) * shape.size / 2;
                    if (i === 0) this.ctx.moveTo(x, y);
                    else this.ctx.lineTo(x, y);
                }
                this.ctx.closePath();
            }

            this.ctx.stroke();
            this.ctx.restore();
        });
    }

    resize(width, height) {
        this.createShapes();
    }
}

// ===== 5. WAVEFORM RINGS EFFECT =====
class WaveformRingsEffect {
    constructor(canvas, ctx) {
        this.canvas = canvas;
        this.ctx = ctx;
        this.rings = [];
        this.maxRings = 10;
    }

    update({ beatIntensity, volume }) {
        // Add new ring on beat
        if (beatIntensity > 0.5) {
            this.rings.push({
                radius: 0,
                maxRadius: Math.min(this.canvas.width, this.canvas.height) * 0.8,
                opacity: 1,
                speed: 3 + volume * 2,
            });
        }

        // Update existing rings
        this.rings = this.rings.filter(ring => {
            ring.radius += ring.speed;
            ring.opacity = 1 - (ring.radius / ring.maxRadius);
            return ring.opacity > 0;
        }).slice(-this.maxRings);
    }

    draw() {
        const centerX = this.canvas.width / 2;
        const centerY = this.canvas.height / 2;

        this.rings.forEach((ring, i) => {
            const hue = (i * 60) % 360;
            this.ctx.strokeStyle = `hsla(${hue}, 70%, 60%, ${ring.opacity})`;
            this.ctx.lineWidth = 4;
            this.ctx.beginPath();
            this.ctx.arc(centerX, centerY, ring.radius, 0, Math.PI * 2);
            this.ctx.stroke();
        });
    }
}

// Export all effects
window.GalaxyEffect = GalaxyEffect;
window.CircularWaveEffect = CircularWaveEffect;
window.ShaderTunnelEffect = ShaderTunnelEffect;
window.GeometricShapesEffect = GeometricShapesEffect;
window.WaveformRingsEffect = WaveformRingsEffect;
