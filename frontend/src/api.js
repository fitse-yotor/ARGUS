export async function api(path, options = {}) {
  return (await request(path, options)).json();
}
// Paged list endpoints report the unpaged match count in X-Total-Count.
export async function apiPage(path, options = {}) {
  const response = await request(path, options);
  const items = await response.json();
  return {
    items,
    total: Number(response.headers.get("X-Total-Count") ?? items.length),
  };
}
async function request(path, options) {
  const isForm = options.body instanceof FormData;
  const response = await fetch("/api" + path, {
    credentials: "same-origin",
    ...options,
    headers: {
      "X-Argus-Request": "1",
      ...(!isForm && options.body
        ? { "Content-Type": "application/json" }
        : {}),
      ...options.headers,
    },
    body: options.body && !isForm ? JSON.stringify(options.body) : options.body,
  });
  if (!response.ok) {
    let data;
    try {
      data = await response.json();
    } catch {}
    throw Error(
      typeof data?.detail === "string"
        ? data.detail
        : JSON.stringify(data?.detail || response.statusText),
    );
  }
  return response;
}
export const clock = (t) =>
  `${Math.floor((t || 0) / 60)
    .toString()
    .padStart(2, "0")}:${Math.floor((t || 0) % 60)
    .toString()
    .padStart(2, "0")}`;
