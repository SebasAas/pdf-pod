export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <body style={{fontFamily:'system-ui,Segoe UI,Roboto,Inter,sans-serif', maxWidth: 860, margin: '0 auto', padding: 16}}>
        <header style={{display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:24}}>
          <a href="/" style={{fontWeight:700}}>🎧 StudyPodcast</a>
          <nav style={{display:'flex',gap:12}}>
            <a href="/login">Login</a>
            <a href="/register">Register</a>
            <a href="/dashboard">Dashboard</a>
          </nav>
        </header>
        {children}
      </body>
    </html>
  );
}