import type React from 'react';
import {Carton} from './Carton';
import {CarteEurope} from './CarteEurope';
import {DrapeauOnu} from './DrapeauOnu';

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
];
