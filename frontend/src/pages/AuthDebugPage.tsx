import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { btnPrimary, card, errorBox } from '../components/ui';
import { api } from '../services/api';
import { useAuth } from '../services/AuthContext';
import type { GithubConfig } from '../types';

function ConfigRow({ ok, label, value }: { ok: boolean; label: string; value?: string }) {
  return (
    <li className="flex items-start justify-between gap-4 py-2.5 text-sm">
      <span className="text-slate-500">{label}</span>
      <span className={ok ? 'text-right text-teal-700' : 'text-right text-rose-600'}>
        {ok ? '✓' : '✗'} {value}
      </span>
    </li>
  );
}

export default function AuthDebugPage() {
  const { user, loading } = useAuth();
  const [cfg, setCfg] = useState<GithubConfig | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    api.githubConfig().then(setCfg).catch(e => setError((e as Error).message));
  }, []);

  const isGithub = user?.auth_provider === 'github';

  return (
    <div className="flex min-h-screen items-start justify-center px-4 py-12">
      <div className="w-full max-w-xl space-y-6">
        <div>
          <h1 className="text-xl font-semibold text-slate-800">Kiểm tra đăng nhập GitHub</h1>
          <p className="mt-1 text-sm text-slate-500">
            Trang này xác nhận cấu hình OAuth và trạng thái đăng nhập hiện tại.
          </p>
        </div>

        <section className={card}>
          <h2 className="mb-3 font-medium text-slate-800">Trạng thái đăng nhập</h2>
          {loading && <p className="text-sm text-slate-400">Đang kiểm tra...</p>}
          {!loading && !user && <p className="text-sm text-slate-600">Bạn chưa đăng nhập.</p>}
          {!loading && user && isGithub && (
            <p className="text-sm text-teal-700">
              ✓ Đã đăng nhập bằng GitHub: <strong>@{user.github_login}</strong> (id {user.github_id})
            </p>
          )}
          {!loading && user && !isGithub && (
            <p className="text-sm text-amber-700">
              Đang đăng nhập bằng tài khoản thường ({user.username}), chưa dùng GitHub.
            </p>
          )}

          <div className="mt-4 flex gap-3">
            {!isGithub && (
              <a href={api.githubLoginUrl} className={btnPrimary}>Đăng nhập bằng GitHub</a>
            )}
            <Link to="/" className="self-center text-sm text-slate-500 hover:text-slate-800">
              Về trang chủ
            </Link>
          </div>
        </section>

        <section className={card}>
          <h2 className="mb-2 font-medium text-slate-800">Cấu hình backend</h2>
          {error && <p className={errorBox}>Không gọi được backend: {error}</p>}
          {cfg && (
            <ul className="divide-y divide-slate-100">
              <ConfigRow ok={cfg.client_id_set} label="GITHUB_CLIENT_ID" value={cfg.client_id_set ? cfg.client_id_preview ?? 'đã đặt' : 'chưa đặt'} />
              <ConfigRow ok={cfg.client_secret_set} label="GITHUB_CLIENT_SECRET" value={cfg.client_secret_set ? 'đã đặt' : 'chưa đặt'} />
              <ConfigRow ok label="Callback URL (phải khớp GitHub OAuth App)" value={cfg.redirect_uri} />
              <ConfigRow ok label="Frontend URL" value={cfg.frontend_url} />
            </ul>
          )}
        </section>

        {user && (
          <section className={card}>
            <h2 className="mb-2 font-medium text-slate-800">Dữ liệu user</h2>
            <pre className="overflow-auto rounded-lg bg-slate-50 p-4 text-xs text-slate-600">
              {JSON.stringify(user, null, 2)}
            </pre>
          </section>
        )}
      </div>
    </div>
  );
}
