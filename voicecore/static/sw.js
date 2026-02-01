/**
 * Service Worker for VoiceCore AI Agent PWA
 * 
 * Provides offline functionality, push notifications, and background sync
 * for the enterprise virtual receptionist agent application.
 */

const CACHE_NAME = 'voicecore-agent-v1.0.0';
const STATIC_CACHE_NAME = 'voicecore-static-v1.0.0';
const DYNAMIC_CACHE_NAME = 'voicecore-dynamic-v1.0.0';

// Files to cache for offline functionality
const STATIC_FILES = [
  '/',
  '/agent/',
  '/agent/dashboard',
  '/agent/call',
  '/agent/status',
  '/agent/history',
  '/static/css/agent.css',
  '/static/js/agent.js',
  '/static/js/webrtc.js',
  '/static/js/notifications.js',
  '/static/icons/icon-192x192.png',
  '/static/icons/icon-512x512.png',
  '/static/manifest.json'
];

// API endpoints that should be cached
const CACHEABLE_APIS = [
  '/api/agent/profile',
  '/api/agent/status',
  '/api/agent/settings'
];

// API endpoints that should trigger background sync
const SYNC_APIS = [
  '/api/agent/status',
  '/api/calls/',
  '/api/agent/activity'
];

/**
 * Service Worker Installation
 */
self.addEventListener('install', event => {
  console.log('[SW] Installing Service Worker');
  
  event.waitUntil(
    Promise.all([
      // Cache static files
      caches.open(STATIC_CACHE_NAME).then(cache => {
        console.log('[SW] Caching static files');
        return cache.addAll(STATIC_FILES);
      }),
      
      // Skip waiting to activate immediately
      self.skipWaiting()
    ])
  );
});

/**
 * Service Worker Activation
 */
self.addEventListener('activate', event => {
  console.log('[SW] Activating Service Worker');
  
  event.waitUntil(
    Promise.all([
      // Clean up old caches
      caches.keys().then(cacheNames => {
        return Promise.all(
          cacheNames.map(cacheName => {
            if (cacheName !== STATIC_CACHE_NAME && 
                cacheName !== DYNAMIC_CACHE_NAME &&
                cacheName.startsWith('voicecore-')) {
              console.log('[SW] Deleting old cache:', cacheName);
              return caches.delete(cacheName);
            }
          })
        );
      }),
      
      // Take control of all clients
      self.clients.claim()
    ])
  );
});

/**
 * Fetch Event Handler
 */
self.addEventListener('fetch', event => {
  const { request } = event;
  const url = new URL(request.url);
  
  // Handle different types of requests
  if (request.method === 'GET') {
    if (isStaticFile(url.pathname)) {
      // Static files: Cache first, then network
      event.respondWith(cacheFirst(request));
    } else if (isAPIRequest(url.pathname)) {
      // API requests: Network first, then cache
      event.respondWith(networkFirst(request));
    } else {
      // Other requests: Network first with fallback
      event.respondWith(networkFirstWithFallback(request));
    }
  } else if (request.method === 'POST' || request.method === 'PUT') {
    // Handle POST/PUT requests with background sync
    if (isSyncableAPI(url.pathname)) {
      event.respondWith(handleSyncableRequest(request));
    }
  }
});

/**
 * Push Notification Handler
 */
self.addEventListener('push', event => {
  console.log('[SW] Push notification received');
  
  let notificationData = {
    title: 'VoiceCore AI',
    body: 'You have a new notification',
    icon: '/static/icons/icon-192x192.png',
    badge: '/static/icons/badge-72x72.png',
    tag: 'voicecore-notification',
    requireInteraction: false,
    actions: []
  };
  
  if (event.data) {
    try {
      const data = event.data.json();
      notificationData = { ...notificationData, ...data };
      
      // Handle different notification types
      if (data.type === 'incoming_call') {
        notificationData = {
          ...notificationData,
          title: 'Incoming Call',
          body: `Call from ${data.caller_number || 'Unknown'}`,
          tag: 'incoming-call',
          requireInteraction: true,
          actions: [
            {
              action: 'answer',
              title: 'Answer',
              icon: '/static/icons/answer-32x32.png'
            },
            {
              action: 'decline',
              title: 'Decline',
              icon: '/static/icons/decline-32x32.png'
            }
          ],
          data: {
            call_id: data.call_id,
            caller_number: data.caller_number,
            type: 'incoming_call'
          }
        };
      } else if (data.type === 'status_update') {
        notificationData = {
          ...notificationData,
          title: 'Status Update',
          body: data.message || 'Your status has been updated',
          tag: 'status-update',
          requireInteraction: false
        };
      } else if (data.type === 'system_alert') {
        notificationData = {
          ...notificationData,
          title: 'System Alert',
          body: data.message || 'System notification',
          tag: 'system-alert',
          requireInteraction: true
        };
      }
    } catch (error) {
      console.error('[SW] Error parsing push data:', error);
    }
  }
  
  event.waitUntil(
    self.registration.showNotification(notificationData.title, notificationData)
  );
});

