// Outils communs aux générateurs de sons (scripts/gen-*.ts) : bruit déterministe, filtres, écriture WAV.
import {mkdirSync, writeFileSync} from 'node:fs';
import path from 'node:path';

export const SR = 48000; // fréquence d'échantillonnage vidéo

// Bruit blanc déterministe dans [-1, 1[ : le même fichier à chaque génération.
export const creerBruit = (graine = 0x9e3779b9) => {
  let g = graine;
  return () => {
    g = (g + 0x6d2b79f5) | 0;
    let t = Math.imul(g ^ (g >>> 15), 1 | g);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 2147483648 - 1;
  };
};

// Filtres biquad (RBJ), 2e ordre ; cascader deux fois pour un 4e ordre.
export type Biquad = {b0: number; b1: number; b2: number; a1: number; a2: number};
export const passeBas = (f: number, q = Math.SQRT1_2): Biquad => {
  const w = (2 * Math.PI * f) / SR, c = Math.cos(w), al = Math.sin(w) / (2 * q), a0 = 1 + al;
  return {b0: (1 - c) / 2 / a0, b1: (1 - c) / a0, b2: (1 - c) / 2 / a0, a1: (-2 * c) / a0, a2: (1 - al) / a0};
};
export const passeHaut = (f: number, q = Math.SQRT1_2): Biquad => {
  const w = (2 * Math.PI * f) / SR, c = Math.cos(w), al = Math.sin(w) / (2 * q), a0 = 1 + al;
  return {b0: (1 + c) / 2 / a0, b1: -(1 + c) / a0, b2: (1 + c) / 2 / a0, a1: (-2 * c) / a0, a2: (1 - al) / a0};
};
export const filtrer = (x: Float64Array, {b0, b1, b2, a1, a2}: Biquad) => {
  let x1 = 0, x2 = 0, y1 = 0, y2 = 0;
  for (let i = 0; i < x.length; i++) {
    const y = b0 * x[i] + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2;
    x2 = x1; x1 = x[i]; y2 = y1; y1 = y; x[i] = y;
  }
};

export const rms = (x: Float64Array) => Math.sqrt(x.reduce((a, v) => a + v * v, 0) / x.length);

// Fondu en cosinus sur la fin, jusqu'au zéro exact.
export const fonduFinal = (x: Float64Array, secondes: number) => {
  const n = Math.round(secondes * SR);
  for (let i = 0; i < n; i++) x[x.length - 1 - i] *= 0.5 - 0.5 * Math.cos((Math.PI * i) / n);
};

// Réverbération de type Schroeder/Freeverb, stéréo (8 filtres en peigne amortis + 4 passe-tout par canal).
// rt60 : durée de décroissance de 60 dB (s) ; amortissement : 0 = clair, 0,9 = très sombre ;
// taille : multiplie les retards (1 = pièce, 2,5 = grand espace ouvert) ; ecart : décorrélation droite (éch.).
export const reverbe = (
  x: Float64Array,
  {rt60, amortissement, taille = 1, ecart = 23}: {rt60: number; amortissement: number; taille?: number; ecart?: number},
): [Float64Array, Float64Array] => {
  const echelle = SR / 44100;
  const peignes = [1116, 1188, 1277, 1356, 1422, 1491, 1557, 1617].map((d) => Math.round(d * taille * echelle));
  const passeTout = [556, 441, 341, 225].map((d) => Math.round(d * echelle));
  const canal = (dec: number) => {
    const out = new Float64Array(x.length);
    for (const d0 of peignes) {
      const d = d0 + dec;
      const g = Math.pow(10, (-3 * d) / SR / rt60);
      const buf = new Float64Array(d);
      let idx = 0, lp = 0;
      for (let i = 0; i < x.length; i++) {
        const y = buf[idx];
        lp = y * (1 - amortissement) + lp * amortissement;
        buf[idx] = x[i] + lp * g;
        out[i] += y;
        idx = (idx + 1) % d;
      }
    }
    for (const a0 of passeTout) {
      const d = a0 + dec;
      const buf = new Float64Array(d);
      let idx = 0;
      for (let i = 0; i < out.length; i++) {
        const b = buf[idx];
        buf[idx] = out[i] + b * 0.5;
        out[i] = b - out[i];
        idx = (idx + 1) % d;
      }
    }
    return out;
  };
  return [canal(0), canal(ecart)];
};

// Normalise à la crête voulue et écrit un WAV PCM 24 bits stéréo.
// Un signal mono est écrit à l'identique sur les deux canaux.
export const ecrireWav = (chemin: string, x: Float64Array | [Float64Array, Float64Array], creteDb: number) => {
  const [g, d] = x instanceof Float64Array ? [x, x] : x;
  const crete = Math.max(...[g, d].map((c) => c.reduce((m, v) => Math.max(m, Math.abs(v)), 0)));
  const gain = Math.pow(10, creteDb / 20) / crete;
  const CANAUX = 2, OCTETS = 3;
  const n = g.length;
  const data = Buffer.alloc(n * CANAUX * OCTETS);
  const ech = (v: number) => Math.max(-8388608, Math.min(8388607, Math.round(v * gain * 8388607)));
  for (let i = 0; i < n; i++) {
    data.writeIntLE(ech(g[i]), (i * CANAUX) * OCTETS, OCTETS);
    data.writeIntLE(ech(d[i]), (i * CANAUX + 1) * OCTETS, OCTETS);
  }
  const entete = Buffer.alloc(44);
  entete.write('RIFF', 0); entete.writeUInt32LE(36 + data.length, 4); entete.write('WAVE', 8);
  entete.write('fmt ', 12); entete.writeUInt32LE(16, 16); entete.writeUInt16LE(1, 20);
  entete.writeUInt16LE(CANAUX, 22); entete.writeUInt32LE(SR, 24);
  entete.writeUInt32LE(SR * CANAUX * OCTETS, 28); entete.writeUInt16LE(CANAUX * OCTETS, 32);
  entete.writeUInt16LE(OCTETS * 8, 34); entete.write('data', 36); entete.writeUInt32LE(data.length, 40);
  const sortie = path.resolve(chemin);
  mkdirSync(path.dirname(sortie), {recursive: true});
  writeFileSync(sortie, Buffer.concat([entete, data]));
  console.log(`${path.relative(process.cwd(), sortie)} — ${(n / SR).toFixed(2)}s, crête ${creteDb} dBFS`);
};
