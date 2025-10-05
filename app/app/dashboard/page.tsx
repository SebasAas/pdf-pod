"use client";
import { useEffect, useState } from "react";
import { apiBase, authHeader } from "@/lib/api";

type Episode = {
  id: number;
  title: string;
  status: string;
  duration_sec: number;
};

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
  const [voices, setVoices] = useState<string[]>([]);
  const [selectedVoice, setSelectedVoice] = useState<string>("");
  const [episodes, setEpisodes] = useState<Episode[]>([]);
  const [minutes, setMinutes] = useState(10);
  const [msg, setMsg] = useState("");
  const [uploadId, setUploadId] = useState<number | null>(null);
  const [draftId, setDraftId] = useState<number | null>(null);
  const [refinedText, setRefinedText] = useState<string>("");
  const [currentScript, setCurrentScript] = useState<Script | null>(null);
  const [editingSection, setEditingSection] = useState<number | null>(null);
  const [editingContent, setEditingContent] = useState<string>("");
  const [step, setStep] = useState<
    "idle" | "uploaded" | "draft_ready" | "generating"
  >("idle");

  useEffect(() => {
    fetch(`${apiBase()}/voices`)
      .then((r) => r.json())
      .then((d) => {
        setVoices(d.voices || []);
        if (!d.kokoro_available) {
          setMsg(
            "Nota: Kokoro TTS no está disponible. Se está usando pyttsx3 como alternativa."
          );
        }
      });
    refreshEpisodes();
  }, []);

  const refreshEpisodes = async () => {
    const r = await fetch(`${apiBase()}/episodes`);
    if (r.ok) setEpisodes(await r.json());
  };

  const onUpload = async (e: any) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const form = new FormData();
    form.append("file", file);
    const r = await fetch(`${apiBase()}/uploads`, {
      method: "POST",
      body: form,
    });
    if (!r.ok) {
      setMsg("Error subiendo archivo");
      return;
    }
    const { upload_id } = await r.json();
    setUploadId(upload_id);
    setStep("uploaded");
    setMsg("Archivo subido. Generando script con secciones...");

    // Generar script con secciones usando el endpoint /generate-script
    const processResponse = await fetch(`${apiBase()}/generate-script`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        upload_id,
        target_minutes: minutes,
        style: "conversational",
        voice: selectedVoice || "em_santa",
      }),
    });
    if (!processResponse.ok) {
      setMsg("No se pudo generar script");
      return;
    }
    const scriptData = await processResponse.json();
    // Crear objeto Script con secciones
    const script: Script = {
      id: Date.now(), // ID temporal
      title: scriptData.title,
      script_content: scriptData.script_content,
      sections: scriptData.sections || [],
      target_minutes: scriptData.target_minutes,
      style: scriptData.style,
      voice: scriptData.voice,
      status: "draft",
      created_at: new Date().toISOString(),
    };
    setCurrentScript(script);
    setStep("draft_ready");
    setMsg(
      "Script generado con secciones. Podés editar cada sección individualmente."
    );
  };

  const startEditingSection = (sectionId: number, content: string) => {
    setEditingSection(sectionId);
    setEditingContent(content);
  };

  const saveSectionEdit = () => {
    if (!currentScript || editingSection === null) return;

    const updatedSections = currentScript.sections.map((section) =>
      section.id === editingSection
        ? { ...section, content: editingContent }
        : section
    );

    setCurrentScript({
      ...currentScript,
      sections: updatedSections,
    });

    setEditingSection(null);
    setEditingContent("");
    setMsg("Sección actualizada");
  };

  const cancelSectionEdit = () => {
    setEditingSection(null);
    setEditingContent("");
  };

  const generateAudio = async () => {
    if (!currentScript || !uploadId) {
      setMsg("Falta script o upload");
      return;
    }
    setStep("generating");

    // Combinar todas las secciones en un script completo
    const fullScript = currentScript.sections
      .map((section) => `## ${section.title}\n\n${section.content}`)
      .join("\n\n");

    const p = await fetch(`${apiBase()}/process`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        upload_id: uploadId,
        text_override: fullScript,
        target_minutes: minutes,
        style: "conversational",
        voice: selectedVoice || "em_santa",
      }),
    });
    setMsg(p.ok ? "Episodio creado" : "Error procesando");
    await refreshEpisodes();
    setStep("idle");
    setCurrentScript(null);
  };

  return (
    <main>
      <h2>Panel</h2>
      <section style={{ display: "grid", gap: 8, maxWidth: 900 }}>
        <label>
          Voz:
          <select
            value={selectedVoice}
            onChange={(e) => setSelectedVoice(e.target.value)}
          >
            <option value="">Por defecto</option>
            {voices.map((v) => (
              <option key={v} value={v}>
                {v}
              </option>
            ))}
          </select>
        </label>
        <label>
          Duración objetivo (min):
          <input
            type="number"
            min={3}
            max={30}
            value={minutes}
            onChange={(e) => setMinutes(parseInt(e.target.value || "10"))}
          />
        </label>

        <div style={{ border: "1px solid #ddd", padding: 12, borderRadius: 8 }}>
          <h3>1) Subir archivo</h3>
          <input type="file" accept=".pdf,.txt" onChange={onUpload} />
          <p>{msg}</p>
        </div>

        {step !== "idle" && currentScript && (
          <div
            style={{ border: "1px solid #ddd", padding: 12, borderRadius: 8 }}
          >
            <h3>2) Revisar y editar script por secciones</h3>
            <p>
              <strong>Título:</strong> {currentScript.title}
            </p>
            <p>
              <strong>Duración objetivo:</strong> {currentScript.target_minutes}{" "}
              minutos
            </p>

            <div style={{ marginTop: "1rem" }}>
              <h4>Secciones del Script:</h4>
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
                    <h5>
                      {section.title} ({section.estimated_duration} min)
                    </h5>
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
                            onClick={saveSectionEdit}
                            style={{ marginRight: "0.5rem" }}
                          >
                            Guardar
                          </button>
                          <button onClick={cancelSectionEdit}>Cancelar</button>
                        </div>
                      </div>
                    ) : (
                      <div>
                        <p
                          style={{
                            whiteSpace: "pre-wrap",
                            marginBottom: "0.5rem",
                          }}
                        >
                          {section.content}
                        </p>
                        <button
                          onClick={() =>
                            startEditingSection(section.id, section.content)
                          }
                        >
                          Editar sección
                        </button>
                      </div>
                    )}
                  </div>
                ))}
            </div>

            <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
              <button onClick={generateAudio} disabled={step === "generating"}>
                3) Generar audio
              </button>
            </div>
          </div>
        )}
      </section>

      <h3 style={{ marginTop: 24 }}>Tus episodios</h3>
      <ul>
        {episodes.map((ep) => (
          <li key={ep.id} style={{ margin: "8px 0" }}>
            <b>{ep.title}</b> — {ep.status}
            {ep.status === "ready" && (
              <audio
                controls
                src={`${apiBase()}/episodes/${ep.id}/audio`}
                style={{ display: "block", marginTop: 4 }}
              />
            )}
          </li>
        ))}
      </ul>
    </main>
  );
}
