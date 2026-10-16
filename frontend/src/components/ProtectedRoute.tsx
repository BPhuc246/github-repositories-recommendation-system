import type { ReactNode } from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../services/AuthContext';

export default function ProtectedRoute({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();

  if (loading) {
    return <p className="py-20 text-center text-sm text-slate-400">Đang tải...</p>;
  }
  return user ? <>{children}</> : <Navigate to="/login" replace />;
}
