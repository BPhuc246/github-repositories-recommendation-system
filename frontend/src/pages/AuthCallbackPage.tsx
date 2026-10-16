import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../services/AuthContext';

// Backend đã đặt cookie. Trang này chỉ kiểm tra phiên rồi chuyển đi.
export default function AuthCallbackPage() {
  const { refresh } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    refresh().then(me =>
      navigate(me ? '/' : '/login?error=github_session_missing', { replace: true }),
    );
  }, []);

  return <p className="py-20 text-center text-sm text-slate-400">Đang hoàn tất đăng nhập...</p>;
}
