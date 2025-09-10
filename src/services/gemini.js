// src/services/gemini.js
import { GoogleGenerativeAI } from "@google/generative-ai";
import { collection, getDocs } from "firebase/firestore";
import { db } from "../firebase";

const genAI = new GoogleGenerativeAI(import.meta.env.VITE_GEMINI_API_KEY);

export async function askGemini(prompt) {
  try {
    // 🔥 Fetch real courses from Firestore
    const snapshot = await getDocs(collection(db, "courses"));
    const courses = snapshot.docs.map(doc => doc.data());

    // Gemini model
    const model = genAI.getGenerativeModel({ model: "gemini-1.5-flash" });

    // Add course context
    const contextPrompt = `
    You are an AI assistant for a course platform.
The user may ask about available courses. 

Here are the courses: 
${JSON.stringify(courses, null, 2)}

👉 Rules for your reply:
- Keep answers short and clear
- Use bullet points
- Mention course name, duration, and price/free
- No extra explanations
`;

    const result = await model.generateContent(contextPrompt);
    return result.response.text();
  } catch (error) {
    console.error("Gemini Error:", error);
    return "Sorry, something went wrong.";
  }
}
