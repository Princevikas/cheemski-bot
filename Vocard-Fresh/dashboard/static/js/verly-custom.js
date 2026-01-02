/**
 * Custom VerlyRange implementation for Cheemski Dashboard
 * Adapted from VerlyRangeSlider to fix sizing and layout issues
 */
function VerlyRange(id, color) {
    const DOMSlider = document.getElementById(id);
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');

    // Custom Dimensions
    // Use the container height or fixed small height
    const width = DOMSlider.offsetWidth; // Use offsetWidth to include padding/border
    const height = 40; // Fixed tight height (was width/2)

    canvas.width = width;
    canvas.height = height;
    canvas.style.pointerEvents = 'none';
    canvas.style.position = 'absolute';
    canvas.style.top = '0';
    canvas.style.left = '0';
    canvas.style.zIndex = '5'; // Above the fill bar

    // Ensure parent has relative positioning
    DOMSlider.parentElement.style.position = 'relative';
    DOMSlider.parentElement.appendChild(canvas);

    // Hide the original slider but keep it interactive
    DOMSlider.style.opacity = '0';
    DOMSlider.style.zIndex = '10'; // Above canvas for interaction
    DOMSlider.style.position = 'relative';

    // Physics Config
    const gravity = new Vector(0, 0.5); // Slightly stronger gravity for snap

    // Initialize Verly Physics Engine
    // 50 iterations for stability
    let verly = new Verly(50, canvas, ctx);
    let rope = generateRope();

    function generateRope() {
        // Create rope: x, y, segments, gap, pin
        // We want a tighter rope.
        // Gap calculation:
        const segments = 15;
        // We want total length to be just slightly longer than width to allow a little sag
        // width * 1.05
        const totalLen = width * 1.05;
        const gap = totalLen / segments;

        // Start slightly lower to center vertically?
        // createRope(x, y, gap, segments, pin)
        // We pin index 0.
        let rope = verly.createRope(0, height / 2, gap, segments, 0);

        let lastIndex = rope.points.length - 1;

        // Apply gravity
        rope.setGravity(gravity);

        // Pin the last point initially (will be moved by slider)
        rope.pin(lastIndex);

        // Overwrite render function for custom style (Neon Glow handled by CSS)
        rope.renderSticks = () => {
            // We draw a continuous path for smoother look
            ctx.beginPath();
            ctx.strokeStyle = color;
            ctx.lineWidth = 4; // Thinner, elegant line
            ctx.lineCap = 'round';
            ctx.lineJoin = 'round';

            if (rope.points.length > 0) {
                ctx.moveTo(rope.points[0].pos.x, rope.points[0].pos.y);
                for (let i = 1; i < rope.points.length; i++) {
                    // Simple line to point (or could do bezier for super smooth)
                    ctx.lineTo(rope.points[i].pos.x, rope.points[i].pos.y);
                }
            }
            ctx.stroke();
            ctx.closePath();
        }
        return rope;
    }

    // Handle Resize
    window.addEventListener('resize', function () {
        const newWidth = DOMSlider.offsetWidth;
        // Only re-init if width changes
        if (newWidth !== canvas.width) {
            canvas.width = verly.WIDTH = newWidth;
            canvas.height = verly.HEIGHT = height;
            rope = generateRope();
            setRopePosition();
        }
    });

    // Sync Rope with Slider Value
    function setRopePosition() {
        // Calculate ratio 0.0 - 1.0
        let ratio = (DOMSlider.value - DOMSlider.min) / (DOMSlider.max - DOMSlider.min);

        // The original library had "floating point correction" hacks.
        // We'll trust the math but clamp it.
        ratio = Math.max(0, Math.min(1, ratio));

        const lastIdx = rope.points.length - 1;

        // Target X: ratio * width
        // Target Y: height/2 (center vertical)
        const targetX = ratio * canvas.width;
        const targetY = height / 2;

        // Move the last point
        const point = rope.points[lastIdx];
        point.pos.x = targetX;
        point.pos.y = targetY;

        // Reset velocity to prevent crazy swinging when dragging fast?
        // point.oldpos.x = targetX;
        // point.oldpos.y = targetY;
    }

    // Initial sync
    setRopePosition();

    // Listen to updates
    DOMSlider.addEventListener('input', setRopePosition);
    DOMSlider.addEventListener('change', setRopePosition);

    // Animation Loop
    function animate() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        verly.update();
        rope.renderSticks();

        requestAnimationFrame(animate);
    }
    animate();

    return {
        updateColor: (newColor) => {
            color = newColor;
        }
    };
}
