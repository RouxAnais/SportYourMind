import streamlit.components.v1 as components


def _beep_html(notes: list[tuple[float, float, float]]) -> str:
    """notes: list of (delay_from_start, frequency, duration) tuples, each
    played as a short sine tone. Delays are in seconds."""
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
                    gain.gain.exponentialRampToValueAtTime(0.25, ctx.currentTime + 0.01);
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


def play_start_beep():
    """Single beep -- signals the start of a work/exercise phase."""
    components.html(_beep_html([(0, 880, 0.16)]), height=0)


def play_rest_beep():
    """Double beep -- signals the start of a rest/recovery phase."""
    components.html(_beep_html([(0, 880, 0.16), (0.22, 880, 0.16)]), height=0)


def play_end_beep():
    """Two-note descending tone -- signals a countdown reaching zero, clearly
    distinct from the start/rest beeps (lower pitch, descending, longer)."""
    components.html(_beep_html([(0, 660, 0.14), (0.13, 392, 0.28)]), height=0)
