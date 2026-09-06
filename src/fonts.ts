import {loadFont} from '@remotion/google-fonts/Anton';

// Charge Anton une seule fois pour tout le bundle.
export const {fontFamily, waitUntilDone} = loadFont('normal', {
  weights: ['400'],
  subsets: ['latin', 'latin-ext'],
});
