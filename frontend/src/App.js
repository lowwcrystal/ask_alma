// src/App.js
import AskAlma from "./AskAlma/AskAlma";

import "./index.css"; // make sure Tailwind styles are applied

function App() {
  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <AskAlma />
    </div>
  );
}

export default App;
