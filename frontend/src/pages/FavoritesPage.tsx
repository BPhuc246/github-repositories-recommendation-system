import { useEffect, useState } from 'react';
import RepoCard from '../components/RepoCard';
import { errorBox } from '../components/ui';
import { api } from '../services/api';
import type { Repo } from '../types';

export default function FavoritesPage() {
  const [repos, setRepos] = useState<Repo[] | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    api.favorites().then(setRepos).catch(e => setError((e as Error).message));
  }, []);

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold text-slate-800">Repository yêu thích</h1>

      {error && <p className={errorBox}>{error}</p>}
      {!repos && !error && <p className="text-sm text-slate-400">Đang tải...</p>}
      {repos && repos.length === 0 && (
        <p className="py-10 text-center text-sm text-slate-400">
          Bạn chưa yêu thích repository nào.
        </p>
      )}

      <div className="grid gap-4 sm:grid-cols-2">
        {repos?.map(r => <RepoCard key={r.repo_id} repo={r} />)}
      </div>
    </div>
  );
}
