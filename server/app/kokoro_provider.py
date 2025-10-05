import os
from typing import List, Optional, Tuple
import numpy as np

KOKORO_AVAILABLE = False
_pipeline = None

def _try_import():
    global KOKORO_AVAILABLE, _pipeline
    if _pipeline is not None:
        return
    try:
        print("Attempting to import Kokoro...")
        from kokoro import KPipeline  # type: ignore
        lang = os.getenv("KOKORO_LANG_CODE", "e")
        print(f"Initializing Kokoro with lang_code: {lang}")
        _pipeline = KPipeline(lang_code=lang)
        KOKORO_AVAILABLE = True
        print("Kokoro initialized successfully!")
    except Exception as e:
        print(f"Failed to import/initialize Kokoro: {e}")
        KOKORO_AVAILABLE = False

def list_voices() -> List[str]:
    _try_import()
    if KOKORO_AVAILABLE and hasattr(_pipeline, "voice_list"):
        return list(getattr(_pipeline, "voice_list", []))
    return ["em_santa", "em_gabriel", "em_diego", "pm_brazil", "pf_brazil"]

def synthesize(text: str, voice: Optional[str] = None, sample_rate: int = 24000) -> Tuple[bytes, int]:
    _try_import()
    print(f"KOKORO_AVAILABLE: {KOKORO_AVAILABLE}")
    print(f"Voice requested: {voice}")
    
    if KOKORO_AVAILABLE:
        voice_name = voice or os.getenv("KOKORO_DEFAULT_VOICE", "em_santa")
        print(f"Using Kokoro voice: {voice_name}")
        print(f"Pipeline available: {_pipeline is not None}")
        
        try:
            audio_chunks = []
            generator = _pipeline(text, voice=voice_name, speed=0.8, split_pattern=r'\n+')
            for i, (gs, ps, audio) in enumerate(generator):
                print(f"Generated chunk {i}: {len(audio)} samples")
                arr = np.asarray(audio, dtype=np.float32)
                pcm16 = (np.clip(arr, -1.0, 1.0) * 32767).astype(np.int16).tobytes()
                audio_chunks.append(pcm16)
            return (b"".join(audio_chunks), sample_rate)
        except Exception as e:
            print(f"Kokoro synthesis error: {e}")
            return (b"", 0)
    # fallback pyttsx3 -> return full WAV bytes
    print("Kokoro not available, using pyttsx3 fallback")
    try:
        import pyttsx3, tempfile
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            name = tmp.name
        engine = pyttsx3.init()
        
        # Configurar la voz según la selección del usuario
        voices = engine.getProperty('voices')
        if voice and voices:
            # Mapear las voces de Kokoro a las voces disponibles de pyttsx3
            voice_mapping = {
                'em_santa': 0,  # Primera voz disponible
                'em_gabriel': 1 if len(voices) > 1 else 0,
                'em_diego': 2 if len(voices) > 2 else 0,
                'pm_brazil': 0,  # Usar voz por defecto
                'pf_brazil': 1 if len(voices) > 1 else 0,
            }
            voice_index = voice_mapping.get(voice, 0)
            if voice_index < len(voices):
                engine.setProperty('voice', voices[voice_index].id)
                print(f"Using pyttsx3 voice: {voices[voice_index].name}")
        
        engine.save_to_file(text, name)
        engine.runAndWait()
        data = open(name, "rb").read()
        os.remove(name)
        print(f"Generated audio with pyttsx3: {len(data)} bytes")
        return (data, 22050)
    except Exception as e:
        print(f"pyttsx3 fallback error: {e}")
        return (b"", 0)
