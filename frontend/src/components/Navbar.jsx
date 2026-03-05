// ============================================================
// Navbar.jsx
// ============================================================
// This is the navigation bar that shows at the top of every
// page. It's simple — just the app name and a little tagline.
// ============================================================

import { Camera } from "lucide-react";
// Camera icon from lucide-react to use as our logo
// lucide-react has hundreds of icons we can import like this
import "./Navbar.css";



function Navbar() {
  return (
    <nav className="navbar">
      {/* nav is a semantic HTML element for navigation bars */}

      <div className="navbar-content">

        <div className="navbar-logo">
          <Camera size={24} color="#6366f1" />
          {/* Camera icon, size 24px, purple color */}

          <span className="navbar-title">snapshot</span>
          {/* Our app name */}
        </div>

        <span className="navbar-tagline">
          College Schedule → Google Calendar
        </span>
        {/* Small tagline on the right side */}

      </div>
    </nav>
  );
}

export default Navbar;