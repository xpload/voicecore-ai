// Dashboard widget types
export interface DashboardWidget {
  id: string;
  type: 'metrics' | 'chart' | 'calls' | 'activity' | 'custom';
  title: string;
  config: WidgetConfig;
}

export interface WidgetConfig {
  refreshInterval?: number;
  dataSource?: string;
  chartType?: 'line' | 'bar' | 'pie' | 'area';
  metrics?: string[];
  filters?: Record<string, any>;
  customSettings?: Record<string, any>;
}

export interface DashboardLayout {
  i: string; // widget id
  x: number;
  y: number;
  w: number; // width in grid units
  h: number; // height in grid units
  minW?: number;
  minH?: number;
  maxW?: number;
  maxH?: number;
  static?: boolean;
}

export interface DashboardConfig {
  id: string;
  name: string;
  widgets: DashboardWidget[];
  layout: DashboardLayout[];
  createdAt: string;
  updatedAt: string;
}
