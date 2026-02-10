import { createTheme, Theme, ThemeOptions } from '@mui/material/styles';

// Shared theme options
const getThemeOptions = (mode: 'light' | 'dark'): ThemeOptions => ({
  palette: {
    mode,
    primary: {
      main: '#00d4ff',
      light: '#33ddff',
      dark: '#00a8cc',
      contrastText: '#ffffff',
    },
    secondary: {
      main: '#ff6b35',
      light: '#ff8c5f',
      dark: '#cc5527',
      contrastText: '#ffffff',
    },
    background: {
      default: mode === 'dark' ? '#0a0a0a' : '#f5f5f5',
      paper: mode === 'dark' ? '#1a1a1a' : '#ffffff',
    },
    text: {
      primary: mode === 'dark' ? '#ffffff' : '#000000',
      secondary: mode === 'dark' ? 'rgba(255, 255, 255, 0.7)' : 'rgba(0, 0, 0, 0.6)',
    },
    error: {
      main: '#f44336',
    },
    warning: {
      main: '#ff9800',
    },
    info: {
      main: '#2196f3',
    },
    success: {
      main: '#4caf50',
    },
  },
  typography: {
    fontFamily: '"Inter", "Roboto", "Helvetica", "Arial", sans-serif',
    h1: {
      fontSize: '2.5rem',
      fontWeight: 700,
      lineHeight: 1.2,
    },
    h2: {
      fontSize: '2rem',
      fontWeight: 600,
      lineHeight: 1.3,
    },
    h3: {
      fontSize: '1.75rem',
      fontWeight: 600,
      lineHeight: 1.4,
    },
    h4: {
      fontSize: '1.5rem',
      fontWeight: 600,
      lineHeight: 1.4,
    },
    h5: {
      fontSize: '1.25rem',
      fontWeight: 500,
      lineHeight: 1.5,
    },
    h6: {
      fontSize: '1rem',
      fontWeight: 500,
      lineHeight: 1.5,
    },
    body1: {
      fontSize: '1rem',
      lineHeight: 1.5,
    },
    body2: {
      fontSize: '0.875rem',
      lineHeight: 1.43,
    },
    button: {
      textTransform: 'none',
      fontWeight: 500,
    },
  },
  shape: {
    borderRadius: 8,
  },
  spacing: 8,
  breakpoints: {
    values: {
      xs: 0,
      sm: 600,
      md: 960,
      lg: 1280,
      xl: 1920,
    },
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 8,
          padding: '8px 16px',
          fontSize: '0.875rem',
        },
        contained: {
          boxShadow: 'none',
          '&:hover': {
            boxShadow: '0 2px 8px rgba(0, 0, 0, 0.15)',
          },
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          borderRadius: 12,
          boxShadow: mode === 'dark' 
            ? '0 2px 8px rgba(0, 0, 0, 0.3)' 
            : '0 2px 8px rgba(0, 0, 0, 0.1)',
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          backgroundImage: 'none',
        },
      },
    },
    MuiDrawer: {
      styleOverrides: {
        paper: {
          borderRight: mode === 'dark' 
            ? '1px solid rgba(255, 255, 255, 0.12)' 
            : '1px solid rgba(0, 0, 0, 0.12)',
        },
      },
    },
  },
});

export const createAppTheme = (mode: 'light' | 'dark'): Theme => {
  return createTheme(getThemeOptions(mode));
};

// CSS variables for dynamic theming
export const themeVariables = {
  light: {
    '--color-primary': '#00d4ff',
    '--color-secondary': '#ff6b35',
    '--color-background': '#f5f5f5',
    '--color-paper': '#ffffff',
    '--color-text-primary': '#000000',
    '--color-text-secondary': 'rgba(0, 0, 0, 0.6)',
  },
  dark: {
    '--color-primary': '#00d4ff',
    '--color-secondary': '#ff6b35',
    '--color-background': '#0a0a0a',
    '--color-paper': '#1a1a1a',
    '--color-text-primary': '#ffffff',
    '--color-text-secondary': 'rgba(255, 255, 255, 0.7)',
  },
};
