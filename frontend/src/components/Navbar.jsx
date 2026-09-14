import { Camera, ArrowUpRight } from "lucide-react";
import "./Navbar.css";
export default function Navbar() {
  return <nav className="navbar"><div className="navbar-content">
    <a className="navbar-logo" href="/"><span className="brand-icon"><Camera size={22}/></span><span className="navbar-title">snapshot<span className="brand-period">.</span></span></a>
    <span className="navbar-tagline">STEVENS STUDENT EDITION <ArrowUpRight size={15}/></span>
  </div></nav>;
}
