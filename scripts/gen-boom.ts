// Génère public/sons/boom-punchline.wav : boom d'explosion de cinéma pour marquer une punchline,
// synthétisé (aucun échantillon externe). Coup sec, grave puissant qui chute, souffle grondant
// de l'explosion, grondement large et courte résonance de grande salle. Pas d'échos, pas d'éboulis.
// Le coup est à 0 s : se cale directement sur la punchline.
// À relancer seulement si le son change : npx tsx scripts/gen-boom.ts
import {SR, creerBruit, ecrireWav, filtrer, fonduFinal, passeBas, passeHaut, reverbe, rms} from './lib/audio';

const DUREE = 3.6; // s
const CRETE_DB = -6; // niveau crête : à remonter dans Premiere si besoin
const N = Math.round(SR * DUREE);
const bruit = creerBruit(0xb00e7);

// 1. Coup : sinus qui chute vite de 110 à 35 Hz, harmoniques brèves pour qu'il porte sur toutes les enceintes.
const coup = new Float64Array(N);
let phase = 0;
for (let i = 0; i < N; i++) {
  const t = i / SR;
  phase += (2 * Math.PI * (35 + 75 * Math.exp(-t / 0.06))) / SR;
  const env = (1 - Math.exp(-t / 0.0015)) * Math.exp(-t / 0.55);
  coup[i] = env * (Math.sin(phase) + 0.35 * Math.exp(-t / 0.1) * Math.sin(2 * phase) + 0.15 * Math.exp(-t / 0.05) * Math.sin(3 * phase));
}

// 2. Claquement : l'attaque de l'explosion, très brève, sans aigus sifflants.
const claque = new Float64Array(N);
for (let i = 0; i < N; i++) {
  const t = i / SR;
  claque[i] = bruit() * (1 - Math.exp(-t / 0.0003)) * Math.exp(-t / 0.012);
}
filtrer(claque, passeHaut(200));
filtrer(claque, passeBas(5000));
filtrer(claque, passeBas(5000));

// 3. Souffle : le corps de l'explosion, bas-médium, avec un grondement irrégulier (turbulence).
const turbulence = new Float64Array(N);
for (let i = 0; i < N; i++) turbulence[i] = bruit();
filtrer(turbulence, passeBas(25));
filtrer(turbulence, passeBas(25));
const tRms = rms(turbulence);
const souffle = new Float64Array(N);
for (let i = 0; i < N; i++) {
  const t = i / SR;
  const flutter = Math.max(0, 1 + (0.6 * turbulence[i]) / tRms);
  souffle[i] = bruit() * flutter * (1 - Math.exp(-t / 0.002)) * Math.exp(-t / 0.3);
}
filtrer(souffle, passeHaut(50));
filtrer(souffle, passeBas(1200));
filtrer(souffle, passeBas(1200));

// 4. Grondement : la masse grave qui gonfle juste après le coup puis s'éteint, large (gauche ≠ droite).
const grondement = () => {
  const g = new Float64Array(N);
  for (let i = 0; i < N; i++) {
    const t = i / SR;
    g[i] = bruit() * (1 - Math.exp(-t / 0.08)) * Math.exp(-t / 0.9);
  }
  filtrer(g, passeHaut(28));
  filtrer(g, passeBas(140));
  filtrer(g, passeBas(140));
  return g;
};
const grondG = grondement(), grondD = grondement();

// Mélange (énergies relatives au coup).
const r = rms(coup);
const kClaque = (0.45 * r) / rms(claque);
const kSouffle = (1.15 * r) / rms(souffle);
const kGrond = (0.6 * r) / rms(grondG);
const directG = new Float64Array(N), directD = new Float64Array(N), mono = new Float64Array(N);
for (let i = 0; i < N; i++) {
  const centre = coup[i] + kClaque * claque[i] + kSouffle * souffle[i];
  directG[i] = centre + kGrond * grondG[i];
  directD[i] = centre + kGrond * grondD[i];
  mono[i] = 0.5 * (directG[i] + directD[i]);
}

// 5. Grande salle : résonance courte et sombre, qui épaissit sans faire d'écho.
const [revG, revD] = reverbe(mono, {rt60: 1.8, amortissement: 0.55, taille: 1.6});
const kRev = (0.35 * rms(mono)) / rms(revG);

// Saturation franche : densité et impact.
const gauche = new Float64Array(N), droite = new Float64Array(N);
for (let i = 0; i < N; i++) {
  gauche[i] = Math.tanh(2 * (directG[i] + kRev * revG[i]));
  droite[i] = Math.tanh(2 * (directD[i] + kRev * revD[i]));
}

// Coupe-bas 28 Hz, coupe-haut 6 kHz (4e ordre) : du grain, pas de sifflement.
for (const c of [gauche, droite]) {
  filtrer(c, passeHaut(28));
  filtrer(c, passeBas(6000));
  filtrer(c, passeBas(6000));
  fonduFinal(c, 0.5);
}
ecrireWav('public/sons/boom-punchline.wav', [gauche, droite], CRETE_DB);
