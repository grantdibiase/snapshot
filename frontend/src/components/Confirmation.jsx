// ============================================================
// Confirmation.jsx
// ============================================================
// Updated to handle the new OAuth redirect flow.
// Instead of the backend opening a popup, we redirect the
// user to Google, they log in, and come back with a session_id
// that we use to create their calendar events.
// ============================================================

import { useState, useEffect } from "react";
import axios from "axios";
import eventTypes from "../eventTypes.json";
import { Pencil, Check, X, Calendar } from "lucide-react";
import "./Confirmation.css";

function Confirmation({ events, setEvents, onConfirmComplete }) {

  const [editingIndex, setEditingIndex] = useState(null);
  const [editForm, setEditForm] = useState({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [sessionId, setSessionId] = useState(() => sessionStorage.getItem("snapshot_session"));
  const [connecting, setConnecting] = useState(false);
  const [datesReviewed, setDatesReviewed] = useState(false);
  // sessionId is what proves the user logged into Google.
  // We get it from the URL after Google redirects them back.
  const [isAuthenticated, setIsAuthenticated] = useState(() => Boolean(sessionStorage.getItem("snapshot_session")));
  // Tracks whether the user has connected Google Calendar yet.

  useEffect(() => {
    // --------------------------------------------------------
    // When the user returns from Google, the SPA reloads and we
    // may lose the in-memory event list. Persist events locally
    // so we can restore after the OAuth redirect.
    // --------------------------------------------------------
    const stored = localStorage.getItem("snapshot_events");
    if (stored && events.length === 0) {
      try {
        const parsed = JSON.parse(stored);
        if (Array.isArray(parsed) && parsed.length > 0) {
          setEvents(parsed);
        }
      } catch {
        // ignore bad JSON
      }
    }

    const params = new URLSearchParams(window.location.search);
    // window.location.search gets the "?session_id=...&auth=success"
    // part of the URL. URLSearchParams parses it into key/value pairs.

    const sid = params.get("session_id");
    const auth = params.get("auth");

    if (sid && auth === "success") {
      setSessionId(sid);
      sessionStorage.setItem("snapshot_session", sid);
      setIsAuthenticated(true);
      // User just came back from Google login successfully!

      // Clean up the URL so it looks nice
      window.history.replaceState({}, "", "/confirm");
      // replaceState changes the URL without reloading the page
      
    }

    if (auth === "error") {
      const msg = params.get("message");
      setError(
        msg
          ? `Google authentication failed: ${msg}`
          : "Google authentication failed. Please try again."
      );
    }
  }, [events, setEvents]);
  // Include events in dependency array since we check events.length

  const handleConnectGoogle = async () => {
    // --------------------------------------------------------
    // Called when user clicks "Connect Google Calendar".
    // We persist the current events to localStorage so they
    // survive the redirect back from Google's login page.
    // --------------------------------------------------------
    try {
      setConnecting(true);
      setError(null);
      localStorage.setItem("snapshot_events", JSON.stringify(events));
      localStorage.setItem("snapshot_step", "2");

      const response = await axios.get("https://snapshot-backend-j49i.onrender.com/auth/google");
      window.location.href = response.data.auth_url;
      // Redirect the user to Google's login page!
      // After they log in Google sends them back to our app.
    } catch (err) {
      setConnecting(false);
      setError(err.response?.data?.detail || "Google connection could not start. Wait a moment and try again.");
    }
  };

  const handleEdit = (index) => {
    setEditingIndex(index);
    setEditForm({ ...events[index] });
  };

  const handleSave = (index) => {
    const updatedEvents = [...events];
    updatedEvents[index] = { ...editForm };
    setEvents(updatedEvents);
    setDatesReviewed(false);
    localStorage.setItem("snapshot_events", JSON.stringify(updatedEvents));
    setEditingIndex(null);
  };

  const handleCancel = () => {
    setEditingIndex(null);
    setEditForm({});
  };

  const handleFormChange = (field, value) => {
    setEditForm((prev) => ({ ...prev, [field]: value }));
  };

  const handleConfirm = async () => {
    // --------------------------------------------------------
    // Sends confirmed events to backend with the session_id
    // so it knows whose Google Calendar to add events to.
    // --------------------------------------------------------
    if (!isAuthenticated || !sessionId) {
      setError("Please connect your Google Calendar first!");
      return;
    }

    if (events.length === 0) {
      setError("No events to add! Please upload screenshots first.");
      return;
    }

    if (!datesReviewed || events.some(e => e.days?.length && !e.date && (!e.semester_start || !e.semester_end || e.semester_end < e.semester_start))) {
      setError("Set semester dates for recurring events and confirm you reviewed the dates.");
      return;
    }
    setLoading(true);
    setError(null);

    try {
      await axios.post("https://snapshot-backend-j49i.onrender.com/confirm", {
        events,
        session_id: sessionId
        // Send session_id so backend knows whose calendar to use
      });

      localStorage.removeItem("snapshot_events");
      onConfirmComplete();

    } catch (err) {
      if (err.response?.status === 401) {
        sessionStorage.removeItem("snapshot_session");
        setSessionId(null);
        setIsAuthenticated(false);
      }
      setError(
        err.response?.data?.detail ||
        err.message ||
        "Something went wrong adding events to Google Calendar."
      );
    } finally {
      setLoading(false);
    }
  };

  const getTypeColor = type => (eventTypes[type] || eventTypes.lecture).color;
  const applySemester = (field, value) => {
    const updated = events.map(e => e.days?.length && !e.date ? {...e, [field]: value} : e);
    setEvents(updated);
    localStorage.setItem("snapshot_events", JSON.stringify(updated));
    setDatesReviewed(false);
  };

  return (
    <div className="confirmation-container">

      <div className="confirmation-header">
        <h1 className="confirmation-title">Review Your Schedule</h1>
        <p className="confirmation-subtitle">
          We found <strong>{events.length} events</strong>. Review them below
          and edit anything that looks wrong before adding to your calendar.
        </p>
      </div>

      {/* Google Calendar Connection Banner */}
      {!isAuthenticated ? (
        <div className="auth-banner">
          <div className="auth-banner-text">
            <Calendar size={20} color="#6366f1" />
            <div>
              <p className="auth-banner-title">Connect Google Calendar</p>
              <p className="auth-banner-subtitle">
                You need to connect your Google account before adding events.
              </p>
            </div>
          </div>
          <button className="btn-connect-google" onClick={handleConnectGoogle} disabled={connecting}>
            {connecting ? "Opening Google…" : "Connect Google Calendar"}
          </button>
        </div>
      ) : (
        <div className="auth-success-banner">
          <Check size={18} color="#10b981" />
          <span>Google Calendar connected!</span>
        </div>
      )}

      <section className="semester-panel" aria-label="Semester dates">
        <h2>Semester dates</h2>
        <p>Choose dates for all recurring classes. Check individual events below before importing.</p>
        <div className="semester-inputs">
          <label>Semester starts<input type="date" onChange={e => applySemester("semester_start", e.target.value)} /></label>
          <label>Semester ends<input type="date" onChange={e => applySemester("semester_end", e.target.value)} /></label>
        </div>
        <label className="review-check"><input type="checkbox" checked={datesReviewed} onChange={e => setDatesReviewed(e.target.checked)} />I reviewed every event’s dates, including the year.</label>
      </section>
      <div className="color-legend">{Object.entries(eventTypes).map(([key, item]) => <span key={key}><i style={{background:item.color}} />{item.label}</span>)}</div>
      <details className="auth-help"><summary>About connecting Google Calendar</summary><p>You’ll return here after signing in. Connecting gives Snapshot permission to add the events you confirm. During testing, Google may show an unverified-app warning; only continue if you recognize and trust this Snapshot app.</p></details>
      {/* Events Table */}
      <div className="events-table">
        {events.map((event, index) => (
          <div key={index} className="event-row">
            {editingIndex === index ? (
              <div className="event-edit-form">
                <div className="edit-grid">

                  <div className="edit-field">
                    <label>Title</label>
                    <input
                      value={editForm.title || ""}
                      onChange={(e) => handleFormChange("title", e.target.value)}
                    />
                  </div>

                  <div className="edit-field">
                    <label>Type</label>
                    <select
                      value={editForm.type === "class" ? "lecture" : editForm.type || "other"}
                      onChange={(e) => handleFormChange("type", e.target.value)}
                    >
                      <option value="lecture">Lecture</option><option value="lab">Lab</option><option value="recitation">Recitation</option>
                      <option value="exam">Exam</option>
                      <option value="assignment">Assignment</option>
                      <option value="office_hours">Office Hours</option>
                      <option value="other">Other</option>
                    </select>
                  </div>

                  <div className="edit-field">
                    <label>Start Time</label>
                    <input
                      value={editForm.start_time || ""}
                      onChange={(e) => handleFormChange("start_time", e.target.value)}
                      placeholder="e.g. 9:00 AM"
                    />
                  </div>

                  <div className="edit-field">
                    <label>End Time</label>
                    <input
                      value={editForm.end_time || ""}
                      onChange={(e) => handleFormChange("end_time", e.target.value)}
                      placeholder="e.g. 10:00 AM"
                    />
                  </div>

                  <div className="edit-field">
                    <label>Location</label>
                    <input
                      value={editForm.location || ""}
                      onChange={(e) => handleFormChange("location", e.target.value)}
                      placeholder="e.g. Room 204"
                    />
                  </div>

                  <div className="edit-field">
                    <label>Days (comma separated)</label>
                    <input
                      value={(editForm.days || []).join(", ")}
                      onChange={(e) =>
                        handleFormChange(
                          "days",
                          e.target.value.split(",").map((d) => d.trim())
                        )
                      }
                      placeholder="e.g. Monday, Wednesday"
                    />
                  </div>

                  <div className="edit-field">
                    <label>Semester Start</label>
                    <input
                      value={editForm.semester_start || ""}
                      onChange={(e) => handleFormChange("semester_start", e.target.value)}
                      placeholder="e.g. 2025-01-13"
                    />
                  </div>

                  <div className="edit-field">
                    <label>Semester End</label>
                    <input
                      value={editForm.semester_end || ""}
                      onChange={(e) => handleFormChange("semester_end", e.target.value)}
                      placeholder="e.g. 2025-05-10"
                    />
                  </div>

                </div>

                <div className="edit-actions">
                  <button className="btn-icon-green" onClick={() => handleSave(index)}>
                    <Check size={16} /> Save
                  </button>
                  <button className="btn-icon-red" onClick={handleCancel}>
                    <X size={16} /> Cancel
                  </button>
                </div>
              </div>

            ) : (
              <div className="event-view">
                <div className="event-main">
                  <span
                    className="event-type-badge"
                    style={{ backgroundColor: getTypeColor(event.type) }}
                  >
                    {(eventTypes[event.type] || eventTypes.lecture).label}
                  </span>
                  <span className="event-title">{event.title}</span>
                </div>

                <div className="event-details">
                  {event.days && event.days.length > 0 && (
                    <span className="event-detail">
                      📅 {event.days.join(", ")}
                    </span>
                  )}
                  {event.date && (
                    <span className="event-detail">📅 {event.date}</span>
                  )}
                  {event.start_time && (
                    <span className="event-detail">
                      🕐 {event.start_time}
                      {event.end_time && ` - ${event.end_time}`}
                    </span>
                  )}
                  {event.location && (
                    <span className="event-detail">📍 {event.location}</span>
                  )}
                  {event.semester_start && (
                    <span className="event-detail">
                      🗓 {event.semester_start} → {event.semester_end}
                    </span>
                  )}
                </div>

                <button aria-label={`Edit ${event.title}`} className="btn-edit" onClick={() => handleEdit(index)}>
                  <Pencil size={14} />
                </button>
              </div>
            )}
          </div>
        ))}
      </div>

      {error && (
        <div role="alert" className="confirmation-error">{error}</div>
      )}

      <button
        className="btn-primary"
        onClick={handleConfirm}
        disabled={loading || !isAuthenticated || !datesReviewed || editingIndex !== null}
      >
        {loading ? (
          "Adding to Google Calendar..."
        ) : (
          <span>Add {events.length} Events to Google Calendar</span>
        )}
      </button>

    </div>
  );
}

export default Confirmation;
