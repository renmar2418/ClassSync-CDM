export function registerServiceWorker(onUpdate?: () => void): void {
  if (typeof window !== 'undefined' && 'serviceWorker' in navigator && (process.env.NODE_ENV === 'production' || window.location.hostname !== 'localhost')) {
    window.addEventListener('load', () => {
      navigator.serviceWorker
        .register('/sw.js')
        .then((registration) => {
          registration.onupdatefound = () => {
            const installingWorker = registration.installing;
            if (installingWorker) {
              installingWorker.onstatechange = () => {
                if (installingWorker.state === 'installed') {
                  if (navigator.serviceWorker.controller) {
                    if (onUpdate) onUpdate();
                  }
                }
              };
            }
          };
        })
        .catch((error) => {
          console.warn('Service worker registration failed:', error);
        });
    });
  }
}
