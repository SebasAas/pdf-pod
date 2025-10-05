'use client'
import { useState } from 'react'
import { apiBase } from '@/lib/api'
export default function Register() {
  const [email, setEmail] = useState(''); const [password, setPassword] = useState(''); const [msg, setMsg] = useState('')
  const onSubmit = async (e:any) => {
    e.preventDefault()
    const res = await fetch(`${apiBase()}/auth/register`, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({email,password})})
    setMsg(res.ok ? 'Registro ok. Ir a login.' : 'No se pudo registrar'); if (res.ok) location.href='/login'
  }
  return <main><h2>Registro</h2><form onSubmit={onSubmit} style={{display:'grid', gap:8, maxWidth:320}}>
    <input placeholder="email" value={email} onChange={e=>setEmail(e.target.value)} />
    <input type="password" placeholder="password" value={password} onChange={e=>setPassword(e.target.value)} />
    <button type="submit">Crear cuenta</button></form><p>{msg}</p></main>
}
