'use client';

import { useEffect, useState } from 'react';
import axios from 'axios';
import { useAuthStore } from '@/store/authStore';

export default function AuthProvider({ children }: { children: React.ReactNode }) {
  const [loading, setLoading] = useState(true);
  const setAuth = useAuthStore((state) => state.setAuth);

  useEffect(() => {
    const checkSession = async () => {
      try {
        const response = await axios.get('/api/auth/session');
        if (response.data.authenticated) {
          setAuth(true, response.data.user.username);
        } else {
          setAuth(false, null);
        }
      } catch (error) {
        setAuth(false, null);
      } finally {
        setLoading(false);
      }
    };

    checkSession();
  }, [setAuth]);

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-bg-primary text-accent-yellow">
        <div className="h-12 w-12 animate-spin rounded-full border-4 border-accent-yellow border-t-transparent"></div>
      </div>
    );
  }

  return <>{children}</>;
}
