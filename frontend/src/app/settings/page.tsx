'use client';

import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import { useBotStore } from '@/store/botStore';
import { Shield, Bell, Globe, Zap, CheckCircle2, AlertCircle, RefreshCw, Smartphone } from 'lucide-react';
import Toggle from '@/components/ui/Toggle';
import Badge from '@/components/ui/Badge';
import Skeleton from '@/components/ui/Skeleton';
import ErrorState from '@/components/ui/ErrorState';

const SettingsPage = () => {
  const queryClient = useQueryClient();
  const { mode, setMode, connectionStatus } = useBotStore();
  const [pinging, setPinging] = useState(false);
  const [latency, setLatency] = useState<number | null>(null);

  // Fetch settings
  const { data: settings = {}, isLoading, isError, refetch } = useQuery({
    queryKey: ['settings'],
    queryFn: async () => {
      const res = await axios.get('/api/v1/settings');
      return res.data;
    }
  });

  // Mutation for Mode
  const modeMutation = useMutation({
    mutationFn: async (newMode: 'AUTO' | 'MANUAL') => {
      return axios.patch('/api/v1/settings/mode', { mode: newMode });
    },
    onSuccess: (_, newMode) => {
      setMode(newMode); // Update Zustand store as requested
      queryClient.invalidateQueries({ queryKey: ['settings'] });
    }
  });

  // Mutation for general settings
  const updateSettingsMutation = useMutation({
    mutationFn: async ({ section, data }: { section: string, data: any }) => {
      return axios.patch(`/api/v1/settings/${section}`, data);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['settings'] });
    }
  });

  const handlePing = async () => {
    setPinging(true);
    const start = Date.now();
    try {
      await axios.get('/health/binance');
      setLatency(Date.now() - start);
    } catch (e) {
      setLatency(null);
    } finally {
      setPinging(false);
    }
  };

  if (isLoading) {
    return (
      <div className="p-6 max-w-4xl mx-auto space-y-8">
        <Skeleton className="h-8 w-48 mb-8" />
        <Skeleton className="h-40 w-full" />
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <Skeleton className="h-64 w-full" />
          <Skeleton className="h-64 w-full" />
        </div>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="p-6 max-w-4xl mx-auto">
        <ErrorState onRetry={refetch} />
      </div>
    );
  }

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold text-[#EAECEF] mb-8">System Settings</h1>

      <div className="space-y-6">
        {/* Section 1: Bot Mode */}
        <div className="bg-bg-secondary border border-cbx-border rounded-xl p-6 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <div className="bg-accent-yellow/10 p-2 rounded-lg text-accent-yellow">
                <Zap size={24} />
              </div>
              <div>
                <h2 className="text-lg font-bold text-[#EAECEF]">Execution Mode</h2>
                <p className="text-sm text-cbx-muted">Toggle between automatic and manual trading confirm</p>
              </div>
            </div>
            <div className="flex items-center gap-4">
              <span className={`text-sm font-bold ${mode === 'AUTO' ? 'text-accent-yellow' : 'text-cbx-muted'}`}>
                {mode === 'AUTO' ? 'AUTOMATIC' : 'MANUAL'}
              </span>
              <Toggle 
                checked={mode === 'AUTO'} 
                onChange={(v) => modeMutation.mutate(v ? 'AUTO' : 'MANUAL')}
              />
            </div>
          </div>
          <div className="mt-4 p-3 bg-bg-primary/50 rounded border border-cbx-border/30 text-xs text-cbx-muted">
            {mode === 'AUTO' 
              ? "🟢 AUTO: Bot will automatically place orders on Binance when high-quality signals are detected."
              : "⚪ MANUAL: Bot will generate signals but wait for user confirmation via Dashboard or Telegram."}
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Section 2: Risk Management */}
          <div className="bg-bg-secondary border border-cbx-border rounded-xl p-6 flex flex-col">
            <div className="flex items-center gap-2 mb-6 text-accent-green font-bold">
              <Shield size={20} />
              <span>Risk Management</span>
            </div>
            <div className="space-y-4 flex-1">
              <div>
                <label className="text-xs text-cbx-muted block mb-1">Risk per trade (%)</label>
                <input 
                  type="number" 
                  className="w-full bg-bg-primary border border-cbx-border rounded px-3 py-2 text-sm text-cbx-text outline-none focus:border-accent-green transition-all"
                  defaultValue={settings.risk?.per_trade_pct || 0.25}
                />
              </div>
              <div>
                <label className="text-xs text-cbx-muted block mb-1">Max positions portfolio</label>
                <input 
                  type="number" 
                  className="w-full bg-bg-primary border border-cbx-border rounded px-3 py-2 text-sm text-cbx-text outline-none focus:border-accent-green transition-all"
                  defaultValue={settings.risk?.max_positions || 2}
                />
              </div>
              <div>
                <label className="text-xs text-cbx-muted block mb-1">Daily stop loss (R)</label>
                <input 
                  type="number" 
                  className="w-full bg-bg-primary border border-cbx-border rounded px-3 py-2 text-sm text-cbx-text outline-none focus:border-accent-red transition-all"
                  defaultValue={settings.risk?.daily_stop_r || -2.0}
                />
              </div>
            </div>
            <button className="mt-6 w-full bg-bg-tertiary border border-cbx-border hover:border-accent-green text-cbx-text py-2 rounded text-sm font-bold transition-all">
              Save Risk Settings
            </button>
          </div>

          {/* Section 3: Notifications */}
          <div className="bg-bg-secondary border border-cbx-border rounded-xl p-6">
            <div className="flex items-center gap-2 mb-6 text-blue-400 font-bold">
              <Bell size={20} />
              <span>Notifications</span>
            </div>
            <div className="space-y-5">
              {[
                { label: 'Notify on signal', key: 'notify_signal' },
                { label: 'Notify on entry', key: 'notify_entry' },
                { label: 'Notify on exit', key: 'notify_exit' },
                { label: 'Daily summary report', key: 'daily_summary' },
              ].map(item => (
                <div key={item.key} className="flex items-center justify-between">
                  <span className="text-sm text-cbx-text">{item.label}</span>
                  <Toggle size="sm" checked={settings.notifications?.[item.key] ?? true} onChange={() => {}} />
                </div>
              ))}
            </div>
            <div className="mt-8 pt-6 border-t border-cbx-border flex items-center justify-between">
              <div className="flex items-center gap-2 text-xs text-cbx-muted">
                <Smartphone size={14} /> Telegram Bot Connected
              </div>
              <Badge variant="success">Active</Badge>
            </div>
          </div>
        </div>

        {/* Section 4: Connection Status */}
        <div className="bg-bg-secondary border border-cbx-border rounded-xl p-6">
          <div className="flex items-center gap-2 mb-6 text-purple-400 font-bold">
            <Globe size={20} />
            <span>Connection & Health</span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="bg-bg-primary/50 p-4 rounded-lg flex items-center justify-between">
              <div>
                <div className="text-[10px] text-cbx-muted uppercase">Binance API</div>
                <div className="flex items-center gap-1.5 mt-1 font-bold">
                  <CheckCircle2 size={14} className="text-accent-green" /> Connected
                </div>
              </div>
              <button 
                onClick={handlePing}
                disabled={pinging}
                className="p-2 hover:bg-bg-tertiary rounded-full transition-colors text-cbx-muted hover:text-accent-yellow"
              >
                <RefreshCw size={16} className={pinging ? 'animate-spin' : ''} />
              </button>
            </div>
            <div className="bg-bg-primary/50 p-4 rounded-lg">
              <div className="text-[10px] text-cbx-muted uppercase">Latency</div>
              <div className="flex items-center gap-1.5 mt-1 font-bold text-[#EAECEF]">
                {latency ? `${latency}ms` : '--- ms'}
              </div>
            </div>
            <div className="bg-bg-primary/50 p-4 rounded-lg flex items-center justify-between">
              <div>
                <div className="text-[10px] text-cbx-muted uppercase">WebSocket</div>
                <div className="flex items-center gap-1.5 mt-1 font-bold">
                  {connectionStatus === 'connected' ? (
                    <Badge variant="success">Online</Badge>
                  ) : (
                    <Badge variant="danger">Offline</Badge>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SettingsPage;
