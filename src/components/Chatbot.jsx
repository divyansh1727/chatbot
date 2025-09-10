import { useState } from "react";
import { askGemini } from "../services/gemini";
import { FaMicrophone, FaStop } from "react-icons/fa";
import { motion, AnimatePresence } from "framer-motion";

export default function Chatbot() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [listening, setListening] = useState(false);

  let recognition;

  const speak = (text) => {
    if (!window.speechSynthesis) return;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = "en-US";
    utterance.onend = () => console.log("Speech finished.");
    window.speechSynthesis.speak(utterance);
  };

  const sendMessage = async () => {
  if (!input.trim()) return;
  
  const newMessages = [...messages, { role: "user", text: input }];
  setMessages(newMessages);
  setInput("");
  setLoading(true);

  const text = input.toLowerCase().trim();
  let reply = "";

  // ✅ Check greetings first
  if (text === "hey" || text === "hello") {
    reply = "Hello! How can I assist you today?";
  }
  // ✅ Check if user wants to see courses
  else if (text.includes("course") || text.includes("show")) {
    reply = "Here are the courses: Mastery in Python, Firebase Intro, Intro to React, Design Tools.";
  }
  // ✅ For other inputs, ask Gemini
  else {
    reply = await askGemini(input);
  }

  setMessages([...newMessages, { role: "bot", text: reply }]);
  setLoading(false);
  speak(reply);
};


  const startListening = () => {
    if (!("webkitSpeechRecognition" in window)) {
      alert("Your browser does not support Speech Recognition. Try Chrome.");
      return;
    }
    recognition = new window.webkitSpeechRecognition();
    recognition.lang = "en-US";
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.onstart = () => setListening(true);
    recognition.onend = () => setListening(false);
    recognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript;
      setInput(transcript);
      setTimeout(() => sendMessage(), 300);
    };
    recognition.start();
  };

  const stopListening = () => {
    if (recognition) {
      recognition.stop();
      setListening(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 50, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ duration: 0.4, ease: "easeOut" }}
      className="w-full max-w-md bg-[#1e1e2f] text-white rounded-2xl shadow-2xl flex flex-col border border-gray-700"
    >
      {/* Header */}
      <div className="p-4 bg-gradient-to-r from-orange-700 to-gray-800 rounded-t-2xl border-b border-gray-700">
        <h2 className="text-lg font-semibold flex items-center justify-center gap-2">
          🤖 AI Assistant
        </h2>
      </div>

      {/* Messages */}
      <div className="flex-1 p-4 overflow-y-auto max-h-96 space-y-3">
        <AnimatePresence>
          {messages.map((m, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 10, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.3 }}
              className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <span
                className={`px-3 py-2 rounded-2xl max-w-[75%] text-sm shadow-md ${
                  m.role === "user"
                    ? "bg-blue-600 text-white"
                    : "bg-gray-700 text-gray-100"
                }`}
              >
                {m.text}
              </span>
            </motion.div>
          ))}
        </AnimatePresence>

        {loading && (
          <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="text-gray-400 text-sm">
            Typing...
          </motion.p>
        )}
      </div>

      {/* Input */}
      <div className="flex p-3 border-t border-gray-700 items-center bg-[#11111b] rounded-b-2xl">
        <input
          className="flex-1 px-3 py-2 bg-transparent border border-gray-600 text-white rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && sendMessage()}
          placeholder="Ask me anything..."
        />
        <motion.button
          whileTap={{ scale: 0.9 }}
          onClick={sendMessage}
          className="ml-2 bg-orange-600 hover:bg-blue-700 px-4 py-2 rounded-lg text-sm font-medium transition"
        >
          Send
        </motion.button>

        <motion.button
          whileTap={{ scale: 0.9 }}
          onClick={listening ? stopListening : startListening}
          className={`ml-2 p-3 rounded-full transition ${
            listening ? "bg-red-600 animate-pulse" : "bg-yellow-600 hover:bg-green-700"
          }`}
        >
          {listening ? <FaStop /> : <FaMicrophone />}
        </motion.button>
      </div>
    </motion.div>
  );
}
