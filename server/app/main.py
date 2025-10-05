import os, uuid, wave, io
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlmodel import select
from passlib.hash import bcrypt

from .db import init_db, get_session, User, Upload, Episode
from .auth import create_token, verify_password, hash_password, get_current_user_id
from .pdf_extract import extract_text
from .summarize import summarize_text, script_from_summary
from .kokoro_provider import list_voices, synthesize
from .refine import refine_with_llm_like

app = FastAPI(title="PDF→Podcast MVP")

origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

init_db()

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
UPLOAD_DIR = os.path.join(DATA_DIR, "uploads")
AUDIO_DIR = os.path.join(DATA_DIR, "audio")
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(AUDIO_DIR, exist_ok=True)

class AuthIn(BaseModel):
    email: str
    password: str

@app.post("/auth/register")
def register(body: AuthIn):
    with get_session() as s:
        if s.exec(select(User).where(User.email == body.email)).first():
            raise HTTPException(400, "Email ya registrado")
        user = User(email=body.email, password_hash=hash_password(body.password))
        s.add(user); s.commit(); s.refresh(user)
        return {"ok": True}

@app.post("/auth/login")
def login(body: AuthIn):
    with get_session() as s:
        u = s.exec(select(User).where(User.email == body.email)).first()
        if not u or not verify_password(body.password, u.password_hash):
            raise HTTPException(401, "Credenciales inválidas")
        return {"access_token": create_token(u.id)}

@app.get("/voices")
def voices():
    from .kokoro_provider import KOKORO_AVAILABLE
    voices_list = list_voices()
    note = "Kokoro TTS no está disponible en este sistema. Se está usando pyttsx3 como alternativa." if not KOKORO_AVAILABLE else "Kokoro TTS está disponible."
    return {
        "voices": voices_list,
        "kokoro_available": KOKORO_AVAILABLE,
        "note": note
    }

@app.post("/uploads")
def upload_file(file: UploadFile = File(...)):
    # validate type and size (basic)
    allowed = {"application/pdf", "text/plain"}
    if file.content_type not in allowed:
        raise HTTPException(415, f"Tipo no soportado: {file.content_type}")
    uid = str(uuid.uuid4())
    path = os.path.join(UPLOAD_DIR, uid + "_" + file.filename)
    data = file.file.read()
    if len(data) > 40 * 1024 * 1024:
        raise HTTPException(413, "Archivo > 40MB")
    with open(path, "wb") as f:
        f.write(data)
    with get_session() as s:
        up = Upload(user_id=1, filename=file.filename, path=path)  # user_id fijo para testing
        s.add(up); s.commit(); s.refresh(up)
    return {"upload_id": up.id}

class DraftCreateIn(BaseModel):
    upload_id: int
    language: str = "es"

class DraftUpdateIn(BaseModel):
    refined_text: str

@app.post("/drafts")
def create_draft(body: DraftCreateIn):
    from .db import Draft
    with get_session() as s:
        up = s.get(Upload, body.upload_id)
        if not up:
            raise HTTPException(404, "Upload no encontrado")
        raw_text = extract_text(up.path)
        if not raw_text.strip():
            raise HTTPException(400, "No se pudo extraer texto (¿PDF escaneado?)")
        title, refined = refine_with_llm_like(raw_text, language=body.language)
        d = Draft(user_id=1, upload_id=up.id, raw_text=raw_text, refined_text=f"# {title}\n\n{refined}")  # user_id fijo para testing
        s.add(d); s.commit(); s.refresh(d)
        return {"draft_id": d.id, "title": title, "refined_text": d.refined_text}

@app.get("/drafts/{draft_id}")
def get_draft(draft_id: int):
    from .db import Draft
    with get_session() as s:
        d = s.get(Draft, draft_id)
        if not d:
            raise HTTPException(404, "Draft no encontrado")
        return {"draft_id": d.id, "refined_text": d.refined_text, "upload_id": d.upload_id}

@app.put("/drafts/{draft_id}")
def update_draft(draft_id: int, body: DraftUpdateIn):
    from .db import Draft
    with get_session() as s:
        d = s.get(Draft, draft_id)
        if not d:
            raise HTTPException(404, "Draft no encontrado")
        d.refined_text = body.refined_text
        s.add(d); s.commit(); s.refresh(d)
        return {"ok": True}