/**
 * Notification Click Handler
 */
self.addEventListener('notificationclick', event => {
  console.log('[SW] Notification clicked:', event.notification.tag);
  
  event.notification.close();
  
  const notificationData = event.notification.data || {};
  const action = event.action;
  
  event.waitUntil(
    (async () => {
      const clients = await self.clients.matchAll({ type: 'window' });
      
      if (notificationData.type === 'incoming_call') {
        if (action === 'answer') {
          // Handle call answer
          await handleCallAction('answer', notificationData.call_id);
          await focusOrOpenClient('/agent/call?action=answer&call_id=' + notificationData.call_id, clients);
        } else if (action === 'decline') {
          // Handle call decline
          await handleCallAction('decline', notificationData.call_id);
        } else {
          // Default: open call interface
          await focusOrOpenClient('/agent/call?call_id=' + notificationData.call_id, clients);
        }
      } else {
        // Default: open agent dashboard
        await focusOrOpenClient('/agent/dashboard', clients);
      }
    })()
  );
});

/**
 * Background Sync Handler
 */
self.addEventListener('sync', event => {
  console.log('[SW] Background sync triggered:', event.tag);
  
  if (event.tag === 'agent-status-sync') {
    event.waitUntil(syncAgentStatus());
  } else if (event.tag === 'call-activity-sync') {
    event.waitUntil(syncCallActivity());
  } else if (event.tag === 'offline-actions-sync') {
    event.waitUntil(syncOfflineActions());
  }
});

/**
 * Message Handler (from main thread)
 */
self.addEventListener('message', event => {
  console.log('[SW] Message received:', event.data);
  
  const { type, data } = event.data;
  
  if (type === 'SKIP_WAITING') {
    self.skipWaiting();
  } else if (type === 'CACHE_URLS') {
    event.waitUntil(cacheUrls(data.urls));
  } else if (type === 'CLEAR_CACHE') {
    event.waitUntil(clearCache(data.cacheName));
  } else if (type === 'REGISTER_SYNC') {
    event.waitUntil(self.registration.sync.register(data.tag));
  }
});

// Helper Functions

/**
 * Check if URL is a static file
 */
function isStaticFile(pathname) {
  return pathname.startsWith('/static/') || 
         pathname.endsWith('.css') || 
         pathname.endsWith('.js') || 
         pathname.endsWith('.png') || 
         pathname.endsWith('.jpg') || 
         pathname.endsWith('.svg') ||
         pathname === '/manifest.json';
}

/**
 * Check if URL is an API request
 */
function isAPIRequest(pathname) {
  return pathname.startsWith('/api/') || pathname.startsWith('/ws/');
}

/**
 * Check if API should be synced in background
 */
function isSyncableAPI(pathname) {
  return SYNC_APIS.some(api => pathname.startsWith(api));
}

/**
 * Cache First Strategy
 */
async function cacheFirst(request) {
  try {
    const cachedResponse = await caches.match(request);
    if (cachedResponse) {
      return cachedResponse;
    }
    
    const networkResponse = await fetch(request);
    if (networkResponse.ok) {
      const cache = await caches.open(STATIC_CACHE_NAME);
      cache.put(request, networkResponse.clone());
    }
    
    return networkResponse;
  } catch (error) {
    console.error('[SW] Cache first failed:', error);
    return new Response('Offline - Resource not available', { status: 503 });
  }
}

/**
 * Network First Strategy
 */
