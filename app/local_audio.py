import os
import sys
import subprocess
import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel

class LocalSTT:
    def __init__(self, model_size="base", device="cpu", compute_type="int8"):
        print(f"[Local STT] Initializing Faster-Whisper model '{model_size}'...")
        self.model = WhisperModel(model_size, device=device, compute_type=compute_type)

    def transcribe(self, audio_data: np.ndarray, sample_rate: int = 16000) -> str:
        if audio_data.dtype != np.float32:
            audio_data = audio_data.astype(np.float32)

        segments, _ = self.model.transcribe(
            audio_data, 
            beam_size=5, 
            vad_filter=True, 
            language="en"
        )
        return " ".join([segment.text for segment in segments]).strip()

    def transcribe_file(self, audio_path: str) -> str:
        segments, _ = self.model.transcribe(
            audio_path,
            beam_size=5,
            vad_filter=True,
            language="en"
        )
        return " ".join([segment.text for segment in segments]).strip()


class LocalTTS:
    def __init__(self, piper_dir: str, model_path: str):
        self.piper_dir = piper_dir
        self.model_path = model_path

        # Determine binary executable path based on OS
        binary_name = "piper.exe" if sys.platform == "win32" else "piper"
        self.executable = os.path.join(piper_dir, binary_name)

        if not os.path.exists(self.executable):
            raise FileNotFoundError(f"Piper binary executable not found at: {self.executable}")
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"Piper ONNX model not found at: {self.model_path}")

        print(f"[Local TTS] Initialized Piper binary engine using '{self.executable}'")

    def speak(self, text: str):
        if not text.strip():
            return

        cmd = [
            self.executable,
            "--model", self.model_path,
            "--output-raw"  # Stream raw PCM audio bytes to stdout
        ]

        try:
            # Spawn Piper binary process
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                cwd=self.piper_dir
            )

            # Pass the input text to Piper STDIN and capture stdout audio bytes
            raw_pcm, _ = process.communicate(input=text.encode("utf-8"))

            if raw_pcm:
                # Convert raw 16-bit 22050Hz PCM stream into numpy array and play
                audio_np = np.frombuffer(raw_pcm, dtype=np.int16)
                sd.play(audio_np, samplerate=22050)
                sd.wait()

        except Exception as e:
            print(f"[Local TTS Error] Audio synthesis failed: {e}")


class AudioRecorder:
    def __init__(self, sample_rate=16000):
        self.sample_rate = sample_rate

    def record_seconds(self, duration: float = 5.0) -> np.ndarray:
        print(f"[Audio Recorder] Listening via microphone for {duration} seconds...")
        audio = sd.rec(
            int(duration * self.sample_rate),
            samplerate=self.sample_rate,
            channels=1,
            dtype="float32"
        )
        sd.wait()
        return audio.flatten()