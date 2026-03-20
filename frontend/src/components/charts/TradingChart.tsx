'use client';

import React, { useEffect, useRef } from 'react';
import { createChart, CandlestickSeries, CandlestickData, UTCTimestamp } from 'lightweight-charts';

interface TradingChartProps {
  symbol: string;
  interval?: string;
}

const generateMockKlines = (count: number): CandlestickData[] => {
  const data: CandlestickData[] = [];
  let time = Math.floor(Date.now() / 1000) - count * 900;
  let lastClose = 60000;

  for (let i = 0; i < count; i++) {
    const open = lastClose;
    const high = open + Math.random() * 200;
    const low = open - Math.random() * 200;
    const close = low + Math.random() * (high - low);
    
    data.push({
      time: time as UTCTimestamp,
      open,
      high,
      low,
      close,
    });
    
    time += 900;
    lastClose = close;
  }
  return data;
};

const TradingChart: React.FC<TradingChartProps> = ({ symbol, interval = '15m' }) => {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<any>(null);
  const seriesRef = useRef<any>(null);

  useEffect(() => {
    if (!chartContainerRef.current) return;

    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { color: '#0B0E11' },
        textColor: '#848E9C',
      },
      grid: {
        vertLines: { color: '#1E2026' },
        horzLines: { color: '#1E2026' },
      },
      width: chartContainerRef.current.clientWidth,
      height: 400,
      timeScale: {
        borderColor: '#1E2026',
        timeVisible: true,
        secondsVisible: false,
      },
      rightPriceScale: {
        borderColor: '#1E2026',
      },
    });

    const series = chart.addSeries(CandlestickSeries, {
      upColor: '#0ECB81',
      downColor: '#F6465D',
      borderUpColor: '#0ECB81',
      borderDownColor: '#F6465D',
      wickUpColor: '#0ECB81',
      wickDownColor: '#F6465D',
    });

    chartRef.current = chart;
    seriesRef.current = series;

    const fetchData = async () => {
      try {
        const response = await fetch(
          `https://api.binance.com/api/v3/klines?symbol=${symbol}&interval=${interval}&limit=200`
        );
        if (!response.ok) throw new Error('Binance API failed');
        
        const rawData = await response.json();
        const formattedData: CandlestickData[] = rawData.map((d: any[]) => ({
          time: (Math.floor(d[0] / 1000)) as UTCTimestamp,
          open: parseFloat(d[1]),
          high: parseFloat(d[2]),
          low: parseFloat(d[3]),
          close: parseFloat(d[4]),
        }));

        if (seriesRef.current) {
          seriesRef.current.setData(formattedData);
        }
      } catch (error) {
        console.warn('TradingChart: Falling back to mock data', error);
        if (seriesRef.current) {
          seriesRef.current.setData(generateMockKlines(200));
        }
      }
    };

    // Re-fetch when symbol/interval changes
    fetchData();

    const handleResize = () => {
      if (chartContainerRef.current) {
        chart.applyOptions({ width: chartContainerRef.current.clientWidth });
      }
    };

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      chart.remove();
    };
  }, [symbol, interval]);

  return <div ref={chartContainerRef} className="w-full h-[400px]" />;
};

export default TradingChart;
