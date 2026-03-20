'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { 
  LayoutDashboard, 
  Zap, 
  Repeat, 
  Coins, 
  History, 
  Settings,
  Circle
} from 'lucide-react';
import { useBotStore } from '@/store/botStore';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

const navItems = [
  { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
  { name: 'Signals', href: '/signals', icon: Zap },
  { name: 'Trades', href: '/trades', icon: Repeat },
  { name: 'Symbols', href: '/symbols', icon: Coins },
  { name: 'Backtest', href: '/backtest', icon: History },
  { name: 'Settings', href: '/settings', icon: Settings },
];

export default function Sidebar() {
  const pathname = usePathname();
  const connectionStatus = useBotStore((state) => state.connectionStatus);

  return (
    <div className="flex flex-col h-screen w-64 bg-bg-secondary border-r border-cbx-border">
      {/* Logo */}
      <div className="flex items-center justify-center h-20 border-b border-cbx-border">
        <span className="text-3xl font-black text-accent-yellow tracking-tighter">CBX</span>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto py-4">
        <ul className="space-y-1 px-2">
          {navItems.map((item) => {
            const isActive = pathname.startsWith(item.href);
            return (
              <li key={item.name}>
                <Link
                  href={item.href}
                  className={cn(
                    "flex items-center px-4 py-3 text-sm font-medium rounded-md transition-colors",
                    isActive 
                      ? "text-accent-yellow bg-bg-tertiary" 
                      : "text-cbx-muted hover:text-cbx-text hover:bg-bg-tertiary/50"
                  )}
                >
                  <item.icon className="mr-3 h-5 w-5" />
                  {item.name}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>

      {/* Bot Status */}
      <div className="p-4 border-t border-cbx-border">
        <div className="flex items-center space-x-3 px-2">
          <Circle 
            size={10} 
            className={cn(
              "fill-current",
              connectionStatus === 'connected' ? "text-accent-green" : "text-accent-red"
            )} 
          />
          <span className="text-sm font-medium text-cbx-muted">
            Bot: {connectionStatus.charAt(0).toUpperCase() + connectionStatus.slice(1)}
          </span>
        </div>
      </div>
    </div>
  );
}
