'use client';

import React, { useState, useEffect } from 'react';
import { SignalNotification } from '@/lib/types';
import { Clock, CheckCircle, XCircle } from 'lucide-react';
import clsx from 'clsx';

interface SignalCardProps {
  signal: SignalNotification;
  onPlaceOrder?: (id: string) => void;
  onDismiss?: (id: string) => void;
  onClick?: (signal: SignalNotification) => void;
}

const SignalCard: React.FC<SignalCardProps> = ({ signal, onPlaceOrder, onDismiss, onClick }) => {
  const [timeLeft, setTimeLeft] = useState<string>('');

  useEffect(() => {
    if (signal.status !== 'ACTIVE') return;

    const updateTimer = () => {
      const now = new Date().getTime();
      const expiry = new Date(signal.expires_at).getTime();
      const diff = expiry - now;

      if (diff <= 0) {
        setTimeLeft('EXPIRED');
        return;
      }

      const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
      const seconds = Math.floor((diff % (1000 * 60)) / 1000);
      setTimeLeft(`${minutes}:${seconds.toString().padStart(2, '0')}`);
    };

    updateTimer();
    const interval = setInterval(updateTimer, 1000);
    return () => clearInterval(interval);
  }, [signal.status, signal.expires_at]);

  const isLong = signal.side === 'LONG';
  const isActive = signal.status === 'ACTIVE';

  return (
    <div 
      onClick={() => onClick?.(signal)}
      className={clsx(
        "bg-bg-secondary border-l-4 p-4 mb-4 rounded-r-lg shadow-md transition-all cursor-pointer hover:bg-bg-tertiary group",
        isLong ? "border-accent-green" : "border-accent-red"
      )}
    >
      {/* Row 1: Header */}
      <div className="flex justify-between items-center mb-2">
        <div className="flex items-center space-x-2">
          <span className="text-lg font-bold group-hover:text-accent-yellow transition-colors">{signal.symbol}</span>
          <span className={clsx(
            "text-[10px] px-2 py-0.5 rounded font-bold uppercase",
            isLong ? "bg-accent-green/20 text-accent-green" : "bg-accent-red/20 text-accent-red"
          )}>
            {signal.side}
          </span>
        </div>
        <span className="text-xs text-cbx-muted">
          {new Date(signal.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </span>
      </div>

      {/* Row 2: Price Levels */}
      <div className="grid grid-cols-3 gap-2 text-sm mb-3">
        <div>
          <div className="text-[10px] text-cbx-muted uppercase">Entry</div>
          <div className="font-mono font-medium">{signal.entry_price.toLocaleString()}</div>
        </div>
        <div>
          <div className="text-[10px] text-cbx-muted uppercase">SL</div>
          <div className="font-mono text-accent-red">{signal.stop_loss.toLocaleString()}</div>
        </div>
        <div>
          <div className="text-[10px] text-cbx-muted uppercase">TP</div>
          <div className="font-mono text-accent-green">{signal.take_profit.toLocaleString()}</div>
        </div>
      </div>

      {/* Row 3: Quality Bar */}
      <div className="mb-3">
        <div className="flex justify-between text-[10px] text-cbx-muted uppercase mb-1">
          <span>Signal Quality</span>
          <span>{signal.quality_score}/10</span>
        </div>
        <div className="w-full bg-bg-primary h-1.5 rounded-full overflow-hidden">
          <div 
            className="bg-accent-yellow h-full transition-all duration-500" 
            style={{ width: `${(signal.quality_score / 10) * 100}%` }}
          />
        </div>
      </div>

      {/* Row 4: Badges */}
      <div className="flex items-center space-x-2 mb-4">
        <span className="text-[10px] bg-bg-tertiary text-cbx-text px-2 py-0.5 rounded border border-cbx-border uppercase font-medium">
          {signal.regime}
        </span>
        <span className="text-[10px] bg-bg-tertiary text-cbx-text px-2 py-0.5 rounded border border-cbx-border uppercase font-medium">
          EMA {signal.ema_direction}
        </span>
      </div>

      {/* Row 5: Actions / Footer */}
      <div className="flex items-center justify-between pt-2 border-t border-cbx-border">
        {isActive ? (
          <>
            <div className="flex items-center text-accent-yellow text-xs font-medium">
              <Clock size={14} className="mr-1" />
              <span>{timeLeft}</span>
            </div>
            <div className="flex space-x-2">
              <button 
                onClick={(e) => {
                  e.stopPropagation();
                  onPlaceOrder?.(signal.id);
                }}
                className="flex items-center bg-accent-green text-bg-primary text-xs font-bold px-3 py-1.5 rounded hover:bg-green-500 transition-colors shadow-sm"
              >
                <CheckCircle size={14} className="mr-1" />
                ĐẶT LỆNH
              </button>
              <button 
                onClick={(e) => {
                  e.stopPropagation();
                  onDismiss?.(signal.id);
                }}
                className="flex items-center bg-bg-tertiary text-cbx-text text-xs font-bold px-3 py-1.5 rounded border border-cbx-border hover:bg-cbx-border transition-colors shadow-sm"
              >
                <XCircle size={14} className="mr-1" />
                BỎ QUA
              </button>
            </div>
          </>
        ) : (
          <div className="text-xs font-medium uppercase text-cbx-muted flex items-center">
            {signal.status === 'TRADED' ? (
              <><CheckCircle size={14} className="mr-1 text-accent-green" /> Đã vào lệnh</>
            ) : (
              <><XCircle size={14} className="mr-1 text-accent-red" /> Hết hạn</>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default SignalCard;
