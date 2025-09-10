import Chatbot from "./components/Chatbot";

function App() {
  return (
    <div className="min-h-screen bg-gray-900 flex flex-col items-center justify-center p-4">
      <h1 className="text-center p-6 text-4xl font-bold text-white">
        Chatbot 
      </h1>
      <Chatbot />
    </div>
  );
}

export default App;
