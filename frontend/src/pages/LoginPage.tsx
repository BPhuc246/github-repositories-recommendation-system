import { useState, type FormEvent } from 'react';
import { Link, Navigate, useNavigate, useSearchParams } from 'react-router-dom';
import { btnOutline, btnPrimary, card, errorBox, input } from '../components/ui';
import { api } from '../services/api';
import { useAuth } from '../services/AuthContext';

const GITHUB_ERRORS: Record<string, string> = {
  github_not_configured: 'Chưa cấu hình GITHUB_CLIENT_ID và GITHUB_CLIENT_SECRET trong backend/.env.',
  github_state_mismatch:
    'Phiên đăng nhập GitHub không khớp. Hãy mở trang bằng http://localhost:5173 (không dùng 127.0.0.1) và thử lại.',
  github_access_denied: 'Bạn đã từ chối cấp quyền cho ứng dụng trên GitHub.',
  github_token_redirect_uri_mismatch: 'Callback URL trong GitHub OAuth App không khớp GITHUB_REDIRECT_URI.',
  github_token_incorrect_client_credentials: 'GITHUB_CLIENT_SECRET không đúng.',
  github_token_bad_verification_code: 'Mã xác thực GitHub đã hết hạn hoặc đã dùng. Hãy thử lại.',
  github_network_error: 'Backend không kết nối được tới GitHub.',
  github_db_error: 'Lỗi ghi dữ liệu. Hãy kiểm tra đã chạy migration và xem log backend.',
  github_session_missing: 'Không tạo được phiên đăng nhập. Hãy thử lại.',
};

function githubErrorMessage(code: string): string {
  return GITHUB_ERRORS[code] ?? `Đăng nhập GitHub thất bại (${code}). Xem log backend để biết chi tiết.`;
}

export default function LoginPage() {
  const { user, loading, refresh } = useAuth();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const [form, setForm] = useState({ username: '', password: '' });
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  if (!loading && user) return <Navigate to="/" replace />;

  const urlError = params.get('error');
  const shownError = error || (urlError ? githubErrorMessage(urlError) : '');

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError('');
    try {
      await api.login(form);
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
          <h1 className="text-2xl font-semibold text-slate-800">Repo<span className="text-brand">Finder</span></h1>
          <p className="mt-1 text-sm text-slate-500">Khám phá repository GitHub phù hợp với bạn</p>
        </div>

        <div className={card}>
          <form onSubmit={submit} className="space-y-3">
            <input
              className={input}
              placeholder="Tên đăng nhập"
              value={form.username}
              onChange={e => setForm({ ...form, username: e.target.value })}
            />
            <input
              className={input}
              type="password"
              placeholder="Mật khẩu"
              value={form.password}
              onChange={e => setForm({ ...form, password: e.target.value })}
            />
            <button type="submit" disabled={busy} className={`${btnPrimary} w-full`}>
              Đăng nhập
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

        {shownError && <p className={errorBox}>{shownError}</p>}

        <p className="text-center text-sm text-slate-500">
          Chưa có tài khoản?{' '}
          <Link to="/register" className="text-brand hover:text-brand-dark">Đăng ký</Link>
        </p>
      </div>
    </div>
  );
}
