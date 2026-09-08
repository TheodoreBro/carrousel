import {loadFont} from '@remotion/google-fonts/Anton';
import {loadFont as loadInter} from '@remotion/google-fonts/Inter';

// Charge Anton une seule fois pour tout le bundle.
export const {fontFamily, waitUntilDone} = loadFont('normal', {
  weights: ['400'],
  subsets: ['latin', 'latin-ext'],
});

// Police secondaire, fine, pour les textes courants (bas de casse).
export const {fontFamily: fontFamilySecondary} = loadInter('normal', {
  weights: ['500', '600'],
  subsets: ['latin', 'latin-ext'],
});
