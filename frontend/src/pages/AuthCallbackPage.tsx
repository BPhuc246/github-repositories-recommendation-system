import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../services/AuthContext';

// Backend đã đặt cookie. Trang này kiểm tra phiên rồi chuyển sang trang GitHub để đồng bộ.
export default function AuthCallbackPage() {
  const { refresh } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    refresh().then(me =>
      navigate(me ? '/github' : '/login?error=github_session_missing', { replace: true }),
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return <p className="py-20 text-center text-sm text-slate-400">Đang hoàn tất đăng nhập...</p>;
}
