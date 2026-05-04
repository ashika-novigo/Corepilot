"use client";

import { useEffect, useRef, useState } from "react";

type Message = {
  role: "user" | "assistant";
  content: string;
  agent?: string;
};

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content:
        "👋 Hi! I’m your Enterprise AI Copilot.\n\nI can help with HR policies, leave history, IT tickets, and asset request status.",
    },
  ]);

  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function sendMessage(messageText?: string) {
    const text = messageText || input;
    if (!text.trim()) return;

    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setInput("");
    setLoading(true);

    try {
      const response = await fetch("http://127.0.0.1:8000/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text }),
      });

      const data = await response.json();

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: data.reply || "No response received.",
          agent: data.agent,
        },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "⚠️ Backend connection failed. Please check FastAPI server.",
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

  return (
    <main className="min-h-screen bg-gradient-to-br from-purple-100 via-pink-100 to-white flex items-center justify-center p-6">
      <div className="w-full max-w-5xl h-[90vh] bg-white/90 backdrop-blur-xl rounded-3xl shadow-2xl border border-white flex flex-col overflow-hidden">
        {/* Header */}
        <div className="bg-gradient-to-r from-purple-700 via-fuchsia-600 to-pink-500 text-white px-8 py-6">
          <h1 className="text-2xl font-bold">Enterprise AI Copilot</h1>
          <p className="text-sm text-purple-100 mt-1">
            HR • IT • RAG • Multi-Agent Assistant
          </p>
        </div>

        {/* Quick Actions */}
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

        {/* Chat Area */}
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
  <div className="mb-2 text-xs font-semibold text-purple-500">
    {msg.agent?.toUpperCase() || "AI"}
  </div>
)}

{msg.content}
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

        {/* Input */}
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