// ---------------------------------------------------------------------------
// Skills Gallery plugin
// ---------------------------------------------------------------------------
// Registers the left-hand SkillsGalleryWidget, wires it to the active
// notebook's kernel (so it can pull skills + the knowledge base), and exposes
// an "open" command via the command palette. Clicking a knowledge doc renders
// its HTML in a main-area tab.
// ---------------------------------------------------------------------------
import { JupyterFrontEnd, JupyterFrontEndPlugin, ILayoutRestorer } from '@jupyterlab/application';
import { ICommandPalette, MainAreaWidget } from '@jupyterlab/apputils';
import { INotebookTracker } from '@jupyterlab/notebook';
import { Widget } from '@lumino/widgets';
import { LabIcon } from '@jupyterlab/ui-components';
import { SkillsGalleryWidget } from './galleryWidget';

// Simple sparkle mark — matches the ✦ avatar used across skillbot surfaces.
const gallerySvg = `
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
  <path d="M12 3l1.9 5.6L19.5 10.5 13.9 12.4 12 18l-1.9-5.6L4.5 10.5 10.1 8.6z"/>
</svg>`;

const galleryIcon = new LabIcon({
  name: 'skillbot:gallery-icon',
  svgstr: gallerySvg,
});

const OPEN_CMD = 'skillbot:open-gallery';

/** Render a rendered-HTML KB doc inside an isolated iframe main-area tab. */
function makeDocWidget(title: string, html: string, docId: string): MainAreaWidget<Widget> {
  const content = new Widget();
  content.node.style.overflow = 'hidden';
  const iframe = document.createElement('iframe');
  iframe.style.width = '100%';
  iframe.style.height = '100%';
  iframe.style.border = 'none';
  iframe.setAttribute(
    'sandbox',
    'allow-scripts allow-popups allow-popups-to-escape-sandbox',
  );

  // Deep-link handshake: the KB page announces `kb-ready`, then we post the
  // target doc id so it jumps straight to that card's reader view. No race —
  // the listener is registered before `srcdoc` is set, and the iframe's script
  // cannot run (nor emit `kb-ready`) until after the document loads.
  const onMessage = (ev: MessageEvent) => {
    if (ev.source === iframe.contentWindow && (ev.data || {}).type === 'kb-ready') {
      iframe.contentWindow?.postMessage({ type: 'kb-open', id: docId }, '*');
    }
  };
  window.addEventListener('message', onMessage);
  content.disposed.connect(() => window.removeEventListener('message', onMessage));

  iframe.srcdoc = html;
  content.node.appendChild(iframe);

  const widget = new MainAreaWidget({ content });
  widget.title.label = title;
  widget.title.icon = galleryIcon;
  widget.title.closable = true;
  return widget;
}

export const galleryPlugin: JupyterFrontEndPlugin<void> = {
  id: 'skillbot:gallery',
  autoStart: true,
  requires: [INotebookTracker],
  optional: [ICommandPalette, ILayoutRestorer],
  activate: (
    app: JupyterFrontEnd,
    tracker: INotebookTracker,
    palette: ICommandPalette | null,
    restorer: ILayoutRestorer | null,
  ) => {
    const gallery = new SkillsGalleryWidget();
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
    if (restorer) restorer.add(gallery, 'skillbot-gallery');

    // ---- kernel wiring: follow the active notebook's kernel ----
    let _ctx: any = null;
    const onKernelChanged = (_s: any, args: any) => {
      if (args.oldValue) gallery.resetComm();
      if (args.newValue) gallery.connectKernel(args.newValue);
    };
    const bind = () => {
      const nb = tracker.currentWidget;
      const ctx = nb?.context?.sessionContext;
      if (!ctx || ctx === _ctx) return;
      if (_ctx) _ctx.kernelChanged.disconnect(onKernelChanged);
      _ctx = ctx;
      ctx.kernelChanged.connect(onKernelChanged);
      const k = ctx.session?.kernel;
      if (k) gallery.connectKernel(k);
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
    if (palette) palette.addItem({ command: OPEN_CMD, category: 'skillbot' });
  },
};
