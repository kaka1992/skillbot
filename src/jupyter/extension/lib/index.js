"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
const comm_1 = require("./comm");
const sql_1 = require("./sql");
const plugins = [comm_1.commPlugin, sql_1.sqlPlugin];
exports.default = plugins;
