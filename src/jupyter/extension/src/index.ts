import { JupyterFrontEndPlugin } from '@jupyterlab/application';
import { commPlugin } from './comm';
import { panelPlugin } from './panel';
import { sqlPlugin } from './sql';

const plugins: JupyterFrontEndPlugin<void>[] = [commPlugin, sqlPlugin, panelPlugin];
export default plugins;
