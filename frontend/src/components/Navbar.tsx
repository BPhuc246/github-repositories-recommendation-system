import { Link, NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../services/AuthContext';

const linkClass = ({ isActive }: { isActive: boolean }) =>
  `rounded-md px-3 py-1.5 text-sm transition ${
    isActive ? 'bg-teal-50 text-brand-dark' : 'text-slate-500 hover:text-slate-800'
  }`;

export default function Navbar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate('/login', { replace: true });
  };

  return (
    <header className="border-b border-slate-200 bg-white">
      <div className="mx-auto flex max-w-5xl items-center justify-between gap-4 px-4 py-3">
        <Link to="/" className="font-semibold text-slate-800">
          Repo<span className="text-brand">Finder</span>
        </Link>

        <nav className="flex items-center gap-1">
          <NavLink to="/" end className={linkClass}>Tìm kiếm</NavLink>
          <NavLink to="/github" className={linkClass}>GitHub của tôi</NavLink>
          <NavLink to="/favorites" className={linkClass}>Yêu thích</NavLink>
          <NavLink to="/auth/debug" className={linkClass}>Kiểm tra</NavLink>
        </nav>

        <div className="flex items-center gap-3">
          {user?.avatar_url && (
            <img src={user.avatar_url} alt="" className="h-7 w-7 rounded-full" />
          )}
          <span className="hidden text-sm text-slate-500 sm:block">
            {user?.github_login ?? user?.username}
          </span>
          <button onClick={handleLogout} className="text-sm text-slate-400 hover:text-slate-700">
            Đăng xuất
          </button>
        </div>
      </div>
    </header>
  );
}
