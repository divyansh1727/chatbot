// src/services/gemini.js
import { GoogleGenerativeAI } from "@google/generative-ai";
import { collection, getDocs } from "firebase/firestore";
import { db } from "../firebase";

const genAI = new GoogleGenerativeAI(import.meta.env.VITE_GEMINI_API_KEY);

export async function askGemini(userPrompt) {
  try {
    // 🔥 Fetch real courses from Firestore
    const snapshot = await getDocs(collection(db, "courses"));
    const courses = snapshot.docs.map(doc => doc.data());

    // Gemini model
    const model = genAI.getGenerativeModel({ model: "gemini-1.5-flash" });

    // ✅ Combine website context + user question
    const contextPrompt = `
You are an AI assistant for a course platform. 
The user may ask about available courses OR general questions.

Here are the courses from the database: 
${JSON.stringify(courses, null, 2)}

👉 Rules for your reply:
- If the user asks about courses → answer using the above list (short, bullet points, course name, duration, price/free).
- If the user asks about anything else (e.g., Google, general knowledge) → answer normally using your knowledge.
- Keep answers concise and clear.

User question: "${userPrompt}"
`;

    const result = await model.generateContent(contextPrompt);
    return result.response.text();
  } catch (error) {
    console.error("Gemini Error:", error);
    return "Sorry, something went wrong.";
  }
}
