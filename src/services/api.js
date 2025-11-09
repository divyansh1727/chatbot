const BASE_URL = "http://127.0.0.1:8080";

export async function askBackend(question) {
  try {
    const res = await fetch(`${BASE_URL}/ask`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: question }),
    });
    

    const data = await res.json();
    console.log("Backend response:", data); // 👀 for debugging

    return {
      answer: data.answer || "Sorry, I couldn’t understand.",
      mood: data.mood || "neutral",
    };
  } catch (err) {
    console.error("API error:", err);
    return { text: "⚠️ Backend is not responding.", mood: "error" };
  }
}
