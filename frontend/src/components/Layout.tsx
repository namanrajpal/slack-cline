import { Link, Outlet, useLocation } from 'react-router-dom';

export default function Layout() {
  const location = useLocation();

  const isActive = (path: string) => {
    return location.pathname === path || location.pathname.startsWith(path + '/');
  };

  const navLinkClass = (path: string) => {
    return `px-3 py-2 rounded-md text-sm font-medium ${
      isActive(path)
        ? 'bg-blue-700 text-white'
        : 'text-blue-100 hover:bg-blue-600 hover:text-white'
    }`;
  };

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Header/Navigation */}
      <nav className="bg-blue-600 shadow-lg">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center">
              <Link to="/" className="flex-shrink-0">
                <h1 className="text-white text-xl font-bold">
                  🤖 Slack-Cline Dashboard
                </h1>
              </Link>
              <div className="ml-10 flex items-baseline space-x-4">
                <Link to="/" className={navLinkClass('/')}>
                  Dashboard
                </Link>
                <Link to="/projects" className={navLinkClass('/projects')}>
                  Projects
                </Link>
                <Link to="/runs" className={navLinkClass('/runs')}>
                  Runs
                </Link>
                <Link to="/admin" className={navLinkClass('/admin')}>
                  Admin Panel
                </Link>
                <Link to="/settings" className={navLinkClass('/settings')}>
                  Settings
                </Link>
              </div>
            </div>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        <Outlet />
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-gray-200 mt-8">
        <div className="max-w-7xl mx-auto py-4 px-4 sm:px-6 lg:px-8">
          <p className="text-center text-sm text-gray-500">
            Slack-Cline Dashboard • Manage projects, monitor runs, and test integrations
          </p>
        </div>
      </footer>
    </div>
  );
}
