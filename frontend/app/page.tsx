"use client";

import { useEffect, useRef, useState } from "react";

/* ─────────────────────────────────────────────
   Palette
   E1A36F  Harvest Gold
   DEC484  Calico
   E2D8A5  Hampton (cream)
   6F9F9C  Sea Nymph  ← accent / CTA
   577E89  Smalt Blue ← deep / structural
───────────────────────────────────────────── */

type Message = {
  role: "user" | "assistant";
  content: string;
  agent?: string;
};
type User = { name: string; email: string; role: string };

const AGENT_META: Record<string, { label: string; dot: string; badge: string }> = {
  system:  { label: "SYSTEM",    dot: "#6F9F9C", badge: "rgba(111,159,156,0.15)" },
  auth:    { label: "AUTH",      dot: "#DEC484", badge: "rgba(222,196,132,0.15)" },
  ai:      { label: "COREPILOT", dot: "#E1A36F", badge: "rgba(225,163,111,0.15)" },
  hr:      { label: "HR AGENT",  dot: "#E2D8A5", badge: "rgba(226,216,165,0.12)" },
  it:      { label: "IT AGENT",  dot: "#6F9F9C", badge: "rgba(111,159,156,0.15)" },
};

const QUICK = [
  { icon: "📋", label: "Leave History",  q: "show my leave history" },
  { icon: "🎫", label: "Ticket Status",  q: "show my ticket status" },
  { icon: "💼", label: "Asset Request",  q: "show my asset request status" },
  { icon: "📖", label: "Leave Policy",   q: "what is leave policy?" },
];

