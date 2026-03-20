'use client';

import React, { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import { Trade } from '@/lib/types';
import Badge from '@/components/ui/Badge';
import Skeleton from '@/components/ui/Skeleton';
import ErrorState from '@/components/ui/ErrorState';
import { Download, Filter, Search, TrendingUp, TrendingDown, Clock, Activity } from 'lucide-react';

const TradesPage = () => {
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<'ALL' | 'OPEN' | 'CLOSED'>('ALL');

  const { data: trades = [], isLoading, isError, refetch } = useQuery({
    queryKey: ['trades'],
    queryFn: async () => {
      const res = await axios.get('/api/v1/trades');
      return res.data;
    },
    refetchInterval: 10000 // Refetch every 10s as requested
  });

  const filteredTrades = useMemo(() => {
    return trades.filter((t: Trade) => {
      const matchesSearch = t.symbol.toLowerCase().includes(searchTerm.toLowerCase());
      const matchesStatus = statusFilter === 'ALL' || t.status === statusFilter;
      return matchesSearch && matchesStatus;
    });
  }, [trades, searchTerm, statusFilter]);

  // Aggregate Stats
  const stats = useMemo(() => {
    if (!trades.length) return { winRate: 0, avgWinR: 0, avgLossR: 0, profitFactor: 0, totalR: 0 };
    
    const closedTrades = trades.filter((t: Trade) => t.status === 'CLOSED');
    if (!closedTrades.length) return { winRate: 0, avgWinR: 0, avgLossR: 0, profitFactor: 0, totalR: 0 };

    const wins = closedTrades.filter((t: Trade) => t.total_pnl_r > 0);
    const losses = closedTrades.filter((t: Trade) => t.total_pnl_r <= 0);

    const winRate = (wins.length / closedTrades.length) * 100;
    const avgWinR = wins.reduce((acc: number, t: Trade) => acc + t.total_pnl_r, 0) / (wins.length || 1);
    const avgLossR = losses.reduce((acc: number, t: Trade) => acc + Math.abs(t.total_pnl_r), 0) / (losses.length || 1);
    
    const totalWinR = wins.reduce((acc: number, t: Trade) => acc + t.total_pnl_r, 0);
    const totalLossR = losses.reduce((acc: number, t: Trade) => acc + Math.abs(t.total_pnl_r), 0);
    const profitFactor = totalWinR / (totalLossR || 1);
    const totalR = closedTrades.reduce((acc: number, t: Trade) => acc + t.total_pnl_r, 0);

    return { winRate, avgWinR, avgLossR, profitFactor, totalR };
  }, [trades]);

  const exportToCSV = () => {
    if (!trades.length) return;
    
    const headers = ['ID', 'Time', 'Symbol', 'Side', 'Entry', 'Exit', 'PnL(R)', 'PnL(USD)', 'Status', 'Reason'];
    const rows = trades.map((t: Trade) => [
      t.id,
      new Date(t.entry_at).toLocaleString(),
      t.symbol,
      t.side,
      t.entry_price,
      t.exit_price || 'N/A',
      t.total_pnl_r.toFixed(2),
      t.pnl_usd.toFixed(2),
      t.status,
      t.reason || ''
    ]);

    const csvContent = [headers, ...rows].map(e => e.join(',')).join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.setAttribute('href', url);
    link.setAttribute('download', `cbx_trades_${new Date().toISOString().split('T')[0]}.csv`);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="p-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
        <h1 className="text-2xl font-bold text-[#EAECEF]">Trade History</h1>
        
        <div className="flex flex-wrap items-center gap-3">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-cbx-muted" size={16} />
            <input 
              type="text" 
              placeholder="Filter symbol..." 
              className="bg-bg-secondary border border-cbx-border rounded px-9 py-1.5 text-sm focus:border-accent-yellow outline-none transition-colors w-full md:w-48"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
          
          <button 
            onClick={exportToCSV}
            className="flex items-center gap-2 bg-bg-secondary border border-cbx-border hover:border-accent-yellow px-4 py-1.5 rounded text-sm text-cbx-text transition-all"
          >
            <Download size={16} />
            <span>Export CSV</span>
          </button>
        </div>
      </div>

      {/* Stats Dashboard */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-4 mb-8">
        <div className="bg-bg-secondary border border-cbx-border p-4 rounded-lg">
          <div className="text-[10px] text-cbx-muted uppercase mb-1 flex items-center gap-1">
            <Activity size={10} /> Win Rate
          </div>
          <div className="text-xl font-bold text-accent-green">{stats.winRate.toFixed(1)}%</div>
        </div>
        <div className="bg-bg-secondary border border-cbx-border p-4 rounded-lg">
          <div className="text-[10px] text-cbx-muted uppercase mb-1 flex items-center gap-1">
            <TrendingUp size={10} /> Avg Win R
          </div>
          <div className="text-xl font-bold text-accent-green">+{stats.avgWinR.toFixed(2)}R</div>
        </div>
        <div className="bg-bg-secondary border border-cbx-border p-4 rounded-lg">
          <div className="text-[10px] text-cbx-muted uppercase mb-1 flex items-center gap-1">
            <TrendingDown size={10} /> Avg Loss R
          </div>
          <div className="text-xl font-bold text-accent-red">-{stats.avgLossR.toFixed(2)}R</div>
        </div>
        <div className="bg-bg-secondary border border-cbx-border p-4 rounded-lg">
          <div className="text-[10px] text-cbx-muted uppercase mb-1 flex items-center gap-1">
            <TrendingUp size={10} /> Profit Factor
          </div>
          <div className="text-xl font-bold text-accent-yellow">{stats.profitFactor.toFixed(2)}</div>
        </div>
        <div className="bg-bg-secondary border border-cbx-border p-4 rounded-lg">
          <div className="text-[10px] text-cbx-muted uppercase mb-1 flex items-center gap-1">
            <Activity size={10} /> Total Net R
          </div>
          <div className={`text-xl font-bold ${stats.totalR >= 0 ? 'text-accent-green' : 'text-accent-red'}`}>
            {stats.totalR >= 0 ? '+' : ''}{stats.totalR.toFixed(2)}R
          </div>
        </div>
      </div>

      {/* Trades Table */}
      <div className="bg-bg-secondary border border-cbx-border rounded-lg overflow-hidden">
        <div className="overflow-x-auto custom-scrollbar">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-bg-primary text-cbx-muted text-[10px] uppercase tracking-wider border-b border-cbx-border">
                <th className="px-5 py-4 font-bold">Time</th>
                <th className="px-5 py-4 font-bold">Symbol</th>
                <th className="px-5 py-4 font-bold">Side</th>
                <th className="px-5 py-4 font-bold text-right">Entry</th>
                <th className="px-5 py-4 font-bold text-right">Stop</th>
                <th className="px-5 py-4 font-bold text-right">Exit</th>
                <th className="px-5 py-4 font-bold text-right">PnL(R)</th>
                <th className="px-5 py-4 font-bold">Reason</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-cbx-border">
              {isLoading ? (
                Array(5).fill(0).map((_, i) => (
                  <tr key={i}>
                    <td colSpan={8} className="px-5 py-4">
                       <Skeleton className="h-4 w-full" />
                    </td>
                  </tr>
                ))
              ) : isError ? (
                <tr>
                   <td colSpan={8} className="p-4">
                      <ErrorState onRetry={refetch} />
                   </td>
                </tr>
              ) : filteredTrades.length > 0 ? (
                filteredTrades.map((trade: Trade) => {
                  const isOpen = trade.status === 'OPEN';
                  const isWin = trade.status === 'CLOSED' && trade.total_pnl_r > 0;
                  const isLoss = trade.status === 'CLOSED' && trade.total_pnl_r < 0;
                  
                  // Color coding based on requirements
                  const rowColorClass = isOpen 
                    ? 'text-accent-yellow' 
                    : isWin 
                      ? 'text-accent-green' 
                      : isLoss ? 'text-accent-red' : 'text-cbx-text';

                  return (
                    <tr key={trade.id} className={`${rowColorClass} hover:bg-bg-tertiary transition-colors group`}>
                      <td className="px-5 py-4 whitespace-nowrap text-xs">
                        <div className="flex flex-col">
                          <span>{new Date(trade.entry_at).toLocaleDateString()}</span>
                          <span className="text-[10px] opacity-70 italic">{new Date(trade.entry_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                        </div>
                      </td>
                      <td className="px-5 py-4 font-bold">{trade.symbol}</td>
                      <td className="px-5 py-4">
                        <Badge variant={trade.side === 'LONG' ? 'success' : 'danger'}>{trade.side}</Badge>
                      </td>
                      <td className="px-5 py-4 font-mono text-right text-xs group-hover:text-cbx-text transition-colors">
                        {trade.entry_price.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                      </td>
                      <td className="px-5 py-4 font-mono text-right text-xs text-accent-red/70 group-hover:text-accent-red transition-colors">
                        {trade.stop_loss.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                      </td>
                      <td className="px-5 py-4 font-mono text-right text-xs text-accent-green/70 group-hover:text-accent-green transition-colors">
                        {trade.exit_price ? trade.exit_price.toLocaleString(undefined, { minimumFractionDigits: 2 }) : '-'}
                      </td>
                      <td className="px-5 py-4 font-mono font-bold text-right text-xs">
                        {isOpen ? '-' : `${trade.total_pnl_r > 0 ? '+' : ''}${trade.total_pnl_r.toFixed(2)}R`}
                      </td>
                      <td className="px-5 py-4 text-xs whitespace-nowrap overflow-hidden text-ellipsis max-w-[150px]">
                        {isOpen ? <span className="italic opacity-60">In Progress...</span> : (trade.reason || 'Manual Exit')}
                      </td>
                    </tr>
                  );
                })
              ) : (
                <tr>
                  <td colSpan={8} className="px-5 py-20 text-center text-cbx-muted">
                    No trades found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default TradesPage;
