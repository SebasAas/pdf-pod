"use client";
import { useState, useEffect } from "react";
import { apiBase, authHeader } from "@/lib/api";

interface Voice {
  name: string;
  displayName: string;
}

interface Episode {
  id: number;
  title: string;
  status: string;
  duration_sec: number;
}

interface ScriptSection {
  id: number;
  title: string;
  content: string;
  estimated_duration: number;
}

interface Script {
  id: number;
  title: string;
  script_content: string;
  sections: ScriptSection[];
  target_minutes: number;
  style: string;
  voice: string;
  status: string;
  created_at: string;
}

export default function Dashboard() {
  const [file, setFile] = useState<File | null>(null);
  const [voices, setVoices] = useState<Voice[]>([]);
  const [selectedVoice, setSelectedVoice] = useState<string>("");
  const [targetMinutes, setTargetMinutes] = useState<number>(10);
  const [style, setStyle] = useState<string>("conversational");
  const [episodes, setEpisodes] = useState<Episode[]>([]);
  const [currentScript, setCurrentScript] = useState<Script | null>(null);
  const [extractedText, setExtractedText] = useState<string>("");
  const [isUploading, setIsUploading] = useState(false);
  const [isExtracting, setIsExtracting] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isGeneratingAudio, setIsGeneratingAudio] = useState(false);
  const [uploadId, setUploadId] = useState<number | null>(null);
  const [error, setError] = useState<string>("");
  const [editingSection, setEditingSection] = useState<number | null>(null);
  const [editingContent, setEditingContent] = useState<string>("");
  const [currentStep, setCurrentStep] = useState<
    "upload" | "extract" | "script" | "audio"
  >("upload");

  // Cargar voces disponibles
  useEffect(() => {
    fetch(`${apiBase()}/voices`)
      .then((res) => res.json())
      .then((data) => {
        const voiceOptions = data.voices.map((voice: string) => ({
          name: voice,
          displayName: voice.replace("_", " ").toUpperCase(),
        }));
        setVoices(voiceOptions);
        if (voiceOptions.length > 0) {
          setSelectedVoice(voiceOptions[0].name);
        }
      })
      .catch((err) => console.error("Error loading voices:", err));
  }, []);

  // Cargar episodios existentes
  useEffect(() => {
    const token = localStorage.getItem("token");
    if (token) {
      // Cargar episodios
      fetch(`${apiBase()}/episodes`, {
        headers: authHeader(),
      })
        .then((res) => res.json())
        .then((data) => setEpisodes(data))
        .catch((err) => console.error("Error loading episodes:", err));
    }
  }, []);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile && selectedFile.type === "application/pdf") {
      setFile(selectedFile);
      setError("");
    } else {
      setError("Por favor selecciona un archivo PDF válido");
    }
  };

  const handleUpload = async () => {
    if (!file) {
      setError("Por favor selecciona un archivo PDF");
      return;
    }

    setIsUploading(true);
    setError("");

    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await fetch(`${apiBase()}/uploads`, {
        method: "POST",
        headers: authHeader(),
        body: formData,
      });

      if (!response.ok) {
        throw new Error("Error al subir el archivo");
      }

      const data = await response.json();
      setUploadId(data.upload_id);
      setIsUploading(false);
      setCurrentStep("extract");
    } catch (err) {
      setError("Error al subir el archivo");
      setIsUploading(false);
    }
  };

  const handleExtractText = async () => {
    if (!uploadId) {
      setError("Primero debes subir un archivo");
      return;
    }

    setIsExtracting(true);
    setError("");

    try {
      const response = await fetch(`${apiBase()}/extract-text`, {
        method: "POST",
        headers: {
          ...authHeader(),
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          upload_id: uploadId,
          target_minutes: targetMinutes,
          style: style,
          voice: selectedVoice,
        }),
      });

      if (!response.ok) {
        throw new Error("Error al extraer texto del PDF");
      }

      const data = await response.json();
      setExtractedText(data.extracted_text);
      setIsExtracting(false);
      setCurrentStep("script");
    } catch (err) {
      setError("Error al extraer texto del PDF");
      setIsExtracting(false);
    }
  };

  const handleProcess = async () => {
    if (!uploadId) {
      setError("Primero debes subir un archivo");
      return;
    }

    setIsProcessing(true);
    setError("");

    try {
      const response = await fetch(`${apiBase()}/process`, {
        method: "POST",
        headers: {
          ...authHeader(),
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          upload_id: uploadId,
          target_minutes: targetMinutes,
          style: style,
          voice: selectedVoice,
        }),
      });

      if (!response.ok) {
        throw new Error("Error al procesar el archivo");
      }

      const data = await response.json();

      // Establecer el script actual directamente desde la respuesta
      setCurrentScript({
        id: 0, // No usamos ID por ahora
        title: data.title,
        script_content: data.script_content,
        sections: data.sections,
        target_minutes: data.target_minutes,
        style: data.style,
        voice: data.voice,
        status: "script_generated",
        created_at: new Date().toISOString(),
      });

      setIsProcessing(false);
      setCurrentStep("audio");

      // Limpiar el input de archivo
      const fileInput = document.getElementById("pdf-file") as HTMLInputElement;
      if (fileInput) fileInput.value = "";
    } catch (err) {
      setError("Error al procesar el archivo");
      setIsProcessing(false);
    }
  };

  const playEpisode = (episodeId: number) => {
    const audioUrl = `${apiBase()}/episodes/${episodeId}/audio`;
    const audio = new Audio(audioUrl);
    audio.play();
  };

  const handleEditSection = (sectionId: number, content: string) => {
    setEditingSection(sectionId);
    setEditingContent(content);
  };

  const handleSaveSection = async () => {
    if (!currentScript || editingSection === null) return;

    // Actualizar la sección localmente
    const updatedSections = currentScript.sections.map((section) => {
      if (section.id === editingSection) {
        return { ...section, content: editingContent };
      }
      return section;
    });

    // Reconstruir el script content
    const updatedScriptContent = updatedSections
      .map((section) => section.content)
      .join("\n\n");

    setCurrentScript({
      ...currentScript,
      sections: updatedSections,
      script_content: updatedScriptContent,
    });

    setEditingSection(null);
    setEditingContent("");
  };

  const handleGenerateAudio = async () => {
    if (!currentScript) return;

    setIsGeneratingAudio(true);
    setError("");

    try {
      const response = await fetch(`${apiBase()}/generate-audio`, {
        method: "POST",
        headers: {
          ...authHeader(),
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          script_content: currentScript.script_content,
          title: currentScript.title,
          voice: currentScript.voice,
          target_minutes: currentScript.target_minutes,
        }),
      });

      if (!response.ok) {
        throw new Error("Error al generar el audio");
      }

      const data = await response.json();

      // Recargar episodios
      const episodesResponse = await fetch(`${apiBase()}/episodes`, {
        headers: authHeader(),
      });
      const episodesData = await episodesResponse.json();
      setEpisodes(episodesData);

      setIsGeneratingAudio(false);
      setCurrentScript(null);
      alert("¡Audio generado exitosamente!");
    } catch (err) {
      setError("Error al generar el audio");
      setIsGeneratingAudio(false);
    }
  };

  return (
    <main>
      <h1>🎧 Dashboard - StudyPodcast</h1>

      <div
        style={{
          marginBottom: "2rem",
          padding: "1rem",
          border: "1px solid #ddd",
          borderRadius: "8px",
        }}
      >
        <h2>Crear nuevo podcast</h2>

        {/* Paso 1: Subir PDF */}
        {currentStep === "upload" && (
          <div>
            <h3>Paso 1: Subir archivo PDF</h3>
            <div style={{ marginBottom: "1rem" }}>
              <label
                htmlFor="pdf-file"
                style={{ display: "block", marginBottom: "0.5rem" }}
              >
                Seleccionar archivo PDF:
              </label>
              <input
                id="pdf-file"
                type="file"
                accept=".pdf"
                onChange={handleFileChange}
                style={{ marginBottom: "0.5rem" }}
              />
              {file && <p>Archivo seleccionado: {file.name}</p>}
            </div>

            {error && (
              <div style={{ color: "red", marginBottom: "1rem" }}>{error}</div>
            )}

            <button
              onClick={handleUpload}
              disabled={!file || isUploading}
              style={{
                padding: "0.75rem 1.5rem",
                backgroundColor: isUploading ? "#ccc" : "#007bff",
                color: "white",
                border: "none",
                borderRadius: "4px",
                cursor: isUploading ? "not-allowed" : "pointer",
              }}
            >
              {isUploading ? "Subiendo..." : "Subir PDF"}
            </button>
          </div>
        )}

        {/* Paso 2: Extraer texto */}
        {currentStep === "extract" && (
          <div>
            <h3>Paso 2: Extraer texto del PDF</h3>
            <p>
              El archivo se ha subido correctamente. Ahora vamos a extraer el
              texto para que puedas verificar que esté correcto.
            </p>

            {error && (
              <div style={{ color: "red", marginBottom: "1rem" }}>{error}</div>
            )}

            <button
              onClick={handleExtractText}
              disabled={isExtracting}
              style={{
                padding: "0.75rem 1.5rem",
                backgroundColor: isExtracting ? "#ccc" : "#28a745",
                color: "white",
                border: "none",
                borderRadius: "4px",
                cursor: isExtracting ? "not-allowed" : "pointer",
              }}
            >
              {isExtracting ? "Extrayendo texto..." : "Extraer Texto"}
            </button>
          </div>
        )}

        {/* Paso 3: Verificar texto extraído */}
        {currentStep === "script" && (
          <div>
            <h3>Paso 3: Verificar texto extraído</h3>
            <p>
              Revisa el texto extraído del PDF. Si está correcto, puedes
              proceder a generar el script del podcast.
            </p>

            <div style={{ marginBottom: "1rem" }}>
              <label
                htmlFor="voice-select"
                style={{ display: "block", marginBottom: "0.5rem" }}
              >
                Seleccionar voz:
              </label>
              <select
                id="voice-select"
                value={selectedVoice}
                onChange={(e) => setSelectedVoice(e.target.value)}
                style={{
                  padding: "0.5rem",
                  borderRadius: "4px",
                  border: "1px solid #ccc",
                }}
              >
                {voices.map((voice) => (
                  <option key={voice.name} value={voice.name}>
                    {voice.displayName}
                  </option>
                ))}
              </select>
            </div>

            <div style={{ marginBottom: "1rem" }}>
              <label
                htmlFor="minutes"
                style={{ display: "block", marginBottom: "0.5rem" }}
              >
                Duración objetivo (minutos):
              </label>
              <input
                id="minutes"
                type="number"
                min="5"
                max="30"
                value={targetMinutes}
                onChange={(e) => setTargetMinutes(Number(e.target.value))}
                style={{
                  padding: "0.5rem",
                  borderRadius: "4px",
                  border: "1px solid #ccc",
                }}
              />
            </div>

            <div style={{ marginBottom: "1rem" }}>
              <label
                htmlFor="style"
                style={{ display: "block", marginBottom: "0.5rem" }}
              >
                Estilo:
              </label>
              <select
                id="style"
                value={style}
                onChange={(e) => setStyle(e.target.value)}
                style={{
                  padding: "0.5rem",
                  borderRadius: "4px",
                  border: "1px solid #ccc",
                }}
              >
                <option value="conversational">Conversacional</option>
                <option value="formal">Formal</option>
                <option value="casual">Casual</option>
              </select>
            </div>

            <div style={{ marginBottom: "1rem" }}>
              <h4>Texto extraído:</h4>
              <textarea
                value={extractedText}
                onChange={(e) => setExtractedText(e.target.value)}
                style={{
                  width: "100%",
                  minHeight: "200px",
                  padding: "0.5rem",
                  border: "1px solid #ccc",
                  borderRadius: "4px",
                }}
                placeholder="El texto extraído aparecerá aquí..."
              />
            </div>

            {error && (
              <div style={{ color: "red", marginBottom: "1rem" }}>{error}</div>
            )}

            <div style={{ display: "flex", gap: "1rem" }}>
              <button
                onClick={handleProcess}
                disabled={isProcessing}
                style={{
                  padding: "0.75rem 1.5rem",
                  backgroundColor: isProcessing ? "#ccc" : "#28a745",
                  color: "white",
                  border: "none",
                  borderRadius: "4px",
                  cursor: isProcessing ? "not-allowed" : "pointer",
                }}
              >
                {isProcessing
                  ? "Generando Script..."
                  : "Generar Script de Podcast"}
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Sección del Script */}
      {currentScript && (
        <div
          style={{
            marginBottom: "2rem",
            padding: "1rem",
            border: "1px solid #ddd",
            borderRadius: "8px",
            backgroundColor: "#f9f9f9",
          }}
        >
          <h2>📝 Script del Podcast: {currentScript.title}</h2>
          <p>
            <strong>Estilo:</strong> {currentScript.style} |{" "}
            <strong>Voz:</strong> {currentScript.voice} |{" "}
            <strong>Duración objetivo:</strong> {currentScript.target_minutes}{" "}
            minutos
          </p>

          <div style={{ marginBottom: "1rem" }}>
            <h3>Secciones del Script:</h3>
            {currentScript.sections &&
              currentScript.sections.map((section) => (
                <div
                  key={section.id}
                  style={{
                    marginBottom: "1rem",
                    padding: "1rem",
                    border: "1px solid #ccc",
                    borderRadius: "4px",
                    backgroundColor: "white",
                  }}
                >
                  <h4>
                    {section.title} ({section.estimated_duration} min)
                  </h4>
                  {editingSection === section.id ? (
                    <div>
                      <textarea
                        value={editingContent}
                        onChange={(e) => setEditingContent(e.target.value)}
                        style={{
                          width: "100%",
                          minHeight: "100px",
                          padding: "0.5rem",
                          border: "1px solid #ccc",
                          borderRadius: "4px",
                        }}
                      />
                      <div style={{ marginTop: "0.5rem" }}>
                        <button
                          onClick={handleSaveSection}
                          style={{
                            padding: "0.5rem 1rem",
                            backgroundColor: "#28a745",
                            color: "white",
                            border: "none",
                            borderRadius: "4px",
                            cursor: "pointer",
                            marginRight: "0.5rem",
                          }}
                        >
                          Guardar
                        </button>
                        <button
                          onClick={() => {
                            setEditingSection(null);
                            setEditingContent("");
                          }}
                          style={{
                            padding: "0.5rem 1rem",
                            backgroundColor: "#6c757d",
                            color: "white",
                            border: "none",
                            borderRadius: "4px",
                            cursor: "pointer",
                          }}
                        >
                          Cancelar
                        </button>
                      </div>
                    </div>
                  ) : (
                    <div>
                      <p style={{ whiteSpace: "pre-wrap" }}>
                        {section.content}
                      </p>
                      <button
                        onClick={() =>
                          handleEditSection(section.id, section.content)
                        }
                        style={{
                          padding: "0.25rem 0.5rem",
                          backgroundColor: "#007bff",
                          color: "white",
                          border: "none",
                          borderRadius: "4px",
                          cursor: "pointer",
                          fontSize: "0.8rem",
                        }}
                      >
                        ✏️ Editar
                      </button>
                    </div>
                  )}
                </div>
              ))}
          </div>

          <div style={{ display: "flex", gap: "1rem" }}>
            <button
              onClick={handleGenerateAudio}
              disabled={isGeneratingAudio}
              style={{
                padding: "0.75rem 1.5rem",
                backgroundColor: isGeneratingAudio ? "#ccc" : "#dc3545",
                color: "white",
                border: "none",
                borderRadius: "4px",
                cursor: isGeneratingAudio ? "not-allowed" : "pointer",
              }}
            >
              {isGeneratingAudio
                ? "Generando Audio..."
                : "🎵 Generar Audio Final"}
            </button>
            <button
              onClick={() => setCurrentScript(null)}
              style={{
                padding: "0.75rem 1.5rem",
                backgroundColor: "#6c757d",
                color: "white",
                border: "none",
                borderRadius: "4px",
                cursor: "pointer",
              }}
            >
              Cerrar Script
            </button>
          </div>
        </div>
      )}

      <div>
        <h2>🎧 Mis Podcasts</h2>
        {episodes.length === 0 ? (
          <p>No tienes podcasts generados aún.</p>
        ) : (
          <div>
            {episodes.map((episode) => (
              <div
                key={episode.id}
                style={{
                  padding: "1rem",
                  border: "1px solid #ddd",
                  borderRadius: "8px",
                  marginBottom: "1rem",
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                }}
              >
                <div>
                  <h3>{episode.title}</h3>
                  <p>Estado: {episode.status}</p>
                  <p>
                    Duración: {Math.round(episode.duration_sec / 60)} minutos
                  </p>
                </div>
                <button
                  onClick={() => playEpisode(episode.id)}
                  disabled={episode.status !== "ready"}
                  style={{
                    padding: "0.5rem 1rem",
                    backgroundColor:
                      episode.status === "ready" ? "#007bff" : "#ccc",
                    color: "white",
                    border: "none",
                    borderRadius: "4px",
                    cursor:
                      episode.status === "ready" ? "pointer" : "not-allowed",
                  }}
                >
                  ▶️ Reproducir
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </main>
  );
}
