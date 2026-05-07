"use client";
import { useEffect, useRef, useState, ReactNode } from "react";

type Message  = { role:"user"|"assistant"; content:string; agent?:string; tool?:string; };
type User     = { name:string; email:string; role:string; };
type LvReq = {
  id: number;
  emp: string;
  employee_id?: number;
  type: string;
  from: string;
  to: string;
  days: number;
  reason: string;
  status: "pending" | "approved" | "rejected" | "cancelled";
};
type Ticket = {
  id: number;
  emp: string;
  title: string;
  priority: "low" | "medium" | "high" | "critical";
  status: "open" | "in-progress" | "in_progress" | "resolved" | "closed" | "rejected";
  assignee: string;
  created: string;
};
type AssetReq = {
  id: number;
  emp: string;
  asset: string;
  reason: string;
  manager_status: string;
  it_status: string;
  inventory_status: string;
  final_status: string;
  status?: string;
  created: string;
};
type InventoryItem = { id:number; item:string; total:number; available:number; reserved:number; };
type LogEntry = { id:number; time:string; agent:string; action:string; user:string; status:string; };
type DashboardSummary = Record<string, number>;
type LeaveBalanceItem = { used:number; total:number; remaining:number; };
type LeaveBalance = Record<"sick"|"casual"|"earned", LeaveBalanceItem>;
type NavItem  = { id:string; icon:string; label:string; roles:string[]; };

const NAV_ITEMS: NavItem[] = [
  { id:"overview",  icon:"⬡",  label:"Overview",      roles:["employee","manager","hr","it","admin"] },
  { id:"chat",      icon:"✦",  label:"AI Copilot",    roles:["employee","manager","hr","it","admin"] },
  { id:"leave",     icon:"📋", label:"Leave",         roles:["employee","manager","hr","admin"] },
  { id:"tickets",   icon:"🎫", label:"IT Tickets",    roles:["employee","manager","it","admin"] },
  { id:"assets",    icon:"💼", label:"Assets",        roles:["employee","manager","it","admin"] },
  { id:"approvals", icon:"✓",  label:"Approvals",     roles:["manager","hr","it","admin"] },
  { id:"analytics", icon:"◈",  label:"Analytics",     roles:["hr","admin"] },
  { id:"logs",      icon:"⌬",  label:"Logs & Traces", roles:["admin","it"] },
];

const ROLE_QUICK: Record<string, {icon:string;label:string;q:string}[]> = {
  employee: [
    { icon:"📅", label:"Apply Leave",     q:"Apply leave for tomorrow" },
    { icon:"📊", label:"Leave Balance",   q:"Show my leave balance" },
    { icon:"🔧", label:"Raise VPN Ticket",q:"Raise VPN issue ticket" },
    { icon:"💻", label:"Request Laptop",  q:"Request a laptop" },
    { icon:"📦", label:"Asset Status",    q:"Show my asset request status" },
  ],
  manager: [
    { icon:"✅", label:"Pending Approvals", q:"Show pending approvals" },
    { icon:"👥", label:"Team Leave",        q:"Show team leave requests" },
  ],
  hr: [
    { icon:"📋", label:"Leave Overview", q:"Show all leave requests" },
    { icon:"📜", label:"Leave Policy",   q:"What is the leave policy?" },
  ],
  it: [
    { icon:"🎫", label:"Open Tickets",   q:"Show all open tickets" },
    { icon:"📦", label:"Inventory",      q:"Check inventory status" },
    { icon:"✓",  label:"Resolve #1",    q:"Resolve ticket #1" },
  ],
  admin: [
    { icon:"⌬", label:"Agent Logs",   q:"Show agent activity logs" },
    { icon:"👤", label:"Employees", q:"All employees" },
  ],
};

const AGENT_META: Record<string, {label:string;dot:string;badge:string}> = {
  system:   { label:"SYSTEM",    dot:"#6F9F9C", badge:"rgba(111,159,156,0.15)" },
  auth:     { label:"AUTH",      dot:"#DEC484", badge:"rgba(222,196,132,0.15)" },
  ai:       { label:"COREPILOT", dot:"#E1A36F", badge:"rgba(225,163,111,0.15)" },
  hr:       { label:"HR AGENT",  dot:"#E2D8A5", badge:"rgba(226,216,165,0.12)" },
  it:       { label:"IT AGENT",  dot:"#6F9F9C", badge:"rgba(111,159,156,0.15)" },
  approval: { label:"APPROVAL",  dot:"#E1A36F", badge:"rgba(225,163,111,0.15)" },
  rag:      { label:"RAG",       dot:"#E2D8A5", badge:"rgba(226,216,165,0.12)" },
  router:   { label:"ROUTER",    dot:"#577E89", badge:"rgba(87,126,137,0.2)"   },
};

