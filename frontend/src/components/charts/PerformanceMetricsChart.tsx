import React from 'react';
import {
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  ResponsiveContainer,
  Legend,
} from 'recharts';

interface PerformanceData {
  metric: string;
  value: number;
  fullMark: number;
}

interface PerformanceMetricsChartProps {
  data?: PerformanceData[];
  height?: number;
}

const PerformanceMetricsChart: React.FC<PerformanceMetricsChartProps> = ({
  data,
  height = 300,
}) => {
  const defaultData: PerformanceData[] = [
    { metric: 'Response Time', value: 85, fullMark: 100 },
    { metric: 'Accuracy', value: 92, fullMark: 100 },
    { metric: 'Customer Satisfaction', value: 88, fullMark: 100 },
    { metric: 'Call Resolution', value: 78, fullMark: 100 },
    { metric: 'Uptime', value: 99, fullMark: 100 },
    { metric: 'AI Confidence', value: 87, fullMark: 100 },
  ];

  const chartData = data || defaultData;

  return (
    <ResponsiveContainer width="100%" height={height}>
      <RadarChart cx="50%" cy="50%" outerRadius="80%" data={chartData}>
        <PolarGrid />
        <PolarAngleAxis dataKey="metric" />
        <PolarRadiusAxis angle={90} domain={[0, 100]} />
        <Radar
          name="Performance"
          dataKey="value"
          stroke="#00d4ff"
          fill="#00d4ff"
          fillOpacity={0.6}
        />
        <Legend />
      </RadarChart>
    </ResponsiveContainer>
  );
};

export default PerformanceMetricsChart;
