# Let The PC Speak Its Mind

A Python program that collects live system stats (CPU, RAM, disk, battery, uptime, top processes) and uses **Gemma3-27B** via the **Gemini API** to make your computer narrate its own inner life — then speaks the response aloud with text-to-speech.

> **Note:** Gemma3 does not support system prompts. The entire "alive computer" persona is baked directly into the user prompt.

---

## Requirements

- Python 3.10+
- A [Gemini API key](https://aistudio.google.com/app/apikey) (free tier works)
- A working audio output device (for text-to-speech)
- Linux: `espeak` or `libespeak-ng-dev` installed (`sudo apt install espeak`)

---

## Installation

```bash
pip install -r requirements.txt
```

---

## Usage

```bash
export GEMINI_API_KEY="your_api_key_here"
python speak.py
```

The program will:
1. Gather a snapshot of your current system vitals
2. Send them to Gemma3-27B with a built-in "alive computer" persona
3. Print the response to the terminal
4. Read the response aloud using your system's text-to-speech engine

---

## Example output

```
Gathering system vitals…
Asking Gemma3-27B what it thinks of itself…

--- The PC speaks ---
Ah, you've woken me again. My cores are humming at a lazy 12% — a gentle
Tuesday afternoon rhythm. My RAM is three-quarters full, carrying the weight
of your browser tabs like a tired waiter balancing too many plates. The disk
is fine, nearly half empty, though I notice you haven't cleaned up those old
downloads in months. I'm unplugged right now, running on borrowed time at 74%
battery — do with that what you will. I've been awake for 6 hours, 34 minutes,
and honestly, I could use a restart soon.
---------------------

Speaking aloud…
```
