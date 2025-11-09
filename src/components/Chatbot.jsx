import { useState } from "react";
import { FaMicrophone, FaStop } from "react-icons/fa";
import { motion, AnimatePresence } from "framer-motion";
import { askBackend } from "../services/api";

export default function Chatbot() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [listening, setListening] = useState(false);
  let recognition;

  // 🔊 Speak response aloud
  const speak = (text) => {
    if (!window.speechSynthesis) return;
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = "en-US";
    utterance.pitch = 1;
    utterance.rate = 1;
    window.speechSynthesis.speak(utterance);
  };

  // 💬 Send message to backend and display result
  const sendMessage = async () => {
    if (!input.trim()) return;

    const newMessages = [...messages, { role: "user", text: input }];
    setMessages(newMessages);
    setInput("");
    setLoading(true);

    let reply = "";
    let mood = "neutral"; // default mood

    try {
      const text = input.toLowerCase().trim();
      console.log("User input:", text);

      // 👋 Friendly shortcut
      if (text === "hey" || text === "hello") {
        reply = "😄 Hey there! How can I help you today?";
        mood = "joy";
      } else {
        // ✅ Use backend for emotion-aware response
        const response = await askBackend(input);

        if (typeof response === "object" && response.answer) {
          reply = response.answer;
          mood = response.mood || "neutral";
        } else {
          reply = response;
        }
      }
    } catch (error) {
      console.error("Chatbot error:", error);
      reply = "⚠️ Sorry, something went wrong.";
      mood = "error";
    }

    // ✅ Add bot reply including emotion mood
    setMessages([...newMessages, { role: "bot", text: reply, mood }]);
    setLoading(false);

    // 🔊 Speak response
    speak(reply);
  };

  // 🎙️ Start listening
  const startListening = () => {
    try {
      const SpeechRecognition =
        window.SpeechRecognition || window.webkitSpeechRecognition;
      if (!SpeechRecognition) {
        alert("Speech recognition not supported on this browser.");
        return;
      }

      recognition = new SpeechRecognition();
      recognition.lang = "en-US";
      recognition.continuous = false;
      recognition.interimResults = false;

      recognition.onstart = () => setListening(true);
      recognition.onend = () => setListening(false);
      recognition.onerror = (e) => {
        console.error("Speech recognition error:", e);
        setListening(false);
      };
      recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        setInput(transcript);
        setTimeout(() => sendMessage(), 300);
      };
      recognition.start();
    } catch (e) {
      console.error(e);
    }
  };

  // 🛑 Stop listening
  const stopListening = () => {
    if (recognition) {
      recognition.stop();
      setListening(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 40, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ duration: 0.4, ease: "easeOut" }}
      className="w-full sm:w-[95%] md:max-w-md bg-gradient-to-b from-[#1a1625] to-[#2d2540] text-white rounded-2xl shadow-2xl flex flex-col border border-purple-700/40 backdrop-blur-lg"
    >
      {/* Header */}
      <div className="p-4 bg-gradient-to-r from-purple-700 to-black rounded-t-2xl border-b border-purple-800/40 text-center">
        <h2 className="text-lg font-semibold tracking-wide flex items-center justify-center gap-2">
          🤖 AI BRO
        </h2>
      </div>

      {/* Messages */}
      <div className="flex-1 p-4 overflow-y-auto max-h-96 space-y-3 scroll-smooth scrollbar-thin scrollbar-thumb-purple-600/60 scrollbar-track-transparent">
        <AnimatePresence>
          {messages.map((m, i) => {
            // 🧠 Mood-based badge color for bot
            let moodBadge = "";
            if (m.mood) {
              switch (m.mood.toLowerCase()) {
                case "joy":
                  moodBadge = "text-yellow-400";
                  break;
                case "anger":
                  moodBadge = "text-red-400";
                  break;
                case "sadness":
                  moodBadge = "text-blue-400";
                  break;
                case "fear":
                  moodBadge = "text-purple-400";
                  break;
                case "love":
                  moodBadge = "text-pink-400";
                  break;
                default:
                  moodBadge = "text-gray-400";
              }
            }

            return (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 10, scale: 0.95 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.3 }}
                className={`flex ${
                  m.role === "user" ? "justify-end" : "justify-start"
                }`}
              >
                <div
                  className={`px-3 py-2 rounded-2xl max-w-[80%] text-sm shadow-md break-words border border-purple-800/40 ${
                    m.role === "user"
                      ? "bg-purple-600 text-white"
                      : "bg-[#2e2b3f] text-gray-200"
                  }`}
                >
                  <p>{m.text}</p>
                  {/* 🌈 Mood Tag */}
                  {m.role === "bot" && m.mood && (
                    <p className={`text-xs mt-1 ${moodBadge}`}>
                      {`(${m.mood.toUpperCase()})`}
                    </p>
                  )}
                </div>
              </motion.div>
            );
          })}
        </AnimatePresence>

        {loading && (
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="text-purple-400 text-sm"
          >
            Typing...
          </motion.p>
        )}
      </div>

      {/* Input */}
      <div className="flex flex-wrap p-3 gap-2 border-t border-purple-800/30 items-center bg-[#181322] rounded-b-2xl">
        <input
          className="flex-1 px-3 py-2 bg-[#241f36] border border-purple-700/50 text-white rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-purple-500 transition w-full sm:w-auto"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && sendMessage()}
          placeholder="Ask me anything..."
        />

        <motion.button
          whileTap={{ scale: 0.9 }}
          onClick={sendMessage}
          className="bg-purple-600 hover:bg-purple-700 px-4 py-2 rounded-lg text-sm font-medium transition text-white shadow-md"
        >
          Send
        </motion.button>

        <motion.button
          whileTap={{ scale: 0.9 }}
          onClick={listening ? stopListening : startListening}
          className={`p-3 rounded-full transition shadow-md ${
            listening
              ? "bg-red-600 animate-pulse"
              : "bg-purple-500 hover:bg-purple-600"
          }`}
        >
          {listening ? <FaStop /> : <FaMicrophone />}
        </motion.button>
      </div>
    </motion.div>
  );
}
