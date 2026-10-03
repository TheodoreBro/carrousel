// Génère public/sons/pierre-ravin.wav : explosion de roche au fond d'un ravin, façon révélation,
// synthétisée (aucun échantillon externe). Choc très grave qui chute, souffle de l'explosion,
// éboulis, puis un grondement qui gonfle et s'étire dans le ravin (échos, résonance), en stéréo.
// Le choc est à 0 s : se cale directement sur la punchline.
// À relancer seulement si le son change : npx tsx scripts/gen-ravin.ts
import {SR, creerBruit, ecrireWav, filtrer, fonduFinal, passeBas, passeHaut, reverbe, rms} from './lib/audio';

const DUREE = 4.2; // s
const CRETE_DB = -6; // niveau crête : discret, à remonter dans Premiere si besoin
const N = Math.round(SR * DUREE);
const bruit = creerBruit(0x7a51c3);
const alea = () => bruit() * 0.5 + 0.5; // dans [0, 1[

// 1. Choc : sinus qui chute de 85 à 28 Hz, attaque franche, longue tenue.
const choc = new Float64Array(N);
let phase = 0;
for (let i = 0; i < N; i++) {
  const t = i / SR;
  phase += (2 * Math.PI * (28 + 57 * Math.exp(-t / 0.11))) / SR;
  const env = (1 - Math.exp(-t / 0.002)) * Math.exp(-t / 0.7);
  choc[i] = env * (Math.sin(phase) + 0.3 * Math.exp(-t / 0.15) * Math.sin(2 * phase));
}

// 2. Souffle : l'explosion elle-même, large et sombre (jusqu'à ~1,8 kHz), très brève.
const souffle = new Float64Array(N);
for (let i = 0; i < N; i++) {
  const t = i / SR;
  souffle[i] = bruit() * (1 - Math.exp(-t / 0.0005)) * Math.exp(-t / 0.12);
}
filtrer(souffle, passeHaut(60));
filtrer(souffle, passeBas(1800));
filtrer(souffle, passeBas(1800));

// 3. Masse : le corps épais de l'explosion, bas-médium, un peu plus long.
const masse = new Float64Array(N);
for (let i = 0; i < N; i++) {
  const t = i / SR;
  masse[i] = bruit() * (1 - Math.exp(-t / 0.004)) * Math.exp(-t / 0.28);
}
filtrer(masse, passeHaut(35));
filtrer(masse, passeBas(260));
filtrer(masse, passeBas(260));

// 4. Éboulis : blocs de roche qui retombent, de plus en plus rares, placés à gauche ou à droite.
const eboulisG = new Float64Array(N), eboulisD = new Float64Array(N);
for (let k = 0; k < 140; k++) {
  const t0 = 0.02 - 0.45 * Math.log(1 - 0.999 * alea()); // répartition exponentielle
  const amp = (0.3 + 0.7 * alea()) * Math.exp(-t0 / 0.5);
  const longueur = Math.round((0.006 + 0.018 * alea()) * SR);
  const pan = alea();
  const debut = Math.round(t0 * SR);
  for (let j = 0; j < longueur && debut + j < N; j++) {
    const v = amp * bruit() * Math.exp(-j / (0.004 * SR));
    eboulisG[debut + j] += v * Math.sqrt(1 - pan);
    eboulisD[debut + j] += v * Math.sqrt(pan);
  }
}
for (const c of [eboulisG, eboulisD]) {
  filtrer(c, passeHaut(90));
  filtrer(c, passeBas(1200));
  filtrer(c, passeBas(1200));
}

// 5. Révélation : grondement qui gonfle juste après le choc puis s'étire, large (bruit distinct à gauche et à droite).
const grondement = () => {
  const g = new Float64Array(N);
  for (let i = 0; i < N; i++) {
    const t = i / SR;
    g[i] = bruit() * (1 - Math.exp(-t / 0.18)) * Math.exp(-t / 1.0);
  }
  filtrer(g, passeHaut(30));
  filtrer(g, passeBas(110));
  filtrer(g, passeBas(110));
  return g;
};
const grondG = grondement(), grondD = grondement();

// Son direct.
const r = rms(choc);
const kSouffle = (0.55 * r) / rms(souffle);
const kMasse = (0.6 * r) / rms(masse);
const kEboulis = (0.22 * r) / rms(eboulisG);
const kGrond = (0.55 * r) / rms(grondG);
const directG = new Float64Array(N), directD = new Float64Array(N);
for (let i = 0; i < N; i++) {
  const centre = choc[i] + kSouffle * souffle[i] + kMasse * masse[i];
  directG[i] = centre + kEboulis * eboulisG[i] + kGrond * grondG[i];
  directD[i] = centre + kEboulis * eboulisD[i] + kGrond * grondD[i];
}

// 6. Le ravin : échos sur les parois, de plus en plus lointains et sombres, puis résonance longue.
const echo = (x: Float64Array, retard: number, coupure: number) => {
  const e = new Float64Array(N);
  const d = Math.round(retard * SR);
  for (let i = d; i < N; i++) e[i] = x[i - d];
  filtrer(e, passeBas(coupure));
  filtrer(e, passeBas(coupure));
  return e;
};
const e1 = echo(directG, 0.19, 500), e2 = echo(directD, 0.33, 330), e3 = echo(directG, 0.52, 220), e4 = echo(directD, 0.52, 220);
const mono = new Float64Array(N);
for (let i = 0; i < N; i++) mono[i] = 0.5 * (directG[i] + directD[i]);
const [revG, revD] = reverbe(mono, {rt60: 3.0, amortissement: 0.6, taille: 2.5});
const kRev = (0.5 * rms(mono)) / rms(revG);

const gauche = new Float64Array(N), droite = new Float64Array(N);
for (let i = 0; i < N; i++) {
  const g = directG[i] + 0.3 * e1[i] + 0.1 * e2[i] + 0.14 * e3[i] + kRev * revG[i];
  const d = directD[i] + 0.1 * e1[i] + 0.26 * e2[i] + 0.14 * e4[i] + kRev * revD[i];
  // Saturation franche : le grain de l'explosion.
  gauche[i] = Math.tanh(1.6 * g);
  droite[i] = Math.tanh(1.6 * d);
}

// Sombre, sans souffle aigu : coupe-bas 25 Hz, coupe-haut 2 kHz (4e ordre).
for (const c of [gauche, droite]) {
  filtrer(c, passeHaut(25));
  filtrer(c, passeBas(2000));
  filtrer(c, passeBas(2000));
  fonduFinal(c, 0.6);
}
ecrireWav('public/sons/pierre-ravin.wav', [gauche, droite], CRETE_DB);
