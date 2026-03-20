'use client';

import React, { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Zap, Activity, TrendingUp, Target, RefreshCw } from 'lucide-react';
import { useWebSocket } from '@/hooks/useWebSocket';
import { dashboardService } from '@/lib/services';
import { SignalNotification } from '@/lib/types';
import { useBotStore } from '@/store/botStore';
import TradingChart from '@/components/charts/TradingChart';
import EquityCurve from '@/components/charts/EquityCurve';
import SignalCard from '@/components/signals/SignalCard';
import clsx from 'clsx';

const SYMBOLS = ['BTCUSDC', 'BNBUSDC', 'SOLUSDC'];

export default function DashboardPage() {
  const [activeSymbol, setActiveSymbol] = useState(SYMBOLS[0]);
  const [signals, setSignals] = useState<SignalNotification[]>([]);
  const { connectionStatus } = useBotStore();
  const { on } = useWebSocket();

  // Fetch initial metrics
  const { data: metrics, refetch: refetchMetrics } = useQuery({
    queryKey: ['dashboard-metrics'],
    queryFn: dashboardService.getMetrics,
    refetchInterval: 30000, // every 30s
  });

  // Fetch initial signals
  const { data: initialSignals } = useQuery({
    queryKey: ['dashboard-signals'],
    queryFn: () => dashboardService.getSignals(10),
  });

  // Fetch equity history
  const { data: equityHistory } = useQuery({
    queryKey: ['equity-history'],
    queryFn: () => dashboardService.getEquityHistory(50),
    refetchInterval: 60000,
  });

  useEffect(() => {
    if (initialSignals) {
      setSignals(initialSignals);
    }
  }, [initialSignals]);

  // WebSocket event listeners
  useEffect(() => {
    on('signal_detected', (newSignal: SignalNotification) => {
      setSignals((prev) => [newSignal, ...prev.slice(0, 19)]);
      refetchMetrics();
    });

    on('trade_closed', () => {
      refetchMetrics();
    });
  }, [on, refetchMetrics]);

  return (
    <div className="space-y-6">
      {/* Top Header Section */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Dashboard</h1>
        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-2">
            <div className={clsx(
              "w-2.5 h-2.5 rounded-full animate-pulse",
              connectionStatus === 'connected' ? "bg-accent-green" : 
              connectionStatus === 'connecting' ? "bg-accent-yellow" : "bg-accent-red"
            )} />
            <span className="text-xs font-medium uppercase text-cbx-muted">
              WS {connectionStatus}
            </span>
          </div>
          <button 
            onClick={() => refetchMetrics()}
            className="p-1 hover:bg-bg-secondary rounded transition-colors text-cbx-muted"
          >
            <RefreshCw size={16} />
          </button>
        </div>
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard 
          label="Active Signals" 
          value={metrics?.activeSignals || 0} 
          icon={Zap} 
          color="text-accent-yellow" 
        />
        <MetricCard 
          label="Open Trades" 
          value={metrics?.openTrades || 0} 
          icon={Activity} 
          color="text-accent-green" 
        />
        <MetricCard 
          label="Win Rate" 
          value="68%" // Mocked for now, depending on API
          icon={Target} 
          color="text-accent-yellow" 
        />
        <MetricCard 
          label="Session PnL" 
          value={`+${metrics?.dailyPnl || 0}R`} 
          icon={TrendingUp} 
          color="text-accent-green" 
        />
      </div>

      {/* Main Content Area */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Charts */}
        <div className="lg:col-span-2 space-y-6">
          <div className="bg-bg-secondary border border-cbx-border rounded-lg overflow-hidden">
            <div className="flex border-b border-cbx-border">
              {SYMBOLS.map((s) => (
                <button
                  key={s}
                  onClick={() => setActiveSymbol(s)}
                  className={clsx(
                    "px-6 py-3 text-sm font-bold transition-all",
                    activeSymbol === s 
                      ? "text-accent-yellow border-b-2 border-accent-yellow bg-bg-tertiary" 
                      : "text-cbx-muted hover:text-cbx-text hover:bg-bg-tertiary/50"
                  )}
                >
                  {s.replace('USDC', '')}
                </button>
              ))}
            </div>
            <div className="p-4">
              <TradingChart symbol={activeSymbol} key={activeSymbol} />
            </div>
          </div>
          
          <EquityCurve data={equityHistory} />
        </div>

        {/* Right Column: Signal Feed */}
        <div className="bg-bg-secondary border border-cbx-border rounded-lg p-4 h-full flex flex-col">
          <h3 className="text-xs font-bold text-cbx-muted uppercase tracking-wider mb-4 flex items-center">
            <Zap size={14} className="mr-2 text-accent-yellow" />
            Signal Feed (Live)
          </h3>
          <div className="flex-1 overflow-y-auto pr-1 space-y-4 max-h-[800px] scrollbar-thin scrollbar-thumb-cbx-border">
            {signals.length === 0 ? (
              <div className="h-40 flex items-center justify-center text-cbx-muted text-sm italic">
                Scanning for compression...
              </div>
            ) : (
              signals.map((signal) => (
                <SignalCard key={signal.id} signal={signal} />
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function MetricCard({ label, value, icon: Icon, color }: any) {
  return (
    <div className="bg-bg-secondary border border-cbx-border p-4 rounded-lg">
      <div className="flex items-center justify-between mb-2">
        <span className="text-cbx-muted text-xs font-semibold uppercase">{label}</span>
        <Icon size={18} className={color} />
      </div>
      <div className="text-2xl font-bold">{value}</div>
    </div>
  );
}
