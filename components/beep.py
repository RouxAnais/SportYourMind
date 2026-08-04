import streamlit.components.v1 as components


def _beep_html(pattern: list[float]) -> str:
    """pattern: list of gaps in seconds between successive short beeps, e.g.
    [0] for a single beep, [0, 0.18] for a double beep (first beep at t=0,
    second beep 0.18s later)."""
    delays_js = ",".join(str(d) for d in pattern)
    return f"""
    <script>
    (function() {{
        try {{
            const ctx = new (window.AudioContext || window.webkitAudioContext)();
            const delays = [{delays_js}];
            let t = 0;
            delays.forEach(function(gap) {{
                t += gap;
                setTimeout(function() {{
                    const osc = ctx.createOscillator();
                    const gain = ctx.createGain();
                    osc.type = "sine";
                    osc.frequency.value = 880;
                    gain.gain.setValueAtTime(0.001, ctx.currentTime);
                    gain.gain.exponentialRampToValueAtTime(0.25, ctx.currentTime + 0.01);
                    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.16);
                    osc.connect(gain);
                    gain.connect(ctx.destination);
                    osc.start();
                    osc.stop(ctx.currentTime + 0.18);
                }}, t * 1000);
            }});
        }} catch (e) {{ /* audio not available, fail silently */ }}
    }})();
    </script>
    """


def play_start_beep():
    """Single beep -- signals the start of a work/exercise phase."""
    components.html(_beep_html([0]), height=0)


def play_rest_beep():
    """Double beep -- signals the start of a rest/recovery phase."""
    components.html(_beep_html([0, 0.22]), height=0)
