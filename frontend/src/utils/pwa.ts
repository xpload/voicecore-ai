// PWA utilities for service worker registration and offline support

export const registerServiceWorker = async () => {
  if ('serviceWorker' in navigator) {
    try {
      const registration = await navigator.serviceWorker.register('/service-worker.js');
      console.log('Service Worker registered:', registration);

      // Check for updates
      registration.addEventListener('updatefound', () => {
        const newWorker = registration.installing;
        if (newWorker) {
          newWorker.addEventListener('statechange', () => {
            if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
              // New service worker available
              console.log('New service worker available');
              // Notify user about update
              if (window.confirm('New version available! Reload to update?')) {
                window.location.reload();
              }
            }
          });
        }
      });

      return registration;
    } catch (error) {
      console.error('Service Worker registration failed:', error);
      throw error;
    }
  } else {
    console.warn('Service Workers not supported');
    return null;
  }
};

export const unregisterServiceWorker = async () => {
  if ('serviceWorker' in navigator) {
    const registration = await navigator.serviceWorker.ready;
    await registration.unregister();
    console.log('Service Worker unregistered');
  }
};

export const checkOnlineStatus = () => {
  return navigator.onLine;
};

export const addOnlineListener = (callback: () => void) => {
  window.addEventListener('online', callback);
  return () => window.removeEventListener('online', callback);
};

export const addOfflineListener = (callback: () => void) => {
  window.addEventListener('offline', callback);
  return () => window.removeEventListener('offline', callback);
};

// IndexedDB for offline data storage
export const openOfflineDB = (): Promise<IDBDatabase> => {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open('voicecore-offline', 1);

    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve(request.result);

    request.onupgradeneeded = (event) => {
      const db = (event.target as IDBOpenDBRequest).result;
      
      if (!db.objectStoreNames.contains('pendingActions')) {
        db.createObjectStore('pendingActions', { keyPath: 'id', autoIncrement: true });
      }
      
      if (!db.objectStoreNames.contains('cachedData')) {
        db.createObjectStore('cachedData', { keyPath: 'key' });
      }
    };
  });
};

export const savePendingAction = async (action: any) => {
  const db = await openOfflineDB();
  return new Promise((resolve, reject) => {
    const transaction = db.transaction(['pendingActions'], 'readwrite');
    const store = transaction.objectStore('pendingActions');
    const request = store.add(action);

    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve(request.result);
  });
};

export const cacheData = async (key: string, data: any) => {
  const db = await openOfflineDB();
  return new Promise((resolve, reject) => {
    const transaction = db.transaction(['cachedData'], 'readwrite');
    const store = transaction.objectStore('cachedData');
    const request = store.put({ key, data, timestamp: Date.now() });

    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve(request.result);
  });
};

export const getCachedData = async (key: string) => {
  const db = await openOfflineDB();
  return new Promise((resolve, reject) => {
    const transaction = db.transaction(['cachedData'], 'readonly');
    const store = transaction.objectStore('cachedData');
    const request = store.get(key);

    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve(request.result?.data);
  });
};

// Request notification permission
export const requestNotificationPermission = async () => {
  if ('Notification' in window) {
    const permission = await Notification.requestPermission();
    return permission === 'granted';
  }
  return false;
};

// Show notification
export const showNotification = (title: string, options?: NotificationOptions) => {
  if ('Notification' in window && Notification.permission === 'granted') {
    return new Notification(title, {
      icon: '/logo192.png',
      badge: '/logo192.png',
      ...options,
    });
  }
  return null;
};

// Check if app is installed (PWA)
export const isAppInstalled = () => {
  return window.matchMedia('(display-mode: standalone)').matches ||
         (window.navigator as any).standalone === true;
};

// Prompt to install PWA
export const promptInstall = (deferredPrompt: any) => {
  if (deferredPrompt) {
    deferredPrompt.prompt();
    return deferredPrompt.userChoice;
  }
  return Promise.resolve({ outcome: 'dismissed' });
};
