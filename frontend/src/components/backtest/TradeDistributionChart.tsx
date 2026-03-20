'use client';

import React, { useMemo } from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell
} from 'recharts';

interface Trade {
  id: string;
  symbol: string;
  pnl_r: number;
}

interface TradeDistributionChartProps {
  trades: Trade[];
}

const BUCKETS = [
  { label: '< -2R', min: -Infinity, max: -2 },
  { label: '-2R to -1R', min: -2, max: -1 },
  { label: '-1R to 0', min: -1, max: 0 },
  { label: '0 to 1R', min: 0, max: 1 },
  { label: '1R to 2R', min: 1, max: 2 },
  { label: '> 2R', min: 2, max: Infinity },
];

const TradeDistributionChart: React.FC<TradeDistributionChartProps> = ({ trades }) => {
  const data = useMemo(() => {
    return BUCKETS.map(bucket => {
      const count = trades.filter(t => t.pnl_r >= bucket.min && t.pnl_r < bucket.max).length;
      return {
        name: bucket.label,
        count,
        color: bucket.max <= 0 ? '#F6465D' : (bucket.max <= 1 ? '#F0B90B' : '#0ECB81')
      };
    });
  }, [trades]);

  return (
    <div className="h-[300px] w-full bg-bg-secondary p-4 rounded-lg border border-cbx-border">
      <h4 className="text-sm font-bold text-cbx-muted mb-4 uppercase">Trade Distribution (PnL R)</h4>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#2B2F36" vertical={false} />
          <XAxis 
            dataKey="name" 
            axisLine={false} 
            tickLine={false} 
            tick={{ fill: '#848E9C', fontSize: 10 }} 
          />
          <YAxis 
            axisLine={false} 
            tickLine={false} 
            tick={{ fill: '#848E9C', fontSize: 10 }} 
          />
          <Tooltip 
            cursor={{ fill: 'rgba(255,255,255,0.05)' }}
            contentStyle={{ 
              backgroundColor: '#1E2329', 
              border: '1px solid #2B2F36',
              borderRadius: '4px',
              fontSize: '12px',
              color: '#EAECEF'
            }}
          />
          <Bar dataKey="count" radius={[4, 4, 0, 0]}>
            {data.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={entry.color} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
};

export default TradeDistributionChart;
