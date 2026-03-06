// ============================================================
// Home.jsx
// ============================================================
// This is the main page of our app.
// It controls which "step" the user is on and shows the
// right component for each step.
//
// Think of it like a wizard with 3 steps:
// Step 1: Upload screenshots
// Step 2: Review and confirm events
// Step 3: Success screen
//
// We use React "state" to track which step we're on.
// State is just a variable that when it changes, React
// automatically re-renders the page to reflect the change.
// ============================================================

import { useState } from "react";
// useState is React's way of storing data that can change.
// When state changes React automatically updates the screen.

import Upload from "../components/Upload";
import Confirmation from "../components/Confirmation";
import Success from "../components/Success";
// Import all three step components

import "./Home.css";

function Home({ startAtStep }) {
  const [step, setStep] = useState(() => {
    // Restore step from localStorage so we don't lose progress
    // when the app reloads (e.g., after OAuth redirect).
    const saved = window.localStorage.getItem("snapshot_step");
    return saved ? Number(saved) : startAtStep || 1;
  });
  // "step" tracks which step we're on (1, 2, or 3)

  const [events, setEvents] = useState(() => {
    // Restore events from localStorage so we don't lose them after a reload.
    const saved = window.localStorage.getItem("snapshot_events");
    if (saved) {
      try {
        return JSON.parse(saved);
      } catch {
        return [];
      }
    }
    return [];
  });
  // "events" stores the list of events the AI found
  // starts as empty array, gets filled after upload

  const handleUploadComplete = (extractedEvents) => {
    // --------------------------------------------------------
    // This function gets called by Upload.jsx when the AI
    // finishes reading the screenshots and returns events.
    // We save the events and move to step 2.
    // --------------------------------------------------------
    setEvents(extractedEvents);
    window.localStorage.setItem("snapshot_events", JSON.stringify(extractedEvents));

    setStep(2);
    window.localStorage.setItem("snapshot_step", "2");
  };

  const handleConfirmComplete = () => {
    // --------------------------------------------------------
    // This function gets called by Confirmation.jsx when
    // the user confirms and events are added to Google Calendar.
    // We move to the success screen.
    // --------------------------------------------------------
    setStep(3);
    window.localStorage.setItem("snapshot_step", "3");
    // Cleanup events once we're done (so the user can start fresh later).
    window.localStorage.removeItem("snapshot_events");
  };

  const handleStartOver = () => {
    // --------------------------------------------------------
    // Reset everything back to step 1 so the user can
    // upload new screenshots.
    // --------------------------------------------------------
    setEvents([]);
    setStep(1);
    window.localStorage.removeItem("snapshot_events");
    window.localStorage.setItem("snapshot_step", "1");
  };

  return (
    <div className="home">

      {/* Step indicator at the top showing progress */}
      <div className="steps-indicator">
        <div className={`step ${step >= 1 ? "active" : ""}`}>
          <div className="step-number">1</div>
          <span>Upload</span>
        </div>
        {/* The className changes based on which step we're on.
            "active" adds the purple highlight style. */}

        <div className="step-line" />
        {/* The line connecting the steps */}

        <div className={`step ${step >= 2 ? "active" : ""}`}>
          <div className="step-number">2</div>
          <span>Review</span>
        </div>

        <div className="step-line" />

        <div className={`step ${step >= 3 ? "active" : ""}`}>
          <div className="step-number">3</div>
          <span>Done</span>
        </div>
      </div>

      {/* Show the right component based on which step we're on */}
      {step === 1 && (
        <Upload onUploadComplete={handleUploadComplete} />
        // Pass handleUploadComplete as a prop so Upload.jsx
        // can call it when it's done processing screenshots
      )}

      {step === 2 && (
        <Confirmation
          events={events}
          setEvents={setEvents}
          onConfirmComplete={handleConfirmComplete}
        />
        // Pass events and setEvents so Confirmation.jsx can
        // display and edit them
        // Pass handleConfirmComplete so it can move to step 3
      )}

      {step === 3 && (
        <Success onStartOver={handleStartOver} />
        // Pass handleStartOver so the user can go back to step 1
      )}

    </div>
  );
}

export default Home;