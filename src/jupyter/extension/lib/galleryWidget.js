"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.SkillsGalleryWidget = void 0;
// ---------------------------------------------------------------------------
// SkillsGalleryWidget — read-only left-hand console
// ---------------------------------------------------------------------------
// A left-area sidebar widget that surfaces two skillbot assets:
//   • Skills   — the installed skill list (name / description / enabled)
//   • Knowledge — the risk-knowledge-base documents, grouped by category
//
// Data is pulled from the kernel over a dedicated comm target
// (`skillbot:gallery`), mirroring the Agent Panel's comm pattern. Clicking a
// knowledge doc opens its rendered HTML in a main-area tab (handled by the
// plugin via the onOpenDoc callback), keeping this widget purely a browser.
//
// Everything renders inside a shadow root so the styles never touch — and are
// never touched by — JupyterLab's native chrome.
// ---------------------------------------------------------------------------
const widgets_1 = require("@lumino/widgets");
const galleryStyles_1 = require("./galleryStyles");
const GALLERY_TARGET = 'skillbot:gallery';
class SkillsGalleryWidget extends widgets_1.Widget {
    constructor() {
        super();
        this._kernel = null;
        this._comm = null;
        this._skills = [];
        this._kbDocs = [];
        this._pendingDoc = null;
        /**
         * Set by the plugin: open a rendered KB doc (full gallery HTML) in a
         * main-area tab. Called once the doc HTML arrives over the comm.
         */
        this.onDocOpen = null;
        this.addClass('skillbot-gallery');
        this._root = this.node.attachShadow({ mode: 'open' });
        const style = document.createElement('style');
        style.textContent = galleryStyles_1.GALLERY_STYLES;
        this._root.appendChild(style);
        // header
        const header = document.createElement('div');
        header.className = 'gallery-header';
        header.innerHTML =
            '<span class="gallery-avatar">✦</span>' +
                '<span class="gallery-title">skillbot</span>';
        this._root.appendChild(header);
        // tab strip
        const tabs = document.createElement('div');
        tabs.className = 'gallery-tabs';
        this._tabSkills = document.createElement('div');
        this._tabSkills.className = 'gallery-tab active';
        this._tabSkills.textContent = 'Skills';
        this._tabSkills.onclick = () => this._switchTab('skills');
        this._tabKb = document.createElement('div');
        this._tabKb.className = 'gallery-tab';
        this._tabKb.textContent = 'Knowledge';
        this._tabKb.onclick = () => this._switchTab('kb');
        tabs.appendChild(this._tabSkills);
        tabs.appendChild(this._tabKb);
        this._root.appendChild(tabs);
        // body with two pages
        this._bodyEl = document.createElement('div');
        this._bodyEl.className = 'gallery-body';
        this._skillsPage = document.createElement('div');
        this._skillsPage.className = 'gallery-page active';
        this._kbPage = document.createElement('div');
        this._kbPage.className = 'gallery-page';
        this._bodyEl.appendChild(this._skillsPage);
        this._bodyEl.appendChild(this._kbPage);
        this._root.appendChild(this._bodyEl);
        this._renderEmpty(this._skillsPage, 'Start a kernel to load skills.');
        this._renderEmpty(this._kbPage, 'Start a kernel to load the knowledge base.');
    }
    // -- kernel wiring --------------------------------------------------------
    /** (Re)connect to a kernel and open the gallery comm. */
    connectKernel(kernel) {
        this._kernel = kernel;
        this._comm = null;
        if (!kernel)
            return;
        try {
            this._comm = kernel.createComm(GALLERY_TARGET);
            this._comm.onMsg = (m) => { var _a; return this._onMsg(((_a = m.content) === null || _a === void 0 ? void 0 : _a.data) || {}); };
            this._comm.open();
            this.refresh();
        }
        catch (e) {
            console.error('[gallery] createComm failed:', e);
        }
    }
    /** Ask the kernel to (re)send skills + kb manifest. */
    refresh() {
        if (!this._kernel)
            return;
        try {
            this._kernel.requestExecute({
                code: `get_ipython().user_ns['_gallery_refresh']()`,
                store_history: false,
            });
        }
        catch (_) { }
    }
    resetComm() {
        this._comm = null;
        this._kernel = null;
    }
    _onMsg(d) {
        var _a;
        switch (d.action) {
            case 'gallery_skills':
                this._skills = Array.isArray(d.skills) ? d.skills : [];
                this._renderSkills();
                break;
            case 'gallery_kb':
                this._kbDocs = Array.isArray(d.docs) ? d.docs : [];
                this._renderKb();
                break;
            case 'gallery_kb_html':
                if (this._pendingDoc && typeof d.html === 'string') {
                    (_a = this.onDocOpen) === null || _a === void 0 ? void 0 : _a.call(this, this._pendingDoc, d.html);
                    this._pendingDoc = null;
                }
                break;
        }
    }
    /** Request the rendered KB HTML for a doc; opens a tab when it arrives. */
    _openDoc(doc) {
        if (!this._kernel)
            return;
        this._pendingDoc = doc;
        try {
            this._kernel.requestExecute({
                code: `get_ipython().user_ns['_gallery_kb_html'](${JSON.stringify(doc.path)})`,
                store_history: false,
            });
        }
        catch (_) {
            this._pendingDoc = null;
        }
    }
    // -- rendering ------------------------------------------------------------
    _switchTab(tab) {
        const on = tab === 'skills';
        this._tabSkills.classList.toggle('active', on);
        this._tabKb.classList.toggle('active', !on);
        this._skillsPage.classList.toggle('active', on);
        this._kbPage.classList.toggle('active', !on);
    }
    _renderEmpty(page, msg) {
        page.innerHTML = '';
        const el = document.createElement('div');
        el.className = 'gallery-empty';
        el.textContent = msg;
        page.appendChild(el);
    }
    _renderSkills() {
        this._skillsPage.innerHTML = '';
        if (this._skills.length === 0) {
            this._renderEmpty(this._skillsPage, 'No skills installed.');
            return;
        }
        for (const s of this._skills) {
            const card = document.createElement('div');
            card.className = 'gallery-card';
            const head = document.createElement('div');
            head.className = 'gallery-card-head';
            const dot = document.createElement('span');
            dot.className = 'gallery-status' + (s.enabled ? ' on' : '');
            dot.title = s.enabled ? 'enabled' : 'disabled';
            const name = document.createElement('span');
            name.className = 'gallery-card-name';
            name.textContent = s.name;
            head.appendChild(dot);
            head.appendChild(name);
            card.appendChild(head);
            if (s.description) {
                const desc = document.createElement('div');
                desc.className = 'gallery-card-desc';
                desc.textContent = s.description;
                card.appendChild(desc);
            }
            this._skillsPage.appendChild(card);
        }
    }
    _renderKb() {
        this._kbPage.innerHTML = '';
        if (this._kbDocs.length === 0) {
            this._renderEmpty(this._kbPage, 'Knowledge base is empty.');
            return;
        }
        // group by category, preserving manifest order
        const seen = [];
        const byCat = {};
        for (const d of this._kbDocs) {
            const cat = d.category || 'Uncategorized';
            if (!byCat[cat]) {
                byCat[cat] = [];
                seen.push(cat);
            }
            byCat[cat].push(d);
        }
        for (const cat of seen) {
            const hd = document.createElement('div');
            hd.className = 'gallery-cat';
            hd.textContent = cat;
            this._kbPage.appendChild(hd);
            for (const doc of byCat[cat]) {
                this._kbPage.appendChild(this._kbCard(doc));
            }
        }
    }
    _kbCard(doc) {
        const card = document.createElement('div');
        card.className = 'gallery-card clickable';
        card.onclick = () => this._openDoc(doc);
        const head = document.createElement('div');
        head.className = 'gallery-card-head';
        const name = document.createElement('span');
        name.className = 'gallery-card-name';
        name.textContent = doc.title;
        head.appendChild(name);
        card.appendChild(head);
        if (doc.summary) {
            const desc = document.createElement('div');
            desc.className = 'gallery-card-desc';
            desc.textContent = doc.summary;
            card.appendChild(desc);
        }
        const tags = (doc.tags || []).slice(0, 3);
        if (tags.length) {
            const meta = document.createElement('div');
            meta.className = 'gallery-card-meta';
            for (const t of tags) {
                const chip = document.createElement('span');
                chip.className = 'gallery-chip';
                chip.textContent = t;
                meta.appendChild(chip);
            }
            card.appendChild(meta);
        }
        return card;
    }
}
exports.SkillsGalleryWidget = SkillsGalleryWidget;
