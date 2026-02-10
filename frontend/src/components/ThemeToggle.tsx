import React from 'react';
import { IconButton, Tooltip } from '@mui/material';
import { Brightness4, Brightness7 } from '@mui/icons-material';
import { useAppStore } from '@/store';

const ThemeToggle: React.FC = () => {
  const { theme, setTheme } = useAppStore();

  const handleToggle = () => {
    const newTheme = theme === 'light' ? 'dark' : 'light';
    setTheme(newTheme);
    
    // Apply CSS variables
    const root = document.documentElement;
    const variables = theme === 'light' 
      ? {
          '--color-primary': '#00d4ff',
          '--color-secondary': '#ff6b35',
          '--color-background': '#0a0a0a',
          '--color-paper': '#1a1a1a',
          '--color-text-primary': '#ffffff',
          '--color-text-secondary': 'rgba(255, 255, 255, 0.7)',
        }
      : {
          '--color-primary': '#00d4ff',
          '--color-secondary': '#ff6b35',
          '--color-background': '#f5f5f5',
          '--color-paper': '#ffffff',
          '--color-text-primary': '#000000',
          '--color-text-secondary': 'rgba(0, 0, 0, 0.6)',
        };
    
    Object.entries(variables).forEach(([key, value]) => {
      root.style.setProperty(key, value);
    });
  };

  return (
    <Tooltip title={`Switch to ${theme === 'light' ? 'dark' : 'light'} mode`}>
      <IconButton onClick={handleToggle} color="inherit">
        {theme === 'light' ? <Brightness4 /> : <Brightness7 />}
      </IconButton>
    </Tooltip>
  );
};

export default ThemeToggle;