class ProcessIn(BaseModel):
    upload_id: int
    draft_id: int | None = None
    text_override: str | None = None
    target_minutes: int = 10
    style: str = "conversational"
    voice: str | None = None

@app.post("/generate-script")
def generate_script(body: ProcessIn):
    """
    Genera solo el script con secciones, sin generar audio
    """
    with get_session() as s:
        up = s.get(Upload, body.upload_id)
        if not up:
            raise HTTPException(404, "Upload no encontrado")
        
        # source: text_override > draft > extract
        if body.text_override:
            text_source = body.text_override
        elif body.draft_id:
            from .db import Draft
            d = s.get(Draft, body.draft_id)
            if not d or d.upload_id != up.id:
                raise HTTPException(404, "Draft no válido")
            text_source = d.refined_text
        else:
            text_source = extract_text(up.path)
        if not text_source.strip():
            raise HTTPException(400, "No hay texto disponible para procesar")

        # Dividir el texto en secciones basadas en títulos y subtítulos
        sections = create_sections_from_text(text_source, body.target_minutes)
        
        # Crear el script completo combinando todas las secciones
        script_content = create_full_script(sections)

        return {
            "upload_id": body.upload_id,
            "title": up.filename,
            "script_content": script_content,
            "sections": sections,
            "target_minutes": body.target_minutes,
            "style": body.style,
            "voice": body.voice or "em_santa"
        }

