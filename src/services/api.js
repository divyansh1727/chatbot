// src/services/api.js
export async function askBackend(question) {
  try {
    const res = await fetch("http://localhost:8000/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: question }),
    });
    const data = await res.json();
    return data.answer || "Sorry, I couldn’t understand.";
  } catch (err) {
    console.error("API error:", err);
    return "⚠️ Backend is not responding.";
  }
}
