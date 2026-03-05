import { CalendarCheck, ExternalLink, RotateCcw } from "lucide-react";
import "./Success.css";

function Success({ onStartOver }) {
  return (
    <div className="success-container">

      <div className="success-icon">
        <CalendarCheck size={64} color="#10b981" />
      </div>

      <div className="success-header">
        <h1 className="success-title">You&apos;re all set!</h1>
        <p className="success-subtitle">
          All your events have been added to Google Calendar.
          Head over to check them out!
        </p>
      </div>

      <div className="success-actions">
        <a
          href="https://calendar.google.com"
          target="_blank"
          rel="noopener noreferrer"
          className="btn-success-primary"
        >
          <ExternalLink size={16} />
          <span>Open Google Calendar</span>
        </a>

        <button
          className="btn-success-secondary"
          onClick={onStartOver}
        >
          <RotateCcw size={16} />
          <span>Upload More Screenshots</span>
        </button>
      </div>

      <div className="success-tips">
        <p className="success-tips-title">Tips</p>
        <ul>
          <li>Events are color coded - blue for classes, red for exams, yellow for assignments</li>
          <li>Recurring classes will repeat every week until the semester end date</li>
          <li>You can edit or delete any event directly in Google Calendar</li>
        </ul>
      </div>

    </div>
  );
}

export default Success;