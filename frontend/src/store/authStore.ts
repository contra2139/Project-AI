import { create } from 'zustand';

interface AuthState {
  isAuthenticated: boolean;
  username: string | null;
  login: (username: string) => void;
  logout: () => void;
  setAuth: (isAuthenticated: boolean, username: string | null) => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  isAuthenticated: false,
  username: null,
  login: (username) => set({ isAuthenticated: true, username }),
  logout: () => set({ isAuthenticated: false, username: null }),
  setAuth: (isAuthenticated, username) => set({ isAuthenticated, username }),
}));