async function networkFirst(request) {
  try {
    const networkResponse = await fetch(request);
    
    if (networkResponse.ok && CACHEABLE_APIS.some(api => request.url.includes(api))) {
      const cache = await caches.open(DYNAMIC_CACHE_NAME);
      cache.put(request, networkResponse.clone());
    }
    
    return networkResponse;
  } catch (error) {
    console.log('[SW] Network failed, trying cache:', error);
    const cachedResponse = await caches.match(request);
    
    if (cachedResponse) {
      return cachedResponse;
    }
    
    return new Response(JSON.stringify({
      error: 'Offline - Network request failed',
      offline: true
    }), {
      status: 503,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

/**
 * Network First with Fallback
 */
async function networkFirstWithFallback(request) {
  try {
    return await fetch(request);
  } catch (error) {
    const cachedResponse = await caches.match(request);
    
    if (cachedResponse) {
      return cachedResponse;
    }
    
    // Return offline page for navigation requests
    if (request.mode === 'navigate') {
      return caches.match('/agent/offline');
    }
    
    return new Response('Offline', { status: 503 });
  }
}

/**
 * Handle Syncable Requests
 */
async function handleSyncableRequest(request) {
  try {
    const response = await fetch(request);
    return response;
  } catch (error) {
    // Store request for background sync
    await storeOfflineAction(request);
    
    // Register background sync
    await self.registration.sync.register('offline-actions-sync');
    
    return new Response(JSON.stringify({
      success: true,
      offline: true,
      message: 'Request queued for sync'
    }), {
      status: 202,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

/**
 * Store Offline Action
 */
async function storeOfflineAction(request) {
  const db = await openDB();
  const transaction = db.transaction(['offline_actions'], 'readwrite');
  const store = transaction.objectStore('offline_actions');
  
  const action = {
    id: Date.now(),
    url: request.url,
    method: request.method,
    headers: Object.fromEntries(request.headers.entries()),
    body: await request.text(),
    timestamp: Date.now()
  };
  
  await store.add(action);
}

/**
 * Sync Agent Status
 */
async function syncAgentStatus() {
  try {
    // Get stored status updates
    const db = await openDB();
    const transaction = db.transaction(['agent_status'], 'readonly');
    const store = transaction.objectStore('agent_status');
    const statusUpdates = await store.getAll();
    
    for (const update of statusUpdates) {
      try {
        const response = await fetch('/api/agent/status', {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(update.data)
        });
        
        if (response.ok) {
          // Remove synced update
          const deleteTransaction = db.transaction(['agent_status'], 'readwrite');
          const deleteStore = deleteTransaction.objectStore('agent_status');
          await deleteStore.delete(update.id);
        }
      } catch (error) {
        console.error('[SW] Failed to sync status update:', error);
      }
    }
  } catch (error) {
    console.error('[SW] Agent status sync failed:', error);
  }
}

/**
 * Sync Call Activity
 */
async function syncCallActivity() {
  try {
    const db = await openDB();
    const transaction = db.transaction(['call_activity'], 'readonly');
    const store = transaction.objectStore('call_activity');
    const activities = await store.getAll();
    
    for (const activity of activities) {
      try {
        const response = await fetch('/api/calls/activity', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(activity.data)
        });
        
        if (response.ok) {
          const deleteTransaction = db.transaction(['call_activity'], 'readwrite');
          const deleteStore = deleteTransaction.objectStore('call_activity');
          await deleteStore.delete(activity.id);
        }
      } catch (error) {
        console.error('[SW] Failed to sync call activity:', error);
      }
    }
  } catch (error) {
    console.error('[SW] Call activity sync failed:', error);
  }
}

/**
 * Sync Offline Actions
 */
async function syncOfflineActions() {
  try {
    const db = await openDB();
    const transaction = db.transaction(['offline_actions'], 'readonly');
    const store = transaction.objectStore('offline_actions');
    const actions = await store.getAll();
    
    for (const action of actions) {
      try {
        const response = await fetch(action.url, {
          method: action.method,
          headers: action.headers,
          body: action.body
        });
        
        if (response.ok) {
          const deleteTransaction = db.transaction(['offline_actions'], 'readwrite');
          const deleteStore = deleteTransaction.objectStore('offline_actions');
          await deleteStore.delete(action.id);
        }
      } catch (error) {
        console.error('[SW] Failed to sync offline action:', error);
      }
    }
  } catch (error) {
    console.error('[SW] Offline actions sync failed:', error);
  }
}

/**
 * Handle Call Actions
 */
async function handleCallAction(action, callId) {
  try {
    const response = await fetch(`/api/calls/${callId}/${action}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    });
    
    if (!response.ok) {
      throw new Error(`Call ${action} failed`);
    }
    
    console.log(`[SW] Call ${action} successful`);
  } catch (error) {
    console.error(`[SW] Call ${action} failed:`, error);
  }
}

/**
 * Focus or Open Client Window
 */
async function focusOrOpenClient(url, clients) {
  // Try to focus existing client
  for (const client of clients) {
    if (client.url.includes('/agent/')) {
      await client.focus();
      client.postMessage({ type: 'NAVIGATE', url });
      return;
    }
  }
  
  // Open new client
  await self.clients.openWindow(url);
}

/**
 * Cache URLs
 */
async function cacheUrls(urls) {
  const cache = await caches.open(DYNAMIC_CACHE_NAME);
  await cache.addAll(urls);
}

/**
 * Clear Cache
 */
async function clearCache(cacheName) {
  await caches.delete(cacheName || DYNAMIC_CACHE_NAME);
}

/**
 * Open IndexedDB
 */
async function openDB() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open('VoiceCoreDB', 1);
    
    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve(request.result);
    
    request.onupgradeneeded = (event) => {
      const db = event.target.result;
      
      // Create object stores
      if (!db.objectStoreNames.contains('offline_actions')) {
        db.createObjectStore('offline_actions', { keyPath: 'id' });
      }
      
      if (!db.objectStoreNames.contains('agent_status')) {
        db.createObjectStore('agent_status', { keyPath: 'id' });
      }
      
      if (!db.objectStoreNames.contains('call_activity')) {
        db.createObjectStore('call_activity', { keyPath: 'id' });
      }
    };
  });
}