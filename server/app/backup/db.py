from sqlmodel import SQLModel, Field, Session, create_engine, select
from typing import Optional
from datetime import datetime

engine = create_engine("sqlite:///app.db", echo=False)

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(index=True, unique=True)
    password_hash: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Upload(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    filename: str
    path: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class PodcastScript(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    upload_id: int
    title: str
    raw_text: str  # Texto extraído del PDF
    script_content: str  # Script generado por IA
    script_sections: str  # JSON con las secciones del script
    target_minutes: int
    style: str
    voice: str
    status: str = Field(default="script_generated")  # script_generated|script_edited|audio_generated
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class Episode(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    script_id: int  # Referencia al script
    title: str
    voice: str
    lang_code: str
    duration_sec: int = 0
    status: str = Field(default="pending")  # pending|ready|error
    audio_path: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)

def init_db():
    SQLModel.metadata.create_all(engine)

def get_session():
    return Session(engine)
