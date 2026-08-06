import streamlit.components.v1 as components


def _beep_html(notes: list[tuple[float, float, float]]) -> str:
    """notes: list of (delay_from_start, frequency, duration) tuples, each
    played as a short sine tone. Delays and durations are in seconds."""
    notes_js = ",".join(f"[{delay},{freq},{dur}]" for delay, freq, dur in notes)
    return f"""
    <script>
    (function() {{
        try {{
            const ctx = new (window.AudioContext || window.webkitAudioContext)();
            const notes = [{notes_js}];
            notes.forEach(function(n) {{
                const delay = n[0], freq = n[1], dur = n[2];
                setTimeout(function() {{
                    const osc = ctx.createOscillator();
                    const gain = ctx.createGain();
                    osc.type = "sine";
                    osc.frequency.value = freq;
                    gain.gain.setValueAtTime(0.001, ctx.currentTime);
                    gain.gain.exponentialRampToValueAtTime(0.28, ctx.currentTime + 0.01);
                    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + dur);
                    osc.connect(gain);
                    gain.connect(ctx.destination);
                    osc.start();
                    osc.stop(ctx.currentTime + dur + 0.02);
                }}, delay * 1000);
            }});
        }} catch (e) {{ /* audio not available, fail silently */ }}
    }})();
    </script>
    """


def play_doorbell_beep():
    """Two-note chime (high then low), like a doorbell -- played once, 2
    seconds into a countdown."""
    components.html(_beep_html([(0, 784, 0.22), (0.24, 659, 0.30)]), height=0)


def play_countdown_beep():
    """One long beep -- played once per second on each of the last 3
    seconds of a countdown."""
    components.html(_beep_html([(0, 523, 0.6)]), height=0)
