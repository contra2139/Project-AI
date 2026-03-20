'use client';

import React, { useState, useEffect, useRef } from 'react';
import { useWebSocket } from '@/hooks/useWebSocket';
import { Terminal, CheckCircle2, AlertCircle, Loader2 } from 'lucide-react';

interface RunProgressProps {
  runId: string;
  onComplete: () => void;
}

interface LogEntry {
  timestamp: string;
  message: string;
  level: 'info' | 'warn' | 'error';
}

const RunProgress: React.FC<RunProgressProps> = ({ runId, onComplete }) => {
  const { on, off } = useWebSocket();
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [progress, setProgress] = useState(0);
  const [status, setStatus] = useState<'running' | 'completed' | 'failed'>('running');
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleProgress = (payload: any) => {
      if (payload.run_id !== runId) return;
      
      const newLog: LogEntry = {
        timestamp: new Date().toLocaleTimeString(),
        message: payload.message,
        level: payload.level || 'info'
      };
      
      setLogs(prev => [...prev.slice(-49), newLog]);
      if (payload.progress_pct) {
        setProgress(payload.progress_pct);
      }
    };

    const handleComplete = (payload: any) => {
      if (payload.run_id !== runId) return;
      setStatus('completed');
      setProgress(100);
      onComplete();
    };

    on('backtest_progress', handleProgress);
    on('backtest_complete', handleComplete);

    return () => {
      off('backtest_progress', handleProgress);
      off('backtest_complete', handleComplete);
    };
  }, [runId, on, off, onComplete]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [logs]);

  return (
    <div className="bg-bg-secondary border border-cbx-border rounded-lg overflow-hidden flex flex-col h-full max-h-[400px]">
      {/* Header */}
      <div className="bg-bg-primary/50 px-4 py-3 border-b border-cbx-border flex items-center justify-between">
        <div className="flex items-center gap-2">
          {status === 'running' ? (
            <Loader2 className="w-4 h-4 text-accent-yellow animate-spin" />
          ) : status === 'completed' ? (
            <CheckCircle2 className="w-4 h-4 text-accent-green" />
          ) : (
            <AlertCircle className="w-4 h-4 text-accent-red" />
          )}
          <span className="text-sm font-bold text-[#EAECEF]">
            {status === 'running' ? `Backtest Running: ${runId}` : 'Backtest Complete'}
          </span>
        </div>
        <span className="text-xs font-mono text-accent-yellow">{progress}%</span>
      </div>

      {/* Progress Bar */}
      <div className="h-1 bg-bg-primary w-full overflow-hidden">
        <div 
          className="h-full bg-accent-yellow transition-all duration-300 ease-out"
          style={{ width: `${progress}%` }}
        />
      </div>

      {/* Log Console */}
      <div 
        ref={scrollRef}
        className="flex-1 p-4 font-mono text-[11px] overflow-y-auto space-y-1 bg-[#0B0E11]"
      >
        {logs.length === 0 && (
          <div className="text-cbx-muted italic opacity-50 flex items-center gap-2">
            <Terminal size={12} />
            <span>Waiting for server logs...</span>
          </div>
        )}
        {logs.map((log, i) => (
          <div key={i} className="flex gap-2">
            <span className="text-cbx-muted shrink-0">[{log.timestamp}]</span>
            <span className={
              log.level === 'error' ? 'text-accent-red' : 
              log.level === 'warn' ? 'text-accent-yellow' : 
              'text-[#EAECEF]'
            }>
              {log.message}
            </span>
          </div>
        ))}
      </div>

      {/* Footer */}
      <div className="px-4 py-2 bg-bg-primary/30 border-t border-cbx-border flex justify-end gap-2">
        <button 
          className="text-[10px] text-cbx-muted hover:text-cbx-text uppercase font-bold"
          onClick={() => setLogs([])}
        >
          Clear Logs
        </button>
      </div>
    </div>
  );
};

export default RunProgress;