@app.post("/process")
def process(body: ProcessIn):
    with get_session() as s:
        up = s.get(Upload, body.upload_id)
        if not up:
            raise HTTPException(404, "Upload no encontrado")
        # source: text_override > draft > extract
        if body.text_override:
            text_source = body.text_override
        elif body.draft_id:
            from .db import Draft
            d = s.get(Draft, body.draft_id)
            if not d or d.upload_id != up.id:
                raise HTTPException(404, "Draft no válido")
            text_source = d.refined_text
        else:
            text_source = extract_text(up.path)
        if not text_source.strip():
            raise HTTPException(400, "No hay texto disponible para procesar")

        from .summarize import summarize_text, script_from_summary
        summary = summarize_text(text_source, max_sentences=min(18, 3*body.target_minutes))
        script = script_from_summary(summary)

        pcm_or_wav, sr = synthesize(script, voice=body.voice)
        if not pcm_or_wav:
            raise HTTPException(500, "TTS no disponible")

        eid = str(uuid.uuid4())
        wav_path = os.path.join(AUDIO_DIR, f"{eid}.wav")
        # If we received a full WAV (fallback), just write it. If PCM16, wrap it.
        if pcm_or_wav[:4] == b'RIFF':
            with open(wav_path, "wb") as f:
                f.write(pcm_or_wav)
        else:
            with wave.open(wav_path, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(sr or 24000)
                wf.writeframes(pcm_or_wav)

        ep = Episode(user_id=1, upload_id=up.id, title=up.filename, voice=body.voice or "default", lang_code=os.getenv("KOKORO_LANG_CODE","e"), duration_sec=body.target_minutes*60, status="ready", audio_path=wav_path)  # user_id fijo para testing
        s.add(ep); s.commit(); s.refresh(ep)
        return {"episode_id": ep.id}

@app.get("/episodes")
def list_episodes():
    with get_session() as s:
        eps = s.exec(select(Episode).where(Episode.user_id==1).order_by(Episode.created_at.desc())).all()  # user_id fijo para testing
        return [{"id": e.id, "title": e.title, "status": e.status, "duration_sec": e.duration_sec} for e in eps]

@app.get("/debug-text/{upload_id}")
def debug_text(upload_id: int):
    """Endpoint de debug para ver el texto extraído"""
    with get_session() as s:
        up = s.get(Upload, upload_id)
        if not up:
            raise HTTPException(404, "Upload no encontrado")
        
        text = extract_text(up.path)
        return {
            "upload_id": upload_id,
            "filename": up.filename,
            "raw_text": text[:1000] + "..." if len(text) > 1000 else text,
            "text_length": len(text)
        }

@app.get("/episodes/{episode_id}/audio")
def get_audio(episode_id: int):
    with get_session() as s:
        e = s.get(Episode, episode_id)
        if not e or not os.path.exists(e.audio_path):
            raise HTTPException(404, "Audio no disponible")
        return FileResponse(e.audio_path, media_type="audio/wav", filename=os.path.basename(e.audio_path))

def create_sections_from_text(text: str, target_minutes: int) -> list:
    """
    Divide el texto en secciones lógicas basadas en títulos y subtítulos
    """
    import re
    
    # Limpiar el texto
    text = re.sub(r'\s+', ' ', text.strip())
    
    sections = []
    section_id = 1
    
    # Dividir por títulos principales (UNIDAD, CAPÍTULO, etc.)
    main_sections = re.split(r'(UNIDAD\s+\d+[:\s]*[^.]*?|CAPÍTULO\s+\d+[:\s]*[^.]*?|\d+\.\s*[A-Z][^.]*?)', text, flags=re.IGNORECASE)
    
    if len(main_sections) > 1:
        # Procesar cada sección principal
        for i in range(0, len(main_sections), 2):
            if i + 1 < len(main_sections):
                title = main_sections[i].strip()
                content = main_sections[i + 1].strip()
                
                if len(content) > 50:
                    # Dividir la sección en subsecciones si es muy larga
                    subsections = split_large_section(content, title)
                    for subsection in subsections:
                        cleaned_content = clean_and_enhance_content(subsection['content'])
                        sections.append({
                            "id": section_id,
                            "title": subsection['title'][:100],
                            "content": cleaned_content,
                            "estimated_duration": max(1, len(cleaned_content.split()) // 150)
                        })
                        section_id += 1
    
    # Si no se encontraron secciones, dividir por párrafos largos
    if not sections:
        # Buscar subtítulos específicos del contenido de criptografía (manejar caracteres especiales)
        crypto_sections = re.split(r'(CRIPTOGRAF[IÍ]A[^.]*?|CRIPTOAN[ÁA]LISIS[^.]*?|BLOCKCHAIN[^.]*?|HASH[^.]*?|P2P[^.]*?|CONTRATOS INTELIGENTES[^.]*?|SERVICIOS DE LA CRIPTOGRAF[IÍ]A[^.]*?|PRIMITIVAS CRIPTOGR[ÁA]FICAS[^.]*?|UNIDAD\s+\d+[^.]*?|INTRODUCCI[ÓO]N[^.]*?)', text, flags=re.IGNORECASE)
        
        if len(crypto_sections) > 1:
            for i in range(0, len(crypto_sections), 2):
                if i + 1 < len(crypto_sections):
                    title = crypto_sections[i].strip()
                    content = crypto_sections[i + 1].strip()
                    
                    if len(content) > 50:
                        cleaned_content = clean_and_enhance_content(content)
                        sections.append({
                            "id": section_id,
                            "title": title[:100] if title else f"Sección {section_id}",
                            "content": cleaned_content,
                            "estimated_duration": max(1, len(cleaned_content.split()) // 150)
                        })
                        section_id += 1
        
        # Si aún no hay secciones, dividir por párrafos
        if not sections:
            paragraphs = re.split(r'\.\s+(?=[A-Z])', text)  # Dividir por oraciones que empiecen con mayúscula
            current_content = ""
            
            for para in paragraphs:
                para = para.strip()
                if len(para) > 100:
                    current_content += para + ". "
                    
                    # Crear sección cada ~300 palabras
                    if len(current_content.split()) > 300:
                        cleaned_content = clean_and_enhance_content(current_content)
                        sections.append({
                            "id": section_id,
                            "title": f"Sección {section_id}",
                            "content": cleaned_content,
                            "estimated_duration": max(1, len(cleaned_content.split()) // 150)
                        })
                        section_id += 1
                        current_content = ""
            
            # Agregar contenido restante
            if current_content.strip():
                cleaned_content = clean_and_enhance_content(current_content)
                sections.append({
                    "id": section_id,
                    "title": f"Sección {section_id}",
                    "content": cleaned_content,
                    "estimated_duration": max(1, len(cleaned_content.split()) // 150)
                })
    
    # Si aún no hay secciones, crear una sección con todo el contenido
    if not sections:
        cleaned_content = clean_and_enhance_content(text)
        sections.append({
            "id": 1,
            "title": "Contenido Principal",
            "content": cleaned_content,
            "estimated_duration": max(1, len(cleaned_content.split()) // 150)
        })
    
    return sections

def split_large_section(content: str, base_title: str) -> list:
    """
    Divide una sección grande en subsecciones más pequeñas
    """
    import re
    
    subsections = []
    
    # Buscar subtítulos dentro de la sección
    sub_patterns = [
        r'(CRIPTOGRAFÍA[^.]*?|CRIPTOANÁLISIS[^.]*?|BLOCKCHAIN[^.]*?|HASH[^.]*?|P2P[^.]*?|CONTRATOS INTELIGENTES[^.]*?|SERVICIOS DE LA CRIPTOGRAFÍA[^.]*?|PRIMITIVAS CRIPTOGRÁFICAS[^.]*?)',
        r'([A-Z][A-Z\s]{10,}?)(?=[A-Z][A-Z\s]{10,}|$)',
    ]
    
    for pattern in sub_patterns:
        parts = re.split(pattern, content, flags=re.IGNORECASE)
        if len(parts) > 1:
            for i in range(0, len(parts), 2):
                if i + 1 < len(parts):
                    title = parts[i].strip()
                    subcontent = parts[i + 1].strip()
                    
                    if len(subcontent) > 50:
                        subsections.append({
                            "title": title[:100] if title else f"{base_title} - Parte {len(subsections) + 1}",
                            "content": subcontent
                        })
            break
    
    # Si no se encontraron subtítulos, dividir por párrafos
    if not subsections:
        paragraphs = re.split(r'\.\s+(?=[A-Z])', content)
        current_content = ""
        part_num = 1
        
        for para in paragraphs:
            para = para.strip()
            if len(para) > 100:
                current_content += para + ". "
                
                if len(current_content.split()) > 200:
                    subsections.append({
                        "title": f"{base_title} - Parte {part_num}",
                        "content": current_content
                    })
                    part_num += 1
                    current_content = ""
        
        if current_content.strip():
            subsections.append({
                "title": f"{base_title} - Parte {part_num}",
                "content": current_content
            })
    
    return subsections

def clean_and_enhance_content(content: str) -> str:
    """
    Limpia y mejora el contenido para que sea más comprensible
    """
    import re
    
    # Limpiar el texto
    content = re.sub(r'\s+', ' ', content.strip())
    
    # Agregar contexto y explicaciones para términos técnicos (manejar caracteres especiales)
    enhancements = {
        r'\bCRIPTOGRAF[IÍ]A\b': 'La criptografía',
        r'\bCRIPTOAN[ÁA]LISIS\b': 'el criptoanálisis',
        r'\bBLOCKCHAIN\b': 'la tecnología blockchain',
        r'\bHASH\b': 'la función hash',
        r'\bP2P\b': 'las redes peer-to-peer',
        r'\bCONTRATOS INTELIGENTES\b': 'los contratos inteligentes',
        r'\bUNIDAD\s+\d+\b': 'En esta unidad',
        r'\bINTRODUCCI[ÓO]N\b': 'Para introducir',
    }
    
    for pattern, replacement in enhancements.items():
        content = re.sub(pattern, replacement, content, flags=re.IGNORECASE)
    
    # Agregar conectores para mejorar la fluidez
    content = re.sub(r'([.!?])\s*([A-Z])', r'\1 Además, \2', content)
    content = re.sub(r'([.!?])\s*([A-Z])', r'\1 Por otro lado, \2', content)
    
    # Limpiar dobles conectores
    content = re.sub(r'(Además, )+', 'Además, ', content)
    content = re.sub(r'(Por otro lado, )+', 'Por otro lado, ', content)
    
    return content

def create_full_script(sections: list) -> str:
    """
    Crea el script completo combinando todas las secciones
    """
    intro = "Bienvenidos. Hoy repasamos los puntos clave de la clase. "
    outro = " Gracias por escuchar. Repite este episodio para consolidar y consulta tus apuntes."
    
    script_parts = [intro]
    
    for i, section in enumerate(sections):
        script_parts.append(f"## {section['title']}")
        script_parts.append(section['content'])
        if i < len(sections) - 1:
            script_parts.append("Ahora pasemos al siguiente tema.")
    
    script_parts.append(outro)
    
    return " ".join(script_parts)
