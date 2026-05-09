const http = require("http");
const fs = require("fs");
const path = require("path");

const PORT = process.env.PORT || 5175;
const API = process.env.API_TARGET || "http://127.0.0.1:9000";
const DIST = path.join(__dirname, "dist");
const MIME = { ".html": "text/html", ".js": "application/javascript", ".css": "text/css", ".json": "application/json", ".png": "image/png", ".svg": "image/svg+xml", ".ico": "image/x-icon" };

const API_PREFIXES = ["/sessions", "/skills", "/health"];

const server = http.createServer((req, res) => {
  if (API_PREFIXES.some(p => req.url.startsWith(p))) {
    const target = new URL(API + req.url);
    const opts = {
      method: req.method,
      hostname: target.hostname,
      port: target.port,
      path: target.pathname + target.search,
      headers: { ...req.headers, host: target.host },
    };
    const proxy = http.request(opts, proxyRes => {
      res.writeHead(proxyRes.statusCode, proxyRes.headers);
      proxyRes.pipe(res);
    });
    proxy.on("error", () => { res.writeHead(502); res.end("Bad Gateway"); });
    req.pipe(proxy);
    return;
  }
  let filePath = path.join(DIST, req.url === "/" ? "index.html" : req.url);
  fs.stat(filePath, (err, stat) => {
    if (err || stat.isDirectory()) filePath = path.join(DIST, "index.html");
    const ext = path.extname(filePath);
    res.writeHead(200, { "Content-Type": MIME[ext] || "application/octet-stream" });
    fs.createReadStream(filePath).pipe(res);
  });
});

server.listen(PORT, () => console.log(`WebUI http://localhost:${PORT} -> API ${API}`));
