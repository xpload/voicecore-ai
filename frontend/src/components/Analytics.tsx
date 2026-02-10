import React from 'react';
import { Box, Typography, Paper, Grid, Button } from '@mui/material';
import { Download as DownloadIcon } from '@mui/icons-material';
import CallVolumeChart from './charts/CallVolumeChart';
import SentimentChart from './charts/SentimentChart';
import PerformanceMetricsChart from './charts/PerformanceMetricsChart';
import { exportToCSV } from '@/utils/exportData';

const Analytics: React.FC = () => {
  const handleExport = () => {
    const sampleData = [
      { time: '00:00', calls: 45, answered: 42, missed: 3 },
      { time: '04:00', calls: 32, answered: 30, missed: 2 },
      { time: '08:00', calls: 89, answered: 85, missed: 4 },
    ];
    exportToCSV(sampleData, 'analytics-export');
  };

  return (
    <Box>
      <Box sx={{ mb: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography variant="h4" gutterBottom>
          Analytics
        </Typography>
        <Button
          variant="outlined"
          startIcon={<DownloadIcon />}
          onClick={handleExport}
        >
          Export Data
        </Button>
      </Box>

      <Grid container spacing={3}>
        <Grid item xs={12} lg={8}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Call Volume Over Time
            </Typography>
            <CallVolumeChart height={350} />
          </Paper>
        </Grid>

        <Grid item xs={12} lg={4}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Sentiment Analysis
            </Typography>
            <SentimentChart height={350} />
          </Paper>
        </Grid>

        <Grid item xs={12}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Performance Metrics
            </Typography>
            <PerformanceMetricsChart height={400} />
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
};

export default Analytics;
