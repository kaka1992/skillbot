// esbuild bundler for JupyterLab extension
// External: @jupyterlab/* @lumino/* (provided by JupyterLab at runtime)
// Bundled: @codemirror/* (not exposed globally)
const esbuild = require("esbuild");

esbuild.build({
  entryPoints: ["src/index.ts"],
  bundle: true,
  platform: "browser",
  format: "cjs",
  target: "es2020",
  outfile: "lib/index.js",
  external: [
    "@jupyterlab/*",
    "@lumino/*",
  ],
  sourcemap: false,
}).catch(() => process.exit(1));
