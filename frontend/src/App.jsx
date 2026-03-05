// ============================================================
// App.jsx
// ============================================================
// This is the root of our React application.
// Every other component lives inside this one.
//
// We use React Router here to handle navigation between pages.
// Think of it like a traffic controller — depending on what
// URL you're on it shows you a different page component.
//
// Our app has these routes:
// "/"          → Home page (upload screenshots)
// "/confirm"   → Confirmation page (review events)
// "/success"   → Success page (all done!)
// ============================================================

import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
// BrowserRouter — wraps our whole app and enables routing
// Routes — container that holds all our route definitions
// Route — defines a single URL path and what component to show

import Home from "./pages/Home";
// Import our Home page component

import Navbar from "./components/Navbar";
// Import our Navbar so it shows on every page

import "./App.css";
// Import our global styles

function App() {
  return (
    <Router>
      {/* Router wraps everything so routing works throughout the app */}
      <div className="app">
        <Navbar />
        {/* Navbar shows on every single page since it's outside Routes */}

        <main className="main-content">
          <Routes>
            {/* Routes looks at the current URL and renders the right page */}

            <Route path="/" element={<Home />} />
            <Route path="/confirm" element={<Home startAtStep={2} />} />
            {/* When URL is "/" show the Home page */}

          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;
// "export default" makes this component available to import elsewhere.
// index.js imports App and renders it into the browser.