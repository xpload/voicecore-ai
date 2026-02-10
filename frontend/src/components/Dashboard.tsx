import React, { useState, useEffect } from 'react';
import {
  Grid,
  Paper,
  Typography,
  Box,
  Card,
  CardContent,
  LinearProgress,
  Chip,
  IconButton,
} from '@mui/material';
import {
  Phone,
  People,
  TrendingUp,
  Security,
  Refresh,
  PlayArrow,
  Pause,
} from '@mui/icons-material';
import { motion } from 'framer-motion';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

interface DashboardStats {
  activeCalls: number;
  totalAgents: number;
  callsToday: number;
  systemHealth: number;
  aiResponseTime: number;
  customerSatisfaction: number;
}

const Dashboard: React.FC = () => {
  const [stats, setStats] = useState<DashboardStats>({
    activeCalls: 0,
    totalAgents: 0,
    callsToday: 0,
    systemHealth: 0,
    aiResponseTime: 0,
    customerSatisfaction: 0,
  });
  const [isLive, setIsLive] = useState(true);

  // Mock data for charts
  const callData = [
    { time: '00:00', calls: 12 },
    { time: '04:00', calls: 8 },
    { time: '08:00', calls: 45 },
    { time: '12:00', calls: 67 },
    { time: '16:00', calls: 89 },
    { time: '20:00', calls: 34 },
  ];

  useEffect(() => {
    // Simulate real-time data updates
    const interval = setInterval(() => {
      if (isLive) {
        setStats({
          activeCalls: Math.floor(Math.random() * 50) + 10,
          totalAgents: 24,
          callsToday: Math.floor(Math.random() * 500) + 200,
          systemHealth: Math.floor(Math.random() * 10) + 90,
          aiResponseTime: Math.floor(Math.random() * 500) + 800,
          customerSatisfaction: Math.floor(Math.random() * 20) + 80,
        });
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [isLive]);

  const StatCard = ({ title, value, icon, color, suffix = '' }: any) => (
    <motion.div
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
    >
      <Card sx={{ height: '100%', background: 'linear-gradient(135deg, #1a1a1a 0%, #2a2a2a 100%)' }}>
        <CardContent>
          <Box display="flex" alignItems="center" justifyContent="space-between">
            <Box>
              <Typography color="textSecondary" gutterBottom variant="body2">
                {title}
              </Typography>
              <Typography variant="h4" component="div" color={color}>
                {value}{suffix}
              </Typography>
            </Box>
            <Box sx={{ color: color }}>
              {icon}
            </Box>
          </Box>
        </CardContent>
      </Card>
    </motion.div>
  );

  return (
    <Box sx={{ flexGrow: 1 }}>
      {/* Header */}
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4" component="h1" fontWeight="bold">
          🚀 VoiceCore AI 2.0 Dashboard
        </Typography>
        <Box display="flex" alignItems="center" gap={2}>
          <Chip
            label={isLive ? "LIVE" : "PAUSED"}
            color={isLive ? "success" : "default"}
            variant="filled"
          />
          <IconButton
            onClick={() => setIsLive(!isLive)}
            color="primary"
          >
            {isLive ? <Pause /> : <PlayArrow />}
          </IconButton>
          <IconButton color="primary">
            <Refresh />
          </IconButton>
        </Box>
      </Box>

      {/* Stats Cards */}
      <Grid container spacing={3} mb={3}>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Active Calls"
            value={stats.activeCalls}
            icon={<Phone sx={{ fontSize: 40 }} />}
            color="primary.main"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Total Agents"
            value={stats.totalAgents}
            icon={<People sx={{ fontSize: 40 }} />}
            color="secondary.main"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Calls Today"
            value={stats.callsToday}
            icon={<TrendingUp sx={{ fontSize: 40 }} />}
            color="success.main"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="System Health"
            value={stats.systemHealth}
            icon={<Security sx={{ fontSize: 40 }} />}
            color="info.main"
            suffix="%"
          />
        </Grid>
      </Grid>

      {/* Charts and Details */}
      <Grid container spacing={3}>
        {/* Call Volume Chart */}
        <Grid item xs={12} md={8}>
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
          >
            <Paper sx={{ p: 3, height: 400 }}>
              <Typography variant="h6" gutterBottom>
                📈 Call Volume (24h)
              </Typography>
              <ResponsiveContainer width="100%" height="90%">
                <LineChart data={callData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="time" />
                  <YAxis />
                  <Tooltip />
                  <Line
                    type="monotone"
                    dataKey="calls"
                    stroke="#00d4ff"
                    strokeWidth={3}
                    dot={{ fill: '#00d4ff', strokeWidth: 2, r: 6 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </Paper>
          </motion.div>
        </Grid>

        {/* Performance Metrics */}
        <Grid item xs={12} md={4}>
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
          >
            <Paper sx={{ p: 3, height: 400 }}>
              <Typography variant="h6" gutterBottom>
                ⚡ Performance Metrics
              </Typography>
              
              <Box mb={3}>
                <Typography variant="body2" color="textSecondary">
                  AI Response Time
                </Typography>
                <Typography variant="h6" color="primary">
                  {stats.aiResponseTime}ms
                </Typography>
                <LinearProgress
                  variant="determinate"
                  value={Math.max(0, 100 - (stats.aiResponseTime - 800) / 10)}
                  sx={{ mt: 1 }}
                />
              </Box>

              <Box mb={3}>
                <Typography variant="body2" color="textSecondary">
                  Customer Satisfaction
                </Typography>
                <Typography variant="h6" color="success.main">
                  {stats.customerSatisfaction}%
                </Typography>
                <LinearProgress
                  variant="determinate"
                  value={stats.customerSatisfaction}
                  color="success"
                  sx={{ mt: 1 }}
                />
              </Box>

              <Box>
                <Typography variant="body2" color="textSecondary">
                  System Uptime
                </Typography>
                <Typography variant="h6" color="info.main">
                  99.9%
                </Typography>
                <LinearProgress
                  variant="determinate"
                  value={99.9}
                  color="info"
                  sx={{ mt: 1 }}
                />
              </Box>
            </Paper>
          </motion.div>
        </Grid>
      </Grid>
    </Box>
  );
};

export default Dashboard;