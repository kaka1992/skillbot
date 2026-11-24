export declare const COLLAPSE_KEY = "skillbot-sessions-collapsed";
export declare function storageKey(panel: any, path?: string): string;
export declare function saveState(panel: any): void;
export declare function restoreState(panel: any): void;
/** Load the conversation buffer for a notebook path into the visible panel. */
export declare function loadBuffer(panel: any, path: string): void;
/** Paint a serialized buffer (JSON string) into the visible panel. */
export declare function applyBuffer(panel: any, raw: string): void;
/** Map of notebook path → display label, persisted across reloads. */
export declare function loadRegistry(_panel: any): Record<string, string>;
export declare function saveRegistry(_panel: any, reg: Record<string, string>): void;
/** Register (or refresh) a notebook path as a known session. */
export declare function registerSession(panel: any, path: string): void;
/**
 * Switch the panel to a notebook's conversation. Saves the current buffer,
 * loads the target buffer, and (if it differs from the active notebook) opens
 * the corresponding .ipynb via docmanager.
 */
export declare function switchToSession(panel: any, path: string): void;
/** Open an existing notebook file in the main area. */
export declare function openNotebook(panel: any, path: string): void;
/** Create a fresh Untitled.ipynb, open it, and switch the session to it. */
export declare function newSession(panel: any): Promise<void>;
/** Rename a session's display label (persists to registry). */
export declare function renameSession(panel: any, path: string): void;
/** Delete a session record after user confirmation (from the 🗑 button). */
export declare function deleteSession(panel: any, path: string): void;
/**
 * Remove all traces of a session: registry entry, localStorage buffer, and
 * the on-disk conversation file. If it's the session currently shown, clear
 * the panel too. Shared by the 🗑 button and the notebook-file-deletion
 * listener. Does NOT touch the .ipynb file itself.
 */
export declare function purgeSession(panel: any, path: string): void;
/** Public: called by the plugin when a notebook file is deleted from disk.
 *  Silently purges the matching session record (no confirm — the file is
 *  already gone). No-op if we have no record for that path. */
export declare function onNotebookFileDeleted(panel: any, path: string): void;
/** Briefly show a message in the info bar. */
export declare function flashInfo(panel: any, msg: string): void;
export declare function toggleSessionsCollapsed(panel: any): void;
export declare function renderSessionBar(panel: any): void;
