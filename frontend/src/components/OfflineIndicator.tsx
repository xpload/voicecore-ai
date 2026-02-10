import React, { useEffect, useState } from 'react';
import { Snackbar, Alert } from '@mui/material';
import { checkOnlineStatus, addOnlineListener, addOfflineListener } from '@/utils/pwa';

const OfflineIndicator: React.FC = () => {
  const [isOnline, setIsOnline] = useState(checkOnlineStatus());
  const [showOffline, setShowOffline] = useState(false);
  const [showOnline, setShowOnline] = useState(false);

  useEffect(() => {
    const handleOnline = () => {
      setIsOnline(true);
      setShowOnline(true);
      setShowOffline(false);
    };

    const handleOffline = () => {
      setIsOnline(false);
      setShowOffline(true);
      setShowOnline(false);
    };

    const removeOnlineListener = addOnlineListener(handleOnline);
    const removeOfflineListener = addOfflineListener(handleOffline);

    return () => {
      removeOnlineListener();
      removeOfflineListener();
    };
  }, []);

  return (
    <>
      <Snackbar
        open={showOffline}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert severity="warning" sx={{ width: '100%' }}>
          You are offline. Some features may be limited.
        </Alert>
      </Snackbar>

      <Snackbar
        open={showOnline}
        autoHideDuration={3000}
        onClose={() => setShowOnline(false)}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert severity="success" sx={{ width: '100%' }}>
          You are back online!
        </Alert>
      </Snackbar>
    </>
  );
};

export default OfflineIndicator;
