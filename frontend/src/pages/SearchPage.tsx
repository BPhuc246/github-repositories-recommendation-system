import { useEffect, useState } from 'react';
import RepoCard from '../components/RepoCard';
import { btnOutline, errorBox, input } from '../components/ui';
import { api } from '../services/api';
import type { Repo, RepoPage } from '../types';

const PAGE_SIZE = 12;
type Sort = 'stars' | 'forks' | 'updated';

export default function SearchPage() {
  const [q, setQ] = useState('');
  const [debouncedQ, setDebouncedQ] = useState('');
  const [language, setLanguage] = useState('');
  const [sort, setSort] = useState<Sort>('stars');
  const [page, setPage] = useState(1);

  const [languages, setLanguages] = useState<string[]>([]);
  const [recs, setRecs] = useState<Repo[]>([]);
  const [data, setData] = useState<RepoPage | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    api.languages().then(setLanguages).catch(() => {});
    api.recommendations(6).then(setRecs).catch(() => {});
  }, []);

  // Chờ người dùng gõ xong rồi mới tìm
  useEffect(() => {
    const t = setTimeout(() => {
      setDebouncedQ(q);
      setPage(1);
    }, 300);
    return () => clearTimeout(t);
  }, [q]);

  useEffect(() => {
    setLoading(true);
    setError('');
    const params: Record<string, string> = {
      sort,
      page: String(page),
      page_size: String(PAGE_SIZE),
    };
    if (debouncedQ.trim()) params.q = debouncedQ.trim();
    if (language) params.language = language;

    api.searchRepos(params)
      .then(setData)
      .catch(e => setError((e as Error).message))
      .finally(() => setLoading(false));
  }, [debouncedQ, language, sort, page]);

  const totalPages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1;
  const showRecs = !debouncedQ && !language && recs.length > 0;

  return (
    <div className="space-y-8">
      <div className="space-y-3">
        <input
          className={input}
          placeholder="Tìm theo tên hoặc mô tả repository..."
          value={q}
          onChange={e => setQ(e.target.value)}
        />
        <div className="flex flex-wrap gap-3">
          <select
            className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-600 focus:outline-none focus:ring-2 focus:ring-teal-100"
            value={language}
            onChange={e => { setLanguage(e.target.value); setPage(1); }}
          >
            <option value="">Tất cả ngôn ngữ</option>
            {languages.map(l => <option key={l} value={l}>{l}</option>)}
          </select>
          <select
            className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-600 focus:outline-none focus:ring-2 focus:ring-teal-100"
            value={sort}
            onChange={e => { setSort(e.target.value as Sort); setPage(1); }}
          >
            <option value="stars">Nhiều sao nhất</option>
            <option value="forks">Nhiều fork nhất</option>
            <option value="updated">Mới cập nhật</option>
          </select>
        </div>
      </div>

      {showRecs && (
        <section className="space-y-3">
          <h2 className="text-sm font-medium text-slate-500">Gợi ý cho bạn</h2>
          <div className="grid gap-4 sm:grid-cols-2">
            {recs.map(r => <RepoCard key={r.repo_id} repo={r} />)}
          </div>
        </section>
      )}

      <section className="space-y-3">
        <h2 className="text-sm font-medium text-slate-500">
          {data ? `${data.total.toLocaleString('vi-VN')} kết quả` : 'Đang tìm...'}
        </h2>

        {error && <p className={errorBox}>{error}</p>}

        <div className={`grid gap-4 sm:grid-cols-2 transition ${loading ? 'opacity-60' : ''}`}>
          {data?.items.map(r => <RepoCard key={r.repo_id} repo={r} />)}
        </div>

        {data && data.total === 0 && !loading && (
          <p className="py-10 text-center text-sm text-slate-400">Không tìm thấy repository nào.</p>
        )}

        {data && data.total > PAGE_SIZE && (
          <div className="flex items-center justify-center gap-4 pt-4">
            <button className={btnOutline} disabled={page === 1} onClick={() => setPage(p => p - 1)}>
              Trước
            </button>
            <span className="text-sm text-slate-500">Trang {page} / {totalPages}</span>
            <button className={btnOutline} disabled={page >= totalPages} onClick={() => setPage(p => p + 1)}>
              Sau
            </button>
          </div>
        )}
      </section>
    </div>
  );
}
