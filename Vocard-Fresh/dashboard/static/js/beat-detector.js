/**
 * Beat Detector - Estimates beats from BPM and track position
 * Used to create rhythm-reactive visualizations
 */

class BeatDetector {
    constructor(bpm = 120) {
        this.bpm = bpm;
        this.updateBeatInterval();
    }

    updateBeatInterval() {
        // Calculate milliseconds per beat
        this.beatInterval = (60 / this.bpm) * 1000;
    }

    setBPM(bpm) {
        if (bpm && bpm > 0 && bpm < 300) {
            this.bpm = bpm;
            this.updateBeatInterval();
        }
    }

    /**
     * Get the current beat phase (0-1 representing position within a beat)
     * @param {number} position - Current track position in milliseconds
     * @returns {number} Phase value between 0 and 1
     */
    getBeatPhase(position) {
        if (!this.beatInterval || position < 0) return 0;
        return (position % this.beatInterval) / this.beatInterval;
    }

    /**
     * Check if current position is on a beat
     * @param {number} position - Current track position in milliseconds
     * @param {number} threshold - How close to beat start (0-1)
     * @returns {boolean} True if currently on a beat
     */
    isBeat(position, threshold = 0.15) {
        const phase = this.getBeatPhase(position);
        return phase < threshold;
    }

    /**
     * Get beat intensity (1.0 at beat start, fading to 0)
     * @param {number} position - Current track position in milliseconds
     * @returns {number} Intensity value between 0 and 1
     */
    getBeatIntensity(position) {
        const phase = this.getBeatPhase(position);
        // Exponential decay from 1 to 0 over the beat
        return Math.exp(-phase * 4);
    }

    /**
     * Get multiple beat divisions (for complex rhythms)
     * @param {number} position - Current track position in milliseconds
     * @param {number} division - Beat division (2 = half notes, 4 = quarter notes)
     * @returns {number} Phase for the given division
     */
    getBeatDivision(position, division = 1) {
        const divisonInterval = this.beatInterval / division;
        return (position % divisonInterval) / divisonInterval;
    }
}

// Export for use in other scripts
window.BeatDetector = BeatDetector;
