'use client';

import React, { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import { Settings, Play, Plus, RefreshCw, BarChart2, Shield, Zap, Search } from 'lucide-react';
import Toggle from '@/components/ui/Toggle';
import Modal from '@/components/ui/Modal';
import Badge from '@/components/ui/Badge';
import Skeleton from '@/components/ui/Skeleton';
import ErrorState from '@/components/ui/ErrorState';

interface SymbolConfig {
  symbol_id: string;
  symbol: string;
  exchange: string;
  is_active: boolean;
  is_in_universe: boolean;
  current_price?: number;
  strategy_config?: any;
}

const SymbolsPage = () => {
  const queryClient = useQueryClient();
  const [searchTerm, setSearchTerm] = useState('');
  const [editingSymbol, setEditingSymbol] = useState<SymbolConfig | null>(null);
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [prices, setPrices] = useState<Record<string, number>>({});

  // Fetch symbols
  const { data: symbols = [], isLoading, isError, error, refetch } = useQuery({
    queryKey: ['symbols'],
    queryFn: async () => {
      const res = await axios.get('/api/v1/symbols');
      return res.data;
    },
    retry: 1, // Fail faster for better UX
  });

  // Mutation for toggles
  const updateSymbolMutation = useMutation({
    mutationFn: async ({ id, data }: { id: string, data: any }) => {
      return axios.patch(`/api/v1/symbols/${id}`, data);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['symbols'] });
    }
  });

  // Mutation for config
  const updateConfigMutation = useMutation({
    mutationFn: async ({ id, config }: { id: string, config: any }) => {
      return axios.put(`/api/v1/symbols/${id}/config`, config);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['symbols'] });
      setEditingSymbol(null);
    }
  });

  // TODO: WS Price Updates integration
  // prices state should be updated via WebSocket from botStore or a local hook.

  const filteredSymbols = symbols.filter((s: SymbolConfig) => 
    s.symbol.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const handleToggle = (id: string, field: string, value: boolean) => {
    updateSymbolMutation.mutate({ id, data: { [field]: value } });
  };

  return (
    <div className="p-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
        <h1 className="text-2xl font-bold text-[#EAECEF]">Symbols Manager</h1>
        
        <div className="flex flex-wrap items-center gap-3">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-cbx-muted" size={16} />
            <input 
              type="text" 
              placeholder="Search symbol..." 
              className="bg-bg-secondary border border-cbx-border rounded px-9 py-1.5 text-sm focus:border-accent-yellow outline-none transition-colors w-full md:w-48"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
          
          <button 
            onClick={() => setIsAddModalOpen(true)}
            className="flex items-center gap-2 bg-accent-yellow text-bg-primary font-bold px-4 py-1.5 rounded text-sm hover:opacity-90 transition-all"
          >
            <Plus size={16} />
            <span>Add Symbol</span>
          </button>
        </div>
      </div>

      {isError ? (
        <ErrorState 
          message="Không thể kết nối với server. Vui lòng kiểm tra backend hoặc thử lại."
          onRetry={() => refetch()} 
        />
      ) : isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[1, 2, 3].map(i => (
            <Skeleton key={i} className="h-[280px] w-full rounded-lg border border-cbx-border" />
          ))}
        </div>
      ) : filteredSymbols.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 bg-bg-secondary rounded-lg border border-dashed border-cbx-border text-cbx-muted">
          <p className="text-lg">Chưa có symbol nào.</p>
          <p className="text-sm">Bấm {`'+ Add Symbol'`} để thêm.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredSymbols.map((symbol: SymbolConfig) => (
            <div key={symbol.symbol_id} className="bg-bg-secondary border border-cbx-border rounded-lg p-5 flex flex-col hover:border-cbx-muted transition-colors">
              {/* Card Header */}
              <div className="flex justify-between items-start mb-6">
                <div>
                  <h3 className="text-xl font-bold text-[#EAECEF]">{symbol.symbol}</h3>
                  <Badge variant="neutral" className="mt-1">{symbol.exchange}</Badge>
                </div>
                <div className="text-right">
                  <div className="text-[10px] text-cbx-muted uppercase">Mark Price</div>
                  <div className="text-lg font-mono font-bold text-accent-yellow">
                    {prices[symbol.symbol]?.toLocaleString() || '---.---'}
                  </div>
                </div>
              </div>

              {/* Toggles Group */}
              <div className="space-y-4 mb-8 bg-bg-primary/30 p-4 rounded-lg border border-cbx-border/50">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-cbx-text">In Universe</span>
                  <Toggle 
                    checked={symbol.is_in_universe} 
                    onChange={(v) => handleToggle(symbol.symbol_id, 'is_in_universe', v)}
                    size="sm"
                  />
                </div>
                <div className="flex items-center justify-between">
                  <div className="flex flex-col">
                    <span className="text-sm font-medium text-cbx-text">Active Scanning</span>
                    <span className="text-[10px] text-cbx-muted">Bot watches for signals</span>
                  </div>
                  <Toggle 
                    checked={symbol.is_active} 
                    onChange={(v) => handleToggle(symbol.symbol_id, 'is_active', v)}
                    size="sm"
                  />
                </div>
              </div>

              {/* Action Buttons */}
              <div className="mt-auto grid grid-cols-2 gap-3Pt-4 border-t border-cbx-border">
                <button 
                  onClick={() => setEditingSymbol(symbol)}
                  className="flex items-center justify-center gap-2 bg-bg-tertiary border border-cbx-border hover:border-accent-yellow text-cbx-text py-2 rounded text-xs font-bold transition-all"
                >
                  <Settings size={14} />
                  Edit Config
                </button>
                <button 
                  className="flex items-center justify-center gap-2 bg-bg-tertiary border border-cbx-border hover:text-accent-green hover:border-accent-green text-cbx-text py-2 rounded text-xs font-bold transition-all"
                >
                  <Play size={14} />
                  Run Backtest
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Config Modal */}
      <Modal
        open={!!editingSymbol}
        onClose={() => setEditingSymbol(null)}
        title={`Strategy Config: ${editingSymbol?.symbol}`}
      >
        {editingSymbol && (
          <form className="space-y-8" onSubmit={(e) => {
            e.preventDefault();
            const formData = new FormData(e.currentTarget);
            const config = Object.fromEntries(formData.entries());
            // Need complex nesting or flat handling depending on API
            updateConfigMutation.mutate({ id: editingSymbol.symbol_id, config });
          }}>
            {/* Compression Section */}
            <section>
              <div className="flex items-center gap-2 mb-4 text-accent-yellow font-bold uppercase text-xs">
                <BarChart2 size={16} />
                <span>Compression Parameters</span>
              </div>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                {[
                  { label: 'ATR Period', name: 'atr_period', default: 14 },
                  { label: 'Min Bars', name: 'compression_min_bars', default: 8 },
                  { label: 'Max Bars', name: 'compression_max_bars', default: 24 },
                  { label: 'ATR % Threshold', name: 'atr_percentile_threshold', default: 20 },
                  { label: 'BB Std Dev', name: 'bb_std', default: 2.0 },
                  { label: 'Min Conditions', name: 'min_conditions_met', default: 3 },
                ].map(field => (
                  <div key={field.name}>
                    <label className="text-[10px] text-cbx-muted uppercase block mb-1">{field.label}</label>
                    <input 
                      type="number" 
                      step="any"
                      className="w-full bg-bg-primary border border-cbx-border rounded px-3 py-2 text-sm outline-none focus:border-accent-yellow text-[#EAECEF]"
                      defaultValue={editingSymbol.strategy_config?.[field.name] || field.default}
                    />
                  </div>
                ))}
              </div>
            </section>

            {/* Breakout Section */}
            <section>
              <div className="flex items-center gap-2 mb-4 text-blue-400 font-bold uppercase text-xs">
                <Zap size={16} />
                <span>Breakout Parameters</span>
              </div>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                {[
                  { label: 'Body Ratio Min', name: 'breakout_body_ratio_min', default: 0.6 },
                  { label: 'Vol Ratio Min', name: 'breakout_volume_ratio_min', default: 1.3 },
                  { label: 'False Break Limit', name: 'false_break_limit', default: 2 },
                  { label: 'Dist Min ATR', name: 'breakout_distance_min_atr', default: 0.2 },
                ].map(field => (
                  <div key={field.name}>
                    <label className="text-[10px] text-cbx-muted uppercase block mb-1">{field.label}</label>
                    <input 
                      type="number" 
                      step="any"
                      className="w-full bg-bg-primary border border-cbx-border rounded px-3 py-2 text-sm outline-none focus:border-accent-yellow text-[#EAECEF]"
                      defaultValue={editingSymbol.strategy_config?.[field.name] || field.default}
                    />
                  </div>
                ))}
              </div>
            </section>

            {/* Risk & Exit Section */}
            <section>
              <div className="flex items-center gap-2 mb-4 text-accent-green font-bold uppercase text-xs">
                <Shield size={16} />
                <span>Risk & Exit Control</span>
              </div>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                {[
                  { label: 'Risk Per Trade %', name: 'risk_per_trade_pct', default: 0.25 },
                  { label: 'SL ATR Buffer', name: 'stop_loss_atr_buffer', default: 0.25 },
                  { label: 'Partial Exit R', name: 'partial_exit_r_level', default: 1.0 },
                  { label: 'Partial Exit %', name: 'partial_exit_pct', default: 50 },
                ].map(field => (
                  <div key={field.name}>
                    <label className="text-[10px] text-cbx-muted uppercase block mb-1">{field.label}</label>
                    <input 
                      type="number" 
                      step="any"
                      className="w-full bg-bg-primary border border-cbx-border rounded px-3 py-2 text-sm outline-none focus:border-accent-yellow text-[#EAECEF]"
                      defaultValue={editingSymbol.strategy_config?.[field.name] || field.default}
                    />
                  </div>
                ))}
              </div>
            </section>

            <div className="flex justify-end gap-3 pt-6 border-t border-cbx-border">
              <button 
                type="button"
                onClick={() => setEditingSymbol(null)}
                className="px-6 py-2 rounded text-sm font-bold text-cbx-muted hover:text-cbx-text transition-colors"
                disabled={updateConfigMutation.isPending}
              >
                Cancel
              </button>
              <button 
                type="submit"
                className="bg-accent-yellow text-bg-primary px-8 py-2 rounded text-sm font-bold hover:opacity-90 transition-all flex items-center gap-2"
                disabled={updateConfigMutation.isPending}
              >
                {updateConfigMutation.isPending ? <RefreshCw className="animate-spin" size={16} /> : null}
                Save Configuration
              </button>
            </div>
          </form>
        )}
      </Modal>

      {/* Add Symbol Modal Container (Placeholder) */}
      <Modal open={isAddModalOpen} onClose={() => setIsAddModalOpen(false)} title="Add New Symbol">
        <div className="py-10 text-center text-cbx-muted italic">
          Coming Soon: Binance Market Scanner integration...
        </div>
      </Modal>
    </div>
  );
};

export default SymbolsPage;
