/* Service Worker — maneja notificaciones push */
self.addEventListener('push', function(event) {
    let data = {};
    try { data = event.data.json(); } catch (e) { data = { title: 'Notificación', body: event.data ? event.data.text() : '' }; }
    const title = data.title || 'Consultores Expertos';
    const options = {
        body: data.body || '',
        icon: '/static/icon-192.png',
        badge: '/static/icon-72.png',
        data: data.url || '/' 
    };
    event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener('notificationclick', function(event) {
    event.notification.close();
    const url = event.notification.data || '/';
    event.waitUntil(clients.matchAll({type: 'window'}).then( windowClients => {
        for (let client of windowClients) {
            if (client.url === url && 'focus' in client) return client.focus();
        }
        if (clients.openWindow) return clients.openWindow(url);
    }));
});