const CSS = `
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;600;700&family=Syne:wght@400;500;600;700&display=swap');
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0;}
html,body{height:100%;background:#0a1820;font-family:'Syne',sans-serif;overflow:hidden;}
:root{--gold:#E1A36F;--calico:#DEC484;--cream:#E2D8A5;--teal:#6F9F9C;--deep:#577E89;--ink:#0a1820;}

.cp-bg{position:fixed;inset:0;z-index:0;background:#0a1820;overflow:hidden;}
.cp-blob{position:absolute;border-radius:50%;filter:blur(100px);will-change:transform;}
.cp-blob-1{width:720px;height:720px;background:radial-gradient(circle,rgba(225,163,111,0.42) 0%,transparent 65%);top:-250px;left:-200px;animation:bFloat1 20s ease-in-out infinite;}
.cp-blob-2{width:650px;height:650px;background:radial-gradient(circle,rgba(87,126,137,0.5) 0%,transparent 65%);bottom:-200px;right:-180px;animation:bFloat2 25s ease-in-out infinite;}
.cp-blob-3{width:520px;height:520px;background:radial-gradient(circle,rgba(111,159,156,0.32) 0%,transparent 65%);top:35%;left:50%;animation:bFloat3 18s ease-in-out infinite;}
.cp-blob-4{width:420px;height:420px;background:radial-gradient(circle,rgba(222,196,132,0.25) 0%,transparent 65%);top:58%;left:8%;animation:bFloat4 22s ease-in-out infinite 2s;}
.cp-blob-5{width:380px;height:380px;background:radial-gradient(circle,rgba(225,163,111,0.2) 0%,transparent 65%);top:15%;right:12%;animation:bFloat1 16s ease-in-out infinite 4s;}
@keyframes bFloat1{0%,100%{transform:translate(0,0) scale(1)}35%{transform:translate(50px,-60px) scale(1.06)}70%{transform:translate(-30px,35px) scale(0.96)}}
@keyframes bFloat2{0%,100%{transform:translate(0,0) scale(1)}40%{transform:translate(-70px,50px) scale(1.08)}75%{transform:translate(40px,-25px) scale(0.94)}}
@keyframes bFloat3{0%,100%{transform:translate(0,0)}50%{transform:translate(-50px,70px) scale(1.1)}}
@keyframes bFloat4{0%,100%{transform:translate(0,0) scale(1)}45%{transform:translate(60px,-40px) scale(1.07)}}

.cp-grain{position:fixed;inset:0;z-index:1;pointer-events:none;opacity:0.04;
  background-image:url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
  background-size:180px;}

.cp-glass{background:rgba(255,255,255,0.05);border:1px solid rgba(255,255,255,0.1);backdrop-filter:blur(24px) saturate(160%);-webkit-backdrop-filter:blur(24px) saturate(160%);}
.cp-glass-dark{background:rgba(10,24,32,0.62);border:1px solid rgba(255,255,255,0.09);backdrop-filter:blur(36px) saturate(180%);-webkit-backdrop-filter:blur(36px) saturate(180%);}
.cp-card{background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.08);border-radius:16px;backdrop-filter:blur(20px);-webkit-backdrop-filter:blur(20px);transition:border-color .2s,box-shadow .2s;}
.cp-card:hover{border-color:rgba(111,159,156,0.25);box-shadow:0 8px 32px rgba(0,0,0,0.25);}

.cp-scroll::-webkit-scrollbar{width:3px;}
.cp-scroll::-webkit-scrollbar-track{background:transparent;}
.cp-scroll::-webkit-scrollbar-thumb{background:rgba(111,159,156,0.25);border-radius:2px;}
.cp-scroll-x{scrollbar-width:none;}
.cp-scroll-x::-webkit-scrollbar{display:none;}

@keyframes cpFadeUp{from{opacity:0;transform:translateY(20px)}to{opacity:1;transform:translateY(0)}}
@keyframes cpMsgIn{from{opacity:0;transform:translateY(8px) scale(0.98)}to{opacity:1;transform:translateY(0) scale(1)}}
@keyframes cpDot{0%,60%,100%{transform:translateY(0);opacity:0.3}30%{transform:translateY(-5px);opacity:1}}
@keyframes cpPulse{0%,100%{box-shadow:0 0 0 0 rgba(111,159,156,0.5)}50%{box-shadow:0 0 0 6px rgba(111,159,156,0)}}
@keyframes cpSlideIn{from{opacity:0;transform:translateX(-12px)}to{opacity:1;transform:translateX(0)}}
.cp-fade-up{animation:cpFadeUp 0.5s cubic-bezier(.22,1,.36,1) both;}
.cp-msg-in{animation:cpMsgIn 0.3s cubic-bezier(.22,1,.36,1) both;}
.cp-slide-in{animation:cpSlideIn 0.4s cubic-bezier(.22,1,.36,1) both;}

.cp-input{width:100%;background:rgba(255,255,255,0.05);border:1px solid rgba(255,255,255,0.1);border-radius:12px;padding:12px 16px;font-family:'Syne',sans-serif;font-size:13px;color:rgba(226,216,165,0.9);outline:none;transition:border-color .2s,background .2s,box-shadow .2s;letter-spacing:.01em;}
.cp-input::placeholder{color:rgba(111,159,156,0.38);}
.cp-input:focus{border-color:rgba(111,159,156,0.55);background:rgba(111,159,156,0.08);box-shadow:0 0 0 3px rgba(111,159,156,0.12);}

.cp-cta{background:linear-gradient(135deg,#6F9F9C 0%,#4d7a87 100%);border:none;border-radius:10px;color:#E2D8A5;font-family:'Syne',sans-serif;font-size:12px;font-weight:700;letter-spacing:.08em;cursor:pointer;transition:transform .18s,box-shadow .18s;box-shadow:0 4px 18px rgba(87,126,137,0.38),inset 0 1px 0 rgba(255,255,255,0.15);position:relative;overflow:hidden;}
.cp-cta:hover:not(:disabled){transform:translateY(-2px);box-shadow:0 8px 28px rgba(87,126,137,0.5);}
.cp-cta:disabled{opacity:.38;cursor:not-allowed;}

.cp-btn-approve{background:linear-gradient(135deg,rgba(111,159,156,0.25),rgba(87,126,137,0.3));border:1px solid rgba(111,159,156,0.35);border-radius:8px;padding:6px 14px;font-family:'Syne',sans-serif;font-size:11px;font-weight:600;color:#6F9F9C;cursor:pointer;transition:all .18s;letter-spacing:.04em;}
.cp-btn-approve:hover{background:rgba(111,159,156,0.3);border-color:#6F9F9C;color:#E2D8A5;transform:translateY(-1px);}
.cp-btn-reject{background:rgba(192,82,74,0.12);border:1px solid rgba(192,82,74,0.25);border-radius:8px;padding:6px 14px;font-family:'Syne',sans-serif;font-size:11px;font-weight:600;color:#f28a80;cursor:pointer;transition:all .18s;letter-spacing:.04em;}
.cp-btn-reject:hover{background:rgba(192,82,74,0.22);border-color:rgba(192,82,74,0.5);transform:translateY(-1px);}

.cp-pill{display:inline-flex;align-items:center;gap:6px;padding:6px 13px;border-radius:100px;background:rgba(255,255,255,0.05);border:1px solid rgba(255,255,255,0.1);cursor:pointer;white-space:nowrap;font-family:'Syne',sans-serif;font-size:11px;font-weight:500;color:rgba(226,216,165,0.6);letter-spacing:.02em;transition:all .18s;flex-shrink:0;}
.cp-pill:hover:not(:disabled){background:rgba(111,159,156,0.13);border-color:rgba(111,159,156,0.35);color:#E2D8A5;transform:translateY(-1px);}
.cp-pill:disabled{opacity:.3;cursor:not-allowed;}

.cp-send{width:44px;height:44px;border-radius:11px;border:none;flex-shrink:0;background:linear-gradient(135deg,#6F9F9C,#4d7a87);color:#E2D8A5;font-size:19px;display:flex;align-items:center;justify-content:center;cursor:pointer;transition:all .18s;box-shadow:0 4px 16px rgba(87,126,137,0.35);}
.cp-send:hover:not(:disabled){transform:scale(1.08) rotate(-8deg);box-shadow:0 6px 22px rgba(87,126,137,0.5);}
.cp-send:disabled{opacity:.35;cursor:not-allowed;}

.cp-logout{font-family:'Syne',sans-serif;font-size:10.5px;font-weight:600;letter-spacing:.1em;text-transform:uppercase;background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.1);border-radius:8px;padding:6px 13px;color:rgba(226,216,165,0.5);cursor:pointer;transition:all .18s;}
.cp-logout:hover{background:rgba(225,163,111,0.13);border-color:rgba(225,163,111,0.28);color:var(--cream);}
.cp-label{font-family:'Syne',sans-serif;font-size:10px;font-weight:700;letter-spacing:.16em;text-transform:uppercase;color:rgba(111,159,156,0.7);}
.cp-online-dot{width:7px;height:7px;border-radius:50%;background:#6F9F9C;animation:cpPulse 2s ease-in-out infinite;flex-shrink:0;}

.cp-sidebar{width:220px;flex-shrink:0;display:flex;flex-direction:column;background:rgba(10,24,32,0.7);border-right:1px solid rgba(255,255,255,0.07);backdrop-filter:blur(32px);-webkit-backdrop-filter:blur(32px);}
.cp-nav-item{display:flex;align-items:center;gap:10px;padding:10px 18px;cursor:pointer;border-radius:10px;margin:1px 10px;font-family:'Syne',sans-serif;font-size:12.5px;font-weight:500;color:rgba(226,216,165,0.45);letter-spacing:.02em;transition:all .18s;border:1px solid transparent;}
.cp-nav-item:hover{background:rgba(255,255,255,0.05);color:rgba(226,216,165,0.8);}
.cp-nav-item.active{background:rgba(111,159,156,0.13);border-color:rgba(111,159,156,0.2);color:#E2D8A5;}
.cp-nav-icon{font-size:15px;width:20px;text-align:center;flex-shrink:0;}

.cp-topbar{display:flex;align-items:center;justify-content:space-between;padding:0 24px;height:62px;background:rgba(10,24,32,0.65);border-bottom:1px solid rgba(255,255,255,0.07);flex-shrink:0;backdrop-filter:blur(24px);-webkit-backdrop-filter:blur(24px);box-shadow:0 1px 0 rgba(255,255,255,0.05),0 4px 28px rgba(0,0,0,0.2);}

.cp-stat-card{border-radius:16px;padding:20px;display:flex;flex-direction:column;gap:8px;background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.08);backdrop-filter:blur(20px);transition:all .2s;}
.cp-stat-card:hover{border-color:rgba(111,159,156,0.22);transform:translateY(-2px);box-shadow:0 8px 32px rgba(0,0,0,0.2);}

.cp-table{width:100%;border-collapse:collapse;}
.cp-table th{font-family:'Syne',sans-serif;font-size:9.5px;font-weight:700;letter-spacing:.18em;text-transform:uppercase;color:rgba(111,159,156,0.6);padding:10px 14px;text-align:left;border-bottom:1px solid rgba(255,255,255,0.06);}
.cp-table td{font-family:'Syne',sans-serif;font-size:12px;color:rgba(226,216,165,0.8);padding:11px 14px;border-bottom:1px solid rgba(255,255,255,0.04);}
.cp-table tr:last-child td{border-bottom:none;}
.cp-table tr:hover td{background:rgba(255,255,255,0.03);}

.cp-status-pending{background:rgba(222,196,132,0.15);border:1px solid rgba(222,196,132,0.3);color:#DEC484;border-radius:100px;padding:3px 10px;font-size:10px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;white-space:nowrap;}
.cp-status-approved{background:rgba(111,159,156,0.15);border:1px solid rgba(111,159,156,0.3);color:#6F9F9C;border-radius:100px;padding:3px 10px;font-size:10px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;white-space:nowrap;}
.cp-status-rejected{background:rgba(192,82,74,0.12);border:1px solid rgba(192,82,74,0.25);color:#f28a80;border-radius:100px;padding:3px 10px;font-size:10px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;white-space:nowrap;}
.cp-status-open{background:rgba(225,163,111,0.15);border:1px solid rgba(225,163,111,0.3);color:#E1A36F;border-radius:100px;padding:3px 10px;font-size:10px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;white-space:nowrap;}
.cp-status-in-progress{background:rgba(87,126,137,0.2);border:1px solid rgba(87,126,137,0.35);color:#8ab8c2;border-radius:100px;padding:3px 10px;font-size:10px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;white-space:nowrap;}
.cp-status-resolved{background:rgba(111,159,156,0.15);border:1px solid rgba(111,159,156,0.3);color:#6F9F9C;border-radius:100px;padding:3px 10px;font-size:10px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;white-space:nowrap;}

.cp-priority-critical{color:#f28a80;font-weight:700;}
.cp-priority-high{color:#E1A36F;font-weight:600;}
.cp-priority-medium{color:#DEC484;font-weight:500;}
.cp-priority-low{color:rgba(226,216,165,0.5);}

.cp-section-title{font-family:'Playfair Display',serif;font-size:20px;font-weight:600;color:#E2D8A5;letter-spacing:-.01em;}
.cp-section-sub{font-family:'Syne',sans-serif;font-size:11px;color:rgba(111,159,156,0.6);letter-spacing:.05em;margin-top:3px;}

.cp-agent-route{display:flex;align-items:center;gap:6px;padding:6px 12px;background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.08);border-radius:100px;font-family:'Syne',sans-serif;font-size:9.5px;font-weight:600;letter-spacing:.12em;text-transform:uppercase;color:rgba(111,159,156,0.65);}

.cp-pipeline{display:flex;align-items:center;gap:4px;font-family:'Syne',sans-serif;font-size:9.5px;font-weight:600;letter-spacing:.06em;}
.cp-pipe-step{padding:2px 8px;border-radius:100px;white-space:nowrap;}
.cp-pipe-approved{background:rgba(111,159,156,0.2);color:#6F9F9C;border:1px solid rgba(111,159,156,0.3);}
.cp-pipe-pending{background:rgba(222,196,132,0.15);color:#DEC484;border:1px solid rgba(222,196,132,0.25);}
.cp-pipe-rejected{background:rgba(192,82,74,0.12);color:#f28a80;border:1px solid rgba(192,82,74,0.2);}
.cp-pipe-arrow{color:rgba(111,159,156,0.3);font-size:10px;}
`;

// ─────────────────────────────────────────────────────────────────
// SMALL REUSABLE COMPONENTS
// ─────────────────────────────────────────────────────────────────

