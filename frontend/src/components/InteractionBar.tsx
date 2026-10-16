import { useEffect, useState } from 'react';
import { api } from '../services/api';
import type { RepoState } from '../types';
import { btnOutline, errorBox } from './ui';

const activeFavorite =
  'inline-flex items-center justify-center rounded-lg border border-amber-200 bg-amber-50 px-4 py-2 text-sm font-medium text-amber-700 transition disabled:opacity-50';
const activeDislike =
  'inline-flex items-center justify-center rounded-lg border border-rose-200 bg-rose-50 px-4 py-2 text-sm font-medium text-rose-700 transition disabled:opacity-50';

export default function InteractionBar({ repoId }: { repoId: number }) {
  const [state, setState] = useState<RepoState | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    api.getState(repoId).then(setState).catch(e => setError((e as Error).message));
  }, [repoId]);

  const run = async (action: () => Promise<RepoState>) => {
    setBusy(true);
    setError('');
    try {
      setState(await action());
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  if (!state) return <p className="text-sm text-slate-400">Đang tải...</p>;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-3">
        <button
          disabled={busy}
          onClick={() => run(() => api.setFavorite(repoId, !state.favorite))}
          className={state.favorite ? activeFavorite : btnOutline}
        >
          {state.favorite ? '★ Đã yêu thích' : '☆ Yêu thích'}
        </button>
        <button
          disabled={busy}
          onClick={() => run(() => api.setDislike(repoId, !state.disliked))}
          className={state.disliked ? activeDislike : btnOutline}
        >
          {state.disliked ? 'Đã không thích' : 'Không thích'}
        </button>
      </div>

      <div className="flex items-center gap-1">
        <span className="mr-2 text-sm text-slate-500">Đánh giá:</span>
        {[1, 2, 3, 4, 5].map(n => (
          <button
            key={n}
            disabled={busy}
            aria-label={`${n} sao`}
            onClick={() => run(() => api.setRating(repoId, state.rating === n ? null : n))}
            className={`text-2xl leading-none transition disabled:opacity-50 ${
              (state.rating ?? 0) >= n ? 'text-amber-400' : 'text-slate-300 hover:text-amber-300'
            }`}
          >
            ★
          </button>
        ))}
        {state.rating && (
          <span className="ml-2 text-xs text-slate-400">bấm lại để bỏ đánh giá</span>
        )}
      </div>

      {error && <p className={errorBox}>{error}</p>}
    </div>
  );
}
