"""
Servicio de IA para generar scripts de podcast
"""
import json
import re
from typing import List, Dict, Any
from .podcast_rules import get_podcast_prompt

class PodcastAIService:
    def __init__(self):
        # Por ahora usaremos un servicio simple, pero aquí se puede integrar OpenAI, Claude, etc.
        self.available_models = ["simple", "openai", "claude"]
    
    def generate_podcast_script(self, text: str, target_minutes: int = 10, style: str = "conversational") -> Dict[str, Any]:
        """
        Genera un script de podcast a partir del texto extraído del PDF
        """
        # Por ahora usaremos un generador simple, pero esto se puede reemplazar con una API real
        script_content = self._generate_simple_script(text, target_minutes, style)
        sections = self._parse_script_into_sections(script_content)
        
        return {
            "script_content": script_content,
            "sections": sections,
            "estimated_duration": target_minutes,
            "word_count": len(script_content.split())
        }
    
    def _generate_simple_script(self, text: str, target_minutes: int, style: str) -> str:
        """
        Generador simple de script (placeholder para IA real)
        """
        # Extraer las primeras oraciones del texto
        sentences = text.split('.')[:20]  # Tomar las primeras 20 oraciones
        main_content = '. '.join(sentences) + '.'
        
        # Generar script básico
        script = f"""
¡Hola! Bienvenidos a este podcast educativo. Hoy vamos a explorar un tema muy interesante que encontré en mis apuntes.

{self._create_introduction(main_content)}

Ahora, vamos a profundizar en los conceptos principales:

{self._create_main_content(main_content, style)}

Y para finalizar, déjame resumir los puntos más importantes:

{self._create_conclusion(main_content)}

¡Gracias por escuchar! Espero que este contenido te haya sido útil para tu aprendizaje.
        """.strip()
        
        return script
    
    def _create_introduction(self, content: str) -> str:
        """Crea una introducción atractiva"""
        first_sentence = content.split('.')[0] + '.'
        return f"""
En este episodio, vamos a hablar sobre {first_sentence.lower()}

Es un tema fascinante que puede cambiar la forma en que entiendes este concepto. Así que prepárate para un viaje de aprendizaje que será tanto educativo como entretenido.
        """.strip()
    
    def _create_main_content(self, content: str, style: str) -> str:
        """Crea el contenido principal"""
        sentences = content.split('.')[:10]
        main_text = '. '.join(sentences) + '.'
        
        if style == "conversational":
            return f"""
Primero, déjame explicarte esto de una manera simple: {main_text}

¿Te has preguntado alguna vez por qué esto es importante? Bueno, déjame contarte algo interesante...

{main_text}

Y aquí viene la parte más emocionante: cuando entiendes estos conceptos, todo comienza a tener sentido.
            """.strip()
        elif style == "formal":
            return f"""
El contenido principal que debemos analizar es el siguiente: {main_text}

Es importante destacar que este tema presenta varios aspectos fundamentales que requieren nuestra atención.

{main_text}

En consecuencia, podemos observar que estos elementos están interconectados de manera significativa.
            """.strip()
        else:  # casual
            return f"""
Oye, esto es genial: {main_text}

¿Sabes qué? Esto es súper importante y te voy a explicar por qué...

{main_text}

¡Y aquí está lo mejor! Una vez que entiendes esto, todo se vuelve mucho más fácil.
            """.strip()
    
    def _create_conclusion(self, content: str) -> str:
        """Crea una conclusión"""
        return """
Para resumir lo que hemos aprendido hoy:

1. Hemos explorado los conceptos fundamentales de este tema
2. Hemos visto cómo estos elementos se relacionan entre sí
3. Hemos entendido la importancia práctica de este conocimiento

Recuerda que el aprendizaje es un proceso continuo, y cada vez que repases este contenido, encontrarás nuevas conexiones y perspectivas.

¡No olvides practicar lo que has aprendido y seguir explorando!
        """.strip()
    
    def _parse_script_into_sections(self, script: str) -> List[Dict[str, Any]]:
        """
        Parsea el script en secciones para que el usuario pueda editarlas
        """
        sections = []
        
        # Dividir por párrafos y crear secciones
        paragraphs = [p.strip() for p in script.split('\n\n') if p.strip()]
        
        for i, paragraph in enumerate(paragraphs):
            if i == 0:
                title = "Introducción"
            elif i == len(paragraphs) - 1:
                title = "Conclusión"
            else:
                title = f"Sección {i}"
            
            sections.append({
                "id": i + 1,
                "title": title,
                "content": paragraph,
                "estimated_duration": max(1, len(paragraph.split()) // 150)  # ~150 palabras por minuto
            })
        
        return sections
    
    def update_script_section(self, script_content: str, section_id: int, new_content: str) -> str:
        """
        Actualiza una sección específica del script
        """
        sections = script_content.split('\n\n')
        if 0 <= section_id < len(sections):
            sections[section_id] = new_content
            return '\n\n'.join(sections)
        return script_content

# Instancia global del servicio
ai_service = PodcastAIService()

