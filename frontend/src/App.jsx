// src/App.jsx
import { useEffect, useRef, useState } from "react";
import { v4 as uuidv4 } from "uuid";

import "@chatscope/chat-ui-kit-styles/dist/default/styles.min.css";
import {
  MainContainer,
  ChatContainer,
  MessageList,
  Message,
  MessageInput,
  TypingIndicator,
  Avatar,
} from "@chatscope/chat-ui-kit-react";

import "./App.css";

// 👇 Usamos siempre la misma var para el backend
const API_BASE = import.meta.env.VITE_API_BASE; // p.ej. https://iam-ai-bot-meli.fly.dev

const BOT_AVATAR =
  "https://img.icons8.com/ios-filled/50/robot-2.png";
const USER_AVATAR =
  "https://img.icons8.com/fluency/48/user-male-circle.png";

const nowISO = () => new Date().toISOString();

const INITIAL_GREETING = {
  id: uuidv4(),
  message: "¡Hola! Soy el Bot IAM Meli. ¿En qué puedo ayudarte?",
  sender: "bot",
  createdAt: nowISO(),
};

export default function App() {
  // Mensajes + estado de escritura
  const [messages, setMessages] = useState([INITIAL_GREETING]);
  const [typing, setTyping] = useState(false);
  const [error, setError] = useState("");
  const [sessionId, setSessionId] = useState("");
  const listRef = useRef(null);

  // session_id para la memoria del backend
  useEffect(() => {
    const existing = sessionStorage.getItem("session_id");
    const id = existing || uuidv4();
    if (!existing) sessionStorage.setItem("session_id", id);
    setSessionId(id);

    // limpiamos historial viejo del navegador (si lo hubiese)
    sessionStorage.removeItem("chat_history");
  }, []);

  // autoscroll
  useEffect(() => {
    listRef.current?.scrollToBottom?.("auto");
  }, [messages]);

  const handleSend = async (text) => {
    setError("");
    const clean = (text ?? "").trim();
    if (!clean) return;

    const userMsg = {
      id: uuidv4(),
      message: clean,
      sender: "user",
      createdAt: nowISO(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setTyping(true);

    try {
      const res = await fetch(`${API_BASE}/preguntar`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ texto: clean, sesion_id: sessionId }),
      });

      if (!res.ok) {
        const bodyText = await res.text();
        throw new Error(`HTTP ${res.status}: ${bodyText.slice(0, 200)}`);
      }

      const data = await res.json();
      const botText = data?.respuesta ?? "No pude generar una respuesta.";

      setMessages((prev) => [
        ...prev,
        {
          id: uuidv4(),
          message: botText,
          sender: "bot",
          createdAt: nowISO(),
        },
      ]);
    } catch (e) {
      console.error(e);
      setError(
        "No pude contactar al servidor. Verificá que el backend esté disponible."
      );
      setMessages((prev) => [
        ...prev,
        {
          id: uuidv4(),
          message: "⚠️ Error al contactar al bot.",
          sender: "bot",
          createdAt: nowISO(),
        },
      ]);
    } finally {
      setTyping(false);
    }
  };

  return (
    <div className="app-root">
      <header className="app-header">
        <div className="brand">
          <span className="logo">IAM</span>
          Bot IAM Meli
        </div>
        {sessionId && (
          <div className="session-pill">Sesión: {sessionId.slice(0, 8)}…</div>
        )}
      </header>

      {/* Padre que centra todo */}
      <div className="chat-wrapper">
        <div className="chat-card">
          {error && <div className="error-banner">{error}</div>}

          <MainContainer>
            <ChatContainer>
              <MessageList
                ref={listRef}
                typingIndicator={
                  typing && (
                    <TypingIndicator content="El bot está escribiendo…" />
                  )
                }
              >
                {messages.map((m) => (
                  <Message
                    key={m.id}
                    model={{
                      message: m.message,
                      sender: m.sender === "bot" ? "Bot IAM" : "Vos",
                      direction: m.sender === "bot" ? "incoming" : "outgoing",
                    }}
                  >
                    <Avatar
                      className="avatar"
                      src={m.sender === "bot" ? BOT_AVATAR : USER_AVATAR}
                      name={m.sender === "bot" ? "Bot" : "User"}
                      size="md"
                    />
                    <Message.Footer>
                      {new Date(m.createdAt).toLocaleTimeString([], {
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </Message.Footer>
                  </Message>
                ))}
              </MessageList>

              <MessageInput
                placeholder="Escribí tu pregunta… (Shift+Enter para salto de línea)"
                onSend={handleSend}
                attachButton={false}
                disabled={typing}
                sendOnReturnPress={true}
                autoFocus
              />
            </ChatContainer>
          </MainContainer>
        </div>
      </div>
    </div>
  );
}
