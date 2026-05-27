"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
const panel_1 = require("./panel");
const sql_1 = require("./sql");
const plugins = [panel_1.panelPlugin, sql_1.sqlPlugin];
exports.default = plugins;
