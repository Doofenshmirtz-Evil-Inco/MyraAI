import os

import numpy as np
import sounddevice as sd


class KokoroTTS:
    def __init__(
        self,
        voice: str = "af_heart",
        lang_code: str = "a",
        model_path: str | None = None,
        repo_id: str = "hexgrad/Kokoro-82M",
    ):
        try:
            from kokoro import KPipeline
            from kokoro.model import KModel
            import torch
        except ImportError as error:
            raise RuntimeError(
                "Kokoro is not installed. Install the optional Kokoro dependencies first."
            ) from error

        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        model_path = model_path or os.getenv(
            "KOKORO_MODEL_PATH",
            os.path.join(base_dir, "kokoro-v0_19.pth"),
        )
        if not os.path.exists(model_path):
            raise FileNotFoundError(
                f"Kokoro v0.19 checkpoint not found at {model_path}. "
                "Set KOKORO_MODEL_PATH or place kokoro-v0_19.pth in the project root."
            )

        device = os.getenv("KOKORO_DEVICE", "cuda")
        print(f"[Kokoro TTS] Loading {model_path!r} on {device}.", flush=True)
        checkpoint = torch.load(model_path, map_location="cpu", weights_only=True)
        if "net" in checkpoint:
            normalized_path = f"{model_path}.normalized.pth"
            if not os.path.exists(normalized_path):
                torch.save(checkpoint["net"], normalized_path)
            model_path = normalized_path

        model = KModel(model=model_path).to(device).eval()
        self.pipeline = KPipeline(lang_code=lang_code, model=model, device=device)
        self.voice = voice

    def speak(self, text: str):
        if not text.strip():
            return

        for _, _, audio in self.pipeline(text, voice=self.voice, speed=1.0):
            samples = audio.detach().cpu().numpy() if hasattr(audio, "detach") else np.asarray(audio)
            sd.play(samples, samplerate=24000)
            sd.wait()