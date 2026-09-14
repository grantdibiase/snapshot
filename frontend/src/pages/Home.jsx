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
    // Only restore progress on /confirm, which is the OAuth return route.
    // The home route should always be a fresh upload screen.
    const isConfirmationRoute = window.location.pathname === "/confirm";
    const saved = window.localStorage.getItem("snapshot_step");
    return isConfirmationRoute && new URLSearchParams(window.location.search).has("auth") ? 2 : isConfirmationRoute && saved ? Number(saved) : startAtStep || 1;
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

      {step === 1 && <section className="campus-hero"><div><p className="eyebrow">LESS ADMIN. MORE STEVENS.</p><h1>Your semester.<br/><em>In focus.</em></h1><p className="hero-copy">From a schedule screenshot to a week that makes sense. Make room for lectures, late-night labs, and everything in between.</p><div className="hero-tags"><span>01 / Capture</span><span>02 / Check</span><span>03 / Calendar</span></div></div><aside className="week-preview" aria-label="Example schedule preview"><div className="preview-heading"><span>A WEEK ON CASTLE POINT</span><span>EXAMPLE</span></div><div className="preview-days"><span>MON</span><span>TUE</span><span>WED</span></div><div className="preview-grid"><div className="preview-event lecture">09:00<br/><b>Lecture</b><small>Ideas start here.</small></div><div className="preview-event lab">11:00<br/><b>Lab</b><small>Make it real.</small></div><div className="preview-event exam">14:00<br/><b>Exam</b><small>You’ve got this.</small></div></div><p>One calendar. A little more clarity.</p></aside></section>}
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

      <footer className="campus-footer"><span>Built for life at Castle Point.</span><span>Independent student tool · Not affiliated with Stevens Institute of Technology</span></footer>
    </div>
  );
}

export default Home;