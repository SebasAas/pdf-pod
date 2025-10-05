'use client'
import { useState } from 'react'
import { apiBase } from '@/lib/api'
export default function Login() {
  const [email, setEmail] = useState(''); const [password, setPassword] = useState(''); const [msg, setMsg] = useState('')
  const onSubmit = async (e:any) => {
    e.preventDefault()
    const res = await fetch(`${apiBase()}/auth/login`, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({email,password})})
    if (res.ok) { const data = await res.json(); localStorage.setItem('token', data.access_token); location.href='/dashboard' } else setMsg('Error de credenciales')
  }
  return <main><h2>Login</h2><form onSubmit={onSubmit} style={{display:'grid', gap:8, maxWidth:320}}>
    <input placeholder="email" value={email} onChange={e=>setEmail(e.target.value)} />
    <input type="password" placeholder="password" value={password} onChange={e=>setPassword(e.target.value)} />
    <button type="submit">Entrar</button></form><p>{msg}</p></main>
}
