import { useEffect } from 'react';
import { Home, ShieldAlert, MessageSquare, FolderKanban } from 'lucide-react';
import { NavLink, Outlet } from 'react-router-dom';
import { useAppStore } from '../lib/store';
import Spinner from './Spinner';

const navItems = [
  { to: '/', label: '战略沙盘', icon: Home },
  { to: '/alerts', label: '风险预警', icon: ShieldAlert },
  { to: '/diagnosis', label: '诊断', icon: MessageSquare },
  { to: '/cases', label: '病例档案', icon: FolderKanban },
];

const Layout = () => {
  const { fetchInitialData, isLoading, error } = useAppStore();

  useEffect(() => {
    fetchInitialData();
  }, []);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Spinner size={28} />
      </div>
    );
  }

  if (error) {
    return <div className="flex items-center justify-center min-h-screen">Error: {error}</div>;
  }

  return (
    <div className="max-w-md mx-auto bg-white flex flex-col min-h-screen">
      <main className="flex-1 pb-16">
        <Outlet />
      </main>
      <nav className="fixed bottom-0 left-1/2 -translate-x-1/2 w-full max-w-md bg-white border-t border-gray-200 flex justify-around">
        {navItems.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `flex flex-col items-center justify-center w-full pt-2 pb-1 text-xs ${
                isActive ? 'text-green-600' : 'text-gray-500'
              }`
            }
          >
            <Icon className="w-6 h-6 mb-1" />
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>
    </div>
  );
};

export default Layout;