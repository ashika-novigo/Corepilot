"use client";

import { useEffect, useRef, useState } from "react";

type Message = {
  role: "user" | "assistant";
  content: string;
  agent?: string;
};

type User = {
  name: string;
  email: string;
  role: string;
};

export default function Home() {
  const [user, setUser] = useState<User | null>(null);
  const [email, setEmail] = useState("employee@novigo.com");
  const [password, setPassword] = useState("password123");
  const [token, setToken] = useState("");

  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content:
        "👋 Hi! I’m your  AI Corepilot.\n\nLogin to start using HR and IT workflows.",
      agent: "system",
    },
  ]);

  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [loginError, setLoginError] = useState("");

  const bottomRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function login() {
    setLoginError("");

    try {
      const response = await fetch("http://127.0.0.1:8000/login", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          email,
          password,
        }),
      });

      const data = await response.json();

      if (!data.success) {
        setLoginError(data.message || "Login failed");
        return;
      }

      setToken(data.token);
      setUser({
        name: data.name,
        email: data.email,
        role: data.role,
      });

      setMessages([
        {
          role: "assistant",
          content: `Welcome ${data.name}! You are logged in as ${data.role}.`,
          agent: "auth",
        },
      ]);
    } catch {
      setLoginError("Backend login failed. Check FastAPI server.");
    }
  }

  async function sendMessage(messageText?: string) {
    const text = messageText || input;
    if (!text.trim() || !token) return;

    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setInput("");
    setLoading(true);

    try {
      const response = await fetch("http://127.0.0.1:8000/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          message: text,
          token,
        }),
      });

      const data = await response.json();

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: data.reply || "No response received.",
          agent: data.agent || "ai",
        },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "⚠️ Backend connection failed. Please check FastAPI server.",
          agent: "system",
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  const quickActions = [
    "show my leave history",
    "show my ticket status",
    "show my asset request status",
    "what is leave policy?",
  ];

  if (!user) {
    return (
      <main className="min-h-screen bg-gradient-to-br from-purple-100 via-pink-100 to-white flex items-center justify-center p-6">
        <div className="w-full max-w-md bg-white/90 backdrop-blur-xl rounded-3xl shadow-2xl border border-white overflow-hidden">
          <div className="bg-gradient-to-r from-purple-700 via-fuchsia-600 to-pink-500 text-white px-8 py-6">
            <h1 className="text-2xl font-bold"> Corepilot</h1>
            <p className="text-sm text-purple-100 mt-1">
              Secure login for HR & IT workflows
            </p>
          </div>

          <div className="p-8 space-y-5">
            <div>
              <label className="text-sm font-medium text-gray-700">Email</label>
              <input
                className="mt-2 w-full border border-purple-200 rounded-2xl px-4 py-3 outline-none focus:ring-2 focus:ring-pink-400 text-gray-800"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="employee@novigo.com"
              />
            </div>

            <div>
              <label className="text-sm font-medium text-gray-700">
                Password
              </label>
              <input
                type="password"
                className="mt-2 w-full border border-purple-200 rounded-2xl px-4 py-3 outline-none focus:ring-2 focus:ring-pink-400 text-gray-800"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="password123"
              />
            </div>

            {loginError && (
              <div className="text-sm text-red-600 bg-red-50 border border-red-100 rounded-xl px-4 py-3">
                {loginError}
              </div>
            )}

            <button
              onClick={login}
              className="w-full px-7 py-3 rounded-2xl font-semibold text-white bg-gradient-to-r from-purple-700 to-pink-500 hover:opacity-90 transition"
            >
              Login
            </button>

            <div className="text-xs text-gray-500 bg-purple-50 border border-purple-100 rounded-xl p-4">
              Demo users:
              <br />
              employee@novigo.com / password123
              <br />
              it@novigo.com / password123
              <br />
              ashika.shridhar@novigosolutions.com / password123
            </div>
          </div>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-gradient-to-br from-purple-100 via-pink-100 to-white flex items-center justify-center p-6">
      <div className="w-full max-w-5xl h-[90vh] bg-white/90 backdrop-blur-xl rounded-3xl shadow-2xl border border-white flex flex-col overflow-hidden">
        <div className="bg-gradient-to-r from-purple-700 via-fuchsia-600 to-pink-500 text-white px-8 py-6 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">Corepilot</h1>
            <p className="text-sm text-purple-100 mt-1">
              HR • IT • RAG • Multi-Agent Assistant
            </p>
          </div>

          <div className="text-right">
            <p className="text-sm font-semibold">{user.name}</p>
            <p className="text-xs text-purple-100">
              {user.role.toUpperCase()} • {user.email}
            </p>
            <button
              onClick={() => {
                setUser(null);
                setToken("");
                setMessages([
                  {
                    role: "assistant",
                    content: "Logged out. Please login again.",
                    agent: "system",
                  },
                ]);
              }}
              className="mt-2 text-xs bg-white/20 px-3 py-1 rounded-full hover:bg-white/30"
            >
              Logout
            </button>
          </div>
        </div>

        <div className="px-6 py-4 bg-white border-b flex flex-wrap gap-3">
          {quickActions.map((action) => (
            <button
              key={action}
              onClick={() => sendMessage(action)}
              disabled={loading}
              className="px-4 py-2 rounded-full text-sm font-medium bg-purple-50 text-purple-700 border border-purple-200 hover:bg-purple-100 transition disabled:opacity-50"
            >
              {action}
            </button>
          ))}
        </div>

        <div className="flex-1 overflow-y-auto px-6 py-6 space-y-5 bg-gradient-to-b from-white to-purple-50">
          {messages.map((msg, index) => (
            <div
              key={index}
              className={`flex ${
                msg.role === "user" ? "justify-end" : "justify-start"
              }`}
            >
              <div
                className={`max-w-[75%] rounded-2xl px-5 py-4 text-sm leading-relaxed whitespace-pre-wrap shadow ${
                  msg.role === "user"
                    ? "bg-gradient-to-r from-purple-700 to-pink-500 text-white rounded-br-sm"
                    : "bg-white text-gray-800 border border-purple-100 rounded-bl-sm"
                }`}
              >
                {msg.role === "assistant" && (
                  <div className="mb-2 text-xs font-semibold px-2 py-1 rounded-full inline-block bg-purple-100 text-purple-700">
                    {(msg.agent || "AI").toUpperCase()}
                  </div>
                )}

                <div>{msg.content}</div>
              </div>
            </div>
          ))}

          {loading && (
            <div className="flex justify-start">
              <div className="bg-white border border-purple-100 shadow rounded-2xl rounded-bl-sm px-5 py-3 text-sm text-purple-600">
                ✨ Copilot is thinking...
              </div>
            </div>
          )}

          <div ref={bottomRef} />
        </div>

        <div className="bg-white border-t px-6 py-5 flex gap-3">
          <input
            className="flex-1 border border-purple-200 rounded-2xl px-5 py-3 outline-none focus:ring-2 focus:ring-pink-400 text-gray-800"
            placeholder="Ask about leave, tickets, assets, or policies..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") sendMessage();
            }}
          />

          <button
            onClick={() => sendMessage()}
            disabled={loading}
            className="px-7 py-3 rounded-2xl font-semibold text-white bg-gradient-to-r from-purple-700 to-pink-500 hover:opacity-90 transition disabled:opacity-50"
          >
            Send
          </button>
        </div>
      </div>
    </main>
  );
}