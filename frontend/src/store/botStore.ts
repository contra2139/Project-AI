import { create } from 'zustand';

interface BotState {
  mode: 'AUTO' | 'MANUAL';
  isScanning: boolean;
  connectionStatus: 'connected' | 'disconnected' | 'connecting';
  setMode: (mode: 'AUTO' | 'MANUAL') => void;
  setScanning: (isScanning: boolean) => void;
  setStatus: (status: 'connected' | 'disconnected' | 'connecting') => void;
}

export const useBotStore = create<BotState>((set) => ({
  mode: 'AUTO',
  isScanning: false,
  connectionStatus: 'disconnected',
  setMode: (mode) => set({ mode }),
  setScanning: (isScanning) => set({ isScanning }),
  setStatus: (connectionStatus) => set({ connectionStatus }),
}));
