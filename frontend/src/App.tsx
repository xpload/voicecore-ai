import React, { useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { ThemeProvider } from '@mui/material/styles';
import { Box, Snackbar, Alert } from '@mui/material';
import CssBaseline from '@mui/material/CssBaseline';
import { QueryClient, QueryClientProvider } from 'react-query';
import { motion } from 'framer-motion';
import { useAppStore } from '@/store';
import { createAppTheme } from '@/theme';
import { useRealTimeUpdates } from '@/hooks/useRealTimeUpdates';

// Components
import Dashboard from './components/Dashboard';
import CallCenter from './components/CallCenter';
import Analytics from './components/Analytics';
import CRM from './components/CRM';
import Settings from './components/Settings';
import Navigation from './components/Navigation';
import WebSocketStatus from './components/WebSocketStatus';
import OfflineIndicator from './components/OfflineIndicator';

// React Query client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 5 * 60 * 1000, // 5 minutes
    },
  },
});

const AppContent: React.FC = () => {
  const { isConnected, connectionError } = useRealTimeUpdates();
  const [showError, setShowError] = React.useState(false);

  useEffect(() => {
    if (connectionError) {
      setShowError(true);
    }
  }, [connectionError]);

  return (
    <>
      <div className="App" style={{ display: 'flex', minHeight: '100vh' }}>
        <Navigation />
        <motion.main
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          style={{ 
            flexGrow: 1, 
            padding: '20px',
            overflow: 'auto',
          }}
        >
          <Box sx={{ mb: 2, display: 'flex', justifyContent: 'flex-end' }}>
            <WebSocketStatus isConnected={isConnected} error={connectionError} />
          </Box>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/calls" element={<CallCenter />} />
            <Route path="/analytics" element={<Analytics />} />
            <Route path="/crm" element={<CRM />} />
            <Route path="/settings" element={<Settings />} />
          </Routes>
        </motion.main>
      </div>
      <OfflineIndicator />
      <Snackbar
        open={showError}
        autoHideDuration={6000}
        onClose={() => setShowError(false)}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        <Alert onClose={() => setShowError(false)} severity="error" sx={{ width: '100%' }}>
          {connectionError?.message || 'Connection error'}
        </Alert>
      </Snackbar>
    </>
  );
};

function App() {
  const { theme: themeMode } = useAppStore();
  const theme = createAppTheme(themeMode);

  // Apply theme CSS variables on mount and theme change
  useEffect(() => {
    const root = document.documentElement;
    const variables = themeMode === 'dark' 
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
  }, [themeMode]);

  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <Router>
          <AppContent />
        </Router>
      </ThemeProvider>
    </QueryClientProvider>
  );
}

export default App;