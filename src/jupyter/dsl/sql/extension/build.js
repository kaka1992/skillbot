// esbuild bundler — externalize @codemirror/* that JupyterLab provides at runtime
// Only bundle @codemirror/lang-sql (not provided by JupyterLab)
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
    "@codemirror/state",
    "@codemirror/view",
    "@codemirror/language",
    "@codemirror/autocomplete",
  ],
  sourcemap: false,
}).catch(() => process.exit(1));
