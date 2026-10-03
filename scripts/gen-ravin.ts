// Génère public/sons/pierre-ravin.wav : pierre qui éclate au fond d'un ravin, synthétisée
// (aucun échantillon externe). Choc sourd très grave, éclat étouffé, quelques éboulis,
// puis le ravin qui résonne un peu : échos sur les parois et queue sombre, en stéréo.
// À relancer seulement si le son change : npx tsx scripts/gen-ravin.ts
import {SR, creerBruit, ecrireWav, filtrer, fonduFinal, passeBas, passeHaut, reverbe, rms} from './lib/audio';

const DUREE = 3.2; // s
const CRETE_DB = -6; // niveau crête : discret, à remonter dans Premiere si besoin
const N = Math.round(SR * DUREE);
const bruit = creerBruit(0x7a51c3);

// 1. Corps : sinus qui tombe de 62 à 30 Hz, attaque franche, décroissance assez lente.
const corps = new Float64Array(N);
let phase = 0;
for (let i = 0; i < N; i++) {
  const t = i / SR;
  phase += (2 * Math.PI * (30 + 32 * Math.exp(-t / 0.09))) / SR;
  const env = (1 - Math.exp(-t / 0.003)) * Math.exp(-t / 0.45);
  corps[i] = env * (Math.sin(phase) + 0.25 * Math.exp(-t / 0.12) * Math.sin(2 * phase));
}

// 2. Éclat : l'explosion de la pierre, entendue de loin, donc étouffée (rien au-dessus de ~300 Hz).
const eclat = new Float64Array(N);
for (let i = 0; i < N; i++) {
  const t = i / SR;
  eclat[i] = bruit() * (1 - Math.exp(-t / 0.001)) * Math.exp(-t / 0.07);
}
filtrer(eclat, passeHaut(40));
filtrer(eclat, passeBas(320));
filtrer(eclat, passeBas(320));

// 3. Éboulis : petits chocs de roche qui retombent, de plus en plus rares et faibles, étouffés.
const eboulis = new Float64Array(N);
for (let k = 0; k < 70; k++) {
  const t0 = 0.03 - 0.28 * Math.log(1 - 0.999 * (bruit() * 0.5 + 0.5)); // répartition exponentielle
  const amp = (0.4 + 0.6 * (bruit() * 0.5 + 0.5)) * Math.exp(-t0 / 0.3);
  const longueur = Math.round((0.005 + 0.01 * (bruit() * 0.5 + 0.5)) * SR);
  const debut = Math.round(t0 * SR);
  for (let j = 0; j < longueur && debut + j < N; j++) eboulis[debut + j] += amp * bruit() * Math.exp(-j / (0.003 * SR));
}
filtrer(eboulis, passeHaut(80));
filtrer(eboulis, passeBas(500));
filtrer(eboulis, passeBas(500));

// Son direct (au centre).
const kEclat = (0.6 * rms(corps)) / rms(eclat);
const kEboulis = (0.25 * rms(corps)) / rms(eboulis);
const direct = new Float64Array(N);
for (let i = 0; i < N; i++) direct[i] = corps[i] + kEclat * eclat[i] + kEboulis * eboulis[i];

// 4. Le ravin : trois échos sur les parois, de plus en plus lointains et sombres, gauche/droite.
const echo = (retard: number, coupure: number) => {
  const e = new Float64Array(N);
  const r = Math.round(retard * SR);
  for (let i = r; i < N; i++) e[i] = direct[i - r];
  filtrer(e, passeBas(coupure));
  filtrer(e, passeBas(coupure));
  return e;
};
const e1 = echo(0.17, 300), e2 = echo(0.29, 220), e3 = echo(0.47, 160);

// … et sa résonance : réverbération longue, grand espace, très amortie dans les aigus.
const [revG, revD] = reverbe(direct, {rt60: 2.4, amortissement: 0.7, taille: 2.5});
const kRev = (0.45 * rms(direct)) / rms(revG);

const gauche = new Float64Array(N), droite = new Float64Array(N);
for (let i = 0; i < N; i++) {
  const g = direct[i] + 0.3 * e1[i] + 0.08 * e2[i] + 0.14 * e3[i] + kRev * revG[i];
  const d = direct[i] + 0.1 * e1[i] + 0.24 * e2[i] + 0.14 * e3[i] + kRev * revD[i];
  // Légère saturation pour la densité.
  gauche[i] = Math.tanh(1.2 * g);
  droite[i] = Math.tanh(1.2 * d);
}

// Sourd et très grave : coupe-bas 25 Hz, coupe-haut 450 Hz (4e ordre), sur les deux canaux.
for (const c of [gauche, droite]) {
  filtrer(c, passeHaut(25));
  filtrer(c, passeBas(450));
  filtrer(c, passeBas(450));
  fonduFinal(c, 0.4);
}
ecrireWav('public/sons/pierre-ravin.wav', [gauche, droite], CRETE_DB);
