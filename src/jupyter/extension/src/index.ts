import { JupyterFrontEndPlugin } from '@jupyterlab/application';
import { commPlugin } from './comm';
import { sqlPlugin } from './sql';

const plugins: JupyterFrontEndPlugin<void>[] = [commPlugin, sqlPlugin];
export default plugins;
