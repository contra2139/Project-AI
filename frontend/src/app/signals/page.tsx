'use client';

import React, { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import { SignalNotification } from '@/lib/types';
import SignalCard from '@/components/signals/SignalCard';
import Modal from '@/components/ui/Modal';
import Badge from '@/components/ui/Badge';
import Skeleton from '@/components/ui/Skeleton';
import ErrorState from '@/components/ui/ErrorState';
import { Search, Filter, Layers, Brain, BarChart3 } from 'lucide-react';

const SignalsPage = () => {
  const [selectedSignal, setSelectedSignal] = useState<SignalNotification | null>(null);
  const [activeTab, setActiveTab] = useState<'chain' | 'chart' | 'ai'>('chain');
  const [searchTerm, setSearchTerm] = useState('');
  const [sideFilter, setSideFilter] = useState<'ALL' | 'LONG' | 'SHORT'>('ALL');

  // Fetch initial signals
  const { data: signals = [], isLoading, isError, refetch } = useQuery({
    queryKey: ['signals'],
    queryFn: async () => {
      const res = await axios.get('/api/v1/signals?limit=50');
      return res.data;
    }
  });

  // TODO: WS Integration (Already handled in TopBar/Dashboard via botStore but we prepend here if needed)
  // Actually, for a dedicated page, we might want to listen specifically or use the store's latest signal.

  const filteredSignals = signals.filter((s: SignalNotification) => {
    const matchesSearch = s.symbol.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesSide = sideFilter === 'ALL' || s.side === sideFilter;
    return matchesSearch && matchesSide;
  });

  return (
    <div className="p-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
        <h1 className="text-2xl font-bold text-[#EAECEF]">Signals</h1>
        
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
          
          <div className="flex bg-bg-secondary border border-cbx-border rounded p-1">
            {['ALL', 'LONG', 'SHORT'].map((side) => (
              <button
                key={side}
                onClick={() => setSideFilter(side as any)}
                className={`px-3 py-1 text-xs rounded transition-all ${sideFilter === side ? 'bg-accent-yellow text-bg-primary font-bold' : 'text-cbx-muted hover:text-cbx-text'}`}
              >
                {side}
              </button>
            ))}
          </div>
        </div>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {[1, 2, 3, 4].map(i => (
            <Skeleton key={i} className="h-48 w-full rounded-lg" />
          ))}
        </div>
      ) : isError ? (
        <ErrorState onRetry={refetch} />
      ) : filteredSignals.length > 0 ? (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {filteredSignals.map((signal: SignalNotification) => (
            <SignalCard 
              key={signal.id} 
              signal={signal} 
              onClick={(s) => {
                setSelectedSignal(s);
                setActiveTab('chain');
              }}
            />
          ))}
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center py-20 text-cbx-muted">
          <Filter size={48} className="mb-4 opacity-20" />
          <p>No signals found matching your filters.</p>
        </div>
      )}

      {/* Signal Detail Modal */}
      <Modal 
        open={!!selectedSignal} 
        onClose={() => setSelectedSignal(null)}
        title={selectedSignal ? `${selectedSignal.symbol} ${selectedSignal.side} Signal` : ''}
      >
        {selectedSignal && (
          <div className="flex flex-col gap-6">
            {/* Tabs */}
            <div className="flex border-b border-cbx-border">
              {[
                { id: 'chain', label: 'Event Chain', icon: Layers },
                { id: 'chart', label: 'Chart', icon: BarChart3 },
                { id: 'ai', label: 'AI Analysis', icon: Brain },
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id as any)}
                  className={`flex items-center gap-2 px-6 py-3 text-sm transition-colors border-b-2 ${activeTab === tab.id ? 'border-accent-yellow text-accent-yellow' : 'border-transparent text-cbx-muted hover:text-cbx-text'}`}
                >
                  <tab.icon size={16} />
                  {tab.label}
                </button>
              ))}
            </div>

            {/* Tab Content */}
            <div className="min-h-[300px]">
              {activeTab === 'chain' && (
                <div className="space-y-6">
                  <div className="relative border-l-2 border-cbx-border ml-2 pl-6 space-y-8">
                    {[
                      { stage: 'Compression', metrics: selectedSignal.metrics?.compression },
                      { stage: 'Breakout', metrics: selectedSignal.metrics?.breakout },
                      { stage: 'Expansion', metrics: selectedSignal.metrics?.expansion },
                    ].map((item, idx) => (
                      <div key={idx} className="relative">
                        <div className={`absolute -left-[31px] top-0 w-4 h-4 rounded-full border-4 border-bg-secondary ${item.metrics ? 'bg-accent-green' : 'bg-cbx-muted'}`} />
                        <div>
                          <h4 className="font-bold text-[#EAECEF] mb-2">{item.stage}</h4>
                          {item.metrics ? (
                            <div className="grid grid-cols-2 gap-4 bg-bg-primary/50 p-3 rounded border border-cbx-border/30">
                              {Object.entries(item.metrics).map(([key, val]) => (
                                <div key={key}>
                                  <div className="text-[10px] text-cbx-muted uppercase">{key.replace(/_/g, ' ')}</div>
                                  <div className="text-sm font-mono text-accent-yellow">{val as any}</div>
                                </div>
                              ))}
                            </div>
                          ) : (
                            <p className="text-xs text-cbx-muted italic">Waiting for stage completion...</p>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {activeTab === 'chart' && (
                <div className="flex flex-col items-center justify-center border border-dashed border-cbx-border rounded-lg h-[300px] bg-bg-primary">
                  <BarChart3 size={48} className="text-cbx-muted mb-4 opacity-20" />
                  <p className="text-sm text-cbx-muted text-center max-w-xs">
                    TradingChart visualization for snapshot at {new Date(selectedSignal.timestamp).toLocaleTimeString()}
                  </p>
                  <Badge variant="neutral" className="mt-4">TradingView Integration Point</Badge>
                </div>
              )}

              {activeTab === 'ai' && (
                <div className="bg-bg-primary/50 p-6 rounded-lg border border-cbx-border/30 min-h-[200px]">
                  <div className="flex items-center gap-2 mb-4 text-accent-yellow font-medium">
                    <Brain size={18} />
                    <span>AI Insights</span>
                  </div>
                  <p className="text-cbx-text leading-relaxed whitespace-pre-wrap">
                    {selectedSignal.ai_comment || "Chưa có phân tích AI cho signal này."}
                  </p>
                </div>
              )}
            </div>

            {/* Footer Summary */}
            <div className="bg-bg-tertiary p-4 rounded-lg flex items-center justify-between">
              <div>
                <span className="text-xs text-cbx-muted">Quality Score</span>
                <div className="flex items-center gap-2">
                  <span className="text-xl font-bold text-accent-yellow">{selectedSignal.quality_score}/10</span>
                  <Badge variant={selectedSignal.quality_score > 7 ? 'success' : 'warning'}>
                    {selectedSignal.quality_score > 7 ? 'High' : 'Medium'}
                  </Badge>
                </div>
              </div>
              <button 
                onClick={() => setSelectedSignal(null)}
                className="bg-accent-yellow text-bg-primary font-bold px-6 py-2 rounded hover:opacity-90 transition-opacity"
              >
                Close Details
              </button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
};

export default SignalsPage;