function Bg() {
  return (
    <>
      <div className="cp-bg">
        <div className="cp-blob cp-blob-1"/><div className="cp-blob cp-blob-2"/>
        <div className="cp-blob cp-blob-3"/><div className="cp-blob cp-blob-4"/>
        <div className="cp-blob cp-blob-5"/>
      </div>
      <div className="cp-grain"/>
    </>
  );
}

function StatusBadge({ status }: { status: string }) {
  const cls: Record<string,string> = {
    pending:     "cp-status-pending",
    approved:    "cp-status-approved",
    rejected:    "cp-status-rejected",
    open:        "cp-status-open",
    "in-progress": "cp-status-in-progress",
    in_progress: "cp-status-in-progress",
    resolved:    "cp-status-resolved",
    closed:      "cp-status-resolved",
    cancelled:   "cp-status-rejected",
  };
  return <span className={cls[status] || "cp-status-pending"}>{status.replace(/[-_]/g, " ")}</span>;
}

function PriorityBadge({ p }: { p: string }) {
  const cls: Record<string,string> = { critical:"cp-priority-critical", high:"cp-priority-high", medium:"cp-priority-medium", low:"cp-priority-low" };
  return <span className={cls[p] || ""}>{p}</span>;
}

// Shows the 3-stage approval pipeline for assets: Manager → IT → Inventory
function AssetPipeline({ a }: { a: AssetReq }) {
  function cls(s: string) {
    if (!s || s === "—") return "cp-pipe-pending";
    const sl = s.toLowerCase();
    if (sl === "approved" || sl === "fulfilled") return "cp-pipe-approved";
    if (sl.includes("reject")) return "cp-pipe-rejected";
    return "cp-pipe-pending";
  }
  return (
    <div className="cp-pipeline">
      <span className={`cp-pipe-step ${cls(a.manager_status)}`}>Mgr</span>
      <span className="cp-pipe-arrow">→</span>
      <span className={`cp-pipe-step ${cls(a.it_status)}`}>IT</span>
      <span className="cp-pipe-arrow">→</span>
      <span className={`cp-pipe-step ${cls(a.inventory_status)}`}>Inv</span>
    </div>
  );
}

function AgentBadge({ agent }: { agent: string }) {
  const m = AGENT_META[agent] || AGENT_META.ai;
  return (
    <div style={{ display:"inline-flex", alignItems:"center", gap:"5px", padding:"2px 9px", borderRadius:"100px", background:m.badge, border:`1px solid ${m.dot}28`, fontFamily:"'Syne',sans-serif", fontSize:"8.5px", fontWeight:700, letterSpacing:"0.2em", textTransform:"uppercase", color:m.dot }}>
      <span style={{ width:"4px", height:"4px", borderRadius:"50%", background:m.dot, display:"inline-block", boxShadow:`0 0 5px ${m.dot}80` }}/>
      {m.label}
    </div>
  );
}

function StatCard({ icon, label, value, sub, color }: { icon:string; label:string; value:string|number; sub?:string; color?:string }) {
  return (
    <div className="cp-stat-card">
      <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between" }}>
        <span style={{ fontSize:"11px", fontFamily:"'Syne',sans-serif", fontWeight:600, letterSpacing:"0.12em", textTransform:"uppercase", color:"rgba(111,159,156,0.6)" }}>{label}</span>
        <span style={{ fontSize:"20px", opacity:0.7 }}>{icon}</span>
      </div>
      <div style={{ fontFamily:"'Playfair Display',serif", fontSize:"32px", fontWeight:700, color: color || "#E2D8A5", lineHeight:1, letterSpacing:"-0.02em" }}>{value}</div>
      {sub && <div style={{ fontFamily:"'Syne',sans-serif", fontSize:"11px", color:"rgba(111,159,156,0.55)", letterSpacing:"0.03em" }}>{sub}</div>}
    </div>
  );
}

function SectionHeader({ title, sub }: { title:string; sub?:string }) {
  return (
    <div style={{ marginBottom:"20px" }}>
      <div className="cp-section-title">{title}</div>
      {sub && <div className="cp-section-sub">{sub}</div>}
    </div>
  );
}

function TableWrap({ children }: { children:ReactNode }) {
  return (
    <div style={{ background:"rgba(255,255,255,0.03)", border:"1px solid rgba(255,255,255,0.07)", borderRadius:"14px", overflow:"hidden" }}>
      <div className="cp-scroll" style={{ overflowX:"auto" }}>
        <table className="cp-table">{children}</table>
      </div>
    </div>
  );
}

function LogItem({ entry }: { entry: LogEntry }) {
  const dotColor = entry.status === "success" ? "#6F9F9C" : entry.status === "error" ? "#f28a80" : "#DEC484";
  return (
    <div style={{ display:"flex", alignItems:"flex-start", gap:"12px", padding:"10px 0", borderBottom:"1px solid rgba(255,255,255,0.04)" }}>
      <div style={{ width:"6px", height:"6px", borderRadius:"50%", background:dotColor, marginTop:"5px", flexShrink:0, boxShadow:`0 0 6px ${dotColor}80` }}/>
      <div style={{ flex:1 }}>
        <div style={{ display:"flex", alignItems:"center", gap:"10px", flexWrap:"wrap" }}>
          <span style={{ fontFamily:"'Syne',sans-serif", fontSize:"11px", fontWeight:600, color:"rgba(226,216,165,0.9)" }}>{entry.action.replace(/_/g," ")}</span>
          <AgentBadge agent={entry.agent.toLowerCase().split(" ")[0]} />
        </div>
        <div style={{ fontFamily:"'Syne',sans-serif", fontSize:"10.5px", color:"rgba(111,159,156,0.55)", marginTop:"2px" }}>
          {entry.user} · {entry.time}
        </div>
      </div>
    </div>
  );
}

function AgentRouteBar() {
  const routes = ["Router","HR Agent","IT Agent","RAG"];
  return (
    <div style={{ display:"flex", alignItems:"center", gap:"6px", flexWrap:"wrap", marginBottom:"12px" }}>
      {routes.map((r,i) => (
        <div key={r} style={{ display:"flex", alignItems:"center", gap:"5px" }}>
          <div className="cp-agent-route">{r}</div>
          {i < routes.length-1 && <span style={{ color:"rgba(111,159,156,0.3)", fontSize:"12px" }}>→</span>}
        </div>
      ))}
    </div>
  );
}

function leaveUsageRows(leave: LvReq[], balance?: LeaveBalance|null) {
  if (balance) {
    return (["sick","casual","earned"] as const).map((type, i) => ({
      label: type.charAt(0).toUpperCase() + type.slice(1),
      used: balance[type].used,
      total: balance[type].total,
      remaining: balance[type].remaining,
      color: ["#6F9F9C", "#DEC484", "#E1A36F"][i],
    }));
  }

  const approved = leave.filter(l => l.status === "approved");
  return ["sick","casual","earned"].map((type, i) => ({
    label: type.charAt(0).toUpperCase() + type.slice(1),
    used: approved.filter(l => l.type?.toLowerCase() === type).reduce((sum, l) => sum + (l.days || 0), 0),
    total: 0,
    remaining: 0,
    color: ["#6F9F9C", "#DEC484", "#E1A36F"][i],
  }));
}

// ─────────────────────────────────────────────────────────────────
// SECTION VIEWS
// ─────────────────────────────────────────────────────────────────

