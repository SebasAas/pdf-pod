export default function Home() {
  return (
    <main>
      <div style={{ textAlign: "center", marginBottom: "3rem" }}>
        <h1 style={{ fontSize: "2.5rem", marginBottom: "1rem", color: "#333" }}>
          🎧 StudyPodcast
        </h1>
        <p style={{ fontSize: "1.2rem", color: "#666", marginBottom: "2rem" }}>
          Convierte tus apuntes en podcasts para estudiar de forma más eficiente
        </p>
        <p
          style={{
            fontSize: "1rem",
            color: "#888",
            maxWidth: "600px",
            margin: "0 auto",
          }}
        >
          Subí tu PDF, elegí una voz y escuchá un resumen en minutos. Perfecto
          para repasar tus clases mientras caminás, viajás o hacés ejercicio.
        </p>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(250px, 1fr))",
          gap: "2rem",
          marginBottom: "3rem",
        }}
      >
        <div
          style={{
            padding: "1.5rem",
            border: "1px solid #ddd",
            borderRadius: "8px",
            textAlign: "center",
            backgroundColor: "#f9f9f9",
          }}
        >
          <div style={{ fontSize: "2rem", marginBottom: "1rem" }}>📚</div>
          <h3>1. Subí tu PDF</h3>
          <p>Sube los apuntes de tu clase en formato PDF</p>
        </div>

        <div
          style={{
            padding: "1.5rem",
            border: "1px solid #ddd",
            borderRadius: "8px",
            textAlign: "center",
            backgroundColor: "#f9f9f9",
          }}
        >
          <div style={{ fontSize: "2rem", marginBottom: "1rem" }}>🎯</div>
          <h3>2. Personalizá</h3>
          <p>Elegí la voz, duración y estilo que prefieras</p>
        </div>

        <div
          style={{
            padding: "1.5rem",
            border: "1px solid #ddd",
            borderRadius: "8px",
            textAlign: "center",
            backgroundColor: "#f9f9f9",
          }}
        >
          <div style={{ fontSize: "2rem", marginBottom: "1rem" }}>🎧</div>
          <h3>3. Escuchá y estudiá</h3>
          <p>Disfrutá tu podcast personalizado en cualquier momento</p>
        </div>
      </div>

      <div style={{ textAlign: "center" }}>
        <h2 style={{ marginBottom: "1rem" }}>¿Listo para empezar?</h2>
        <div
          style={{
            display: "flex",
            gap: "1rem",
            justifyContent: "center",
            flexWrap: "wrap",
          }}
        >
          <a
            href="/register"
            style={{
              padding: "0.75rem 2rem",
              backgroundColor: "#007bff",
              color: "white",
              textDecoration: "none",
              borderRadius: "4px",
              fontWeight: "bold",
            }}
          >
            Crear Cuenta
          </a>
          <a
            href="/login"
            style={{
              padding: "0.75rem 2rem",
              backgroundColor: "transparent",
              color: "#007bff",
              textDecoration: "none",
              borderRadius: "4px",
              border: "2px solid #007bff",
              fontWeight: "bold",
            }}
          >
            Iniciar Sesión
          </a>
        </div>
      </div>

      <div
        style={{
          marginTop: "3rem",
          padding: "2rem",
          backgroundColor: "#f8f9fa",
          borderRadius: "8px",
          textAlign: "center",
        }}
      >
        <h3 style={{ marginBottom: "1rem" }}>✨ Características</h3>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
            gap: "1rem",
            fontSize: "0.9rem",
          }}
        >
          <div>🤖 IA para resumir contenido</div>
          <div>🎙️ Múltiples voces disponibles</div>
          <div>⏱️ Duración personalizable</div>
          <div>📱 Acceso desde cualquier dispositivo</div>
        </div>
      </div>
    </main>
  );
}