export default function Home() {
  const [user, setUser]             = useState<User | null>(null);
  const [email, setEmail]           = useState("employee@novigo.com");
  const [password, setPassword]     = useState("password123");
  const [token, setToken]           = useState("");
  const [messages, setMessages]     = useState<Message[]>([
    { role: "assistant", content: "👋 Hi! I'm your AI Corepilot.\n\nLogin to start using HR and IT workflows.", agent: "system" },
  ]);
  const [input, setInput]           = useState("");
  const [loading, setLoading]       = useState(false);
  const [loginError, setLoginError] = useState("");
  const bottomRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);

  async function login() {
    setLoginError("");
    try {
      const res  = await fetch("http://127.0.0.1:8000/login", { method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify({ email, password }) });
      const data = await res.json();
      if (!data.success) { setLoginError(data.message || "Login failed"); return; }
      setToken(data.token);
      setUser({ name: data.name, email: data.email, role: data.role });
      setMessages([{ role:"assistant", content:`Welcome back, ${data.name}.\nSigned in as ${data.role}.`, agent:"auth" }]);
    } catch { setLoginError("Backend login failed. Check FastAPI server."); }
  }

  async function sendMessage(messageText?: string) {
    const text = messageText || input;
    if (!text.trim() || !token) return;
    setMessages(prev => [...prev, { role:"user", content:text }]);
    setInput(""); setLoading(true);
    try {
      const res  = await fetch("http://127.0.0.1:8000/chat", { method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify({ message:text, token }) });
      const data = await res.json();
      setMessages(prev => [...prev, { role:"assistant", content: data.reply || "No response received.", agent: data.agent || "ai" }]);
    } catch {
      setMessages(prev => [...prev, { role:"assistant", content:"⚠️ Backend connection failed.", agent:"system" }]);
    } finally { setLoading(false); }
  }

  const initials = user?.name.split(" ").map(n => n[0]).join("").slice(0,2).toUpperCase() ?? "U";

  const css = `
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;600;700&family=Syne:wght@400;500;600;700&display=swap');

    *, *::before, *::after { box-sizing: border-box; margin:0; padding:0; }
    html, body { height:100%; background:#0a1820; font-family:'Syne',sans-serif; }

    :root {
      --gold:   #E1A36F;
      --calico: #DEC484;
      --cream:  #E2D8A5;
      --teal:   #6F9F9C;
      --deep:   #577E89;
      --ink:    #0a1820;
    }

    /* ── ANIMATED MESH BACKGROUND ── */
    .cp-bg {
      position: fixed; inset: 0; z-index: 0;
      background: #0a1820;
      overflow: hidden;
    }
    .cp-blob {
      position: absolute; border-radius: 50%;
      filter: blur(100px); will-change: transform;
    }
    .cp-blob-1 {
      width: 720px; height: 720px;
      background: radial-gradient(circle, rgba(225,163,111,0.48) 0%, transparent 65%);
      top: -250px; left: -200px;
      animation: bFloat1 20s ease-in-out infinite;
    }
    .cp-blob-2 {
      width: 650px; height: 650px;
      background: radial-gradient(circle, rgba(87,126,137,0.55) 0%, transparent 65%);
      bottom: -200px; right: -180px;
      animation: bFloat2 25s ease-in-out infinite;
    }
    .cp-blob-3 {
      width: 520px; height: 520px;
      background: radial-gradient(circle, rgba(111,159,156,0.38) 0%, transparent 65%);
      top: 35%; left: 50%;
      animation: bFloat3 18s ease-in-out infinite;
    }
    .cp-blob-4 {
      width: 420px; height: 420px;
      background: radial-gradient(circle, rgba(222,196,132,0.3) 0%, transparent 65%);
      top: 58%; left: 8%;
      animation: bFloat4 22s ease-in-out infinite 2s;
    }
    .cp-blob-5 {
      width: 380px; height: 380px;
      background: radial-gradient(circle, rgba(225,163,111,0.25) 0%, transparent 65%);
      top: 15%; right: 12%;
      animation: bFloat1 16s ease-in-out infinite 4s;
    }

    @keyframes bFloat1 { 0%,100%{transform:translate(0,0) scale(1)} 35%{transform:translate(50px,-60px) scale(1.06)} 70%{transform:translate(-30px,35px) scale(0.96)} }
    @keyframes bFloat2 { 0%,100%{transform:translate(0,0) scale(1)} 40%{transform:translate(-70px,50px) scale(1.08)} 75%{transform:translate(40px,-25px) scale(0.94)} }
    @keyframes bFloat3 { 0%,100%{transform:translate(0,0)} 50%{transform:translate(-50px,70px) scale(1.1)} }
    @keyframes bFloat4 { 0%,100%{transform:translate(0,0) scale(1)} 45%{transform:translate(60px,-40px) scale(1.07)} }

    /* ── GRAIN OVERLAY ── */
    .cp-grain {
      position: fixed; inset:0; z-index:1; pointer-events:none; opacity:0.04;
      background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
      background-size: 180px;
    }

    /* ── GLASSMORPHISM CARD ── */
    .cp-glass {
      background: rgba(255,255,255,0.05);
      border: 1px solid rgba(255,255,255,0.11);
      backdrop-filter: blur(28px) saturate(160%) brightness(1.05);
      -webkit-backdrop-filter: blur(28px) saturate(160%) brightness(1.05);
    }
    .cp-glass-dark {
      background: rgba(10,24,32,0.60);
      border: 1px solid rgba(255,255,255,0.09);
      backdrop-filter: blur(36px) saturate(180%);
      -webkit-backdrop-filter: blur(36px) saturate(180%);
    }

    /* ── SCROLLBAR ── */
    .cp-scroll::-webkit-scrollbar { width:3px; }
    .cp-scroll::-webkit-scrollbar-track { background:transparent; }
    .cp-scroll::-webkit-scrollbar-thumb { background:rgba(111,159,156,0.28); border-radius:2px; }

    /* ── ANIMATIONS ── */
    @keyframes cpFadeUp { from{opacity:0;transform:translateY(22px)} to{opacity:1;transform:translateY(0)} }
    @keyframes cpMsgIn  { from{opacity:0;transform:translateY(10px) scale(0.98)} to{opacity:1;transform:translateY(0) scale(1)} }
    @keyframes cpDot    { 0%,60%,100%{transform:translateY(0);opacity:0.3} 30%{transform:translateY(-5px);opacity:1} }
    @keyframes cpPulse  { 0%,100%{box-shadow:0 0 0 0 rgba(111,159,156,0.5)} 50%{box-shadow:0 0 0 6px rgba(111,159,156,0)} }

    .cp-fade-up { animation: cpFadeUp 0.55s cubic-bezier(.22,1,.36,1) both; }
    .cp-msg-in  { animation: cpMsgIn  0.32s cubic-bezier(.22,1,.36,1) both; }

    /* ── INPUT ── */
    .cp-input {
      width:100%; background:rgba(255,255,255,0.05); border:1px solid rgba(255,255,255,0.1);
      border-radius:12px; padding:13px 18px;
      font-family:'Syne',sans-serif; font-size:13px; color:rgba(226,216,165,0.9);
      outline:none; transition:border-color .2s, background .2s, box-shadow .2s; letter-spacing:.01em;
    }
    .cp-input::placeholder { color:rgba(111,159,156,0.38); }
    .cp-input:focus { border-color:rgba(111,159,156,0.55); background:rgba(111,159,156,0.08); box-shadow:0 0 0 3px rgba(111,159,156,0.13); }

    /* ── CTA BUTTON (Sea Nymph accent) ── */
    .cp-cta {
      background: linear-gradient(135deg, #6F9F9C 0%, #4d7a87 100%);
      border: none; border-radius:12px; color:#E2D8A5;
      font-family:'Syne',sans-serif; font-size:13px; font-weight:700;
      letter-spacing:.08em; cursor:pointer;
      transition: transform .18s, box-shadow .18s, opacity .18s;
      box-shadow: 0 5px 22px rgba(87,126,137,0.4), inset 0 1px 0 rgba(255,255,255,0.15);
      position:relative; overflow:hidden;
    }
    .cp-cta::after { content:''; position:absolute; inset:0; background:linear-gradient(135deg,rgba(255,255,255,0.14) 0%,transparent 55%); opacity:0; transition:opacity .2s; }
    .cp-cta:hover:not(:disabled) { transform:translateY(-2px); box-shadow:0 10px 32px rgba(87,126,137,0.5); }
    .cp-cta:hover:not(:disabled)::after { opacity:1; }
    .cp-cta:active:not(:disabled) { transform:translateY(0); }
    .cp-cta:disabled { opacity:.38; cursor:not-allowed; }

    /* ── QUICK PILL ── */
    .cp-pill {
      display:inline-flex; align-items:center; gap:7px; padding:7px 15px;
      border-radius:100px; background:rgba(255,255,255,0.05);
      border:1px solid rgba(255,255,255,0.1); cursor:pointer; white-space:nowrap;
      font-family:'Syne',sans-serif; font-size:11.5px; font-weight:500;
      color:rgba(226,216,165,0.65); letter-spacing:.025em;
      transition:all .18s;
    }
    .cp-pill:hover:not(:disabled) { background:rgba(111,159,156,0.14); border-color:rgba(111,159,156,0.38); color:#E2D8A5; transform:translateY(-1px); box-shadow:0 4px 16px rgba(111,159,156,0.18); }
    .cp-pill:disabled { opacity:.3; cursor:not-allowed; }

    /* ── SEND BUTTON ── */
    .cp-send {
      width:46px; height:46px; border-radius:12px; border:none; flex-shrink:0;
      background:linear-gradient(135deg,#6F9F9C,#4d7a87); color:#E2D8A5;
      font-size:20px; display:flex; align-items:center; justify-content:center;
      cursor:pointer; transition:all .18s;
      box-shadow:0 5px 18px rgba(87,126,137,0.38), inset 0 1px 0 rgba(255,255,255,0.15);
    }
    .cp-send:hover:not(:disabled) { transform:scale(1.08) rotate(-8deg); box-shadow:0 8px 26px rgba(87,126,137,0.5); }
    .cp-send:disabled { opacity:.35; cursor:not-allowed; }

    /* ── LOGOUT ── */
    .cp-logout {
      font-family:'Syne',sans-serif; font-size:11px; font-weight:600;
      letter-spacing:.1em; text-transform:uppercase;
      background:rgba(255,255,255,0.06); border:1px solid rgba(255,255,255,0.1);
      border-radius:9px; padding:6px 14px; color:rgba(226,216,165,0.55);
      cursor:pointer; transition:all .18s;
    }
    .cp-logout:hover { background:rgba(225,163,111,0.14); border-color:rgba(225,163,111,0.3); color:var(--cream); }

    /* ── FIELD LABEL ── */
    .cp-label {
      font-family:'Syne',sans-serif; font-size:10.5px; font-weight:700;
      letter-spacing:.16em; text-transform:uppercase; color:rgba(111,159,156,0.7);
    }

    /* ── ONLINE DOT ── */
    .cp-online-dot {
      width:8px; height:8px; border-radius:50%; background:#6F9F9C;
      animation: cpPulse 2s ease-in-out infinite;
    }
  `;

  /* ── LOGIN ── */
  if (!user) return (
    <>
      <style>{css}</style>
      <div className="cp-bg">
        <div className="cp-blob cp-blob-1"/><div className="cp-blob cp-blob-2"/>
        <div className="cp-blob cp-blob-3"/><div className="cp-blob cp-blob-4"/>
        <div className="cp-blob cp-blob-5"/>
      </div>
      <div className="cp-grain"/>

      <main style={{ position:"relative", zIndex:2, minHeight:"100vh", display:"flex", alignItems:"center", justifyContent:"center", padding:"24px" }}>
        <div className="cp-glass-dark cp-fade-up" style={{ width:"100%", maxWidth:"430px", borderRadius:"24px", overflow:"hidden", boxShadow:"0 28px 90px rgba(0,0,0,0.55), inset 0 1px 0 rgba(255,255,255,0.1)" }}>

          {/* Header */}
          <div style={{ padding:"38px 38px 30px", borderBottom:"1px solid rgba(255,255,255,0.07)", position:"relative", overflow:"hidden" }}>
            <div style={{ position:"absolute", top:-60, right:-60, width:200, height:200, borderRadius:"50%", background:"radial-gradient(circle,rgba(225,163,111,0.22),transparent 70%)", filter:"blur(24px)", pointerEvents:"none" }}/>
            <div style={{ position:"absolute", bottom:-40, left:-40, width:160, height:160, borderRadius:"50%", background:"radial-gradient(circle,rgba(111,159,156,0.2),transparent 70%)", filter:"blur(20px)", pointerEvents:"none" }}/>

            <div style={{ display:"flex", alignItems:"center", gap:"12px", marginBottom:"16px" }}>
              <div style={{ width:"38px", height:"38px", borderRadius:"10px", background:"linear-gradient(135deg,#6F9F9C,#577E89)", display:"flex", alignItems:"center", justifyContent:"center", fontSize:"18px", boxShadow:"0 4px 16px rgba(87,126,137,0.45)" }}>✦</div>
              <div>
                <div style={{ fontFamily:"'Playfair Display',serif", fontSize:"10px", fontWeight:400, letterSpacing:"0.22em", textTransform:"uppercase", color:"rgba(111,159,156,0.65)", marginBottom:"2px" }}>Novigo Solutions</div>
                <div style={{ fontFamily:"'Playfair Display',serif", fontSize:"30px", fontWeight:700, color:"#E2D8A5", lineHeight:1, letterSpacing:"-0.02em", textShadow:"0 2px 16px rgba(0,0,0,0.4)" }}>Corepilot</div>
              </div>
            </div>
            <div style={{ fontFamily:"'Syne',sans-serif", fontSize:"12px", color:"rgba(111,159,156,0.6)", letterSpacing:"0.05em" }}>HR · IT · Multi-Agent Intelligence Platform</div>
          </div>

          {/* Form */}
          <div style={{ padding:"30px 38px 38px", display:"flex", flexDirection:"column", gap:"18px" }}>
            <div style={{ display:"flex", flexDirection:"column", gap:"8px" }}>
              <label className="cp-label">Email Address</label>
              <input className="cp-input" value={email} onChange={e=>setEmail(e.target.value)} placeholder="employee@novigo.com"/>
            </div>
            <div style={{ display:"flex", flexDirection:"column", gap:"8px" }}>
              <label className="cp-label">Password</label>
              <input type="password" className="cp-input" value={password} onChange={e=>setPassword(e.target.value)} placeholder="••••••••"/>
            </div>

            {loginError && (
              <div style={{ background:"rgba(192,82,74,0.12)", border:"1px solid rgba(192,82,74,0.25)", borderRadius:"10px", padding:"11px 15px", fontFamily:"'Syne',sans-serif", fontSize:"12.5px", color:"#f28a80", letterSpacing:"0.01em" }}>
                {loginError}
              </div>
            )}

            <button className="cp-cta" style={{ padding:"15px", width:"100%", marginTop:"4px", textTransform:"uppercase", letterSpacing:"0.12em" }} onClick={login}>
              Sign In →
            </button>

            <div style={{ background:"rgba(255,255,255,0.04)", border:"1px solid rgba(255,255,255,0.08)", borderRadius:"12px", padding:"15px 18px", fontFamily:"'Syne',sans-serif", fontSize:"11px", color:"rgba(111,159,156,0.65)", lineHeight:"1.9", letterSpacing:"0.02em" }}>
              <div style={{ fontWeight:700, letterSpacing:"0.18em", textTransform:"uppercase", fontSize:"9.5px", color:"rgba(111,159,156,0.45)", marginBottom:"7px" }}>Demo Credentials</div>
              employee@novigo.com<br/>it@novigo.com<br/>ashika.shridhar@novigosolutions.com
              <br/><span style={{ color:"rgba(226,216,165,0.25)" }}>password: password123</span>
            </div>
          </div>
        </div>
      </main>
    </>
  );

  /* ── CHAT ── */
  return (
    <>
      <style>{css}</style>
      <div className="cp-bg">
        <div className="cp-blob cp-blob-1"/><div className="cp-blob cp-blob-2"/>
        <div className="cp-blob cp-blob-3"/><div className="cp-blob cp-blob-4"/>
        <div className="cp-blob cp-blob-5"/>
      </div>
      <div className="cp-grain"/>

      <main style={{ position:"relative", zIndex:2, minHeight:"100vh", display:"flex", alignItems:"center", justifyContent:"center", padding:"20px" }}>
        <div className="cp-glass-dark cp-fade-up" style={{ width:"100%", maxWidth:"1040px", height:"92vh", borderRadius:"22px", overflow:"hidden", display:"flex", flexDirection:"column", boxShadow:"0 36px 110px rgba(0,0,0,0.6), inset 0 1px 0 rgba(255,255,255,0.1)" }}>

          {/* ── TOPBAR ── */}
          <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between", padding:"0 28px", height:"68px", background:"rgba(10,24,32,0.65)", borderBottom:"1px solid rgba(255,255,255,0.07)", flexShrink:0, backdropFilter:"blur(24px)", WebkitBackdropFilter:"blur(24px)", boxShadow:"0 1px 0 rgba(255,255,255,0.06), 0 4px 30px rgba(0,0,0,0.2)" }}>
            <div style={{ display:"flex", alignItems:"center", gap:"14px" }}>
              <div style={{ width:"34px", height:"34px", borderRadius:"9px", background:"linear-gradient(135deg,#6F9F9C,#577E89)", display:"flex", alignItems:"center", justifyContent:"center", fontSize:"16px", boxShadow:"0 4px 14px rgba(87,126,137,0.45)" }}>✦</div>
              <div>
                <div style={{ fontFamily:"'Playfair Display',serif", fontSize:"22px", fontWeight:700, color:"#E2D8A5", lineHeight:1, letterSpacing:"-0.01em", textShadow:"0 1px 8px rgba(0,0,0,0.3)" }}>Corepilot</div>
                <div style={{ fontFamily:"'Syne',sans-serif", fontSize:"9.5px", fontWeight:500, letterSpacing:"0.18em", textTransform:"uppercase", color:"rgba(111,159,156,0.5)", marginTop:"2px" }}>HR · IT · RAG · Multi-Agent</div>
              </div>
            </div>

            <div style={{ display:"flex", alignItems:"center", gap:"16px" }}>
              <div style={{ display:"flex", alignItems:"center", gap:"7px" }}>
                <div className="cp-online-dot"/>
                <span style={{ fontFamily:"'Syne',sans-serif", fontSize:"10px", color:"rgba(111,159,156,0.55)", letterSpacing:"0.1em", textTransform:"uppercase" }}>Online</span>
              </div>
              <div style={{ width:"1px", height:"26px", background:"rgba(255,255,255,0.09)" }}/>
              <div style={{ display:"flex", alignItems:"center", gap:"11px" }}>
                <div style={{ textAlign:"right" }}>
                  <div style={{ fontFamily:"'Syne',sans-serif", fontSize:"12.5px", fontWeight:600, color:"rgba(226,216,165,0.9)", letterSpacing:"0.02em" }}>{user.name}</div>
                  <div style={{ fontFamily:"'Syne',sans-serif", fontSize:"9.5px", fontWeight:500, color:"rgba(111,159,156,0.5)", letterSpacing:"0.13em", textTransform:"uppercase", marginTop:"1px" }}>{user.role}</div>
                </div>
                <div style={{ width:"36px", height:"36px", borderRadius:"50%", display:"flex", alignItems:"center", justifyContent:"center", fontFamily:"'Syne',sans-serif", fontWeight:700, fontSize:"12px", flexShrink:0, background:"linear-gradient(135deg,#E1A36F,#DEC484)", color:"#1a2a30", border:"2px solid rgba(222,196,132,0.25)", boxShadow:"0 0 18px rgba(225,163,111,0.3)" }}>{initials}</div>
              </div>
              <button className="cp-logout" onClick={()=>{ setUser(null); setToken(""); setMessages([{ role:"assistant", content:"Logged out. Please login again.", agent:"system" }]); }}>Exit</button>
            </div>
          </div>

          {/* ── QUICK ACTIONS ── */}
          <div style={{ display:"flex", gap:"8px", padding:"12px 28px", borderBottom:"1px solid rgba(255,255,255,0.06)", flexShrink:0, overflowX:"auto", scrollbarWidth:"none", background:"rgba(10,24,32,0.25)" }}>
            {QUICK.map(a => (
              <button key={a.q} className="cp-pill" onClick={()=>sendMessage(a.q)} disabled={loading}>
                <span style={{ fontSize:"13px" }}>{a.icon}</span>{a.label}
              </button>
            ))}
          </div>

          {/* ── MESSAGES ── */}
          <div className="cp-scroll" style={{ flex:1, overflowY:"auto", padding:"28px 32px", display:"flex", flexDirection:"column", gap:"24px" }}>
            {messages.map((msg, i) => {
              const meta = AGENT_META[msg.agent||"ai"] || AGENT_META.ai;
              return (
                <div key={i} className="cp-msg-in" style={{ display:"flex", gap:"12px", flexDirection:msg.role==="user"?"row-reverse":"row", animationDelay:`${Math.min(i*0.04,0.24)}s` }}>
                  {/* Avatar */}
                  <div style={{ width:"32px", height:"32px", borderRadius:"50%", flexShrink:0, display:"flex", alignItems:"center", justifyContent:"center", fontFamily:"'Syne',sans-serif", fontWeight:700, fontSize:"11px", marginTop:"5px", letterSpacing:"0.02em", background: msg.role==="user" ? "linear-gradient(135deg,#E1A36F,#DEC484)" : "linear-gradient(135deg,#6F9F9C,#577E89)", color: msg.role==="user" ? "#1a2a30" : "#E2D8A5", boxShadow: msg.role==="user" ? "0 4px 12px rgba(225,163,111,0.3)" : "0 4px 12px rgba(87,126,137,0.3)" }}>
                    {msg.role==="user" ? initials : "✦"}
                  </div>

                  <div style={{ display:"flex", flexDirection:"column", gap:"6px", maxWidth:"67%", alignItems: msg.role==="user"?"flex-end":"flex-start" }}>
                    {msg.role==="assistant" && (
                      <div style={{ display:"inline-flex", alignItems:"center", gap:"5px", padding:"3px 10px", borderRadius:"100px", background:meta.badge, border:`1px solid ${meta.dot}28`, fontFamily:"'Syne',sans-serif", fontSize:"9px", fontWeight:700, letterSpacing:"0.2em", textTransform:"uppercase", color:meta.dot }}>
                        <span style={{ width:"5px", height:"5px", borderRadius:"50%", background:meta.dot, display:"inline-block", boxShadow:`0 0 6px ${meta.dot}80` }}/>
                        {meta.label}
                      </div>
                    )}
                    <div style={{
                      borderRadius:"14px",
                      ...(msg.role==="user" ? { borderBottomRightRadius:"4px" } : { borderBottomLeftRadius:"4px" }),
                      padding:"13px 18px",
                      fontFamily:"'Syne',sans-serif",
                      fontSize:"13px",
                      lineHeight:"1.78",
                      whiteSpace:"pre-wrap",
                      wordBreak:"break-word",
                      letterSpacing:"0.01em",
                      backdropFilter:"blur(8px)",
                      ...(msg.role==="user"
                        ? { background:"linear-gradient(135deg,rgba(111,159,156,0.3),rgba(87,126,137,0.38))", border:"1px solid rgba(111,159,156,0.28)", color:"#E2D8A5", boxShadow:"0 4px 20px rgba(87,126,137,0.2)" }
                        : { background:"rgba(255,255,255,0.06)", border:"1px solid rgba(255,255,255,0.1)", color:"rgba(226,216,165,0.9)", boxShadow:"0 4px 16px rgba(0,0,0,0.2)" }
                      )
                    }}>
                      {msg.content}
                    </div>
                  </div>
                </div>
              );
            })}

            {/* Typing */}
            {loading && (
              <div className="cp-msg-in" style={{ display:"flex", gap:"12px", alignItems:"flex-start" }}>
                <div style={{ width:"32px", height:"32px", borderRadius:"50%", display:"flex", alignItems:"center", justifyContent:"center", fontSize:"15px", color:"#E2D8A5", flexShrink:0, background:"linear-gradient(135deg,#6F9F9C,#577E89)", boxShadow:"0 4px 12px rgba(87,126,137,0.3)" }}>✦</div>
                <div>
                  <div style={{ padding:"14px 18px", borderRadius:"14px", borderBottomLeftRadius:"4px", display:"flex", gap:"7px", alignItems:"center", background:"rgba(255,255,255,0.06)", border:"1px solid rgba(255,255,255,0.1)", backdropFilter:"blur(8px)" }}>
                    {[0,1,2].map(d => (
                      <div key={d} style={{ width:"7px", height:"7px", borderRadius:"50%", background:"#6F9F9C", animation:`cpDot 1.25s ease-in-out ${d*0.18}s infinite` }}/>
                    ))}
                  </div>
                  <div style={{ fontFamily:"'Syne',sans-serif", fontSize:"9.5px", color:"rgba(111,159,156,0.4)", letterSpacing:"0.12em", textTransform:"uppercase", marginTop:"6px", paddingLeft:"4px" }}>Thinking…</div>
                </div>
              </div>
            )}
            <div ref={bottomRef}/>
          </div>

          {/* ── INPUT BAR ── */}
          <div style={{ padding:"16px 28px 22px", borderTop:"1px solid rgba(255,255,255,0.07)", background:"rgba(10,24,32,0.55)", backdropFilter:"blur(24px)", WebkitBackdropFilter:"blur(24px)", display:"flex", gap:"10px", alignItems:"center", flexShrink:0 }}>
            <input
              className="cp-input"
              style={{ borderRadius:"12px" }}
              placeholder="Ask about leave, tickets, assets, or policies…"
              value={input}
              onChange={e=>setInput(e.target.value)}
              onKeyDown={e=>{ if(e.key==="Enter" && !e.shiftKey) sendMessage(); }}
            />
            <button className="cp-send" onClick={()=>sendMessage()} disabled={loading} title="Send (Enter)">↗</button>
          </div>

        </div>
      </main>
    </>
  );
}