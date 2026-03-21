import { NavLink } from 'react-router-dom';

export default function Navbar() {
  return (
    <nav className="navbar">
      <NavLink to="/" className="navbar-brand">
        <div className="logo-icon">T</div>
        <span className="brand-name">Transgraph</span>
      </NavLink>

      <ul className="navbar-links">
        <li><NavLink to="/" end className={({ isActive }) => isActive ? 'active' : ''}>Home</NavLink></li>
        <li><NavLink to="/about" className={({ isActive }) => isActive ? 'active' : ''}>About</NavLink></li>
        <li>
          <button className="btn-primary" style={{ cursor: 'default' }}>Multi‑Agent AI</button>
        </li>
      </ul>
    </nav>
  );
}
