// Génère public/sons/bam.wav : « bam » de cinéma qui résonne, synthétisé (aucun échantillon externe).
// Claquement net, frappe épaisse, grave qui chute, puis une résonance de salle courte et sombre.
// Fait pour s'enchaîner vite (bam bam bam) : la frappe est brève, la résonance prend le relais.
// À relancer seulement si le son change : npx tsx scripts/gen-bam.ts
import {SR, creerBruit, ecrireWav, filtrer, fonduFinal, passeBas, passeHaut, reverbe, rms} from './lib/audio';

const DUREE = 1.3; // s
const CRETE_DB = -4; // niveau crête
const N = Math.round(SR * DUREE);
const bruit = creerBruit(0xba3ba3);

// 1. Claquement : l'attaque, très brève, nette sans siffler.
const claque = new Float64Array(N);
for (let i = 0; i < N; i++) {
  const t = i / SR;
  claque[i] = bruit() * (1 - Math.exp(-t / 0.0003)) * Math.exp(-t / 0.008);
}
filtrer(claque, passeHaut(300));
filtrer(claque, passeBas(6000));
filtrer(claque, passeBas(6000));

// 2. Frappe : le « BAM » épais, bas-médium.
const frappe = new Float64Array(N);
for (let i = 0; i < N; i++) {
  const t = i / SR;
  frappe[i] = bruit() * (1 - Math.exp(-t / 0.0008)) * Math.exp(-t / 0.03);
}
filtrer(frappe, passeHaut(90));
filtrer(frappe, passeBas(550));
filtrer(frappe, passeBas(550));

// 3. Grave : sinus qui chute de 120 à 50 Hz, avec son octave, pour le poids.
const grave = new Float64Array(N);
let phase = 0;
for (let i = 0; i < N; i++) {
  const t = i / SR;
  phase += (2 * Math.PI * (50 + 70 * Math.exp(-t / 0.025))) / SR;
  const env = (1 - Math.exp(-t / 0.001)) * Math.exp(-t / 0.12);
  grave[i] = env * (Math.sin(phase) + 0.3 * Math.exp(-t / 0.05) * Math.sin(2 * phase));
}

// Son direct (énergies relatives à la frappe), saturation pour la densité.
const r = rms(frappe);
const kClaque = (0.6 * r) / rms(claque);
const kGrave = (1.3 * r) / rms(grave);
const direct = new Float64Array(N);
for (let i = 0; i < N; i++) direct[i] = Math.tanh(1.5 * (kClaque * claque[i] + frappe[i] + kGrave * grave[i]));

// 4. Résonance : salle moyenne, sombre, ~1 s ; c'est elle qui fait « résonner » chaque bam.
const [revG, revD] = reverbe(direct, {rt60: 1.1, amortissement: 0.5, taille: 1.4});
const kRev = (0.6 * rms(direct)) / rms(revG);
const gauche = new Float64Array(N), droite = new Float64Array(N);
for (let i = 0; i < N; i++) {
  gauche[i] = direct[i] + kRev * revG[i];
  droite[i] = direct[i] + kRev * revD[i];
}

// Coupe-bas 35 Hz, coupe-haut 8 kHz ; fin propre.
for (const c of [gauche, droite]) {
  filtrer(c, passeHaut(35));
  filtrer(c, passeBas(8000));
  fonduFinal(c, 0.3);
}
ecrireWav('public/sons/bam.wav', [gauche, droite], CRETE_DB);
