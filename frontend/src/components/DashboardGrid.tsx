import React from 'react';
import { Responsive, WidthProvider, Layout } from 'react-grid-layout';
import { Box, Paper, IconButton, Typography } from '@mui/material';
import { Close as CloseIcon, Settings as SettingsIcon } from '@mui/icons-material';
import { useDashboardStore } from '@/store/dashboardStore';
import 'react-grid-layout/css/styles.css';
import 'react-grid-layout/css/resizable.css';

const ResponsiveGridLayout = WidthProvider(Responsive);

interface DashboardGridProps {
  children?: React.ReactNode;
}

const DashboardGrid: React.FC<DashboardGridProps> = ({ children }) => {
  const { layout, widgets, isEditMode, updateLayout, removeWidget } = useDashboardStore();

  const handleLayoutChange = (newLayout: Layout[]) => {
    if (isEditMode) {
      const updatedLayout = newLayout.map((item) => ({
        i: item.i,
        x: item.x,
        y: item.y,
        w: item.w,
        h: item.h,
        minW: layout.find((l) => l.i === item.i)?.minW,
        minH: layout.find((l) => l.i === item.i)?.minH,
        maxW: layout.find((l) => l.i === item.i)?.maxW,
        maxH: layout.find((l) => l.i === item.i)?.maxH,
        static: layout.find((l) => l.i === item.i)?.static,
      }));
      updateLayout(updatedLayout);
    }
  };

  const renderWidget = (widgetId: string) => {
    const widget = widgets.find((w) => w.id === widgetId);
    if (!widget) return null;

    return (
      <Paper
        key={widgetId}
        elevation={2}
        sx={{
          height: '100%',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
          position: 'relative',
          '&:hover .widget-actions': {
            opacity: isEditMode ? 1 : 0,
          },
        }}
      >
        <Box
          sx={{
            p: 2,
            borderBottom: 1,
            borderColor: 'divider',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            cursor: isEditMode ? 'move' : 'default',
          }}
        >
          <Typography variant="h6" component="h2">
            {widget.title}
          </Typography>
          {isEditMode && (
            <Box className="widget-actions" sx={{ opacity: 0, transition: 'opacity 0.2s' }}>
              <IconButton size="small" onClick={() => console.log('Configure', widgetId)}>
                <SettingsIcon fontSize="small" />
              </IconButton>
              <IconButton size="small" onClick={() => removeWidget(widgetId)}>
                <CloseIcon fontSize="small" />
              </IconButton>
            </Box>
          )}
        </Box>
        <Box sx={{ p: 2, flexGrow: 1, overflow: 'auto' }}>
          {/* Widget content will be rendered here */}
          <Typography variant="body2" color="text.secondary">
            {widget.type} widget - Content to be implemented
          </Typography>
        </Box>
      </Paper>
    );
  };

  return (
    <ResponsiveGridLayout
      className="dashboard-grid"
      layouts={{ lg: layout }}
      breakpoints={{ lg: 1200, md: 996, sm: 768, xs: 480, xxs: 0 }}
      cols={{ lg: 12, md: 10, sm: 6, xs: 4, xxs: 2 }}
      rowHeight={100}
      isDraggable={isEditMode}
      isResizable={isEditMode}
      onLayoutChange={handleLayoutChange}
      draggableHandle=".MuiBox-root"
      compactType="vertical"
      preventCollision={false}
    >
      {layout.map((item) => (
        <div key={item.i}>{renderWidget(item.i)}</div>
      ))}
    </ResponsiveGridLayout>
  );
};

export default DashboardGrid;
