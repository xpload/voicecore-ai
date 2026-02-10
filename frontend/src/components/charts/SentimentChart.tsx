import React from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts';
import { Box, Typography } from '@mui/material';

interface SentimentData {
  name: string;
  value: number;
  color: string;
}

interface SentimentChartProps {
  data?: SentimentData[];
  height?: number;
}

const SentimentChart: React.FC<SentimentChartProps> = ({ data, height = 300 }) => {
  const defaultData: SentimentData[] = [
    { name: 'Happy', value: 45, color: '#4caf50' },
    { name: 'Neutral', value: 30, color: '#2196f3' },
    { name: 'Frustrated', value: 15, color: '#ff9800' },
    { name: 'Angry', value: 7, color: '#f44336' },
    { name: 'Sad', value: 3, color: '#9c27b0' },
  ];

  const chartData = data || defaultData;

  const renderCustomLabel = (entry: any) => {
    return `${entry.name}: ${entry.value}%`;
  };

  return (
    <Box>
      <ResponsiveContainer width="100%" height={height}>
        <PieChart>
          <Pie
            data={chartData}
            cx="50%"
            cy="50%"
            labelLine={false}
            label={renderCustomLabel}
            outerRadius={80}
            fill="#8884d8"
            dataKey="value"
          >
            {chartData.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={entry.color} />
            ))}
          </Pie>
          <Tooltip />
          <Legend />
        </PieChart>
      </ResponsiveContainer>
    </Box>
  );
};

export default SentimentChart;
