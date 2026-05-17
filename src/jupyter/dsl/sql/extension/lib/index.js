"use strict";
var __defProp = Object.defineProperty;
var __getOwnPropDesc = Object.getOwnPropertyDescriptor;
var __getOwnPropNames = Object.getOwnPropertyNames;
var __hasOwnProp = Object.prototype.hasOwnProperty;
var __export = (target, all) => {
  for (var name in all)
    __defProp(target, name, { get: all[name], enumerable: true });
};
var __copyProps = (to, from, except, desc) => {
  if (from && typeof from === "object" || typeof from === "function") {
    for (let key of __getOwnPropNames(from))
      if (!__hasOwnProp.call(to, key) && key !== except)
        __defProp(to, key, { get: () => from[key], enumerable: !(desc = __getOwnPropDesc(from, key)) || desc.enumerable });
  }
  return to;
};
var __toCommonJS = (mod) => __copyProps(__defProp({}, "__esModule", { value: true }), mod);

// src/index.ts
var index_exports = {};
__export(index_exports, {
  default: () => index_default
});
module.exports = __toCommonJS(index_exports);
var import_notebook = require("@jupyterlab/notebook");
var PLUGIN_ID = "@skillbot/sql-cell:plugin";
var SQL_MIME = "text/x-sql";
var PYTHON_MIME = "text/x-python";
function isSqlCell(cell) {
  try {
    const text = cell.model.sharedModel.getSource();
    return text.trimStart().startsWith("%%sql");
  } catch {
    return false;
  }
}
function getMimeType(cell) {
  try {
    return cell.editor.model.mimeType || "";
  } catch {
    return "";
  }
}
function setMimeType(cell, mime) {
  try {
    const model = cell.editor.model;
    if (model.mimeType !== mime) {
      model.mimeType = mime;
    }
  } catch {
  }
}
function updateNotebook(panel) {
  const notebook = panel.content;
  notebook.widgets.forEach((cell) => {
    if (cell.model.type === "code") {
      const codeCell = cell;
      if (isSqlCell(codeCell)) {
        if (getMimeType(codeCell) !== SQL_MIME) {
          setMimeType(codeCell, SQL_MIME);
        }
      } else {
        if (getMimeType(codeCell) === SQL_MIME) {
          setMimeType(codeCell, PYTHON_MIME);
        }
      }
    }
  });
}
var plugin = {
  id: PLUGIN_ID,
  autoStart: true,
  requires: [import_notebook.INotebookTracker],
  activate: (app, tracker) => {
    console.log("[%%sql] JupyterLab extension activated");
    tracker.currentChanged.connect((_, panel) => {
      if (panel) {
        updateNotebook(panel);
        panel.content.model?.sharedModel.changed.connect(() => {
          updateNotebook(panel);
        });
      }
    });
    tracker.widgetAdded.connect((_, panel) => {
      updateNotebook(panel);
      panel.content.model?.sharedModel.changed.connect(() => {
        updateNotebook(panel);
      });
    });
    tracker.forEach((panel) => {
      updateNotebook(panel);
      panel.content.model?.sharedModel.changed.connect(() => {
        updateNotebook(panel);
      });
    });
  }
};
var index_default = plugin;
