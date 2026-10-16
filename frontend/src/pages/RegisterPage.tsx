import { useState, type FormEvent } from 'react';
import { Link, Navigate, useNavigate } from 'react-router-dom';
import { btnOutline, btnPrimary, card, errorBox, input } from '../components/ui';
import { api } from '../services/api';
import { useAuth } from '../services/AuthContext';

export default function RegisterPage() {
  const { user, loading, refresh } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ username: '', email: '', password: '' });
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  if (!loading && user) return <Navigate to="/" replace />;

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError('');
    try {
      await api.register({ ...form, email: form.email || undefined });
      await refresh();
      navigate('/', { replace: true });
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center px-4">
      <div className="w-full max-w-sm space-y-6">
        <div className="text-center">
          <h1 className="text-2xl font-semibold text-slate-800">Tạo tài khoản</h1>
          <p className="mt-1 text-sm text-slate-500">Lưu yêu thích và nhận gợi ý phù hợp</p>
        </div>

        <div className={card}>
          <form onSubmit={submit} className="space-y-3">
            <input
              className={input}
              placeholder="Tên đăng nhập (3-50 ký tự)"
              value={form.username}
              onChange={e => setForm({ ...form, username: e.target.value })}
            />
            <input
              className={input}
              placeholder="Email (không bắt buộc)"
              value={form.email}
              onChange={e => setForm({ ...form, email: e.target.value })}
            />
            <input
              className={input}
              type="password"
              placeholder="Mật khẩu (tối thiểu 6 ký tự)"
              value={form.password}
              onChange={e => setForm({ ...form, password: e.target.value })}
            />
            <button type="submit" disabled={busy} className={`${btnPrimary} w-full`}>
              Đăng ký
            </button>
          </form>

          <div className="my-5 flex items-center gap-3 text-xs text-slate-400">
            <span className="h-px flex-1 bg-slate-200" />
            hoặc
            <span className="h-px flex-1 bg-slate-200" />
          </div>

          <a href={api.githubLoginUrl} className={`${btnOutline} w-full`}>
            Tiếp tục với GitHub
          </a>
        </div>

        {error && <p className={errorBox}>{error}</p>}

        <p className="text-center text-sm text-slate-500">
          Đã có tài khoản?{' '}
          <Link to="/login" className="text-brand hover:text-brand-dark">Đăng nhập</Link>
        </p>
      </div>
    </div>
  );
}
