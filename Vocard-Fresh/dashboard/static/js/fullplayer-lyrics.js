// Fullplayer Lyrics - Synced lyrics display
(function () {
    'use strict';

    let currentLyrics = null;
    let currentTrackId = null;
    let lyricsUpdateInterval = null;

    // Toggle lyrics panel
    window.toggleFpLyrics = function () {
        const panel = document.getElementById('fp-lyrics-panel');
        const btn = document.getElementById('fp-lyrics-btn');

        if (!panel) return;

        const isActive = panel.classList.toggle('active');
        if (btn) btn.classList.toggle('active', isActive);

        if (isActive) {
            loadLyrics();
        }
    };

    // Load lyrics for current track
    async function loadLyrics() {
        const content = document.getElementById('fp-lyrics-content');
        if (!content) return;

        // Check if track changed
        const trackId = window.player?.currentTrack?.identifier;
        if (!trackId) {
            content.innerHTML = '<div class="fp-lyrics-empty">🎵 No song playing</div>';
            return;
        }

        // Don't reload if same track
        if (trackId === currentTrackId && currentLyrics) {
            return;
        }

        content.innerHTML = '<div class="fp-lyrics-loading">🔍 Loading lyrics...</div>';
        currentTrackId = trackId;

        try {
            const title = window.player.currentTrack?.title || '';
            const artist = window.player.currentTrack?.author || '';

            // Request lyrics via WebSocket
            if (window.ws && window.ws.readyState === WebSocket.OPEN) {
                window.ws.send(JSON.stringify({
                    op: 'getLyrics',
                    title: title,
                    artist: artist,
                    platform: 'lrclib',
                    full: true  // Request full lyrics for dashboard
                }));
            } else {
                content.innerHTML = '<div class="fp-lyrics-empty">❌ Not connected</div>';
            }
        } catch (e) {
            console.error('Failed to load lyrics:', e);
            content.innerHTML = '<div class="fp-lyrics-empty">❌ Failed to load lyrics</div>';
        }
    }

    // Handle lyrics response
    window.handleLyricsResponse = function (data) {
        const content = document.getElementById('fp-lyrics-content');
        if (!content) return;

        if (!data.lyrics || Object.keys(data.lyrics).length === 0) {
            content.innerHTML = '<div class="fp-lyrics-empty">😢 No lyrics found</div>';
            currentLyrics = null;
            return;
        }

        // Get plain lyrics (prefer synced if available)
        const lyricsText = data.lyrics.synced || data.lyrics.plain || Object.values(data.lyrics)[0];

        if (!lyricsText || lyricsText.length === 0) {
            content.innerHTML = '<div class="fp-lyrics-empty">😢 No lyrics found</div>';
            currentLyrics = null;
            return;
        }

        // Parse and display lyrics
        currentLyrics = parseLyrics(lyricsText);
        renderLyrics(content);

        // Start sync if synced lyrics
        if (data.lyrics.synced) {
            startLyricsSync();
        }
    };

    // Parse lyrics (handle synced LRC format)
    function parseLyrics(text) {
        const lines = [];
        const lrcRegex = /\[(\d+):(\d+)\.(\d+)\](.*)/;

        // Join if array, split by newlines
        const rawLines = Array.isArray(text) ? text : text.split('\n');

        rawLines.forEach(line => {
            const match = line.match(lrcRegex);
            if (match) {
                const mins = parseInt(match[1]);
                const secs = parseInt(match[2]);
                const ms = parseInt(match[3]) * 10;
                const time = (mins * 60 + secs) * 1000 + ms;
                lines.push({ time, text: match[4].trim() });
            } else if (line.trim()) {
                lines.push({ time: null, text: line.trim() });
            }
        });

        return lines;
    }

    // Render lyrics
    function renderLyrics(container) {
        if (!currentLyrics || currentLyrics.length === 0) {
            container.innerHTML = '<div class="fp-lyrics-empty">😢 No lyrics found</div>';
            return;
        }

        const html = currentLyrics.map((line, i) =>
            `<div class="fp-lyrics-line" data-index="${i}" ${line.time ? `data-time="${line.time}"` : ''}>
                ${line.text || '♪'}
            </div>`
        ).join('');

        container.innerHTML = html;
    }

    // Sync lyrics with playback
    function startLyricsSync() {
        if (lyricsUpdateInterval) clearInterval(lyricsUpdateInterval);

        lyricsUpdateInterval = setInterval(() => {
            if (!currentLyrics) return;

            const position = window.player?.currentPosition || 0;
            const container = document.getElementById('fp-lyrics-content');
            if (!container) return;

            // Find current line
            let currentIndex = -1;
            for (let i = 0; i < currentLyrics.length; i++) {
                if (currentLyrics[i].time !== null && currentLyrics[i].time <= position) {
                    currentIndex = i;
                }
            }

            // Update active class
            const lines = container.querySelectorAll('.fp-lyrics-line');
            lines.forEach((line, i) => {
                line.classList.toggle('active', i === currentIndex);
                line.classList.toggle('past', i < currentIndex);
            });

            // Scroll to current line
            if (currentIndex >= 0 && lines[currentIndex]) {
                lines[currentIndex].scrollIntoView({
                    behavior: 'smooth',
                    block: 'center'
                });
            }
        }, 200);
    }

    // Stop sync when fullplayer closes
    const fpObserver = new MutationObserver((mutations) => {
        const fullplayer = document.getElementById('fullplayer');
        if (fullplayer && !fullplayer.classList.contains('active')) {
            if (lyricsUpdateInterval) {
                clearInterval(lyricsUpdateInterval);
                lyricsUpdateInterval = null;
            }
        }
    });

    // Observe fullplayer
    setTimeout(() => {
        const fullplayer = document.getElementById('fullplayer');
        if (fullplayer) {
            fpObserver.observe(fullplayer, { attributes: true, attributeFilter: ['class'] });
        }
    }, 1000);

})();
