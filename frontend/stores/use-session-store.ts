'use client';

import { create } from 'zustand';
import { persist } from 'zustand/middleware';

type SessionState = {
  accessToken: string | null;
  refreshToken: string | null;
  activeIncidentId: number | null;
  setTokens: (accessToken: string, refreshToken: string) => void;
  setActiveIncidentId: (incidentId: number | null) => void;
  clearTokens: () => void;
};

export const useSessionStore = create<SessionState>()(
  persist(
    (set) => ({
      accessToken: null,
      refreshToken: null,
      activeIncidentId: null,
      setTokens: (accessToken, refreshToken) => set({ accessToken, refreshToken }),
      setActiveIncidentId: (activeIncidentId) => set({ activeIncidentId }),
      clearTokens: () => set({ accessToken: null, refreshToken: null }),
    }),
    { name: 'aegisops-session' },
  ),
);
