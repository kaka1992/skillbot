import { JupyterFrontEndPlugin } from '@jupyterlab/application';
import { panelPlugin } from './panel';
import { sqlPlugin } from './sql';

const plugins: JupyterFrontEndPlugin<void>[] = [panelPlugin, sqlPlugin];
export default plugins;
