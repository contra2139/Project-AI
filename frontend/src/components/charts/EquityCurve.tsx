'use client';

import React from 'react';
import { 
  LineChart, 
  Line, 
  XAxis, 
  YAxis, 
  Tooltip, 
  ResponsiveContainer, 
  CartesianGrid 
} from 'recharts';

interface EquityData {
  time: string;
  equity_usd: number;
  drawdown_from_peak_pct: number;
}

interface EquityCurveProps {
  data?: EquityData[];
}

const EquityCurve: React.FC<EquityCurveProps> = ({ data = [] }) => {
  if (data.length === 0) {
    return (
      <div className="w-full h-[300px] flex items-center justify-center bg-bg-secondary border border-cbx-border rounded-lg text-cbx-muted">
        Chưa có dữ liệu equity
      </div>
    );
  }

  return (
    <div className="w-full h-[300px] bg-bg-secondary border border-cbx-border p-4 rounded-lg">
      <h3 className="text-sm font-medium text-cbx-muted mb-4 uppercase tracking-wider">Equity Curve</h3>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1E2026" vertical={false} />
          <XAxis 
            dataKey="time" 
            stroke="#848E9C" 
            fontSize={12}
            tickFormatter={(str) => {
              const date = new Date(str);
              return `${date.getMonth() + 1}/${date.getDate()}`;
            }}
          />
          <YAxis 
            stroke="#848E9C" 
            fontSize={12}
            tickFormatter={(val) => `$${val.toLocaleString()}`}
            domain={['auto', 'auto']}
          />
          <Tooltip 
            contentStyle={{ backgroundColor: '#1E2026', border: '1px solid #cbx-border' }}
            formatter={(value: number, name: string) => {
              if (name === 'equity_usd') return [`$${value.toLocaleString()}`, 'Equity'];
              if (name === 'drawdown_from_peak_pct') return [`${value}%`, 'Drawdown'];
              return [value, name];
            }}
          />
          <Line 
            type="monotone" 
            dataKey="equity_usd" 
            stroke="#0ECB81" 
            strokeWidth={2} 
            dot={false}
            activeDot={{ r: 4 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};

export default EquityCurve;
