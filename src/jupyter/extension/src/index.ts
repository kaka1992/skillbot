import { JupyterFrontEndPlugin } from '@jupyterlab/application';
import { panelPlugin } from './panel';
import { sqlPlugin } from './sql';
import { galleryPlugin } from './gallery';
import { commPlugin } from './comm';

const plugins: JupyterFrontEndPlugin<void>[] = [
  panelPlugin,
  sqlPlugin,
  galleryPlugin,
  commPlugin,
];
export default plugins;
