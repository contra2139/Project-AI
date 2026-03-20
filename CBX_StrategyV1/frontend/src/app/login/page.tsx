'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import axios from 'axios';
import { useAuthStore } from '@/store/authStore';
import { LayoutPanelLeft } from 'lucide-react';

export default function LoginPage() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const router = useRouter();
  const login = useAuthStore((state) => state.login);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const response = await axios.post('/api/auth/login', {
        username,
        password,
      });

      if (response.data.success) {
        login(username);
        router.push('/dashboard');
      }
    } catch (err: any) {
      setError(err.response?.data?.message || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-bg-primary text-cbx-text">
      <div className="w-full max-w-md space-y-8 rounded-lg bg-bg-secondary p-8 border border-cbx-border shadow-xl">
        <div className="text-center">
          <div className="flex justify-center mb-4">
            <LayoutPanelLeft size={48} className="text-accent-yellow" />
          </div>
          <h1 className="text-3xl font-bold text-accent-yellow">CBX Trading Bot</h1>
          <p className="mt-2 text-cbx-muted">Enter your credentials to access the dashboard</p>
        </div>

        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
          <div className="space-y-4">
            <div>
              <label htmlFor="username" className="block text-sm font-medium">
                Username
              </label>
              <input
                id="username"
                type="text"
                required
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="mt-1 block w-full rounded-md border border-cbx-border bg-bg-tertiary p-3 placeholder-cbx-muted focus:border-accent-yellow focus:outline-none focus:ring-1 focus:ring-accent-yellow sm:text-sm"
              />
            </div>
            <div>
              <label htmlFor="password" className="block text-sm font-medium">
                Password
              </label>
              <input
                id="password"
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="mt-1 block w-full rounded-md border border-cbx-border bg-bg-tertiary p-3 placeholder-cbx-muted focus:border-accent-yellow focus:outline-none focus:ring-1 focus:ring-accent-yellow sm:text-sm"
              />
            </div>
          </div>

          {error && (
            <div className="rounded-md bg-accent-red/20 p-3 text-sm text-accent-red border border-accent-red/50">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="group relative flex w-full justify-center rounded-md border border-transparent bg-accent-yellow py-3 text-sm font-bold text-bg-primary hover:bg-yellow-500 focus:outline-none focus:ring-2 focus:ring-accent-yellow focus:ring-offset-2 disabled:opacity-50 transition-colors"
          >
            {loading ? 'Logging in...' : 'Sign In'}
          </button>
        </form>
      </div>
    </div>
  );
}
