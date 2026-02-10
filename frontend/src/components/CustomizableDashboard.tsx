import React from 'react';
import { Box, Typography, Button, Stack } from '@mui/material';
import { Edit as EditIcon, Save as SaveIcon, Refresh as RefreshIcon } from '@mui/icons-material';
import { useDashboardStore } from '@/store/dashboardStore';
import DashboardGrid from './DashboardGrid';
import ResponsiveContainer from './ResponsiveContainer';

const CustomizableDashboard: React.FC = () => {
  const { isEditMode, setEditMode, saveDashboard, resetDashboard } = useDashboardStore();

  const handleSave = async () => {
    try {
      await saveDashboard();
      setEditMode(false);
    } catch (error) {
      console.error('Failed to save dashboard:', error);
    }
  };

  return (
    <ResponsiveContainer>
      <Box sx={{ mb: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography variant="h4" component="h1">
          Customizable Dashboard
        </Typography>
        <Stack direction="row" spacing={2}>
          {isEditMode ? (
            <>
              <Button
                variant="outlined"
                startIcon={<RefreshIcon />}
                onClick={resetDashboard}
              >
                Reset
              </Button>
              <Button
                variant="contained"
                startIcon={<SaveIcon />}
                onClick={handleSave}
              >
                Save Layout
              </Button>
            </>
          ) : (
            <Button
              variant="outlined"
              startIcon={<EditIcon />}
              onClick={() => setEditMode(true)}
            >
              Customize
            </Button>
          )}
        </Stack>
      </Box>

      {isEditMode && (
        <Box
          sx={{
            mb: 2,
            p: 2,
            bgcolor: 'info.main',
            color: 'info.contrastText',
            borderRadius: 1,
          }}
        >
          <Typography variant="body2">
            Edit mode: Drag widgets to rearrange, resize by dragging corners, or remove widgets.
          </Typography>
        </Box>
      )}

      <DashboardGrid />
    </ResponsiveContainer>
  );
};

export default CustomizableDashboard;
