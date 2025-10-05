import os
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from sqlmodel import select
from passlib.hash import bcrypt
from .db import init_db, get_session, User, Upload, Episode, PodcastScript
from .auth import create_token, verify_password, hash_password, get_current_user_id
from .pdf_extract import extract_text
from .summarize import summarize_text, script_from_summary
from .kokoro_provider import list_voices, synthesize
from .ai_service import ai_service

import uuid, wave, io, json
from datetime import datetime

app = FastAPI(title="Podcast Study MVP")

origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:3001").split(",") if o.strip()]
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
    return {"voices": list_voices()}

@app.get("/test-scripts")
def test_scripts():
    return {"message": "Scripts endpoint is working", "status": "ok"}

@app.get("/test-simple")
def test_simple():
    return {"message": "Simple test endpoint", "status": "ok"}

@app.post("/uploads")
def upload_file(file: UploadFile = File(...)):
    # save file
    uid = str(uuid.uuid4())
    path = os.path.join(UPLOAD_DIR, uid + "_" + file.filename)
    with open(path, "wb") as f:
        f.write(file.file.read())
    with get_session() as s:
        up = Upload(user_id=1, filename=file.filename, path=path)  # user_id fijo para testing
        s.add(up); s.commit(); s.refresh(up)
    return {"upload_id": up.id}

class ProcessIn(BaseModel):
    upload_id: int
    target_minutes: int = 10
    style: str = "conversational"
    voice: str | None = None

@app.post("/extract-text")
def extract_text_from_pdf(body: ProcessIn):
    """
    Extrae texto del PDF para que el usuario lo verifique
    """
    # fetch upload
    with get_session() as s:
        up = s.get(Upload, body.upload_id)
        if not up:
            raise HTTPException(404, "Upload no encontrado")
        
        # extract text from PDF
        text = extract_text(up.path)
        if not text.strip():
            raise HTTPException(400, "No se pudo extraer texto del PDF (¿es escaneado?)")
        
        return {
            "upload_id": body.upload_id,
            "title": up.filename,
            "extracted_text": text,
            "word_count": len(text.split()),
            "char_count": len(text)
        }

@app.post("/process")
def process(body: ProcessIn):
    """
    Procesa el texto verificado y genera un script de podcast usando IA
    """
    # fetch upload
    with get_session() as s:
        up = s.get(Upload, body.upload_id)
        if not up:
            raise HTTPException(404, "Upload no encontrado")
        
        # extract text from PDF
        text = extract_text(up.path)
        if not text.strip():
            raise HTTPException(400, "No se pudo extraer texto del PDF (¿es escaneado?)")
        
        # generate podcast script using AI
        script_result = ai_service.generate_podcast_script(
            text=text,
            target_minutes=body.target_minutes,
            style=body.style
        )
        
        # return script directly (sin almacenar en DB por ahora)
        return {
            "upload_id": body.upload_id,
            "title": up.filename,
            "sections": script_result["sections"],
            "script_content": script_result["script_content"],
            "estimated_duration": script_result["estimated_duration"],
            "word_count": script_result["word_count"],
            "target_minutes": body.target_minutes,
            "style": body.style,
            "voice": body.voice or "em_santa"
        }

@app.get("/scripts")
def list_scripts():
    """Lista todos los scripts de podcast del usuario"""
    try:
        from sqlmodel import select
        with get_session() as s:
            scripts = s.exec(select(PodcastScript).where(PodcastScript.user_id==1).order_by(PodcastScript.created_at.desc())).all()
            return [{
                "id": script.id, 
                "title": script.title, 
                "status": script.status,
                "target_minutes": script.target_minutes,
                "style": script.style,
                "voice": script.voice,
                "created_at": script.created_at.isoformat()
            } for script in scripts]
    except Exception as e:
        return {"error": str(e), "message": "Error al obtener scripts"}

@app.get("/scripts/{script_id}")
def get_script(script_id: int):
    """Obtiene un script específico con sus secciones"""
    with get_session() as s:
        script = s.get(PodcastScript, script_id)
        if not script:
            raise HTTPException(404, "Script no encontrado")
        
        sections = json.loads(script.script_sections) if script.script_sections else []
        
        return {
            "id": script.id,
            "title": script.title,
            "script_content": script.script_content,
            "sections": sections,
            "target_minutes": script.target_minutes,
            "style": script.style,
            "voice": script.voice,
            "status": script.status,
            "created_at": script.created_at.isoformat()
        }

class UpdateSectionIn(BaseModel):
    section_id: int
    new_content: str

@app.post("/scripts/{script_id}/update-section")
def update_script_section(script_id: int, body: UpdateSectionIn):
    """Actualiza una sección específica del script"""
    with get_session() as s:
        script = s.get(PodcastScript, script_id)
        if not script:
            raise HTTPException(404, "Script no encontrado")
        
        # Update the script content
        updated_content = ai_service.update_script_section(
            script.script_content, 
            body.section_id, 
            body.new_content
        )
        
        # Update sections JSON
        sections = json.loads(script.script_sections) if script.script_sections else []
        if 0 <= body.section_id < len(sections):
            sections[body.section_id]["content"] = body.new_content
        
        script.script_content = updated_content
        script.script_sections = json.dumps(sections)
        script.status = "script_edited"
        script.updated_at = datetime.utcnow()
        
        s.add(script)
        s.commit()
        s.refresh(script)
        
        return {"message": "Sección actualizada correctamente", "script_id": script.id}

class GenerateAudioIn(BaseModel):
    script_content: str
    title: str
    voice: str
    target_minutes: int

@app.post("/generate-audio")
def generate_audio(body: GenerateAudioIn):
    """Genera el audio final del podcast usando Kokoro"""
    with get_session() as s:
        # synthesize audio using Kokoro
        pcm_bytes, sr = synthesize(body.script_content, voice=body.voice)
        if not pcm_bytes:
            raise HTTPException(500, "TTS no disponible. Instala Kokoro o verifica pyttsx3.")
        
        # write WAV file
        eid = str(uuid.uuid4())
        wav_path = os.path.join(AUDIO_DIR, f"{eid}.wav")
        with wave.open(wav_path, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sr if sr else 24000)
            wf.writeframes(pcm_bytes)
        
        # create episode (sin referencia a script_id por ahora)
        episode = Episode(
            user_id=1,  # user_id fijo para testing
            script_id=0,  # No usamos script_id por ahora
            title=body.title,
            voice=body.voice,
            lang_code=os.getenv("KOKORO_LANG_CODE", "e"),
            duration_sec=body.target_minutes * 60,
            status="ready",
            audio_path=wav_path
        )
        s.add(episode)
        s.commit()
        s.refresh(episode)
        
        return {"episode_id": episode.id, "message": "Audio generado exitosamente"}

@app.get("/episodes")
def list_episodes():
    from sqlmodel import select
    with get_session() as s:
        eps = s.exec(select(Episode).where(Episode.user_id==1).order_by(Episode.created_at.desc())).all()  # user_id fijo para testing
        return [{"id": e.id, "title": e.title, "status": e.status, "duration_sec": e.duration_sec} for e in eps]

@app.get("/episodes/{episode_id}/audio")
def get_audio(episode_id: int):
    with get_session() as s:
        e = s.get(Episode, episode_id)
        if not e or not os.path.exists(e.audio_path):
            raise HTTPException(404, "Audio no disponible")
        return FileResponse(e.audio_path, media_type="audio/wav", filename=os.path.basename(e.audio_path))
