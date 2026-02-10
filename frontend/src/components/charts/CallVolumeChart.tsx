import React from 'react';
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { Box, ToggleButtonGroup, ToggleButton } from '@mui/material';
import { ShowChart, BarChart as BarChartIcon, AreaChart as AreaChartIcon } from '@mui/icons-material';

interface CallVolumeData {
  time: string;
  calls: number;
  answered: number;
  missed: number;
}

interface CallVolumeChartProps {
  data?: CallVolumeData[];
  height?: number;
}

const CallVolumeChart: React.FC<CallVolumeChartProps> = ({ data, height = 300 }) => {
  const [chartType, setChartType] = React.useState<'line' | 'bar' | 'area'>('line');

  const defaultData: CallVolumeData[] = [
    { time: '00:00', calls: 45, answered: 42, missed: 3 },
    { time: '04:00', calls: 32, answered: 30, missed: 2 },
    { time: '08:00', calls: 89, answered: 85, missed: 4 },
    { time: '12:00', calls: 124, answered: 118, missed: 6 },
    { time: '16:00', calls: 156, answered: 148, missed: 8 },
    { time: '20:00', calls: 98, answered: 92, missed: 6 },
  ];

  const chartData = data || defaultData;

  const renderChart = () => {
    const commonProps = {
      data: chartData,
      margin: { top: 5, right: 30, left: 20, bottom: 5 },
    };

    switch (chartType) {
      case 'bar':
        return (
          <BarChart {...commonProps}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="time" />
            <YAxis />
            <Tooltip />
            <Legend />
            <Bar dataKey="answered" fill="#4caf50" name="Answered" />
            <Bar dataKey="missed" fill="#f44336" name="Missed" />
          </BarChart>
        );

      case 'area':
        return (
          <AreaChart {...commonProps}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="time" />
            <YAxis />
            <Tooltip />
            <Legend />
            <Area
              type="monotone"
              dataKey="calls"
              stackId="1"
              stroke="#00d4ff"
              fill="#00d4ff"
              fillOpacity={0.6}
              name="Total Calls"
            />
          </AreaChart>
        );

      case 'line':
      default:
        return (
          <LineChart {...commonProps}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="time" />
            <YAxis />
            <Tooltip />
            <Legend />
            <Line
              type="monotone"
              dataKey="calls"
              stroke="#00d4ff"
              strokeWidth={2}
              dot={{ fill: '#00d4ff', r: 4 }}
              name="Total Calls"
            />
            <Line
              type="monotone"
              dataKey="answered"
              stroke="#4caf50"
              strokeWidth={2}
              dot={{ fill: '#4caf50', r: 4 }}
              name="Answered"
            />
            <Line
              type="monotone"
              dataKey="missed"
              stroke="#f44336"
              strokeWidth={2}
              dot={{ fill: '#f44336', r: 4 }}
              name="Missed"
            />
          </LineChart>
        );
    }
  };

  return (
    <Box>
      <Box sx={{ mb: 2, display: 'flex', justifyContent: 'flex-end' }}>
        <ToggleButtonGroup
          value={chartType}
          exclusive
          onChange={(_, value) => value && setChartType(value)}
          size="small"
        >
          <ToggleButton value="line">
            <ShowChart fontSize="small" />
          </ToggleButton>
          <ToggleButton value="bar">
            <BarChartIcon fontSize="small" />
          </ToggleButton>
          <ToggleButton value="area">
            <AreaChartIcon fontSize="small" />
          </ToggleButton>
        </ToggleButtonGroup>
      </Box>
      <ResponsiveContainer width="100%" height={height}>
        {renderChart()}
      </ResponsiveContainer>
    </Box>
  );
};

export default CallVolumeChart;
