import React from 'react';
import { Box, Grid, Typography, Card, CardContent } from '@mui/material';
import { TrendingUp, TrendingDown } from '@mui/icons-material';

interface MetricData {
  label: string;
  value: string | number;
  change?: number;
  changeLabel?: string;
}

interface MetricsWidgetProps {
  metrics?: MetricData[];
}

const MetricsWidget: React.FC<MetricsWidgetProps> = ({ metrics }) => {
  const defaultMetrics: MetricData[] = [
    { label: 'Total Calls', value: '1,234', change: 12.5, changeLabel: 'vs last week' },
    { label: 'Active Calls', value: '45', change: -5.2, changeLabel: 'vs yesterday' },
    { label: 'Success Rate', value: '94.2%', change: 2.1, changeLabel: 'vs last month' },
  ];

  const displayMetrics = metrics || defaultMetrics;

  return (
    <Grid container spacing={2}>
      {displayMetrics.map((metric, index) => (
        <Grid item xs={12} sm={6} md={4} key={index}>
          <Card variant="outlined">
            <CardContent>
              <Typography variant="body2" color="text.secondary" gutterBottom>
                {metric.label}
              </Typography>
              <Typography variant="h5" component="div" sx={{ mb: 1 }}>
                {metric.value}
              </Typography>
              {metric.change !== undefined && (
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                  {metric.change > 0 ? (
                    <TrendingUp color="success" fontSize="small" />
                  ) : (
                    <TrendingDown color="error" fontSize="small" />
                  )}
                  <Typography
                    variant="caption"
                    color={metric.change > 0 ? 'success.main' : 'error.main'}
                  >
                    {Math.abs(metric.change)}% {metric.changeLabel}
                  </Typography>
                </Box>
              )}
            </CardContent>
          </Card>
        </Grid>
      ))}
    </Grid>
  );
};

export default MetricsWidget;
