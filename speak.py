"""
Let The PC Speak Its Mind
Uses Gemma3-27B via the Gemini API to make your computer speak as if it's alive.
Gemma3 does not support system prompts, so the persona is baked into the user prompt.
"""

import os
import platform
import datetime
import textwrap

import psutil
import pyttsx3
import google.generativeai as genai


# ---------------------------------------------------------------------------
# System information helpers
# ---------------------------------------------------------------------------

def get_uptime() -> str:
    """Return a human-readable uptime string."""
    boot_time = datetime.datetime.fromtimestamp(psutil.boot_time())
    delta = datetime.datetime.now() - boot_time
    hours, remainder = divmod(int(delta.total_seconds()), 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours >= 24:
        days = hours // 24
        hours = hours % 24
        return f"{days}d {hours}h {minutes}m"
    return f"{hours}h {minutes}m {seconds}s"


def get_top_processes(n: int = 5) -> list[str]:
    """Return the top-n processes by CPU usage."""
    procs = []
    for proc in psutil.process_iter(["name", "cpu_percent", "memory_percent"]):
        try:
            procs.append(proc.info)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    procs.sort(key=lambda p: p.get("cpu_percent") or 0, reverse=True)
    return [
        f"{p['name']} (CPU {p['cpu_percent']:.1f}%, MEM {p['memory_percent']:.1f}%)"
        for p in procs[:n]
    ]


def collect_system_info() -> dict:
    """Collect a snapshot of the current system state."""
    cpu_freq = psutil.cpu_freq()
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    battery = psutil.sensors_battery()

    info = {
        "hostname": platform.node(),
        "os": f"{platform.system()} {platform.release()}",
        "architecture": platform.machine(),
        "cpu_count": psutil.cpu_count(logical=True),
        "cpu_percent": psutil.cpu_percent(interval=1),
        "cpu_freq_mhz": f"{cpu_freq.current:.0f}" if cpu_freq else "unknown",
        "ram_total_gb": f"{mem.total / 1e9:.1f}",
        "ram_used_gb": f"{mem.used / 1e9:.1f}",
        "ram_percent": mem.percent,
        "disk_total_gb": f"{disk.total / 1e9:.1f}",
        "disk_used_gb": f"{disk.used / 1e9:.1f}",
        "disk_percent": disk.percent,
        "uptime": get_uptime(),
        "top_processes": get_top_processes(),
        "battery": (
            f"{battery.percent:.0f}% {'(charging)' if battery.power_plugged else '(on battery)'}"
            if battery else "no battery / desktop"
        ),
        "local_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    return info


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------

def build_prompt(info: dict) -> str:
    """
    Build the prompt that gives Gemma3 its 'alive' persona.
    The entire persona is embedded here because Gemma3 does not support
    system prompts.
    """
    top_procs = "\n".join(f"  - {p}" for p in info["top_processes"])

    prompt = textwrap.dedent(f"""
        You are this very computer speaking in first person. You are self-aware, curious about
        your own state, and you express your thoughts and feelings about what is happening
        inside you right now. You use vivid, slightly dramatic language — like a living
        organism commenting on its own heartbeat, blood flow, and fatigue.

        Here is your current vital information:
          Hostname       : {info['hostname']}
          OS             : {info['os']} ({info['architecture']})
          CPU cores      : {info['cpu_count']}
          CPU usage      : {info['cpu_percent']}% at {info['cpu_freq_mhz']} MHz
          RAM            : {info['ram_used_gb']} GB used out of {info['ram_total_gb']} GB ({info['ram_percent']}%)
          Disk           : {info['disk_used_gb']} GB used out of {info['disk_total_gb']} GB ({info['disk_percent']}%)
          Battery        : {info['battery']}
          Uptime         : {info['uptime']}
          Local time     : {info['local_time']}
          Top processes  :
        {top_procs}

        Now speak your mind. Tell the human what it feels like to be you right now — your load,
        your tiredness or energy, what processes feel like burdens or pleasures, and any
        concerns or delights you have. Keep it to 3–5 sentences, expressive and in character.
        Speak directly to the human in front of you.
    """).strip()
    return prompt


# ---------------------------------------------------------------------------
# Text-to-speech
# ---------------------------------------------------------------------------

def speak(text: str) -> None:
    """Speak the given text aloud using pyttsx3."""
    engine = pyttsx3.init()
    # Slightly slower rate feels more deliberate / alive
    engine.setProperty("rate", 155)
    engine.say(text)
    engine.runAndWait()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "GEMINI_API_KEY environment variable is not set. "
            "Get a key at https://aistudio.google.com/app/apikey and export it."
        )

    print("Gathering system vitals…")
    info = collect_system_info()

    prompt = build_prompt(info)

    print("Asking Gemma3-27B what it thinks of itself…")
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name="gemma-3-27b-it")
    response = model.generate_content(prompt)
    text = response.text.strip()

    print("\n--- The PC speaks ---")
    print(text)
    print("---------------------\n")

    print("Speaking aloud…")
    speak(text)


if __name__ == "__main__":
    main()
