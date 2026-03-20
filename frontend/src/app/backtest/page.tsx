'use client';

import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import { 
  Play, 
  History, 
  BarChart3, 
  TrendingUp, 
  Activity, 
  AlertTriangle,
  Calendar,
  Layers,
  Bot
} from 'lucide-react';
import { useToastStore } from '@/store/toastStore';
import Skeleton from '@/components/ui/Skeleton';
import Badge from '@/components/ui/Badge';
import RunProgress from '@/components/backtest/RunProgress';
import TradeDistributionChart from '@/components/backtest/TradeDistributionChart';
import EquityCurve from '@/components/charts/EquityCurve';

interface BacktestRun {
  run_id: string;
  name: string;
  symbol: string;
  status: 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED';
  created_at: string;
  metrics?: {
    total_trades: number;
    win_rate: number;
    total_pnl_r: number;
    max_drawdown: number;
  };
  trades?: any[];
  equity_history?: any[];
}

const BacktestPage = () => {
  const queryClient = useQueryClient();
  const { addToast } = useToastStore();
  
  // State
  const [activeRunId, setActiveRunId] = useState<string | null>(null);
  const [selectedRun, setSelectedRun] = useState<BacktestRun | null>(null);
  const [activeTab, setActiveTab] = useState<'equity' | 'distribution' | 'comparison' | 'ai'>('equity');
  
  // Form State
  const [formData, setFormData] = useState({
    symbol: 'BTCUSDC',
    startDate: '',
    endDate: '',
    entryModel: 'BOTH',
    side: 'BOTH',
    name: ''
  });
  
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [warnings, setWarnings] = useState<Record<string, string>>({});

  // Fetch History
  const { data: history = [], isLoading: isHistoryLoading } = useQuery({
    queryKey: ['backtest-history'],
    queryFn: async () => {
      const res = await axios.get('/api/v1/runs');
      return res.data;
    }
  });

  // Symbols for dropdown
  const { data: symbols = [] } = useQuery({
    queryKey: ['symbols'],
    queryFn: async () => {
      const res = await axios.get('/api/v1/symbols');
      return res.data;
    }
  });

  // Run Mutation
  const runMutation = useMutation({
    mutationFn: async (data: any) => {
      const res = await axios.post('/api/v1/runs', data);
      return res.data;
    },
    onSuccess: (data) => {
      setActiveRunId(data.run_id);
      addToast('Backtest đã bắt đầu', 'success');
      queryClient.invalidateQueries({ queryKey: ['backtest-history'] });
    },
    onError: () => {
      addToast('Không thể bắt đầu backtest', 'error');
    }
  });

  // Form Validation
  const validateForm = () => {
    const newErrors: Record<string, string> = {};
    const newWarnings: Record<string, string> = {};
    const today = new Date().toISOString().split('T')[0];

    if (!formData.startDate) newErrors.startDate = 'Vui lòng chọn ngày bắt đầu';
    if (!formData.endDate) newErrors.endDate = 'Vui lòng chọn ngày kết thúc';
    
    if (formData.startDate && formData.endDate) {
      if (formData.endDate <= formData.startDate) {
        newErrors.endDate = 'Ngày kết thúc phải sau ngày bắt đầu';
      }
      
      const start = new Date(formData.startDate);
      const end = new Date(formData.endDate);
      const diffTime = Math.abs(end.getTime() - start.getTime());
      const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
      
      if (diffDays < 30) {
        newWarnings.endDate = 'Khoảng cách nên >= 30 ngày để có kết quả chính xác hơn';
      }
    }

    if (formData.startDate > today) newErrors.startDate = 'Không được chọn ngày tương lai';
    if (formData.endDate > today) newErrors.endDate = 'Không được chọn ngày tương lai';
    if (!formData.name) newErrors.name = 'Vui lòng đặt tên cho lượt chạy';

    setErrors(newErrors);
    setWarnings(newWarnings);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (validateForm()) {
      runMutation.mutate(formData);
    }
  };

  const handleSelectRun = async (run: BacktestRun) => {
    if (run.status === 'COMPLETED') {
        const res = await axios.get(`/api/v1/runs/${run.run_id}`);
        setSelectedRun(res.data);
    } else {
        setSelectedRun(run);
    }
  };

  return (
    <div className="p-6 max-w-[1600px] mx-auto">
      <div className="flex items-center gap-3 mb-8">
        <div className="bg-accent-yellow/10 p-2 rounded-lg">
          <Activity className="text-accent-yellow w-6 h-6" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-[#EAECEF]">Backtest Dashboard</h1>
          <p className="text-cbx-muted text-sm">Phân tích chiến lược trên dữ liệu quá khứ</p>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-12 gap-6">
        {/* Left Column: Form & History */}
        <div className="xl:col-span-4 space-y-6">
          {/* Form */}
          <div className="bg-bg-secondary border border-cbx-border rounded-lg p-6">
            <h3 className="text-sm font-bold text-cbx-muted uppercase mb-6 flex items-center gap-2">
              <Layers size={16} />
              Cấu hình Backtest
            </h3>
            
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="text-xs text-cbx-muted uppercase mb-1.5 block">Trading Symbol</label>
                <select 
                  className="w-full bg-bg-primary border border-cbx-border rounded px-3 py-2 text-sm text-cbx-text outline-none focus:border-accent-yellow"
                  value={formData.symbol}
                  onChange={(e) => setFormData({...formData, symbol: e.target.value})}
                >
                  {symbols.map((s: any) => (
                    <option key={s.symbol} value={s.symbol}>{s.symbol}</option>
                  ))}
                  {symbols.length === 0 && <option value="BTCUSDC">BTCUSDC</option>}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-xs text-cbx-muted uppercase mb-1.5 block">Start Date</label>
                  <input 
                    type="date" 
                    className={`w-full bg-bg-primary border rounded px-3 py-2 text-sm text-cbx-text outline-none focus:border-accent-yellow ${errors.startDate ? 'border-accent-red' : 'border-cbx-border'}`}
                    value={formData.startDate}
                    onChange={(e) => setFormData({...formData, startDate: e.target.value})}
                  />
                  {errors.startDate && <p className="text-[10px] text-accent-red mt-1">{errors.startDate}</p>}
                </div>
                <div>
                  <label className="text-xs text-cbx-muted uppercase mb-1.5 block">End Date</label>
                  <input 
                    type="date" 
                    className={`w-full bg-bg-primary border rounded px-3 py-2 text-sm text-cbx-text outline-none focus:border-accent-yellow ${errors.endDate ? 'border-accent-red' : 'border-cbx-border'}`}
                    value={formData.endDate}
                    onChange={(e) => setFormData({...formData, endDate: e.target.value})}
                  />
                  {errors.endDate && <p className="text-[10px] text-accent-red mt-1">{errors.endDate}</p>}
                  {warnings.endDate && !errors.endDate && (
                    <p className="text-[10px] text-accent-yellow mt-1 flex items-center gap-1">
                      <AlertTriangle size={10} /> {warnings.endDate}
                    </p>
                  )}
                </div>
              </div>

              <div>
                <label className="text-xs text-cbx-muted uppercase mb-1.5 block">Entry Model</label>
                <div className="grid grid-cols-3 gap-2">
                  {['FOLLOW_THROUGH', 'RETEST', 'BOTH'].map(m => (
                    <button
                      key={m}
                      type="button"
                      onClick={() => setFormData({...formData, entryModel: m})}
                      className={`py-2 text-[10px] font-bold rounded border transition-all ${formData.entryModel === m ? 'bg-accent-yellow text-bg-primary border-accent-yellow' : 'bg-bg-primary border-cbx-border text-cbx-muted hover:border-cbx-muted'}`}
                    >
                      {m.replace('_', ' ')}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="text-xs text-cbx-muted uppercase mb-1.5 block">Run Name</label>
                <input 
                  type="text" 
                  placeholder="e.g. BTC Breakout Test V1"
                  className={`w-full bg-bg-primary border rounded px-3 py-2 text-sm text-cbx-text outline-none focus:border-accent-yellow ${errors.name ? 'border-accent-red' : 'border-cbx-border'}`}
                  value={formData.name}
                  onChange={(e) => setFormData({...formData, name: e.target.value})}
                />
                {errors.name && <p className="text-[10px] text-accent-red mt-1">{errors.name}</p>}
              </div>

              <button 
                type="submit"
                disabled={runMutation.isPending || !!activeRunId}
                className="w-full bg-accent-yellow text-bg-primary font-bold py-3 rounded mt-4 hover:opacity-90 transition-all flex items-center justify-center gap-2 disabled:opacity-50"
              >
                <Play size={18} fill="currentColor" />
                <span>RUN BACKTEST</span>
              </button>
            </form>
          </div>

          {/* History */}
          <div className="bg-bg-secondary border border-cbx-border rounded-lg overflow-hidden flex flex-col min-h-[400px]">
            <div className="p-4 border-b border-cbx-border bg-bg-primary/30 flex items-center justify-between">
              <h3 className="text-xs font-bold text-cbx-muted uppercase flex items-center gap-2">
                <History size={14} />
                Recent Runs
              </h3>
            </div>
            
            <div className="flex-1 overflow-y-auto">
              {isHistoryLoading ? (
                <div className="p-4 space-y-2">
                  {[1,2,3,4,5].map(i => <Skeleton key={i} className="h-12 w-full" />)}
                </div>
              ) : history.length === 0 ? (
                <div className="h-full flex flex-col items-center justify-center text-cbx-muted py-10 italic text-sm">
                  Chưa có backtest nào.
                </div>
              ) : (
                <table className="w-full text-left text-xs">
                  <thead>
                    <tr className="text-cbx-muted border-b border-cbx-border">
                      <th className="px-4 py-3 font-medium">Name</th>
                      <th className="px-4 py-3 font-medium">Symbol</th>
                      <th className="px-4 py-3 font-medium">PnL(R)</th>
                      <th className="px-4 py-3 font-medium">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {history.map((run: BacktestRun) => (
                      <tr 
                        key={run.run_id} 
                        onClick={() => handleSelectRun(run)}
                        className={`border-b border-cbx-border/30 hover:bg-white/5 cursor-pointer transition-colors ${selectedRun?.run_id === run.run_id ? 'bg-accent-yellow/5' : ''}`}
                      >
                        <td className="px-4 py-3">
                          <div className="font-bold text-[#EAECEF] truncate max-w-[120px]">{run.name}</div>
                          <div className="text-[10px] text-cbx-muted">{new Date(run.created_at).toLocaleDateString()}</div>
                        </td>
                        <td className="px-4 py-3 text-cbx-text">{run.symbol}</td>
                        <td className={`px-4 py-3 font-mono font-bold ${(run.metrics?.total_pnl_r || 0) >= 0 ? 'text-accent-green' : 'text-accent-red'}`}>
                          {run.status === 'COMPLETED' ? `${(run.metrics?.total_pnl_r || 0).toFixed(1)}R` : '--'}
                        </td>
                        <td className="px-4 py-3">
                          <Badge variant={run.status === 'COMPLETED' ? 'success' : run.status === 'FAILED' ? 'danger' : 'warning'}>
                            {run.status}
                          </Badge>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        </div>

        {/* Right Column: Execution & Results */}
        <div className="xl:col-span-8 flex flex-col gap-6">
          {activeRunId ? (
            <RunProgress 
              runId={activeRunId} 
              onComplete={() => {
                setActiveRunId(null);
                queryClient.invalidateQueries({ queryKey: ['backtest-history'] });
              }} 
            />
          ) : selectedRun?.status === 'COMPLETED' ? (
            <>
              {/* Metrics Summary */}
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                {[
                  { label: 'Total Trades', value: selectedRun.metrics?.total_trades, icon: BarChart3, color: 'text-blue-400' },
                  { label: 'Win Rate', value: `${(selectedRun.metrics?.win_rate || 0).toFixed(1)}%`, icon: TrendingUp, color: 'text-accent-green' },
                  { label: 'Total PnL (R)', value: `${(selectedRun.metrics?.total_pnl_r || 0).toFixed(1)}R`, icon: Activity, color: 'text-accent-yellow' },
                  { label: 'Max Drawdown', value: `${(selectedRun.metrics?.max_drawdown || 0).toFixed(1)}%`, icon: AlertTriangle, color: 'text-accent-red' },
                ].map((m, i) => (
                  <div key={i} className="bg-bg-secondary border border-cbx-border p-4 rounded-lg">
                    <div className="flex items-center gap-2 mb-2">
                       <m.icon className={`w-4 h-4 ${m.color}`} />
                       <span className="text-[10px] text-cbx-muted uppercase font-bold">{m.label}</span>
                    </div>
                    <div className="text-xl font-mono font-bold text-[#EAECEF]">{m.value}</div>
                  </div>
                ))}
              </div>

              {/* Tabs & Content */}
              <div className="bg-bg-secondary border border-cbx-border rounded-lg flex-1 flex flex-col overflow-hidden">
                <div className="bg-bg-primary/30 border-b border-cbx-border flex overflow-x-auto">
                  {[
                    { id: 'equity', label: 'Equity Curve' },
                    { id: 'distribution', label: 'Trade Distribution' },
                    { id: 'comparison', label: 'Long vs Short' },
                    { id: 'ai', label: 'AI Analysis' },
                  ].map(tab => (
                    <button
                      key={tab.id}
                      onClick={() => setActiveTab(tab.id as any)}
                      className={`px-6 py-4 text-xs font-bold transition-all whitespace-nowrap ${activeTab === tab.id ? 'text-accent-yellow border-b-2 border-accent-yellow bg-accent-yellow/5' : 'text-cbx-muted hover:text-cbx-text'}`}
                    >
                      {tab.label}
                    </button>
                  ))}
                </div>

                <div className="p-6 flex-1 overflow-y-auto">
                  {activeTab === 'equity' && <EquityCurve data={selectedRun.equity_history} />}
                  {activeTab === 'distribution' && <TradeDistributionChart trades={selectedRun.trades || []} />}
                  {activeTab === 'comparison' && (
                    <div className="grid grid-cols-2 gap-6">
                       <div className="bg-bg-primary/50 p-4 rounded-lg border border-cbx-border">
                          <h4 className="text-accent-green font-bold text-xs uppercase mb-4">Long Trades</h4>
                          <div className="space-y-2 text-sm">
                             <div className="flex justify-between">
                                <span className="text-cbx-muted">Count:</span>
                                <span>{selectedRun.trades?.filter((t: any) => t.side === 'LONG').length || 0}</span>
                             </div>
                             {/* Add more metrics */}
                          </div>
                       </div>
                       <div className="bg-bg-primary/50 p-4 rounded-lg border border-cbx-border">
                          <h4 className="text-accent-red font-bold text-xs uppercase mb-4">Short Trades</h4>
                          <div className="space-y-2 text-sm">
                             <div className="flex justify-between">
                                <span className="text-cbx-muted">Count:</span>
                                <span>{selectedRun.trades?.filter((t: any) => t.side === 'SHORT').length || 0}</span>
                             </div>
                             {/* Add more metrics */}
                          </div>
                       </div>
                    </div>
                  )}
                  {activeTab === 'ai' && (
                    <div className="flex flex-col items-center justify-center py-10 space-y-6">
                       <div className="bg-bg-primary border border-cbx-border rounded-xl p-8 max-w-md w-full text-center space-y-4">
                          <div className="bg-accent-yellow/20 w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-2">
                             <Bot className="text-accent-yellow w-8 h-8" />
                          </div>
                          <h3 className="text-lg font-bold text-[#EAECEF]">Gemini Strategy Auditor</h3>
                          <p className="text-sm text-cbx-muted leading-relaxed">
                            Phân tích chi tiết kết quả backtest, nhận diện các điểm yếu của chiến lược và gợi ý tham số tối ưu bằng AI.
                          </p>
                          <button 
                            className="w-full bg-accent-yellow text-bg-primary font-bold py-2.5 rounded flex items-center justify-center gap-2 hover:opacity-90 transition-all mt-4"
                            onClick={() => addToast('Đang kết nối với Gemini AI...', 'info')}
                          >
                            <Bot size={18} />
                            PHÂN TÍCH VỚI AI
                          </button>
                       </div>
                    </div>
                  )}
                </div>
              </div>
            </>
          ) : (
            <div className="h-full bg-bg-secondary border border-cbx-border border-dashed rounded-lg flex flex-col items-center justify-center p-12 text-center text-cbx-muted space-y-4">
               <div className="bg-bg-primary p-6 rounded-full">
                  <BarChart3 size={48} className="opacity-20" />
               </div>
               <div>
                  <h3 className="font-bold text-cbx-text mb-1">Cửa sổ Kết quả</h3>
                  <p className="text-sm max-w-[300px]">Hãy chọn một lượt chạy từ lịch sử hoặc bắt đầu một backtest mới để xem phân tích.</p>
               </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default BacktestPage;
