import { useEffect, useRef, useState } from 'react';
import RepoCard from '../components/RepoCard';
import { btnPrimary, card, errorBox, successBox, tabActive, tabInactive } from '../components/ui';
import { api } from '../services/api';
import type { GithubKind, GithubStatus, Repo } from '../types';

const TABS: { key: GithubKind; label: string; hint: string }[] = [
  { key: 'owner', label: 'Của tôi', hint: 'Repository bạn sở hữu trên GitHub.' },
  { key: 'collab', label: 'Cộng tác', hint: 'Repository bạn được mời làm cộng tác viên.' },
  { key: 'star', label: 'Đã star', hint: 'Repository bạn đã đánh dấu sao.' },
  { key: 'pin', label: 'Đã ghim', hint: 'Repository được ghim trên hồ sơ GitHub của bạn.' },
];

export default function GithubReposPage() {
  const [status, setStatus] = useState<GithubStatus | null>(null);
  const [tab, setTab] = useState<GithubKind>('owner');
  const [repos, setRepos] = useState<Repo[] | null>(null);
  const [syncing, setSyncing] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const autoSynced = useRef(false);

  const runSync = async () => {
    setSyncing(true);
    setError('');
    setMessage('');
    try {
      const r = await api.githubSync();
      const total = Object.values(r.synced).reduce((a, b) => a + b, 0);
      setMessage(`Đã đồng bộ ${total} quan hệ repository từ GitHub.`);
      setStatus(await api.githubStatus());
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSyncing(false);
    }
  };

  // Lần đầu vào trang: nếu đã liên kết GitHub nhưng chưa đồng bộ thì tự đồng bộ
  useEffect(() => {
    api.githubStatus()
      .then(s => {
        setStatus(s);
        if (s.linked && !s.last_synced_at && !autoSynced.current) {
          autoSynced.current = true;
          runSync();
        }
      })
      .catch(e => setError((e as Error).message));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Tải danh sách repo mỗi khi đổi tab hoặc sau khi đồng bộ xong
  useEffect(() => {
    if (!status?.linked) return;
    setRepos(null);
    api.githubRepos(tab)
      .then(setRepos)
      .catch(e => setError((e as Error).message));
  }, [tab, status?.linked, status?.last_synced_at]);

  const activeTab = TABS.find(t => t.key === tab)!;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold text-slate-800">Repository trên GitHub của bạn</h1>
          <p className="mt-1 text-sm text-slate-500">
            {status?.github_login && <>@{status.github_login} · </>}
            {status?.last_synced_at
              ? `Đồng bộ lần cuối: ${new Date(status.last_synced_at).toLocaleString('vi-VN')}`
              : 'Chưa đồng bộ'}
          </p>
        </div>
        {status?.linked && (
          <button className={btnPrimary} onClick={runSync} disabled={syncing}>
            {syncing ? 'Đang đồng bộ...' : 'Đồng bộ ngay'}
          </button>
        )}
      </div>

      {message && <p className={successBox}>{message}</p>}
      {error && <p className={errorBox}>{error}</p>}

      {!status && !error && <p className="py-20 text-center text-sm text-slate-400">Đang tải...</p>}

      {status && !status.linked && (
        <section className={`${card} text-center`}>
          <p className="text-sm text-slate-600">Tài khoản này chưa liên kết GitHub.</p>
          <p className="mt-1 text-xs text-slate-400">
            Đăng nhập bằng GitHub để xem repository bạn sở hữu, đã star, đã ghim và cộng tác.
          </p>
          <a href={api.githubLoginUrl} className={`${btnPrimary} mt-5`}>
            Đăng nhập bằng GitHub
          </a>
        </section>
      )}

      {status?.linked && (
        <>
          <div className="flex flex-wrap gap-2">
            {TABS.map(t => (
              <button
                key={t.key}
                onClick={() => setTab(t.key)}
                className={tab === t.key ? tabActive : tabInactive}
              >
                {t.label}
                <span className="ml-2 rounded-full bg-white/70 px-1.5 text-xs">
                  {status.counts[t.key] ?? 0}
                </span>
              </button>
            ))}
          </div>

          <p className="text-sm text-slate-400">{activeTab.hint}</p>

          {repos === null && (
            <p className="py-10 text-center text-sm text-slate-400">Đang tải...</p>
          )}
          {repos !== null && repos.length === 0 && (
            <p className="py-10 text-center text-sm text-slate-400">
              Chưa có repository nào trong mục này.
            </p>
          )}

          <div className="grid gap-4 sm:grid-cols-2">
            {repos?.map(r => <RepoCard key={r.repo_id} repo={r} />)}
          </div>
        </>
      )}
    </div>
  );
}
