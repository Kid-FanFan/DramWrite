import { Link, useLocation } from 'react-router-dom'
import { Settings, Film } from 'lucide-react'

function Header() {
  const location = useLocation()
  const isHome = location.pathname === '/'

  return (
    <header className="bg-surface border-b border-border">
      <div className="container mx-auto px-4 h-16 flex items-center justify-between">
        <Link to="/" className="flex items-center gap-2 text-primary hover:opacity-80 transition-opacity">
          <Film className="w-6 h-6" />
          <h1 className="text-xl font-bold">剧作大师</h1>
        </Link>

        <div className="flex items-center gap-4">
          {!isHome && (
            <Link
              to="/"
              className="text-sm text-gray-600 hover:text-primary transition-colors"
            >
              返回首页
            </Link>
          )}
          <Link
            to="/settings"
            className={`p-2 rounded-md transition-colors ${
              location.pathname === '/settings'
                ? 'bg-primary/10 text-primary'
                : 'text-gray-600 hover:bg-gray-100'
            }`}
          >
            <Settings className="w-5 h-5" />
          </Link>
        </div>
      </div>
    </header>
  )
}

export default Header
