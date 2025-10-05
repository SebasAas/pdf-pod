from typing import List
import re

def split_sentences(text: str) -> List[str]:
    text = re.sub(r"\s+", " ", text)
    return re.split(r"(?<=[.!?])\s+", text)

def summarize_text(text: str, max_sentences: int = 12) -> str:
    # super simple: take first N sentences + headings heuristic
    sents = [s.strip() for s in split_sentences(text) if len(s.strip()) > 0]
    return " ".join(sents[:max_sentences])

def script_from_summary(summary: str) -> str:
    intro = "Bienvenidos. Hoy repasamos los puntos clave de la clase. "
    outro = "Gracias por escuchar. Repite este episodio para consolidar y consulta tus apuntes. "
    return intro + summary + " " + outro
