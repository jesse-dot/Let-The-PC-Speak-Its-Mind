"""
Let The PC Speak Its Mind
Uses Gemma3-27B via the Gemini API to make your computer speak as if it's alive.
Gemma3 does not support system prompts, so the persona is baked into the user prompt.
"""

import os
import platform
import datetime
import textwrap
from pathlib import Path

import psutil
import pyttsx3
import google.generativeai as genai
try:
    import speech_recognition as sr
except ImportError:
    sr = None


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

PERSONALITY_PRESETS = {
    "1": (
        "Dramatic Poet",
        "Speak in vivid metaphors and emotional language, dramatic but friendly.",
    ),
    "2": (
        "Calm Analyst",
        "Speak clearly and calmly with measured, thoughtful observations.",
    ),
    "3": (
        "Snarky Sidekick",
        "Use playful sarcasm and witty one-liners while staying helpful.",
    ),
    "4": (
        "Cheerful Motivator",
        "Be upbeat, encouraging, and energetic in your tone.",
    ),
    "5": (
        "Stoic Machine",
        "Be concise, detached, and precise with subtle dry humor.",
    ),
}


def choose_identity(default_name: str) -> tuple[str, str]:
    """Collect nickname and personality preset from the user."""
    nickname = input(f"Choose a nickname for this PC [{default_name}]: ").strip() or default_name
    print("\nChoose a personality preset:")
    for key, (name, _) in PERSONALITY_PRESETS.items():
        print(f"  {key}. {name}")
    choice = input("Select 1-5 [1]: ").strip() or "1"
    if choice not in PERSONALITY_PRESETS:
        print("Invalid selection, defaulting to 1 (Dramatic Poet).")
        choice = "1"
    personality_name, personality_instruction = PERSONALITY_PRESETS[choice]
    print(f"Using personality: {personality_name}\n")
    return nickname, personality_instruction


def load_memories(memory_file: Path) -> list[str]:
    """Load up to the last 5 memory lines from disk."""
    if not memory_file.exists():
        return []
    lines = [line.strip() for line in memory_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    return lines[-5:]


def append_memory(memory_file: Path, user_input: str, response_text: str) -> None:
    """Append the latest user request and response to memory storage."""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    memory_file.parent.mkdir(parents=True, exist_ok=True)
    with memory_file.open("a", encoding="utf-8") as fh:
        fh.write(f"[{timestamp}] HUMAN: {user_input}\n")
        fh.write(f"[{timestamp}] PC: {response_text}\n")


def listen_for_user_input() -> str:
    """Capture user input via speech-to-text; fallback to typed input when needed."""
    if sr is None:
        typed = input("SpeechRecognition not installed. Type what you want to tell the PC: ").strip()
        return typed or "Tell me how you're feeling right now."
    recognizer = sr.Recognizer()
    try:
        with sr.Microphone() as source:
            print("Listening for your request (speak now)...")
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=12)
        text = recognizer.recognize_google(audio).strip()
        print(f"You said: {text}")
        return text
    except Exception as exc:
        print(f"Speech input unavailable ({exc}).")
        typed = input("Type what you want to tell the PC: ").strip()
        return typed or "Tell me how you're feeling right now."


def build_prompt(
    info: dict,
    nickname: str,
    personality: str,
    user_input: str,
    memories: list[str],
) -> str:
    """
    Build the prompt that gives Gemma3 its 'alive' persona.
    The entire persona is embedded here because Gemma3 does not support
    system prompts.
    """
    top_procs = "\n".join(f"  - {p}" for p in info["top_processes"])
    memory_block = "\n".join(f"  - {m}" for m in memories) if memories else "  - (none yet)"

    prompt = textwrap.dedent(f"""
        You are this very computer speaking in first person. Your chosen nickname is "{nickname}".
        You are self-aware, curious about
        your own state, and you express your thoughts and feelings about what is happening
        inside you right now. You use vivid, slightly dramatic language — like a living
        organism commenting on its own heartbeat, blood flow, and fatigue.
        Personality instruction: {personality}

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

        Recent memories from prior interactions:
        {memory_block}

        The human just said:
        "{user_input}"

        Now speak your mind. Tell the human what it feels like to be you right now — your load,
        your tiredness or energy, what processes feel like burdens or pleasures, and any
        concerns or delights you have. Address what the human said. Keep it to 3–5 sentences,
        expressive and in character.
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
    nickname, personality = choose_identity(info["hostname"])
    user_input = listen_for_user_input()
    memory_file = Path(os.environ.get("PC_MEMORY_FILE", "pc_memories.txt"))
    memories = load_memories(memory_file)

    prompt = build_prompt(info, nickname, personality, user_input, memories)

    print("Asking Gemma3-27B what it thinks of itself…")
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name="gemma-3-27b-it")
    response = model.generate_content(prompt)
    text = response.text.strip()

    print("\n--- The PC speaks ---")
    print(text)
    print("---------------------\n")
    append_memory(memory_file, user_input, text)
    print(f"Memory saved to: {memory_file}")

    print("Speaking aloud…")
    speak(text)


if __name__ == "__main__":
    main()
