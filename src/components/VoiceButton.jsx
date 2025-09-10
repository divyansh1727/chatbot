import { useState } from "react";
import { askGemini } from "../services/gemini";
import { FaMicrophone, FaStop } from "react-icons/fa";

export default function Chatbot() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [listening, setListening] = useState(false);

  let recognition; // Speech recognition instance

  // ✅ Bot Speech Function (TTS)
  const speak = (text) => {
    if (!window.speechSynthesis) return;
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = "en-US";
    window.speechSynthesis.speak(utterance);
  };

  // ✅ Send message to Gemini
  const sendMessage = async () => {
    if (!input.trim()) return;
    const newMessages = [...messages, { role: "user", text: input }];
    setMessages(newMessages);
    setInput("");
    setLoading(true);

    const reply = await askGemini(input);
    setMessages([...newMessages, { role: "bot", text: reply }]);
    speak(reply); // make bot talk
    setLoading(false);
  };

  // ✅ Start Listening (STT)
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
      setTimeout(() => sendMessage(), 300); // auto-send after speech
    };

    recognition.start();
  };

  // ✅ Stop Listening
  const stopListening = () => {
    if (recognition) {
      recognition.stop();
      setListening(false);
    }
  };

  return (
    <div className="fixed bottom-6 right-6 w-80 bg-gray-900 text-white rounded-2xl shadow-lg flex flex-col">
      {/* Messages */}
      <div className="flex-1 p-3 overflow-y-auto max-h-96">
        {messages.map((m, i) => (
          <p key={i} className={m.role === "user" ? "text-right" : "text-left"}>
            <span
              className={
                m.role === "user"
                  ? "bg-blue-600 px-2 py-1 rounded-lg inline-block"
                  : "bg-gray-700 px-2 py-1 rounded-lg inline-block"
              }
            >
              {m.text}
            </span>
          </p>
        ))}
        {loading && <p className="text-gray-400">Typing...</p>}
      </div>

      {/* Input */}
      <div className="flex p-2 border-t border-gray-700 items-center">
        <input
          className="flex-1 px-2 py-1 text-black rounded"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && sendMessage()}
          placeholder="Ask me anything..."
        />
        <button
          onClick={sendMessage}
          className="ml-2 bg-blue-600 px-3 py-1 rounded"
        >
          Send
        </button>

        {/* 🎤 Mic Button */}
        <button
  onClick={listening ? stopListening : startListening}
  className={`ml-2 p-2 rounded-full text-white ${
    listening ? "bg-red-600" : "bg-green-600"
  }`}
>
  {listening ? <FaStop /> : <FaMicrophone />}
</button>

      </div>
    </div>
  );
}
