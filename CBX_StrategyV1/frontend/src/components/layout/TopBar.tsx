'use client';

import { useBotStore } from '@/store/botStore';
import { useAuthStore } from '@/store/authStore';
import { LogOut, User, Wifi, WifiOff } from 'lucide-react';
import axios from 'axios';
import { useRouter } from 'next/navigation';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export default function TopBar() {
  const { mode, connectionStatus } = useBotStore();
  const { username, logout } = useAuthStore();
  const router = useRouter();

  const handleLogout = async () => {
    try {
      await axios.post('/api/auth/logout');
      logout();
      router.push('/login');
    } catch (error) {
      console.error('Logout failed', error);
    }
  };

  return (
    <header className="h-16 bg-bg-secondary border-b border-cbx-border flex items-center justify-between px-6 shadow-sm">
      <div className="flex items-center space-x-8">
        {/* Equity & PnL */}
        <div className="flex flex-col">
          <span className="text-xs text-cbx-muted uppercase font-bold tracking-wider">Equity</span>
          <span className="text-xl font-bold text-white leading-none">$10,250.00</span>
        </div>
        
        <div className="flex flex-col">
          <span className="text-xs text-cbx-muted uppercase font-bold tracking-wider">Daily PnL</span>
          <span className="text-md font-bold text-accent-green leading-none">+1.2R</span>
        </div>

        {/* Mode Badge */}
        <div className={cn(
          "px-3 py-1 rounded-full text-xs font-black uppercase tracking-widest",
          mode === 'AUTO' ? "bg-accent-yellow text-bg-primary" : "bg-bg-tertiary text-cbx-muted"
        )}>
          {mode}
        </div>
      </div>

      <div className="flex items-center space-x-6">
        {/* WS Connection */}
        <div className="flex items-center space-x-2">
          {connectionStatus === 'connected' ? (
            <Wifi size={16} className="text-accent-green" />
          ) : (
            <WifiOff size={16} className="text-accent-red" />
          )}
          <span className={cn(
            "text-xs font-bold uppercase tracking-tighter",
            connectionStatus === 'connected' ? "text-accent-green" : "text-accent-red"
          )}>
            {connectionStatus}
          </span>
        </div>

        {/* User & Logout */}
        <div className="flex items-center space-x-4 pl-6 border-l border-cbx-border">
          <div className="flex items-center space-x-2">
            <div className="w-8 h-8 rounded-full bg-bg-tertiary flex items-center justify-center border border-cbx-border">
              <User size={16} className="text-accent-yellow" />
            </div>
            <span className="text-sm font-medium">{username || 'User'}</span>
          </div>
          <button 
            onClick={handleLogout}
            className="text-cbx-muted hover:text-accent-red transition-colors p-1"
            title="Logout"
          >
            <LogOut size={20} />
          </button>
        </div>
      </div>
    </header>
  );
}
