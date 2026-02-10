// Zustand store for global state management
import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { User, Tenant, TenantSettings } from '@/types';

interface AppState {
  user: User | null;
  tenant: Tenant | null;
  theme: 'light' | 'dark';
  sidebarOpen: boolean;
  
  // Actions
  setUser: (user: User | null) => void;
  setTenant: (tenant: Tenant | null) => void;
  setTheme: (theme: 'light' | 'dark') => void;
  toggleSidebar: () => void;
  updateTenantSettings: (settings: Partial<TenantSettings>) => void;
}

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      user: null,
      tenant: null,
      theme: 'dark',
      sidebarOpen: true,

      setUser: (user) => set({ user }),
      setTenant: (tenant) => set({ tenant }),
      setTheme: (theme) => set({ theme }),
      toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
      updateTenantSettings: (settings) =>
        set((state) => ({
          tenant: state.tenant
            ? { ...state.tenant, settings: { ...state.tenant.settings, ...settings } }
            : null,
        })),
    }),
    {
      name: 'voicecore-storage',
      partialize: (state) => ({ theme: state.theme, sidebarOpen: state.sidebarOpen }),
    }
  )
);
