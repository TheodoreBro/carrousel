import type React from 'react';
import {Carton} from './Carton';
import {CarteEurope} from './CarteEurope';
import {DrapeauOnu} from './DrapeauOnu';
import {Diptyque} from './Diptyque';

export type ElementDef = {
  // Nom passé à `npm run build -- --nom=<id>` ; sert aussi de nom de fichier.
  id: string;
  component: React.FC<any>;
  props: Record<string, unknown>;
  durationInFrames: number;
  // true → MOV ProRes 4444 alpha ; false → MP4 H.264 opaque plein cadre.
  alpha: boolean;
};

// Un élément = une entrée ici. Le texte est toujours un prop, jamais dans le composant.
export const ELEMENTS: ElementDef[] = [
  {
    id: 'test',
    component: Carton,
    props: {text: 'TEST'},
    durationInFrames: 75,
    alpha: true,
  },
  {
    id: 'carte-europe',
    component: CarteEurope,
    props: {drawFrames: 25, fillAt: 30},
    durationInFrames: 75,
    alpha: true,
  },
  {
    id: 'drapeau-onu',
    component: DrapeauOnu,
    props: {recolorAt: 50},
    durationInFrames: 100,
    alpha: true,
  },
  {
    id: 'chine-hegemon',
    component: Diptyque,
    props: {
      gauche: [{text: 'la'}, {text: 'Chine', size: 260, color: '#6A020C'}],
      gaucheAt: 0,
      gaucheX: 120,
      droite: [{text: 'un'}, {text: 'nouvel'}, {text: 'hégémon', size: 200, color: '#6A020C', gap: 40}],
      droiteAt: 25,
      droiteStagger: 5,
      droiteX: 1000,
      droiteIndent: 70,
    },
    durationInFrames: 100,
    alpha: true,
  },
];
