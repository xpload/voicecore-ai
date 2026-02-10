/**
 * Business Intelligence Dashboard Component
 * 
 * Provides comprehensive BI dashboards with real-time metrics,
 * KPI tracking, executive summaries, and customizable widgets.
 * 
 * Implements Requirement 3.2: Business intelligence dashboards with real-time metrics
 */

import React, { useState, useEffect } from 'react';
import { Box, Grid, Card, CardContent, Typography, Select, MenuItem, FormControl, InputLabel } from '@mui/material';
import { TrendingUp, TrendingDown, Remove } from '@mui/icons-material';
import api from '../services/api';

interface KPI {
  name: string;
  category: string;
  value: number;
  unit: string;
  change_percentage?: number;
  trend?: 'up' | 'down' | 'stable';
  target?: number;
  status?: 'good' | 'warning' | 'critical';
}

interface ExecutiveSummary {
  period: {
    name: string;
    start_date: string;
    end_date: string;
  };
  key_metrics: Record<string, any>;
  performance_indicators: KPI[];
  trends: Record<string, any>;
  insights: string[];
  recommendations: string[];
}

const BIDashboard: React.FC = () => {
  const [period, setPeriod] = useState<string>('today');
  const [executiveData, setExecutiveData] = useState<ExecutiveSummary | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    fetchExecutiveDashboard();
  }, [period]);

  const fetchExecutiveDashboard = async () => {
    try {
      setLoading(true);
      const response = await api.get(`/bi/dashboard/executive?period=${period}`);
      setExecutiveData(response.data);
    } catch (error) {
      console.error('Failed to fetch executive dashboard:', error);
    } finally {
      setLoading(false);
    }
  };

  const getTrendIcon = (trend?: string) => {
    switch (trend) {
      case 'up':
        return <TrendingUp color="success" />;
      case 'down':
        return <TrendingDown color="error" />;
      default:
        return <Remove color="disabled" />;
    }
  };

  const getStatusColor = (status?: string) => {
    switch (status) {
      case 'good':
        return '#4caf50';
      case 'warning':
        return '#ff9800';
      case 'critical':
        return '#f44336';
      default:
        return '#9e9e9e';
    }
  };

  if (loading) {
    return (
      <Box sx={{ p: 3 }}>
        <Typography>Loading dashboard...</Typography>
      </Box>
    );
  }

  if (!executiveData) {
    return (
      <Box sx={{ p: 3 }}>
        <Typography>No data available</Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      {/* Header */}
      <Box sx={{ mb: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography variant="h4" component="h1">
          Business Intelligence Dashboard
        </Typography>
        <FormControl sx={{ minWidth: 200 }}>
          <InputLabel>Period</InputLabel>
          <Select
            value={period}
            label="Period"
            onChange={(e) => setPeriod(e.target.value)}
          >
            <MenuItem value="today">Today</MenuItem>
            <MenuItem value="week">This Week</MenuItem>
            <MenuItem value="month">This Month</MenuItem>
            <MenuItem value="quarter">This Quarter</MenuItem>
            <MenuItem value="year">This Year</MenuItem>
          </Select>
        </FormControl>
      </Box>

      {/* KPI Cards */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        {executiveData.performance_indicators.map((kpi, index) => (
          <Grid item xs={12} sm={6} md={4} lg={2.4} key={index}>
            <Card sx={{ borderLeft: `4px solid ${getStatusColor(kpi.status)}` }}>
              <CardContent>
                <Typography color="textSecondary" gutterBottom variant="body2">
                  {kpi.name}
                </Typography>
                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <Typography variant="h4" component="div">
                    {kpi.value.toFixed(kpi.unit === '%' ? 1 : 0)}
                    <Typography component="span" variant="h6" color="textSecondary">
                      {kpi.unit}
                    </Typography>
                  </Typography>
                  {getTrendIcon(kpi.trend)}
                </Box>
                {kpi.change_percentage !== undefined && (
                  <Typography
                    variant="body2"
                    sx={{
                      color: kpi.change_percentage > 0 ? '#4caf50' : kpi.change_percentage < 0 ? '#f44336' : '#9e9e9e',
                      mt: 1
                    }}
                  >
                    {kpi.change_percentage > 0 ? '+' : ''}
                    {kpi.change_percentage.toFixed(1)}% vs previous period
                  </Typography>
                )}
                {kpi.target !== undefined && (
                  <Typography variant="caption" color="textSecondary">
                    Target: {kpi.target}{kpi.unit}
                  </Typography>
                )}
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      {/* Key Metrics Summary */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Call Metrics
              </Typography>
              <Box sx={{ mt: 2 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                  <Typography>Total Calls:</Typography>
                  <Typography fontWeight="bold">{executiveData.key_metrics.total_calls}</Typography>
                </Box>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                  <Typography>Answered Calls:</Typography>
                  <Typography fontWeight="bold">{executiveData.key_metrics.answered_calls}</Typography>
                </Box>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                  <Typography>Answer Rate:</Typography>
                  <Typography fontWeight="bold">
                    {(executiveData.key_metrics.answer_rate * 100).toFixed(1)}%
                  </Typography>
                </Box>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                  <Typography>AI Handled:</Typography>
                  <Typography fontWeight="bold">{executiveData.key_metrics.ai_handled_calls}</Typography>
                </Box>
                <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                  <Typography>AI Resolution Rate:</Typography>
                  <Typography fontWeight="bold">
                    {(executiveData.key_metrics.ai_resolution_rate * 100).toFixed(1)}%
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Business Metrics
              </Typography>
              <Box sx={{ mt: 2 }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                  <Typography>Total Revenue:</Typography>
                  <Typography fontWeight="bold">
                    ${executiveData.key_metrics.total_revenue.toFixed(2)}
                  </Typography>
                </Box>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                  <Typography>Customer Satisfaction:</Typography>
                  <Typography fontWeight="bold">
                    {executiveData.key_metrics.average_satisfaction.toFixed(2)}/5.0
                  </Typography>
                </Box>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                  <Typography>VIP Calls:</Typography>
                  <Typography fontWeight="bold">{executiveData.key_metrics.vip_calls}</Typography>
                </Box>
                <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
                  <Typography>Escalated Calls:</Typography>
                  <Typography fontWeight="bold">{executiveData.key_metrics.escalated_calls}</Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Insights and Recommendations */}
      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Business Insights
              </Typography>
              <Box sx={{ mt: 2 }}>
                {executiveData.insights.length > 0 ? (
                  executiveData.insights.map((insight, index) => (
                    <Box
                      key={index}
                      sx={{
                        p: 2,
                        mb: 1,
                        bgcolor: '#e3f2fd',
                        borderRadius: 1,
                        borderLeft: '4px solid #2196f3'
                      }}
                    >
                      <Typography variant="body2">{insight}</Typography>
                    </Box>
                  ))
                ) : (
                  <Typography color="textSecondary">No insights available</Typography>
                )}
              </Box>
            </CardContent>
          </Card>
        </Grid>

        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Recommendations
              </Typography>
              <Box sx={{ mt: 2 }}>
                {executiveData.recommendations.length > 0 ? (
                  executiveData.recommendations.map((recommendation, index) => (
                    <Box
                      key={index}
                      sx={{
                        p: 2,
                        mb: 1,
                        bgcolor: '#fff3e0',
                        borderRadius: 1,
                        borderLeft: '4px solid #ff9800'
                      }}
                    >
                      <Typography variant="body2">{recommendation}</Typography>
                    </Box>
                  ))
                ) : (
                  <Typography color="textSecondary">No recommendations available</Typography>
                )}
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default BIDashboard;
