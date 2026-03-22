import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import speak


class SpeakFeatureTests(unittest.TestCase):
    def test_build_prompt_includes_customization_memory_and_input(self) -> None:
        info = {
            "hostname": "host-1",
            "os": "Linux 6.0",
            "architecture": "x86_64",
            "cpu_count": 8,
            "cpu_percent": 14.0,
            "cpu_freq_mhz": "2800",
            "ram_total_gb": "16.0",
            "ram_used_gb": "8.0",
            "ram_percent": 50.0,
            "disk_total_gb": "500.0",
            "disk_used_gb": "150.0",
            "disk_percent": 30.0,
            "battery": "no battery / desktop",
            "uptime": "2h 0m 1s",
            "local_time": "2026-01-01 12:00:00",
            "top_processes": ["python (CPU 10.0%, MEM 2.0%)"],
        }
        prompt = speak.build_prompt(
            info=info,
            nickname="HAL-lite",
            personality="Be calm and analytical.",
            user_input="How are you doing?",
            memories=["[old] HUMAN: hi", "[old] PC: hello there"],
        )
        self.assertIn('nickname is "HAL-lite"', prompt)
        self.assertIn("Personality instruction: Be calm and analytical.", prompt)
        self.assertIn('"How are you doing?"', prompt)
        self.assertIn("[old] HUMAN: hi", prompt)

    def test_memory_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            memory_path = Path(tmpdir) / "memories.txt"
            speak.append_memory(memory_path, "hello", "hi human")
            memories = speak.load_memories(memory_path)
            self.assertEqual(len(memories), 2)
            self.assertIn("HUMAN: hello", memories[0])
            self.assertIn("PC: hi human", memories[1])

    def test_choose_identity_invalid_personality_defaults(self) -> None:
        with patch("builtins.input", side_effect=["", "9"]):
            nickname, personality = speak.choose_identity("DefaultPC")
        self.assertEqual(nickname, "DefaultPC")
        self.assertEqual(personality, speak.PERSONALITY_PRESETS["1"][1])


if __name__ == "__main__":
    unittest.main()
