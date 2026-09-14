import { Camera } from "lucide-react";
import "./Navbar.css";
export default function Navbar() {
  return <nav className="navbar"><div className="navbar-content">
    <a className="navbar-logo" href="/"><span className="brand-icon"><Camera size={22}/></span><span className="navbar-title">snapshot<span className="brand-period">.</span></span></a>
    <img className="stevens-wordmark" src="/brand/stevens-logo.png" alt="Stevens Institute of Technology with Castle Point building emblem" />
  </div></nav>;
}
