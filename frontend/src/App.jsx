// src/App.jsx
// === Componente principal del frontend (Vite + React + ChatScope) ===

import { useEffect, useRef, useState } from "react";
import { v4 as uuidv4 } from "uuid";

// Estilos y componentes del kit de UI del chat
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

// URL base del backend. Se inyecta en build con Vite (variable .env VITE_API_BASE)
const API_BASE = import.meta.env.VITE_API_BASE; // ej: https://iam-ai-bot.fly.dev

// Avatares del chat
const BOT_AVATAR = "/robot-3d-icon.png";
const USER_AVATAR = "https://img.icons8.com/fluency/48/user-male-circle.png";

// Helper para timestamp ISO (se usa en cada mensaje)
const nowISO = () => new Date().toISOString();

// Mensaje inicial que se muestra al entrar al chat
const INITIAL_GREETING = {
  id: uuidv4(),
  message: "¡Hola! Soy el Bot Security. ¿En qué puedo ayudarte?",
  sender: "bot",
  createdAt: nowISO(),
};

export default function App() {
  // Estado del chat
  const [messages, setMessages] = useState([INITIAL_GREETING]); // historial de mensajes
  const [typing, setTyping] = useState(false);                   // flag “bot escribiendo…”
  const [error, setError] = useState("");                        // errores visibles en UI
  const [sessionId, setSessionId] = useState("");                // ID de sesión (memoria backend)
  const listRef = useRef(null);                                  // para autoscroll

  // --- Botón “Resetear chat”: limpia memoria en backend ---
  // mode="wipe": borra recuerdos pero mantiene el mismo session_id
  // mode="drop": (opcional) elimina sesión y podríamos crear un session_id nuevo
  const handleResetMemoria = async (mode = "wipe") => {
    if (!sessionId) return;
    try {
      setTyping(true);
      await fetch(`${API_BASE}/reset_memoria`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ sesion_id: sessionId, mode }),
      });

      // En el front: reseteamos la vista a sólo el saludo
      setMessages([INITIAL_GREETING]);

      // Si quisieras nueva sesión cliente (DROP), descomentá:
      /*
      if (mode === "drop") {
        const newId = uuidv4();
        sessionStorage.setItem("session_id", newId);
        setSessionId(newId);
        setMessages([INITIAL_GREETING]);
      }
      */
    } catch (e) {
      console.error(e);
      setError("No pude resetear la memoria.");
    } finally {
      setTyping(false);
    }
  };

  // --- Al montar: generar/recuperar session_id y limpiar restos de historial del navegador ---
  useEffect(() => {
    const existing = sessionStorage.getItem("session_id");
    const id = existing || uuidv4();
    if (!existing) sessionStorage.setItem("session_id", id);
    setSessionId(id);

    // Si tuviste una versión vieja que guardaba historial local, se purga acá
    sessionStorage.removeItem("chat_history");
  }, []);

  // --- Autoscroll: cada vez que cambian los mensajes, hacemos scroll abajo ---
  useEffect(() => {
    listRef.current?.scrollToBottom?.("auto");
  }, [messages]);

  // --- Envío de un mensaje del usuario ---
  const handleSend = async (text) => {
    setError("");
    const clean = (text ?? "").trim();
    if (!clean) return;

    // 1) Pintar mensaje del usuario en UI
    const userMsg = {
      id: uuidv4(),
      message: clean,
      sender: "user",
      createdAt: nowISO(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setTyping(true);

    try {
      // 2) Llamar backend para obtener respuesta
      const res = await fetch(`${API_BASE}/preguntar`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ texto: clean, sesion_id: sessionId }),
      });

      if (!res.ok) {
        const bodyText = await res.text();
        throw new Error(`HTTP ${res.status}: ${bodyText.slice(0, 200)}`);
      }

      // 3) Respuesta del bot
      const data = await res.json();
      const botText = data?.respuesta ?? "No pude generar una respuesta.";

      // 4) Pintar respuesta del bot
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
      // Manejo de errores (muestra banner y un mensaje del bot con error)
      console.error(e);
      setError("No pude contactar al servidor. Verificá que el backend esté disponible.");
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

  // --- Render del chat y header ---
  return (
    <div className="app-root">
      <header className="app-header">
        <div className="brand">
          <span className="logo-circle">🤖</span>
          <span className="brand-text">BOT Security</span>
        </div>

        {/* Muestra un resumen del session_id para debug/seguimiento */}
        {sessionId && (
          <div className="session-pill">Sesión: {sessionId.slice(0, 8)}…</div>
        )}

        {/* Botón para borrar memoria en backend y limpiar el chat en la UI */}
        <button
          className="reset-btn"
          onClick={() => handleResetMemoria("wipe")}
          disabled={typing || !sessionId}
          title="Limpiar la memoria de esta sesión"
        >
          🧹 Resetear chat
        </button>
      </header>

      {/* Contenedor que centra el chat */}
      <div className="chat-wrapper">
        <div className="chat-card">
          {error && <div className="error-banner">{error}</div>}

          <MainContainer>
            <ChatContainer>
              <MessageList
                ref={listRef}
                typingIndicator={typing && <TypingIndicator content="El bot está escribiendo…" />}
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
