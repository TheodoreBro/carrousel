// Génère public/sons/impact-sub.wav : impact grave de cinéma, synthétisé (aucun échantillon externe).
// Sub-bass qui tombe de 75 à 40 Hz, attaque douce, courte queue sombre ; rien au-dessus de ~150 Hz.
// À relancer seulement si le son change : npx tsx scripts/gen-impact.ts
import {mkdirSync, writeFileSync} from 'node:fs';
import path from 'node:path';

const SR = 48000; // fréquence d'échantillonnage vidéo
const DUREE = 1.6; // s
const CRETE_DB = -6; // niveau crête : discret, à remonter dans Premiere si besoin
const N = Math.round(SR * DUREE);

// Bruit déterministe (même fichier à chaque génération).
let graine = 0x9e3779b9;
const bruit = () => {
  graine = (graine + 0x6d2b79f5) | 0;
  let t = Math.imul(graine ^ (graine >>> 15), 1 | graine);
  t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
  return ((t ^ (t >>> 14)) >>> 0) / 2147483648 - 1;
};

// Filtres biquad (RBJ), appliqués en place.
type Biquad = {b0: number; b1: number; b2: number; a1: number; a2: number};
const passeBas = (f: number, q = Math.SQRT1_2): Biquad => {
  const w = (2 * Math.PI * f) / SR, c = Math.cos(w), al = Math.sin(w) / (2 * q), a0 = 1 + al;
  return {b0: (1 - c) / 2 / a0, b1: (1 - c) / a0, b2: (1 - c) / 2 / a0, a1: (-2 * c) / a0, a2: (1 - al) / a0};
};
const passeHaut = (f: number, q = Math.SQRT1_2): Biquad => {
  const w = (2 * Math.PI * f) / SR, c = Math.cos(w), al = Math.sin(w) / (2 * q), a0 = 1 + al;
  return {b0: (1 + c) / 2 / a0, b1: -(1 + c) / a0, b2: (1 + c) / 2 / a0, a1: (-2 * c) / a0, a2: (1 - al) / a0};
};
const filtrer = (x: Float64Array, {b0, b1, b2, a1, a2}: Biquad) => {
  let x1 = 0, x2 = 0, y1 = 0, y2 = 0;
  for (let i = 0; i < x.length; i++) {
    const y = b0 * x[i] + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2;
    x2 = x1; x1 = x[i]; y2 = y1; y1 = y; x[i] = y;
  }
};

// 1. Corps : sinus dont la hauteur chute (75 → 40 Hz), enveloppe à attaque douce et décroissance rapide.
const corps = new Float64Array(N);
let phase = 0;
for (let i = 0; i < N; i++) {
  const t = i / SR;
  const f = 40 + 35 * Math.exp(-t / 0.07);
  phase += (2 * Math.PI * f) / SR;
  const env = (1 - Math.exp(-t / 0.006)) * Math.exp(-t / 0.3);
  // Léger second partiel, qui s'éteint vite : rend le choc perceptible sur de petites enceintes.
  corps[i] = env * (Math.sin(phase) + 0.22 * Math.exp(-t / 0.09) * Math.sin(2 * phase));
}

// 2. Choc : souffle très grave, bref, qui donne la matière du « thud ».
const choc = new Float64Array(N);
for (let i = 0; i < N; i++) {
  const t = i / SR;
  choc[i] = bruit() * (1 - Math.exp(-t / 0.003)) * Math.exp(-t / 0.035);
}
filtrer(choc, passeBas(140));
filtrer(choc, passeBas(140));

// 3. Queue sombre : grondement filtré très bas, qui s'éteint en ~1 s.
const queue = new Float64Array(N);
for (let i = 0; i < N; i++) {
  const t = i / SR;
  queue[i] = bruit() * (1 - Math.exp(-t / 0.06)) * Math.exp(-t / 0.4);
}
filtrer(queue, passeBas(85));
filtrer(queue, passeBas(85));

// Mélange (niveaux relatifs mesurés après filtrage), légère saturation pour la rondeur.
const rms = (x: Float64Array) => Math.sqrt(x.reduce((a, v) => a + v * v, 0) / x.length);
const kChoc = (0.35 * rms(corps)) / rms(choc);
const kQueue = (0.3 * rms(corps)) / rms(queue);
const mix = new Float64Array(N);
for (let i = 0; i < N; i++) mix[i] = Math.tanh(1.3 * (corps[i] + kChoc * choc[i] + kQueue * queue[i]));

// Aucun aigu, aucun infra inutile : coupe-haut 150 Hz (4e ordre), coupe-bas 28 Hz.
filtrer(mix, passeHaut(28));
filtrer(mix, passeBas(150));
filtrer(mix, passeBas(150));

// Fin propre sur les 200 dernières ms, puis normalisation à la crête voulue.
const fondu = Math.round(0.2 * SR);
for (let i = 0; i < fondu; i++) mix[N - 1 - i] *= 0.5 - 0.5 * Math.cos((Math.PI * i) / fondu);
const crete = mix.reduce((m, v) => Math.max(m, Math.abs(v)), 0);
const gain = Math.pow(10, CRETE_DB / 20) / crete;

// WAV PCM 24 bits stéréo (même signal sur les deux canaux).
const CANAUX = 2, OCTETS = 3;
const data = Buffer.alloc(N * CANAUX * OCTETS);
for (let i = 0; i < N; i++) {
  const v = Math.max(-8388608, Math.min(8388607, Math.round(mix[i] * gain * 8388607)));
  for (let c = 0; c < CANAUX; c++) data.writeIntLE(v, (i * CANAUX + c) * OCTETS, OCTETS);
}
const entete = Buffer.alloc(44);
entete.write('RIFF', 0); entete.writeUInt32LE(36 + data.length, 4); entete.write('WAVE', 8);
entete.write('fmt ', 12); entete.writeUInt32LE(16, 16); entete.writeUInt16LE(1, 20);
entete.writeUInt16LE(CANAUX, 22); entete.writeUInt32LE(SR, 24);
entete.writeUInt32LE(SR * CANAUX * OCTETS, 28); entete.writeUInt16LE(CANAUX * OCTETS, 32);
entete.writeUInt16LE(OCTETS * 8, 34); entete.write('data', 36); entete.writeUInt32LE(data.length, 40);

const sortie = path.resolve('public/sons/impact-sub.wav');
mkdirSync(path.dirname(sortie), {recursive: true});
writeFileSync(sortie, Buffer.concat([entete, data]));
console.log(`${path.relative(process.cwd(), sortie)} — ${DUREE}s, crête ${CRETE_DB} dBFS`);
