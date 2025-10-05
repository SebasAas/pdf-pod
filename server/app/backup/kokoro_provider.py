import os
from typing import List, Optional
import numpy as np

KOKORO_AVAILABLE = False
_pipeline = None

def _try_import():
    global KOKORO_AVAILABLE, _pipeline
    if _pipeline is not None:
        return
    try:
        from kokoro import KPipeline  # type: ignore
        lang = os.getenv("KOKORO_LANG_CODE", "e")
        _pipeline = KPipeline(lang_code=lang)
        KOKORO_AVAILABLE = True
    except Exception as e:
        KOKORO_AVAILABLE = False

def list_voices() -> List[str]:
    _try_import()
    if KOKORO_AVAILABLE and hasattr(_pipeline, "voice_list"):
        return list(getattr(_pipeline, "voice_list", []))
    # minimal built-ins (common names in Kokoro demos) as fallback hint
    return ["em_santa", "em_gabriel", "em_diego", "pm_brazil", "pf_brazil"]

def synthesize(text: str, voice: Optional[str] = None, sample_rate: int = 44100) -> tuple[bytes, int]:
    _try_import()
    if KOKORO_AVAILABLE:
        voice_name = voice or os.getenv("KOKORO_DEFAULT_VOICE", "em_santa")
        audio_chunks = []
        for _, _, audio in _pipeline(text, voice=voice_name):
            # audio is a numpy array float32 -1..1
            arr = audio
            if isinstance(arr, list):
                arr = np.array(arr, dtype=np.float32)
            pcm16 = np.clip(arr, -1.0, 1.0)
            pcm16 = (pcm16 * 32767).astype(np.int16).tobytes()
            audio_chunks.append(pcm16)
        return (b"".join(audio_chunks), 24000)  # Kokoro default is 24k; adjust if needed
    # fallback TTS (pyttsx3) for pipeline testing
    try:
        import pyttsx3, tempfile, wave
        engine = pyttsx3.init()
        fd, tmp = tempfile.mkstemp(suffix=".wav")
        os.close(fd)
        engine.save_to_file(text, tmp)
        engine.runAndWait()
        with open(tmp, "rb") as f:
            data = f.read()
        os.remove(tmp)
        # return raw wav bytes; frontend will still download
        return (data, 22050)
    except Exception:
        return (b"", 0)
