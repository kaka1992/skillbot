import { JupyterFrontEnd, JupyterFrontEndPlugin } from '@jupyterlab/application';
import { ICommandPalette } from '@jupyterlab/apputils';
import { CodeMirrorEditor } from '@jupyterlab/codemirror';
import { INotebookTracker } from '@jupyterlab/notebook';
import { format, FormatOptionsWithLanguage } from 'sql-formatter';

import { sql, SQLConfig } from '@codemirror/lang-sql';
import { Compartment, Prec } from '@codemirror/state';
import { EditorView } from '@codemirror/view';

// ---- pure SQL helpers ----

function isSqlCell(code: string): boolean {
  const first = code.trimStart().split('\n')[0] || '';
  return first.startsWith('%%sql');
}

function formatCell(code: string, dialect: string): string {
  const lines = code.split('\n');
  const i = lines.findIndex(l => l.trimStart().startsWith('%%sql'));
  const magic = lines.slice(0, i + 1).join('\n');
  const sqlBody = lines.slice(i + 1).join('\n').trim();
  if (!sqlBody) return code;

  const body = format(sqlBody, {
    language: dialect as FormatOptionsWithLanguage['language'],
    tabWidth: 2,
    keywordCase: 'upper',
    linesBetweenQueries: 2,
  });
  return `${magic}\n${body}`;
}

function getEditor(cell: any): { editor: CodeMirrorEditor; view: EditorView } | null {
  const e = cell?.editor as CodeMirrorEditor | undefined;
  if (!e?.injectExtension) return null;
  return { editor: e, view: e.editor };
}

// ---- CodeMirror SQL highlighting ----

const sqlConf: SQLConfig = {};
const sqlCompartment = new Compartment();

function toggleHighlight(e: CodeMirrorEditor, view: EditorView, active: boolean): void {
  if (!active) {
    view.dispatch({ effects: sqlCompartment.reconfigure([]) });
    return;
  }
  try {
    e.injectExtension(Prec.highest(sqlCompartment.of([])));
  } catch {
    // already injected
  }
  view.dispatch({ effects: sqlCompartment.reconfigure(sql(sqlConf)) });
}

// ---- JupyterLab plugin ----

const CMD = 'skillbot:format-sql';

export const sqlPlugin: JupyterFrontEndPlugin<void> = {
  id: 'skillbot:sql-tools',
  autoStart: true,
  requires: [INotebookTracker],
  optional: [ICommandPalette],
  activate: (
    app: JupyterFrontEnd,
    tracker: INotebookTracker,
    palette: ICommandPalette | null,
  ) => {
    const dialect = 'spark';
    let active: { editor: CodeMirrorEditor; view: EditorView } | null = null;

    // ---- format command ----

    app.commands.addCommand(CMD, {
      label: 'Format SQL (%%sql cell)',
      execute: () => {
        const cell = tracker.activeCell;
        if (!cell) return;
        const code = cell.model.sharedModel.getSource();
        if (!isSqlCell(code)) return;
        cell.model.sharedModel.setSource(formatCell(code, dialect));
      },
    });

    if (palette) {
      palette.addItem({ command: CMD, category: 'skillbot' });
    }

    app.commands.addKeyBinding({
      command: CMD,
      keys: ['Ctrl Shift F'],
      selector: '.jp-Notebook-cell',
    });

    // ---- SQL highlighting on active cell change ----

    tracker.activeCellChanged.connect((_, cell) => {
      if (active) {
        toggleHighlight(active.editor, active.view, false);
        active = null;
      }
      if (!cell) return;
      const info = getEditor(cell);
      if (!info) return;

      const code = cell.model.sharedModel.getSource();
      if (isSqlCell(code)) {
        toggleHighlight(info.editor, info.view, true);
        active = info;
      }
    });
  },
};
