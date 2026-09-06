// Rendu ciblé d'un seul élément : npm run build -- --nom=<id>
import {bundle} from '@remotion/bundler';
import {renderMedia, selectComposition, RenderInternals} from '@remotion/renderer';
import {execFileSync} from 'node:child_process';
import {existsSync, mkdirSync, unlinkSync} from 'node:fs';
import path from 'node:path';
import {OUT_DIR, VIDEO} from '../src/config';
import {ELEMENTS} from '../src/elements/registry';

const arg = process.argv.find((a) => a.startsWith('--nom='));
const id = arg?.slice('--nom='.length);
if (!id) {
  console.error('Usage : npm run build -- --nom=<id>');
  console.error('Éléments : ' + ELEMENTS.map((e) => e.id).join(', '));
  process.exit(1);
}
const el = ELEMENTS.find((e) => e.id === id);
if (!el) {
  console.error(`Élément inconnu : ${id}`);
  console.error('Éléments : ' + ELEMENTS.map((e) => e.id).join(', '));
  process.exit(1);
}

const ext = el.alpha ? 'mov' : 'mp4';
const outFile = path.resolve(OUT_DIR, `${el.id}.${ext}`);
mkdirSync(path.dirname(outFile), {recursive: true});
if (existsSync(outFile)) unlinkSync(outFile);

const probe = (file: string) => {
  const ffprobe = RenderInternals.getExecutablePath({
    type: 'ffprobe',
    indent: false,
    logLevel: 'error',
    binariesDirectory: null,
  });
  const lib = path.dirname(ffprobe);
  const out = execFileSync(
    ffprobe,
    [
      '-v', 'error',
      '-select_streams', 'v:0',
      '-show_entries', 'stream=codec_name,pix_fmt,width,height,r_frame_rate,nb_frames',
      '-of', 'default=noprint_wrappers=1',
      file,
    ],
    {env: {...process.env, LD_LIBRARY_PATH: lib, DYLD_LIBRARY_PATH: lib}},
  ).toString();
  return Object.fromEntries(out.trim().split('\n').map((l) => l.split('=')));
};

(async () => {
  const serveUrl = await bundle({entryPoint: path.resolve('src/index.ts')});
  // Optionnel : REMOTION_BROWSER=/chemin/vers/chrome pour éviter le téléchargement de Chrome Headless Shell.
  const browserExecutable = process.env.REMOTION_BROWSER ?? null;
  // REMOTION_IGNORE_CERT=1 seulement derrière un proxy TLS (environnement distant).
  const chromiumOptions = {ignoreCertificateErrors: process.env.REMOTION_IGNORE_CERT === '1'};
  const composition = await selectComposition({serveUrl, id: el.id, inputProps: el.props, browserExecutable, chromiumOptions});

  await renderMedia({
    composition,
    serveUrl,
    inputProps: el.props,
    outputLocation: outFile,
    browserExecutable,
    chromiumOptions,
    ...(el.alpha
      ? {
          codec: 'prores' as const,
          proResProfile: '4444' as const,
          pixelFormat: 'yuva444p10le' as const,
          imageFormat: 'png' as const,
        }
      : {
          codec: 'h264' as const,
          pixelFormat: 'yuv420p' as const,
          imageFormat: 'jpeg' as const,
          jpegQuality: 95,
        }),
  });

  // Vérification ffprobe avant livraison.
  const info = probe(outFile);
  const errors: string[] = [];
  if (info.width !== String(VIDEO.width) || info.height !== String(VIDEO.height)) {
    errors.push(`résolution ${info.width}x${info.height}`);
  }
  if (info.r_frame_rate !== `${VIDEO.fps}/1`) errors.push(`fps ${info.r_frame_rate}`);
  if (el.alpha) {
    if (info.codec_name !== 'prores') errors.push(`codec ${info.codec_name}`);
    if (!info.pix_fmt?.startsWith('yuva')) errors.push(`pas de canal alpha (pix_fmt ${info.pix_fmt})`);
  } else if (info.codec_name !== 'h264') {
    errors.push(`codec ${info.codec_name}`);
  }
  if (errors.length) {
    unlinkSync(outFile);
    console.error('ÉCHEC — fichier supprimé : ' + errors.join(', '));
    process.exit(1);
  }

  const seconds = el.durationInFrames / VIDEO.fps;
  console.log(`${path.relative(process.cwd(), outFile)} — ${seconds}s (${el.durationInFrames} img, ${info.codec_name} ${info.pix_fmt})`);
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