function OverviewSection({ user, leave, leaveBalance, tickets, assets, logs, summary, onChat }: {
  user:User; leave:LvReq[]; leaveBalance:LeaveBalance|null; tickets:Ticket[]; assets:AssetReq[]; logs:LogEntry[]; summary:DashboardSummary|null; onChat:(q:string)=>void;
}) {
  const role = user.role.toLowerCase();
  const pending_leave  = summary?.pending_leaves ?? leave.filter(l=>l.status==="pending").length;
  const open_tickets   = summary?.open_tickets ?? tickets.filter(t=>!["resolved","closed"].includes(t.status)).length;
  const pending_assets = summary?.pending_assets ?? assets.filter(a=>["pending","pending_it_approval"].includes(a.final_status || a.status || "")).length;
  const usageRows = leaveUsageRows(leave, leaveBalance);

  return (
    <div className="cp-slide-in">
      <SectionHeader title={`Welcome back, ${user.name.split(" ")[0]}.`} sub={`${user.role.toUpperCase()} · Novigo Solutions Enterprise Platform`} />

      <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fill,minmax(180px,1fr))", gap:"14px", marginBottom:"24px" }}>
        {(role==="employee"||role==="manager"||role==="hr"||role==="admin") && (
          <StatCard icon="📋" label="Leave Requests" value={pending_leave} sub="Pending" color="#DEC484"/>
        )}
        {(role==="employee"||role==="it"||role==="admin") && (
          <StatCard icon="🎫" label="IT Tickets" value={open_tickets} sub="Open / In-Progress" color="#E1A36F"/>
        )}
        {(role==="employee"||role==="it"||role==="admin") && (
          <StatCard icon="💼" label="Asset Requests" value={pending_assets} sub="Awaiting approval" color="#6F9F9C"/>
        )}
        {role==="admin" && (
          <StatCard icon="⌬" label="System Logs" value={summary?.logs ?? logs.length} sub="Latest traces" color="#6F9F9C"/>
        )}
        {(role==="hr"||role==="admin") && (
          <StatCard icon="👥" label="Inventory Items" value={summary?.inventory_items ?? 0} sub="Tracked" color="#DEC484"/>
        )}
      </div>

      {role === "employee" && (
        <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:"14px" }}>
          <div className="cp-card" style={{ padding:"20px" }}>
            <div style={{ fontFamily:"'Syne',sans-serif", fontSize:"10.5px", fontWeight:700, letterSpacing:"0.14em", textTransform:"uppercase", color:"rgba(111,159,156,0.6)", marginBottom:"14px" }}>Leave Balance</div>
            {usageRows.map(b => (
              <div key={b.label} style={{ marginBottom:"12px" }}>
                <div style={{ display:"flex", justifyContent:"space-between", marginBottom:"5px" }}>
                  <span style={{ fontFamily:"'Syne',sans-serif", fontSize:"11.5px", color:"rgba(226,216,165,0.8)" }}>{b.label}</span>
                  <span style={{ fontFamily:"'Syne',sans-serif", fontSize:"11.5px", color:b.color, fontWeight:600 }}>{b.remaining} left</span>
                </div>
                <div style={{ height:"5px", background:"rgba(255,255,255,0.08)", borderRadius:"100px", overflow:"hidden" }}>
                  <div style={{ height:"100%", width:`${b.total > 0 ? Math.min((b.used / b.total) * 100, 100) : 0}%`, background:b.color, borderRadius:"100px" }}/>
                </div>
              </div>
            ))}
          </div>
          <div className="cp-card" style={{ padding:"20px" }}>
            <div style={{ fontFamily:"'Syne',sans-serif", fontSize:"10.5px", fontWeight:700, letterSpacing:"0.14em", textTransform:"uppercase", color:"rgba(111,159,156,0.6)", marginBottom:"14px" }}>Quick Actions</div>
            <div style={{ display:"flex", flexDirection:"column", gap:"8px" }}>
              {["Apply leave for tomorrow","Raise a VPN issue ticket","Request a new laptop","Show my asset request status","What is the leave policy?"].map(q=>(
                <button key={q} onClick={()=>onChat(q)} style={{ textAlign:"left", background:"rgba(255,255,255,0.04)", border:"1px solid rgba(255,255,255,0.07)", borderRadius:"8px", padding:"9px 13px", fontFamily:"'Syne',sans-serif", fontSize:"11.5px", color:"rgba(226,216,165,0.7)", cursor:"pointer", transition:"all .18s" }}
                  onMouseEnter={e=>{(e.target as HTMLElement).style.background="rgba(111,159,156,0.1)";(e.target as HTMLElement).style.color="#E2D8A5";}}
                  onMouseLeave={e=>{(e.target as HTMLElement).style.background="rgba(255,255,255,0.04)";(e.target as HTMLElement).style.color="rgba(226,216,165,0.7)";}}
                >→ {q}</button>
              ))}
            </div>
          </div>
        </div>
      )}

      {(role==="manager"||role==="hr") && (
        <div className="cp-card" style={{ padding:"20px" }}>
          <div style={{ fontFamily:"'Syne',sans-serif", fontSize:"10.5px", fontWeight:700, letterSpacing:"0.14em", textTransform:"uppercase", color:"rgba(111,159,156,0.6)", marginBottom:"14px" }}>Pending Approvals Queue</div>
          {leave.filter(l=>l.status==="pending").map(l=>(
            <div key={l.id} style={{ display:"flex", alignItems:"center", justifyContent:"space-between", padding:"10px 0", borderBottom:"1px solid rgba(255,255,255,0.05)" }}>
              <div>
                <span style={{ fontFamily:"'Syne',sans-serif", fontSize:"12.5px", color:"rgba(226,216,165,0.9)", fontWeight:500 }}>{l.emp}</span>
                <span style={{ fontFamily:"'Syne',sans-serif", fontSize:"11px", color:"rgba(111,159,156,0.55)", marginLeft:"10px" }}>{l.type} · {l.days}d · {l.from}</span>
              </div>
              <div style={{ display:"flex", gap:"6px" }}>
                <button className="cp-btn-approve" onClick={()=>onChat(`confirm approve leave ${l.id}`)}>Approve</button>
                <button className="cp-btn-reject"  onClick={()=>onChat(`confirm reject leave ${l.id}`)}>Reject</button>
              </div>
            </div>
          ))}
          {leave.filter(l=>l.status==="pending").length === 0 && (
            <div style={{ fontFamily:"'Syne',sans-serif", fontSize:"12px", color:"rgba(111,159,156,0.4)", padding:"12px 0" }}>No pending approvals.</div>
          )}
        </div>
      )}

      {role==="admin" && (
        <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:"14px" }}>
          <div className="cp-card" style={{ padding:"20px" }}>
            <div style={{ fontFamily:"'Syne',sans-serif", fontSize:"10.5px", fontWeight:700, letterSpacing:"0.14em", textTransform:"uppercase", color:"rgba(111,159,156,0.6)", marginBottom:"14px" }}>Recent Agent Activity</div>
            {logs.length === 0 && <div style={{ fontFamily:"'Syne',sans-serif", fontSize:"12px", color:"rgba(111,159,156,0.4)" }}>No logs found.</div>}
            {logs.slice(0,5).map(l=><LogItem key={l.id} entry={l}/>)}
          </div>
          <div className="cp-card" style={{ padding:"20px" }}>
            <div style={{ fontFamily:"'Syne',sans-serif", fontSize:"10.5px", fontWeight:700, letterSpacing:"0.14em", textTransform:"uppercase", color:"rgba(111,159,156,0.6)", marginBottom:"14px" }}>Dashboard Summary</div>
            {Object.entries(summary || {}).map(([name,value])=>(
              <div key={name} style={{ display:"flex", alignItems:"center", justifyContent:"space-between", padding:"9px 0", borderBottom:"1px solid rgba(255,255,255,0.04)" }}>
                <span style={{ fontFamily:"'Syne',sans-serif", fontSize:"12px", color:"rgba(226,216,165,0.8)" }}>{name.replace(/_/g," ")}</span>
                <span style={{ fontFamily:"'Syne',sans-serif", fontSize:"12px", color:"#6F9F9C", fontWeight:700 }}>{value}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function LeaveSection({ user, leave, leaveBalance, onChat }: {
  user:User; leave:LvReq[]; leaveBalance:LeaveBalance|null; onChat:(q:string)=>void;
}) {
  const role = user.role.toLowerCase();
  const usageRows = leaveUsageRows(leave, leaveBalance);

  function update(id:number, status:"approved"|"rejected") {
    onChat(`confirm ${status === "approved" ? "approve" : "reject"} leave ${id}`);
  }

  return (
    <div className="cp-slide-in">
      <SectionHeader title="Leave Management" sub="HR workflows · Approval flows · Leave balance tracking" />
      {(role==="hr"||role==="manager"||role==="admin") && (
        <div style={{ marginBottom:"20px" }}>
          <div style={{ fontFamily:"'Syne',sans-serif", fontSize:"10.5px", fontWeight:700, letterSpacing:"0.14em", textTransform:"uppercase", color:"rgba(111,159,156,0.6)", marginBottom:"12px" }}>All Leave Requests</div>
          <TableWrap>
            <thead><tr><th>#</th><th>Employee</th><th>Type</th><th>From</th><th>To</th><th>Days</th><th>Reason</th><th>Status</th><th>Actions</th></tr></thead>
            <tbody>
              {leave.map(l => (
                <tr key={l.id}>
                  <td style={{ color:"rgba(111,159,156,0.6)", fontWeight:600 }}>#{l.id}</td>
                  <td style={{ fontWeight:600 }}>{l.emp}</td>
                  <td>{l.type}</td><td>{l.from}</td><td>{l.to}</td>
                  <td style={{ textAlign:"center" }}>{l.days}</td>
                  <td style={{ color:"rgba(226,216,165,0.55)", maxWidth:"160px", overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap" }}>{l.reason}</td>
                  <td><StatusBadge status={l.status}/></td>
                  <td>
                    {l.status==="pending" && (
                      <div style={{ display:"flex", gap:"6px" }}>
                        <button className="cp-btn-approve" onClick={()=>update(l.id,"approved")}>✓</button>
                        <button className="cp-btn-reject"  onClick={()=>update(l.id,"rejected")}>✕</button>
                      </div>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </TableWrap>
        </div>
      )}
      {role==="employee" && (
        <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:"14px" }}>
          <div className="cp-card" style={{ padding:"20px" }}>
            <div style={{ fontFamily:"'Syne',sans-serif", fontSize:"10.5px", fontWeight:700, letterSpacing:"0.14em", textTransform:"uppercase", color:"rgba(111,159,156,0.6)", marginBottom:"14px" }}>My Requests</div>
            {leave.length === 0 && <div style={{ fontFamily:"'Syne',sans-serif", fontSize:"12px", color:"rgba(111,159,156,0.4)" }}>No leave requests yet.</div>}
            {leave.slice(0,5).map(l => (
              <div key={l.id} style={{ padding:"10px 0", borderBottom:"1px solid rgba(255,255,255,0.05)", display:"flex", justifyContent:"space-between", alignItems:"center" }}>
                <div>
                  <div style={{ fontFamily:"'Syne',sans-serif", fontSize:"12.5px", color:"rgba(226,216,165,0.9)" }}>{l.type} · {l.days} day(s)</div>
                  <div style={{ fontFamily:"'Syne',sans-serif", fontSize:"10.5px", color:"rgba(111,159,156,0.5)", marginTop:"2px" }}>{l.from} → {l.to}</div>
                </div>
                <StatusBadge status={l.status}/>
              </div>
            ))}
            <button className="cp-cta" style={{ padding:"9px 18px", marginTop:"14px" }} onClick={()=>onChat("Apply annual leave for next week")}>+ Apply Leave</button>
          </div>
          <div className="cp-card" style={{ padding:"20px" }}>
            <div style={{ fontFamily:"'Syne',sans-serif", fontSize:"10.5px", fontWeight:700, letterSpacing:"0.14em", textTransform:"uppercase", color:"rgba(111,159,156,0.6)", marginBottom:"14px" }}>Leave Balance</div>
            {usageRows.map(b=>(
              <div key={b.label} style={{ marginBottom:"14px" }}>
                <div style={{ display:"flex", justifyContent:"space-between", marginBottom:"5px" }}>
                  <span style={{ fontFamily:"'Syne',sans-serif", fontSize:"12px", color:"rgba(226,216,165,0.8)" }}>{b.label}</span>
                  <span style={{ fontFamily:"'Syne',sans-serif", fontSize:"12px", color:b.color, fontWeight:600 }}>{b.remaining} left</span>
                </div>
                <div style={{ height:"5px", background:"rgba(255,255,255,0.08)", borderRadius:"100px" }}>
                  <div style={{ height:"100%", width:`${b.total > 0 ? Math.min((b.used / b.total) * 100, 100) : 0}%`, background:b.color, borderRadius:"100px" }}/>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function TicketsSection({ user, tickets, onChat }: {
  user:User; tickets:Ticket[]; onChat:(q:string)=>void;
}) {
  const role = user.role.toLowerCase();

  function resolve(id:number) {
    onChat(`confirm resolve ticket ${id}`);
  }

  return (
    <div className="cp-slide-in">
      <SectionHeader title="IT Tickets" sub="Issue tracking · Assignment · Resolution workflows" />
      <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fill,minmax(130px,1fr))", gap:"12px", marginBottom:"20px" }}>
        <StatCard icon="🔴" label="Critical" value={tickets.filter(t=>t.priority==="critical"&&t.status!=="resolved").length} color="#f28a80"/>
        <StatCard icon="🟠" label="High"     value={tickets.filter(t=>t.priority==="high"&&t.status!=="resolved").length}     color="#E1A36F"/>
        <StatCard icon="🟡" label="Medium"   value={tickets.filter(t=>t.priority==="medium"&&t.status!=="resolved").length}   color="#DEC484"/>
        <StatCard icon="✓"  label="Resolved" value={tickets.filter(t=>t.status==="resolved").length} color="#6F9F9C"/>
      </div>
      <TableWrap>
        <thead><tr><th>#</th><th>Employee</th><th>Issue</th><th>Priority</th><th>Status</th><th>Assignee</th><th>Created</th>{(role==="it"||role==="admin")&&<th>Actions</th>}</tr></thead>
        <tbody>
          {tickets.map(t=>(
            <tr key={t.id}>
              <td style={{ color:"rgba(111,159,156,0.6)", fontWeight:600 }}>#{t.id}</td>
              <td style={{ fontWeight:500 }}>{t.emp}</td>
              <td style={{ maxWidth:"200px", overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap" }}>{t.title}</td>
              <td><PriorityBadge p={t.priority}/></td>
              <td><StatusBadge status={t.status}/></td>
              <td style={{ color:"rgba(111,159,156,0.65)" }}>{t.assignee}</td>
              <td style={{ color:"rgba(226,216,165,0.4)", fontSize:"11px" }}>{t.created}</td>
              {(role==="it"||role==="admin") && (
                <td>
                  {t.status!=="resolved" && <button className="cp-btn-approve" onClick={()=>resolve(t.id)}>Resolve</button>}
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </TableWrap>
    </div>
  );
}

function AssetsSection({ user, assets, inventory, onChat }: {
  user:User; assets:AssetReq[]; inventory:InventoryItem[]; onChat:(q:string)=>void;
}) {
  const role = user.role.toLowerCase();

  function update(id:number, s:"approved"|"rejected") {
    const asset = assets.find(a => a.id === id);
    const prefix = role === "it" || (role === "admin" && asset?.manager_status === "approved" && asset?.it_status === "pending") ? "it " : "";
    onChat(`confirm ${prefix}${s==="approved"?"approve":"reject"} asset ${id}`);
  }

  const list = assets;

  return (
    <div className="cp-slide-in">
      <SectionHeader title="Asset Requests" sub="Hardware · Equipment · Procurement workflows" />
      <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:"14px", marginBottom:"20px" }}>
        {(role==="it"||role==="admin") && (
          <div className="cp-card" style={{ padding:"20px" }}>
            <div style={{ fontFamily:"'Syne',sans-serif", fontSize:"10.5px", fontWeight:700, letterSpacing:"0.14em", textTransform:"uppercase", color:"rgba(111,159,156,0.6)", marginBottom:"14px" }}>Inventory Status</div>
            {inventory.length === 0 && <div style={{ fontFamily:"'Syne',sans-serif", fontSize:"12px", color:"rgba(111,159,156,0.4)" }}>No inventory data.</div>}
            {inventory.map(i=>(
              <div key={i.id} style={{ padding:"8px 0", borderBottom:"1px solid rgba(255,255,255,0.04)" }}>
                <div style={{ display:"flex", justifyContent:"space-between", marginBottom:"4px" }}>
                  <span style={{ fontFamily:"'Syne',sans-serif", fontSize:"11.5px", color:"rgba(226,216,165,0.8)" }}>{i.item}</span>
                  <span style={{ fontFamily:"'Syne',sans-serif", fontSize:"11px", color:i.available<=2?"#f28a80":i.available<=5?"#E1A36F":"#6F9F9C", fontWeight:600 }}>{i.available} avail</span>
                </div>
                <div style={{ height:"4px", background:"rgba(255,255,255,0.08)", borderRadius:"100px" }}>
                  <div style={{ height:"100%", width:`${i.total > 0 ? (i.available/i.total)*100 : 0}%`, background:i.available<=2?"#f28a80":i.available<=5?"#E1A36F":"#6F9F9C", borderRadius:"100px" }}/>
                </div>
              </div>
            ))}
          </div>
        )}
        <div className="cp-card" style={{ padding:"20px", gridColumn:(role==="it"||role==="admin")?"":"1 / -1" }}>
          <div style={{ fontFamily:"'Syne',sans-serif", fontSize:"10.5px", fontWeight:700, letterSpacing:"0.14em", textTransform:"uppercase", color:"rgba(111,159,156,0.6)", marginBottom:"14px" }}>Asset Requests</div>
          {list.length === 0 && <div style={{ fontFamily:"'Syne',sans-serif", fontSize:"12px", color:"rgba(111,159,156,0.4)" }}>No asset requests.</div>}
          {list.map(a=>(
            <div key={a.id} style={{ padding:"11px 0", borderBottom:"1px solid rgba(255,255,255,0.05)", display:"flex", alignItems:"center", justifyContent:"space-between", gap:"12px" }}>
              <div style={{ flex:1, minWidth:0 }}>
                <div style={{ fontFamily:"'Syne',sans-serif", fontSize:"12.5px", color:"rgba(226,216,165,0.9)", fontWeight:500 }}>{a.asset}</div>
                <div style={{ fontFamily:"'Syne',sans-serif", fontSize:"10.5px", color:"rgba(111,159,156,0.5)", marginTop:"2px" }}>{a.emp} · {a.reason}</div>
                {/* Show 3-stage pipeline instead of single status */}
                <div style={{ marginTop:"5px" }}><AssetPipeline a={a}/></div>
              </div>
              <div style={{ display:"flex", alignItems:"center", gap:"8px", flexShrink:0 }}>
                {(role==="manager"||role==="it"||role==="admin")&&["pending","pending_it_approval"].includes(a.final_status || a.status || "")&&(
                  <div style={{ display:"flex", gap:"5px" }}>
                    <button className="cp-btn-approve" onClick={()=>update(a.id,"approved")}>✓</button>
                    <button className="cp-btn-reject"  onClick={()=>update(a.id,"rejected")}>✕</button>
                  </div>
                )}
              </div>
            </div>
          ))}
          {role==="employee"&&<button className="cp-cta" style={{ padding:"9px 18px", marginTop:"14px" }} onClick={()=>onChat("Request a new laptop")}>+ Request Asset</button>}
        </div>
      </div>
    </div>
  );
}

function ApprovalsSection({ user, leave, assets, tickets, onChat }: {
  user:User; leave:LvReq[]; assets:AssetReq[]; tickets:Ticket[]; onChat:(q:string)=>void;
}) {
  const role = user.role.toLowerCase();
  const pendingLeaves = leave.filter(l=>l.status==="pending");
  const managerAssets = assets.filter(a=>a.manager_status==="pending");
  const itAssets = assets.filter(a=>a.manager_status==="approved" && a.it_status==="pending");
  const approvalAssets = role === "it" ? itAssets : role === "manager" ? managerAssets : [...managerAssets, ...itAssets];
  const openTickets = tickets.filter(t=>["open","in-progress","in_progress"].includes(t.status));

  function assetCommand(a: AssetReq, status: "approved"|"rejected") {
    const prefix = role === "it" || (a.manager_status === "approved" && a.it_status === "pending") ? "it " : "";
    onChat(`confirm ${prefix}${status==="approved"?"approve":"reject"} asset ${a.id}`);
  }

  return (
    <div className="cp-slide-in">
      <SectionHeader title="Approvals" sub="Human-in-the-loop · Multi-level approval flows" />
      <div style={{ display:"flex", flexDirection:"column", gap:"20px" }}>
        <div>
          <div style={{ fontFamily:"'Syne',sans-serif", fontSize:"10.5px", fontWeight:700, letterSpacing:"0.14em", textTransform:"uppercase", color:"rgba(111,159,156,0.6)", marginBottom:"12px" }}>Leave Requests</div>
          {pendingLeaves.length === 0 && (
            <div style={{ fontFamily:"'Syne',sans-serif", fontSize:"12px", color:"rgba(111,159,156,0.4)", padding:"12px 0" }}>No pending leave approvals.</div>
          )}
          {pendingLeaves.map(l=>(
            <div key={l.id} className="cp-card" style={{ padding:"16px 20px", marginBottom:"8px", display:"flex", alignItems:"center", justifyContent:"space-between" }}>
              <div style={{ display:"flex", alignItems:"center", gap:"14px" }}>
                <div style={{ width:"36px", height:"36px", borderRadius:"9px", background:"linear-gradient(135deg,rgba(225,163,111,0.2),rgba(222,196,132,0.2))", display:"flex", alignItems:"center", justifyContent:"center", fontSize:"16px" }}>📋</div>
                <div>
                  <div style={{ fontFamily:"'Syne',sans-serif", fontSize:"13px", fontWeight:600, color:"rgba(226,216,165,0.9)" }}>{l.emp} · {l.type} Leave</div>
                  <div style={{ fontFamily:"'Syne',sans-serif", fontSize:"11px", color:"rgba(111,159,156,0.55)", marginTop:"2px" }}>{l.from} → {l.to} · {l.days} day(s) · {l.reason}</div>
                </div>
              </div>
              <div style={{ display:"flex", gap:"8px", flexShrink:0 }}>
                <button className="cp-btn-approve" onClick={()=>onChat(`confirm approve leave ${l.id}`)}>Approve</button>
                <button className="cp-btn-reject"  onClick={()=>onChat(`confirm reject leave ${l.id}`)}>Reject</button>
              </div>
            </div>
          ))}
        </div>
        <div>
          <div style={{ fontFamily:"'Syne',sans-serif", fontSize:"10.5px", fontWeight:700, letterSpacing:"0.14em", textTransform:"uppercase", color:"rgba(111,159,156,0.6)", marginBottom:"12px" }}>Asset Requests</div>
          {approvalAssets.length === 0 && (
            <div style={{ fontFamily:"'Syne',sans-serif", fontSize:"12px", color:"rgba(111,159,156,0.4)", padding:"12px 0" }}>No pending asset approvals.</div>
          )}
          {approvalAssets.map(a=>(
            <div key={a.id} className="cp-card" style={{ padding:"16px 20px", marginBottom:"8px", display:"flex", alignItems:"center", justifyContent:"space-between" }}>
              <div style={{ display:"flex", alignItems:"center", gap:"14px" }}>
                <div style={{ width:"36px", height:"36px", borderRadius:"9px", background:"linear-gradient(135deg,rgba(111,159,156,0.2),rgba(87,126,137,0.2))", display:"flex", alignItems:"center", justifyContent:"center", fontSize:"16px" }}>💼</div>
                <div>
                  <div style={{ fontFamily:"'Syne',sans-serif", fontSize:"13px", fontWeight:600, color:"rgba(226,216,165,0.9)" }}>{a.emp} · {a.asset}</div>
                  <div style={{ fontFamily:"'Syne',sans-serif", fontSize:"11px", color:"rgba(111,159,156,0.55)", marginTop:"2px" }}>{a.reason}</div>
                  <div style={{ marginTop:"5px" }}><AssetPipeline a={a}/></div>
                </div>
              </div>
              <div style={{ display:"flex", gap:"8px", flexShrink:0 }}>
                <button className="cp-btn-approve" onClick={()=>assetCommand(a,"approved")}>Approve</button>
                <button className="cp-btn-reject"  onClick={()=>assetCommand(a,"rejected")}>Reject</button>
              </div>
            </div>
          ))}
        </div>
        {(role==="it"||role==="admin") && (
          <div>
            <div style={{ fontFamily:"'Syne',sans-serif", fontSize:"10.5px", fontWeight:700, letterSpacing:"0.14em", textTransform:"uppercase", color:"rgba(111,159,156,0.6)", marginBottom:"12px" }}>Open Tickets</div>
            {openTickets.length === 0 && (
              <div style={{ fontFamily:"'Syne',sans-serif", fontSize:"12px", color:"rgba(111,159,156,0.4)", padding:"12px 0" }}>No open tickets.</div>
            )}
            {openTickets.map(t=>(
              <div key={t.id} className="cp-card" style={{ padding:"16px 20px", marginBottom:"8px", display:"flex", alignItems:"center", justifyContent:"space-between" }}>
                <div>
                  <div style={{ fontFamily:"'Syne',sans-serif", fontSize:"13px", fontWeight:600, color:"rgba(226,216,165,0.9)" }}>Ticket #{t.id} - {t.title}</div>
                  <div style={{ fontFamily:"'Syne',sans-serif", fontSize:"11px", color:"rgba(111,159,156,0.55)", marginTop:"2px" }}>{t.emp} - {t.priority} - {t.status}</div>
                </div>
                <button className="cp-btn-approve" onClick={()=>onChat(`confirm resolve ticket ${t.id}`)}>Resolve</button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function AnalyticsSection({ leave }: { leave:LvReq[] }) {
  const byType = leave.reduce((a,l)=>({...a,[l.type]:(a[l.type as keyof typeof a]||0)+1}),{} as Record<string,number>);
  const totalDays = leave.filter(l=>l.status==="approved").reduce((s,l)=>s+l.days,0);
  const approvalRate = leave.length > 0 ? Math.round((leave.filter(l=>l.status==="approved").length/leave.length)*100) : 0;
  return (
    <div className="cp-slide-in">
      <SectionHeader title="Analytics" sub="Leave trends · HR insights" />
      <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fill,minmax(160px,1fr))", gap:"12px", marginBottom:"20px" }}>
        <StatCard icon="📊" label="Total Requests" value={leave.length} color="#E2D8A5"/>
        <StatCard icon="✓"  label="Approved Days"  value={totalDays} color="#6F9F9C"/>
        <StatCard icon="⚡" label="Approval Rate"  value={`${approvalRate}%`} color="#E1A36F"/>
        <StatCard icon="⏳" label="Pending"        value={leave.filter(l=>l.status==="pending").length} color="#DEC484"/>
      </div>
      <div className="cp-card" style={{ padding:"20px" }}>
        <div style={{ fontFamily:"'Syne',sans-serif", fontSize:"10.5px", fontWeight:700, letterSpacing:"0.14em", textTransform:"uppercase", color:"rgba(111,159,156,0.6)", marginBottom:"14px" }}>Leave by Type</div>
        {Object.entries(byType).map(([type,count])=>(
          <div key={type} style={{ marginBottom:"12px" }}>
            <div style={{ display:"flex", justifyContent:"space-between", marginBottom:"5px" }}>
              <span style={{ fontFamily:"'Syne',sans-serif", fontSize:"12px", color:"rgba(226,216,165,0.8)" }}>{type}</span>
              <span style={{ fontFamily:"'Syne',sans-serif", fontSize:"11.5px", color:"#E1A36F", fontWeight:600 }}>{count}</span>
            </div>
            <div style={{ height:"5px", background:"rgba(255,255,255,0.07)", borderRadius:"100px" }}>
              <div style={{ height:"100%", width:`${leave.length > 0 ? (count/leave.length)*100 : 0}%`, background:"#E1A36F", borderRadius:"100px" }}/>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function LogsSection({ logs }: { logs: LogEntry[] }) {
  const distribution = logs.reduce((acc,l)=>({...acc,[l.agent || "unknown"]:(acc[l.agent || "unknown"]||0)+1}),{} as Record<string,number>);
  return (
    <div className="cp-slide-in">
      <SectionHeader title="Logs & Traces" sub="Agent call traces · Tool usage · Observability" />
      <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:"14px" }}>
        <div className="cp-card" style={{ padding:"20px" }}>
          <div style={{ fontFamily:"'Syne',sans-serif", fontSize:"10.5px", fontWeight:700, letterSpacing:"0.14em", textTransform:"uppercase", color:"rgba(111,159,156,0.6)", marginBottom:"14px" }}>Agent Activity Timeline</div>
          {logs.length === 0 && <div style={{ fontFamily:"'Syne',sans-serif", fontSize:"12px", color:"rgba(111,159,156,0.4)" }}>No logs found.</div>}
          {logs.map(l=><LogItem key={l.id} entry={l}/>)}
        </div>
        <div className="cp-card" style={{ padding:"20px" }}>
          <div style={{ fontFamily:"'Syne',sans-serif", fontSize:"10.5px", fontWeight:700, letterSpacing:"0.14em", textTransform:"uppercase", color:"rgba(111,159,156,0.6)", marginBottom:"14px" }}>Agent Call Distribution</div>
          {Object.entries(distribution).map(([agent,count])=>(
            <div key={agent} style={{ marginBottom:"12px" }}>
              <div style={{ display:"flex", justifyContent:"space-between", marginBottom:"5px" }}>
                <span style={{ fontFamily:"'Syne',sans-serif", fontSize:"11.5px", color:"rgba(226,216,165,0.8)" }}>{agent}</span>
                <span style={{ fontFamily:"'Syne',sans-serif", fontSize:"11px", color:"rgba(111,159,156,0.7)", fontWeight:600 }}>{count} calls</span>
              </div>
              <div style={{ height:"4px", background:"rgba(255,255,255,0.07)", borderRadius:"100px" }}>
                <div style={{ height:"100%", width:`${logs.length > 0 ? (count/logs.length)*100 : 0}%`, background:"#6F9F9C", borderRadius:"100px" }}/>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────
// MAIN COMPONENT
// ─────────────────────────────────────────────────────────────────
const API_BASE = "http://127.0.0.1:8000";

async function apiGet(path: string) {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export default function Home() {
  const [user, setUser]         = useState<User|null>(null);
  const [email, setEmail]       = useState("employee@novigo.com");
  const [password, setPassword] = useState("password123");
  const [token, setToken]       = useState("");
  const [loginError, setLoginError] = useState("");

  const [activeNav, setActiveNav] = useState("overview");

  const [messages, setMessages] = useState<Message[]>([
    { role:"assistant", content:"👋 Hi! I'm your AI Corepilot.\n\nI can help with HR, IT, approvals, policy queries, and more.\n\nHow can I assist you today?", agent:"system" },
  ]);
  const [input, setInput]   = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement|null>(null);

  // ── Backend-driven data state (no mock data)
  const [leaveData,     setLeaveData]     = useState<LvReq[]>([]);
  const [ticketData,    setTicketData]    = useState<Ticket[]>([]);
  const [assetData,     setAssetData]     = useState<AssetReq[]>([]);
  const [inventoryData, setInventoryData] = useState<InventoryItem[]>([]);
  const [logData,       setLogData]       = useState<LogEntry[]>([]);
  const [summary,       setSummary]       = useState<DashboardSummary|null>(null);
  const [leaveBalance,  setLeaveBalance]  = useState<LeaveBalance|null>(null);

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior:"smooth" }); }, [messages]);

  // ── Fetch all dashboard data from backend
  async function fetchDashboardData(email: string, role: string) {
    const qs = `email=${encodeURIComponent(email)}&role=${encodeURIComponent(role)}`;
    try {
      const [summaryRes, leaves, tickets, assets, balance] = await Promise.all([
        apiGet(`/dashboard/summary?${qs}`),
        apiGet(`/dashboard/leaves?${qs}`),
        apiGet(`/dashboard/tickets?${qs}`),
        apiGet(`/dashboard/assets?${qs}`),
        apiGet(`/dashboard/leave-balance?${qs}`),
      ]);
      setSummary(summaryRes);
      setLeaveData(leaves);
      setTicketData(tickets);
      setAssetData(assets);
      setLeaveBalance(balance);

      if (role === "it" || role === "admin") {
        setInventoryData(await apiGet(`/dashboard/inventory?${qs}`));
      } else {
        setInventoryData([]);
      }

      if (role === "admin") {
        setLogData(await apiGet(`/dashboard/logs?${qs}`));
      } else {
        setLogData([]);
      }
    } catch (e) {
      console.error("Dashboard fetch failed:", e);
    }
  }

  // ── LOGIN
  async function login() {
    setLoginError("");
    try {
      const res  = await fetch(`${API_BASE}/login`, { method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({ email, password }) });
      const data = await res.json();
      if (!data.success) { setLoginError(data.message || "Login failed"); return; }
      setToken(data.token);
      setUser({ name:data.name, email:data.email, role:data.role });
      setMessages([{ role:"assistant", content:`Welcome back, ${data.name}.\nSigned in as ${data.role}.\n\nYour enterprise dashboard is ready.`, agent:"auth" }]);
      await fetchDashboardData(data.email, data.role);
    } catch {
      setLoginError("Backend login failed. Check FastAPI server.");
    }
  }

  // ── SEND MESSAGE
  async function sendMessage(messageText?: string) {
    const text = messageText || input;
    if (!text.trim() || !token) return;
    if (activeNav !== "chat") setActiveNav("chat");
    setMessages(prev => [...prev, { role:"user", content:text }]);
    setInput(""); setLoading(true);
    try {
      const res  = await fetch(`${API_BASE}/chat`, { method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({ message:text, token }) });
      const data = await res.json();
      setMessages(prev => [...prev, { role:"assistant", content:data.reply || "No response received.", agent:data.agent || "ai", tool:data.tool }]);
      // Refresh dashboard data after chat actions that might have changed state
      if (user) await fetchDashboardData(user.email, user.role);
    } catch {
      setMessages(prev => [...prev, { role:"assistant", content:"⚠️ Backend connection failed.", agent:"system" }]);
    } finally { setLoading(false); }
  }

  function logout() {
    setUser(null); setToken("");
    setLeaveData([]); setTicketData([]); setAssetData([]); setInventoryData([]); setLogData([]); setSummary(null); setLeaveBalance(null);
    setMessages([{ role:"assistant", content:"Logged out. Please login again.", agent:"system" }]);
    setActiveNav("overview");
  }

  const initials   = user?.name.split(" ").map(n=>n[0]).join("").slice(0,2).toUpperCase() ?? "U";
  const role       = user?.role.toLowerCase() ?? "employee";
  const navItems   = NAV_ITEMS.filter(n => n.roles.includes(role));
  const quickPrompts = ROLE_QUICK[role] || ROLE_QUICK.employee;

  // ── LOGIN PAGE
  if (!user) return (
    <>
      <style>{CSS}</style>
      <Bg/>
      <main style={{ position:"relative", zIndex:2, minHeight:"100vh", display:"flex", alignItems:"center", justifyContent:"center", padding:"24px" }}>
        <div className="cp-glass-dark cp-fade-up" style={{ width:"100%", maxWidth:"430px", borderRadius:"24px", overflow:"hidden", boxShadow:"0 28px 90px rgba(0,0,0,0.55), inset 0 1px 0 rgba(255,255,255,0.1)" }}>
          <div style={{ padding:"36px 38px 28px", borderBottom:"1px solid rgba(255,255,255,0.07)", position:"relative", overflow:"hidden" }}>
            <div style={{ position:"absolute", top:-60, right:-60, width:200, height:200, borderRadius:"50%", background:"radial-gradient(circle,rgba(225,163,111,0.22),transparent 70%)", filter:"blur(24px)", pointerEvents:"none" }}/>
            <div style={{ display:"flex", alignItems:"center", gap:"12px", marginBottom:"14px" }}>
              <div style={{ width:"38px", height:"38px", borderRadius:"10px", background:"linear-gradient(135deg,#6F9F9C,#577E89)", display:"flex", alignItems:"center", justifyContent:"center", fontSize:"18px", boxShadow:"0 4px 16px rgba(87,126,137,0.45)" }}>✦</div>
              <div>
                <div style={{ fontFamily:"'Syne',sans-serif", fontSize:"9.5px", fontWeight:600, letterSpacing:"0.22em", textTransform:"uppercase", color:"rgba(111,159,156,0.65)", marginBottom:"2px" }}>Novigo Solutions</div>
                <div style={{ fontFamily:"'Playfair Display',serif", fontSize:"30px", fontWeight:700, color:"#E2D8A5", lineHeight:1, letterSpacing:"-0.02em" }}>Corepilot</div>
              </div>
            </div>
            <div style={{ fontFamily:"'Syne',sans-serif", fontSize:"12px", color:"rgba(111,159,156,0.6)", letterSpacing:"0.04em" }}>HR · IT · Multi-Agent Intelligence Platform</div>
          </div>
          <div style={{ padding:"28px 38px 36px", display:"flex", flexDirection:"column", gap:"16px" }}>
            <div style={{ display:"flex", flexDirection:"column", gap:"7px" }}>
              <label className="cp-label">Email Address</label>
              <input className="cp-input" value={email} onChange={e=>setEmail(e.target.value)} placeholder="employee@novigo.com" onKeyDown={e=>e.key==="Enter"&&login()}/>
            </div>
            <div style={{ display:"flex", flexDirection:"column", gap:"7px" }}>
              <label className="cp-label">Password</label>
              <input type="password" className="cp-input" value={password} onChange={e=>setPassword(e.target.value)} placeholder="••••••••" onKeyDown={e=>e.key==="Enter"&&login()}/>
            </div>
            {loginError && <div style={{ background:"rgba(192,82,74,0.12)", border:"1px solid rgba(192,82,74,0.25)", borderRadius:"10px", padding:"11px 15px", fontFamily:"'Syne',sans-serif", fontSize:"12.5px", color:"#f28a80" }}>{loginError}</div>}
            <button className="cp-cta" style={{ padding:"14px", width:"100%", marginTop:"4px", textTransform:"uppercase", letterSpacing:"0.12em" }} onClick={login}>Sign In →</button>
            <div style={{ background:"rgba(255,255,255,0.03)", border:"1px solid rgba(255,255,255,0.07)", borderRadius:"12px", padding:"14px 16px", fontFamily:"'Syne',sans-serif", fontSize:"11px", color:"rgba(111,159,156,0.6)", lineHeight:"1.9" }}>
              <div style={{ fontWeight:700, letterSpacing:"0.18em", textTransform:"uppercase", fontSize:"9px", color:"rgba(111,159,156,0.4)", marginBottom:"6px" }}>Demo Credentials</div>
              employee@novigo.com · manager@novigo.com<br/>hr@novigo.com · it@novigo.com · admin@novigo.com
              <br/><span style={{ color:"rgba(226,216,165,0.25)" }}>password: password123</span>
            </div>
          </div>
        </div>
      </main>
    </>
  );

  // ── DASHBOARD
  return (
    <>
      <style>{CSS}</style>
      <Bg/>
      <div style={{ position:"relative", zIndex:2, height:"100vh", display:"flex", flexDirection:"column", overflow:"hidden" }}>

        {/* TOPBAR */}
        <div className="cp-topbar">
          <div style={{ display:"flex", alignItems:"center", gap:"12px" }}>
            <div style={{ width:"32px", height:"32px", borderRadius:"8px", background:"linear-gradient(135deg,#6F9F9C,#577E89)", display:"flex", alignItems:"center", justifyContent:"center", fontSize:"15px", boxShadow:"0 4px 12px rgba(87,126,137,0.4)", flexShrink:0 }}>✦</div>
            <div>
              <div style={{ fontFamily:"'Playfair Display',serif", fontSize:"20px", fontWeight:700, color:"#E2D8A5", lineHeight:1, letterSpacing:"-0.01em" }}>Corepilot</div>
              <div style={{ fontFamily:"'Syne',sans-serif", fontSize:"9px", fontWeight:500, letterSpacing:"0.16em", textTransform:"uppercase", color:"rgba(111,159,156,0.45)", marginTop:"1px" }}>Enterprise · Multi-Agent AI Platform</div>
            </div>
          </div>
          <div style={{ display:"flex", alignItems:"center", gap:"14px" }}>
            <div style={{ display:"flex", alignItems:"center", gap:"6px" }}><div className="cp-online-dot"/><span style={{ fontFamily:"'Syne',sans-serif", fontSize:"9.5px", color:"rgba(111,159,156,0.5)", letterSpacing:"0.1em", textTransform:"uppercase" }}>Online</span></div>
            <div style={{ width:"1px", height:"24px", background:"rgba(255,255,255,0.08)" }}/>
            <div style={{ display:"flex", alignItems:"center", gap:"10px" }}>
              <div style={{ textAlign:"right" }}>
                <div style={{ fontFamily:"'Syne',sans-serif", fontSize:"12px", fontWeight:600, color:"rgba(226,216,165,0.9)" }}>{user.name}</div>
                <div style={{ fontFamily:"'Syne',sans-serif", fontSize:"9px", fontWeight:600, color:"rgba(111,159,156,0.5)", letterSpacing:"0.13em", textTransform:"uppercase" }}>{user.role}</div>
              </div>
              <div style={{ width:"34px", height:"34px", borderRadius:"50%", display:"flex", alignItems:"center", justifyContent:"center", fontFamily:"'Syne',sans-serif", fontWeight:700, fontSize:"11px", background:"linear-gradient(135deg,#E1A36F,#DEC484)", color:"#1a2a30", border:"2px solid rgba(222,196,132,0.25)", boxShadow:"0 0 16px rgba(225,163,111,0.25)", flexShrink:0 }}>{initials}</div>
            </div>
            <button className="cp-logout" onClick={logout}>Exit</button>
          </div>
        </div>

        {/* BODY */}
        <div style={{ flex:1, display:"flex", overflow:"hidden" }}>

          {/* SIDEBAR */}
          <div className="cp-sidebar">
            <div style={{ padding:"16px 10px 8px" }}>
              <div style={{ fontFamily:"'Syne',sans-serif", fontSize:"9px", fontWeight:700, letterSpacing:"0.2em", textTransform:"uppercase", color:"rgba(111,159,156,0.35)", padding:"0 10px", marginBottom:"6px" }}>Navigation</div>
              {navItems.map(n => (
                <div key={n.id} className={`cp-nav-item${activeNav===n.id?" active":""}`} onClick={()=>setActiveNav(n.id)}>
                  <span className="cp-nav-icon">{n.icon}</span>
                  {n.label}
                </div>
              ))}
            </div>
            <div style={{ flex:1 }}/>
            <div style={{ padding:"12px 16px 20px", borderTop:"1px solid rgba(255,255,255,0.06)" }}>
              <div style={{ fontFamily:"'Syne',sans-serif", fontSize:"9px", fontWeight:700, letterSpacing:"0.18em", textTransform:"uppercase", color:"rgba(111,159,156,0.35)", marginBottom:"10px" }}>Agents Active</div>
              {["HR","IT","Approval","RAG"].map(a=>(
                <div key={a} style={{ display:"flex", alignItems:"center", gap:"7px", marginBottom:"6px" }}>
                  <div style={{ width:"5px", height:"5px", borderRadius:"50%", background:"#6F9F9C", boxShadow:"0 0 5px rgba(111,159,156,0.7)", flexShrink:0 }}/>
                  <span style={{ fontFamily:"'Syne',sans-serif", fontSize:"11px", color:"rgba(111,159,156,0.55)", letterSpacing:"0.04em" }}>{a} Agent</span>
                </div>
              ))}
            </div>
          </div>

          {/* MAIN */}
          <div className="cp-scroll" style={{ flex:1, overflowY:"auto", padding:"24px 28px" }}>
            {activeNav==="overview"  && <OverviewSection  user={user} leave={leaveData} leaveBalance={leaveBalance} tickets={ticketData} assets={assetData} logs={logData} summary={summary} onChat={sendMessage}/>}
            {activeNav==="leave"     && <LeaveSection     user={user} leave={leaveData} leaveBalance={leaveBalance} onChat={sendMessage}/>}
            {activeNav==="tickets"   && <TicketsSection   user={user} tickets={ticketData} onChat={sendMessage}/>}
            {activeNav==="assets"    && <AssetsSection    user={user} assets={assetData} inventory={inventoryData} onChat={sendMessage}/>}
            {activeNav==="approvals" && <ApprovalsSection user={user} leave={leaveData} assets={assetData} tickets={ticketData} onChat={sendMessage}/>}
            {activeNav==="analytics" && <AnalyticsSection leave={leaveData}/>}
            {activeNav==="logs"      && <LogsSection logs={logData}/>}

            {/* CHAT */}
            {activeNav==="chat" && (
              <div className="cp-slide-in" style={{ height:"calc(100vh - 110px)", display:"flex", flexDirection:"column" }}>
                <div style={{ marginBottom:"14px" }}>
                  <SectionHeader title="AI Copilot" sub="Multi-agent routing · HR · IT · Approval · RAG"/>
                  <AgentRouteBar/>
                  <div className="cp-scroll-x" style={{ display:"flex", gap:"7px", overflowX:"auto", marginBottom:"4px" }}>
                    {quickPrompts.map(p=>(
                      <button key={p.q} className="cp-pill" onClick={()=>sendMessage(p.q)} disabled={loading}>
                        <span style={{ fontSize:"12px" }}>{p.icon}</span>{p.label}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="cp-scroll" style={{ flex:1, overflowY:"auto", display:"flex", flexDirection:"column", gap:"20px", padding:"4px 2px" }}>
                  {messages.map((msg, i) => {
                    return (
                      <div key={i} className="cp-msg-in" style={{ display:"flex", gap:"11px", flexDirection:msg.role==="user"?"row-reverse":"row", animationDelay:`${Math.min(i*0.03,0.2)}s` }}>
                        <div style={{ width:"30px", height:"30px", borderRadius:"50%", flexShrink:0, display:"flex", alignItems:"center", justifyContent:"center", fontFamily:"'Syne',sans-serif", fontWeight:700, fontSize:"10.5px", marginTop:"4px", background:msg.role==="user"?"linear-gradient(135deg,#E1A36F,#DEC484)":"linear-gradient(135deg,#6F9F9C,#577E89)", color:msg.role==="user"?"#1a2a30":"#E2D8A5", boxShadow:msg.role==="user"?"0 3px 10px rgba(225,163,111,0.3)":"0 3px 10px rgba(87,126,137,0.3)" }}>
                          {msg.role==="user" ? initials : "✦"}
                        </div>
                        <div style={{ display:"flex", flexDirection:"column", gap:"5px", maxWidth:"68%", alignItems:msg.role==="user"?"flex-end":"flex-start" }}>
                          {msg.role==="assistant" && <AgentBadge agent={msg.agent||"ai"}/>}
                          <div style={{ borderRadius:"13px", ...(msg.role==="user"?{borderBottomRightRadius:"3px"}:{borderBottomLeftRadius:"3px"}), padding:"12px 16px", fontFamily:"'Syne',sans-serif", fontSize:"12.5px", lineHeight:"1.78", whiteSpace:"pre-wrap", wordBreak:"break-word", backdropFilter:"blur(8px)", ...(msg.role==="user"?{background:"linear-gradient(135deg,rgba(111,159,156,0.28),rgba(87,126,137,0.36))",border:"1px solid rgba(111,159,156,0.26)",color:"#E2D8A5"}:{background:"rgba(255,255,255,0.05)",border:"1px solid rgba(255,255,255,0.09)",color:"rgba(226,216,165,0.9)"}) }}>
                            {msg.content}
                          </div>
                          {msg.tool && msg.role==="assistant" && (
                            <div style={{ display:"inline-flex", alignItems:"center", gap:"5px", padding:"2px 9px", borderRadius:"100px", background:"rgba(87,126,137,0.15)", border:"1px solid rgba(87,126,137,0.25)", fontFamily:"'Syne',sans-serif", fontSize:"9px", fontWeight:600, letterSpacing:"0.15em", textTransform:"uppercase", color:"rgba(111,159,156,0.65)" }}>
                              ⚙ Tool: {msg.tool}
                            </div>
                          )}
                        </div>
                      </div>
                    );
                  })}
                  {loading && (
                    <div className="cp-msg-in" style={{ display:"flex", gap:"11px" }}>
                      <div style={{ width:"30px", height:"30px", borderRadius:"50%", display:"flex", alignItems:"center", justifyContent:"center", background:"linear-gradient(135deg,#6F9F9C,#577E89)", flexShrink:0 }}>✦</div>
                      <div>
                        <div style={{ padding:"13px 16px", borderRadius:"13px", borderBottomLeftRadius:"3px", display:"flex", gap:"6px", alignItems:"center", background:"rgba(255,255,255,0.05)", border:"1px solid rgba(255,255,255,0.09)" }}>
                          {[0,1,2].map(d=><div key={d} style={{ width:"6px", height:"6px", borderRadius:"50%", background:"#6F9F9C", animation:`cpDot 1.25s ease-in-out ${d*0.18}s infinite` }}/>)}
                        </div>
                        <div style={{ fontFamily:"'Syne',sans-serif", fontSize:"9px", color:"rgba(111,159,156,0.4)", letterSpacing:"0.12em", textTransform:"uppercase", marginTop:"5px", paddingLeft:"3px" }}>Routing to agent…</div>
                      </div>
                    </div>
                  )}
                  <div ref={bottomRef}/>
                </div>

                <div style={{ paddingTop:"14px", borderTop:"1px solid rgba(255,255,255,0.07)", marginTop:"12px", display:"flex", gap:"9px", alignItems:"center" }}>
                  <input className="cp-input" style={{ borderRadius:"11px" }} placeholder="Ask Corepilot anything — leave, tickets, assets, policies…" value={input} onChange={e=>setInput(e.target.value)} onKeyDown={e=>{ if(e.key==="Enter"&&!e.shiftKey) sendMessage(); }}/>
                  <button className="cp-send" onClick={()=>sendMessage()} disabled={loading} title="Send">↗</button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  );
}




