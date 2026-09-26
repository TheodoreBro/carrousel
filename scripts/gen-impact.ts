// Génère public/sons/impact-sub.wav : impact grave de cinéma, synthétisé (aucun échantillon externe).
// Sub-bass qui tombe de 75 à 40 Hz, attaque douce, courte queue sombre ; rien au-dessus de ~150 Hz.
// À relancer seulement si le son change : npx tsx scripts/gen-impact.ts
import {SR, creerBruit, ecrireWav, filtrer, fonduFinal, passeBas, passeHaut, rms} from './lib/audio';

const DUREE = 1.6; // s
const CRETE_DB = -6; // niveau crête : discret, à remonter dans Premiere si besoin
const N = Math.round(SR * DUREE);
const bruit = creerBruit();

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
const kChoc = (0.35 * rms(corps)) / rms(choc);
const kQueue = (0.3 * rms(corps)) / rms(queue);
const mix = new Float64Array(N);
for (let i = 0; i < N; i++) mix[i] = Math.tanh(1.3 * (corps[i] + kChoc * choc[i] + kQueue * queue[i]));

// Aucun aigu, aucun infra inutile : coupe-haut 150 Hz (4e ordre), coupe-bas 28 Hz.
filtrer(mix, passeHaut(28));
filtrer(mix, passeBas(150));
filtrer(mix, passeBas(150));

// Fin propre sur les 200 dernières ms.
fonduFinal(mix, 0.2);
ecrireWav('public/sons/impact-sub.wav', mix, CRETE_DB);
