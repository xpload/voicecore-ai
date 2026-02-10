// Dashboard state management
import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { DashboardWidget, DashboardLayout, DashboardConfig } from '@/types/dashboard';

interface DashboardState {
  currentDashboard: DashboardConfig | null;
  widgets: DashboardWidget[];
  layout: DashboardLayout[];
  isEditMode: boolean;
  
  // Actions
  setDashboard: (dashboard: DashboardConfig) => void;
  addWidget: (widget: DashboardWidget, layout: DashboardLayout) => void;
  removeWidget: (widgetId: string) => void;
  updateWidget: (widgetId: string, updates: Partial<DashboardWidget>) => void;
  updateLayout: (layout: DashboardLayout[]) => void;
  setEditMode: (isEditMode: boolean) => void;
  saveDashboard: () => Promise<void>;
  resetDashboard: () => void;
}

const defaultLayout: DashboardLayout[] = [
  { i: 'metrics-1', x: 0, y: 0, w: 3, h: 2, minW: 2, minH: 2 },
  { i: 'chart-1', x: 3, y: 0, w: 6, h: 4, minW: 4, minH: 3 },
  { i: 'calls-1', x: 9, y: 0, w: 3, h: 4, minW: 3, minH: 3 },
  { i: 'activity-1', x: 0, y: 2, w: 3, h: 2, minW: 2, minH: 2 },
];

const defaultWidgets: DashboardWidget[] = [
  {
    id: 'metrics-1',
    type: 'metrics',
    title: 'Key Metrics',
    config: { metrics: ['totalCalls', 'activeCalls', 'successRate'] },
  },
  {
    id: 'chart-1',
    type: 'chart',
    title: 'Call Volume',
    config: { chartType: 'line', dataSource: 'calls', refreshInterval: 30000 },
  },
  {
    id: 'calls-1',
    type: 'calls',
    title: 'Recent Calls',
    config: { refreshInterval: 10000 },
  },
  {
    id: 'activity-1',
    type: 'activity',
    title: 'Recent Activity',
    config: { refreshInterval: 15000 },
  },
];

export const useDashboardStore = create<DashboardState>()(
  persist(
    (set, get) => ({
      currentDashboard: null,
      widgets: defaultWidgets,
      layout: defaultLayout,
      isEditMode: false,

      setDashboard: (dashboard) => set({ 
        currentDashboard: dashboard,
        widgets: dashboard.widgets,
        layout: dashboard.layout,
      }),

      addWidget: (widget, layout) => set((state) => ({
        widgets: [...state.widgets, widget],
        layout: [...state.layout, layout],
      })),

      removeWidget: (widgetId) => set((state) => ({
        widgets: state.widgets.filter((w) => w.id !== widgetId),
        layout: state.layout.filter((l) => l.i !== widgetId),
      })),

      updateWidget: (widgetId, updates) => set((state) => ({
        widgets: state.widgets.map((w) =>
          w.id === widgetId ? { ...w, ...updates } : w
        ),
      })),

      updateLayout: (layout) => set({ layout }),

      setEditMode: (isEditMode) => set({ isEditMode }),

      saveDashboard: async () => {
        const state = get();
        const dashboard: DashboardConfig = {
          id: state.currentDashboard?.id || 'default',
          name: state.currentDashboard?.name || 'My Dashboard',
          widgets: state.widgets,
          layout: state.layout,
          createdAt: state.currentDashboard?.createdAt || new Date().toISOString(),
          updatedAt: new Date().toISOString(),
        };

        // Save to backend
        try {
          // TODO: Implement API call
          console.log('Saving dashboard:', dashboard);
          set({ currentDashboard: dashboard });
        } catch (error) {
          console.error('Failed to save dashboard:', error);
          throw error;
        }
      },

      resetDashboard: () => set({
        widgets: defaultWidgets,
        layout: defaultLayout,
        isEditMode: false,
      }),
    }),
    {
      name: 'dashboard-storage',
      partialize: (state) => ({
        widgets: state.widgets,
        layout: state.layout,
      }),
    }
  )
);
