import { Widget } from '@lumino/widgets';
interface KbDoc {
    id: string;
    title: string;
    summary: string;
    category: string;
    path: string;
    source_url?: string;
    tags?: string[];
}
export declare class SkillsGalleryWidget extends Widget {
    private _root;
    private _bodyEl;
    private _skillsPage;
    private _kbPage;
    private _tabSkills;
    private _tabKb;
    private _kernel;
    private _comm;
    private _skills;
    private _kbDocs;
    private _pendingDoc;
    /**
     * Set by the plugin: open a rendered KB doc (full gallery HTML) in a
     * main-area tab. Called once the doc HTML arrives over the comm.
     */
    onDocOpen: ((doc: KbDoc, html: string) => void) | null;
    constructor();
    /** (Re)connect to a kernel and open the gallery comm. */
    connectKernel(kernel: any): void;
    /** Ask the kernel to (re)send skills + kb manifest. */
    refresh(): void;
    resetComm(): void;
    private _onMsg;
    /** Request the rendered KB HTML for a doc; opens a tab when it arrives. */
    private _openDoc;
    private _switchTab;
    private _renderEmpty;
    private _renderSkills;
    private _renderKb;
    private _kbCard;
}
export {};
