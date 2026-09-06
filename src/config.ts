// Réglages globaux. Tout composant lit ici, jamais de valeur en dur ailleurs.

export const COLORS = {
  white: '#FFFFFF',
  black: '#000000',
  accent: '#FF3B00',
} as const;

// Couleurs officielles de l'Union européenne (hors DA par défaut, sur demande explicite).
export const EU_COLORS = {
  blue: '#003399',
  yellow: '#FFCC00',
} as const;

// Drapeaux (sur demande explicite).
export const FLAG_COLORS = {
  onuBlue: '#5B92E5',
  chinaRed: '#EE1C25',
} as const;

export const FONT = {
  family: 'Anton',
  letterSpacing: '-0.02em',
  lineHeight: 0.9,
  textTransform: 'uppercase',
} as const;

export const VIDEO = {
  width: 1920,
  height: 1080,
  fps: 25,
} as const;

// Durée max d'une entrée/sortie, en frames.
export const CUT_FRAMES = 3;

export const OUT_DIR = 'out';
