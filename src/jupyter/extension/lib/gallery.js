"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.galleryPlugin = void 0;
// ---------------------------------------------------------------------------
// Skills Gallery plugin
// ---------------------------------------------------------------------------
// Registers the left-hand SkillsGalleryWidget, wires it to the active
// notebook's kernel (so it can pull skills + the knowledge base), and exposes
// an "open" command via the command palette. Clicking a knowledge doc renders
// its HTML in a main-area tab.
// ---------------------------------------------------------------------------
const application_1 = require("@jupyterlab/application");
const apputils_1 = require("@jupyterlab/apputils");
const notebook_1 = require("@jupyterlab/notebook");
const widgets_1 = require("@lumino/widgets");
const ui_components_1 = require("@jupyterlab/ui-components");
const galleryWidget_1 = require("./galleryWidget");
// Simple sparkle mark — matches the ✦ avatar used across skillbot surfaces.
const gallerySvg = `
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
  <path d="M12 3l1.9 5.6L19.5 10.5 13.9 12.4 12 18l-1.9-5.6L4.5 10.5 10.1 8.6z"/>
</svg>`;
const galleryIcon = new ui_components_1.LabIcon({
    name: 'skillbot:gallery-icon',
    svgstr: gallerySvg,
});
const OPEN_CMD = 'skillbot:open-gallery';
/** Render a rendered-HTML KB doc inside an isolated iframe main-area tab. */
function makeDocWidget(title, html, docId) {
    const content = new widgets_1.Widget();
    content.node.style.overflow = 'hidden';
    const iframe = document.createElement('iframe');
    iframe.style.width = '100%';
    iframe.style.height = '100%';
    iframe.style.border = 'none';
    iframe.setAttribute('sandbox', 'allow-scripts allow-popups allow-popups-to-escape-sandbox');
    // Deep-link handshake: the KB page announces `kb-ready`, then we post the
    // target doc id so it jumps straight to that card's reader view. No race —
    // the listener is registered before `srcdoc` is set, and the iframe's script
    // cannot run (nor emit `kb-ready`) until after the document loads.
    const onMessage = (ev) => {
        var _a;
        if (ev.source === iframe.contentWindow && (ev.data || {}).type === 'kb-ready') {
            (_a = iframe.contentWindow) === null || _a === void 0 ? void 0 : _a.postMessage({ type: 'kb-open', id: docId }, '*');
        }
    };
    window.addEventListener('message', onMessage);
    content.disposed.connect(() => window.removeEventListener('message', onMessage));
    iframe.srcdoc = html;
    content.node.appendChild(iframe);
    const widget = new apputils_1.MainAreaWidget({ content });
    widget.title.label = title;
    widget.title.icon = galleryIcon;
    widget.title.closable = true;
    return widget;
}
exports.galleryPlugin = {
    id: 'skillbot:gallery',
    autoStart: true,
    requires: [notebook_1.INotebookTracker],
    optional: [apputils_1.ICommandPalette, application_1.ILayoutRestorer],
    activate: (app, tracker, palette, restorer) => {
        const gallery = new galleryWidget_1.SkillsGalleryWidget();
        gallery.id = 'skillbot-gallery';
        gallery.title.icon = galleryIcon;
        gallery.title.caption = 'skillbot — skills & knowledge';
        // Open each requested KB doc in its own main-area tab.
        gallery.onDocOpen = (doc, html) => {
            const w = makeDocWidget(doc.title, html, doc.id);
            app.shell.add(w, 'main', { mode: 'tab-after' });
            app.shell.activateById(w.id);
        };
        app.shell.add(gallery, 'left', { rank: 500 });
        if (restorer)
            restorer.add(gallery, 'skillbot-gallery');
        // ---- kernel wiring: follow the active notebook's kernel ----
        let _ctx = null;
        const onKernelChanged = (_s, args) => {
            if (args.oldValue)
                gallery.resetComm();
            if (args.newValue)
                gallery.connectKernel(args.newValue);
        };
        const bind = () => {
            var _a, _b;
            const nb = tracker.currentWidget;
            const ctx = (_a = nb === null || nb === void 0 ? void 0 : nb.context) === null || _a === void 0 ? void 0 : _a.sessionContext;
            if (!ctx || ctx === _ctx)
                return;
            if (_ctx)
                _ctx.kernelChanged.disconnect(onKernelChanged);
            _ctx = ctx;
            ctx.kernelChanged.connect(onKernelChanged);
            const k = (_b = ctx.session) === null || _b === void 0 ? void 0 : _b.kernel;
            if (k)
                gallery.connectKernel(k);
        };
        tracker.currentChanged.connect(bind);
        bind();
        // ---- open command (+ palette entry) ----
        app.commands.addCommand(OPEN_CMD, {
            label: 'Show Skills Gallery',
            icon: galleryIcon,
            execute: () => {
                app.shell.activateById(gallery.id);
                gallery.refresh();
            },
        });
        if (palette)
            palette.addItem({ command: OPEN_CMD, category: 'skillbot' });
    },
};
