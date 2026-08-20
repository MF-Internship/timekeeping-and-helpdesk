const TITLE = "Bạn có thông báo mới";
const BODY = "Mở ứng dụng để xem nội dung sau khi xác minh quyền truy cập.";
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

self.addEventListener("push", (event) => {
  event.waitUntil(showGenericNotification(event));
});

async function showGenericNotification(event) {
  let payload;
  try {
    payload = event.data?.json();
  } catch {
    return;
  }
  if (
    payload?.version !== 1 ||
    typeof payload.reference !== "string" ||
    !UUID.test(payload.reference)
  )
    return;
  await self.registration.showNotification(TITLE, {
    body: BODY,
    data: { reference: payload.reference },
    tag: `notification-${payload.reference}`,
  });
}

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const reference = event.notification.data?.reference;
  if (typeof reference !== "string" || !UUID.test(reference)) return;
  const path = `/notifications/open/${encodeURIComponent(reference)}`;
  event.waitUntil(openSameOrigin(path));
});

async function openSameOrigin(path) {
  const target = new URL(path, self.location.origin);
  if (target.origin !== self.location.origin || !target.pathname.startsWith("/notifications/open/"))
    return;
  const windows = await self.clients.matchAll({ type: "window", includeUncontrolled: true });
  for (const client of windows) {
    if (new URL(client.url).origin === self.location.origin && "focus" in client) {
      await client.focus();
      if ("navigate" in client) await client.navigate(target.href);
      return;
    }
  }
  if (self.clients.openWindow) await self.clients.openWindow(target.href);
}
