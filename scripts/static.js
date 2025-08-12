const chatDiv = document.getElementById("chat");
const sessionId = crypto.randomUUID();

function enviarPregunta() {
  const input = document.getElementById("pregunta");
  const texto = input.value;
  if (!texto.trim()) return;

  // Mostrar la pregunta
  const preguntaHtml = document.createElement("p");
  preguntaHtml.innerHTML = `<strong>🙋 Vos:</strong> ${texto}`;
  chatDiv.appendChild(preguntaHtml);

  fetch("/preguntar", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ texto: texto, sesion_id: sessionId })
  })
    .then(res => res.json())
    .then(data => {
      const respuestaHtml = document.createElement("p");
      respuestaHtml.innerHTML = `<strong>🤖 Bot:</strong> ${data.respuesta}`;
      chatDiv.appendChild(respuestaHtml);
      input.value = "";
    })
    .catch(err => {
      console.error("Error:", err);
    });
}
