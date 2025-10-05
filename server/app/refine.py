from typing import Tuple
import re

def refine_with_llm_like(text: str, language: str = "es") -> Tuple[str, str]:
    """Devuelve (title, refined_text) mejorado y formateado (MVP heurístico)."""
    t = re.sub(r"\s+", " ", text).strip()
    sentences = re.split(r"(?<=[.!?])\s+", t)
    # Crear 3–5 bloques
    n = max(3, min(5, max(1, len(sentences)//6)))
    size = max(1, len(sentences)//n)
    blocks = [sentences[i*size:(i+1)*size] for i in range(n)]
    if sum(len(b) for b in blocks) < len(sentences):
        blocks[-1].extend(sentences[n*size:])

    parts = ["# Resumen mejorado", ""]
    for i, b in enumerate(blocks, 1):
        parts.append(f"## Sección {i}")
        for s in b:
            s = s.strip()
            if not s: continue
            if any(k in s.lower() for k in ["es ", "son ", "define", "significa"]):
                parts.append(f"- **Idea clave:** {s}")
            else:
                parts.append(f"- {s}")
        parts.append("")
    title = "Resumen y guía de estudio" if language.startswith("es") else "Improved study outline"
    return title, "\n".join(parts).strip()
