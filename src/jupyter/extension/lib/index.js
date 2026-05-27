"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
const comm_1 = require("./comm");
const panel_1 = require("./panel");
const sql_1 = require("./sql");
const plugins = [comm_1.commPlugin, sql_1.sqlPlugin, panel_1.panelPlugin];
exports.default = plugins;
