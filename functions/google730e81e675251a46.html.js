export function onRequest(context) {
  return new Response("google-site-verification: google730e81e675251a46.html", {
    headers: { "Content-Type": "text/plain; charset=utf-8" },
  });
}
