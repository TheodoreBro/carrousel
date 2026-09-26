// Génère public/sons/snap-sec.wav : frappe sèche de cinéma, synthétisée (aucun échantillon externe).
// Claquement serré et mat, soupçon de grave, net sans être métallique (aucune résonance tonale),
// aucune queue de réverbération. 0,5 s.
// À relancer seulement si le son change : npx tsx scripts/gen-snap.ts
import {SR, creerBruit, ecrireWav, filtrer, fonduFinal, passeBas, passeHaut, rms} from './lib/audio';

const DUREE = 0.5; // s
const CRETE_DB = -6; // niveau crête : discret, à remonter dans Premiere si besoin
const N = Math.round(SR * DUREE);
const bruit = creerBruit(0x51a95e7);

// 1. Claquement : bruit large bande très bref, adouci en haut (mat) ; du bruit, pas de sinus aigus,
//    donc aucune note qui sonne métal.
const claque = new Float64Array(N);
for (let i = 0; i < N; i++) {
  const t = i / SR;
  claque[i] = bruit() * (1 - Math.exp(-t / 0.0004)) * Math.exp(-t / 0.009);
}
filtrer(claque, passeHaut(700));
filtrer(claque, passeBas(5500));
filtrer(claque, passeBas(5500));

// 2. Frappe : le « tok » mat, bruit bas-médium à peine plus long que le claquement.
const tok = new Float64Array(N);
for (let i = 0; i < N; i++) {
  const t = i / SR;
  tok[i] = bruit() * (1 - Math.exp(-t / 0.0008)) * Math.exp(-t / 0.02);
}
filtrer(tok, passeHaut(120));
filtrer(tok, passeBas(450));
filtrer(tok, passeBas(450));

// 3. Soupçon de grave : sinus qui tombe de 95 à 55 Hz et s'éteint en quelques dizaines de ms.
const grave = new Float64Array(N);
let phase = 0;
for (let i = 0; i < N; i++) {
  const t = i / SR;
  phase += (2 * Math.PI * (55 + 40 * Math.exp(-t / 0.02))) / SR;
  grave[i] = Math.sin(phase) * (1 - Math.exp(-t / 0.001)) * Math.exp(-t / 0.045);
}

// Mélange (énergies relatives au claquement), légère saturation pour la densité.
const r = rms(claque);
const kTok = (0.9 * r) / rms(tok);
const kGrave = (0.8 * r) / rms(grave);
const mix = new Float64Array(N);
for (let i = 0; i < N; i++) mix[i] = Math.tanh(1.2 * (claque[i] + kTok * tok[i] + kGrave * grave[i]) / 3) * 3;

// Nettoyage : rien sous 35 Hz, rien de brillant au-dessus de 9 kHz.
filtrer(mix, passeHaut(35));
filtrer(mix, passeBas(9000));

// Aucune queue : tout est éteint bien avant la fin, fondu jusqu'au zéro exact par sécurité.
fonduFinal(mix, 0.2);
ecrireWav('public/sons/snap-sec.wav', mix, CRETE_DB);
