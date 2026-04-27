import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'

const NAV_LINKS = [
  { to: '/dashboard', label: 'Dashboard' },
  { to: '/goals',     label: 'Goals' },
  { to: '/history',   label: 'History' },
]

export default function NavBar() {
  const { logout } = useAuth()
  const navigate   = useNavigate()
  const location   = useLocation()

  function handleLogout() {
    logout()
    navigate('/login')
  }

  return (
    <nav className="bg-duke-navy shadow-md">
      <div className="max-w-6xl mx-auto px-4 flex items-center justify-between h-14">
        {/* Brand */}
        <Link to="/dashboard" className="text-white font-bold text-lg tracking-tight">
          Duke<span className="text-blue-300">Macros</span>
        </Link>

        {/* Links */}
        <div className="flex items-center gap-6">
          {NAV_LINKS.map(({ to, label }) => {
            const active = location.pathname === to
            return (
              <Link
                key={to}
                to={to}
                className={`text-sm font-medium transition-colors ${
                  active
                    ? 'text-white border-b-2 border-blue-300 pb-0.5'
                    : 'text-blue-200 hover:text-white'
                }`}
              >
                {label}
              </Link>
            )
          })}
          <button
            onClick={handleLogout}
            className="text-sm text-blue-200 hover:text-white transition-colors ml-2"
          >
            Logout
          </button>
        </div>
      </div>
    </nav>
  )
}
