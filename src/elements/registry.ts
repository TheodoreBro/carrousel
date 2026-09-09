import type React from 'react';
import {EU_COLORS} from '../config';
import {Carton} from './Carton';
import {CarteEurope} from './CarteEurope';
import {DrapeauOnu} from './DrapeauOnu';
import {Diptyque} from './Diptyque';
import {Cascade} from './Cascade';
import {Appel} from './Appel';
import {Chapitres} from './Chapitres';
import {Ronde} from './Ronde';
import {CarteFrance} from './CarteFrance';
import {MotAMot} from './MotAMot';

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
      droiteAt: 63,
      droiteStagger: 5,
      droiteX: 1000,
      droiteIndent: 70,
    },
    durationInFrames: 138,
    alpha: true,
  },
  {
    id: 'europe-invente',
    component: Cascade,
    props: {
      lignes: [
        [{text: 'il faut'}],
        [{text: 'que l’'}, {text: 'Europe', size: 220, color: EU_COLORS.blue}],
        [{text: 'invente un ...'}],
      ],
      startAt: 0,
      stagger: 5,
      indent: 70,
      gap: 30,
    },
    durationInFrames: 100,
    alpha: true,
  },
  {
    id: 'etat-chinois',
    component: Diptyque,
    props: {
      gauche: [{text: 'l’État'}, {text: 'chinois', size: 260, color: '#6A020C'}],
      gaucheAt: 0,
      gaucheX: 120,
      droite: [
        {text: 'un'},
        {text: 'état', size: 200, color: '#6A020C', gap: 40},
        {text: 'de'},
        {text: 'droit', size: 200, color: '#6A020C'},
        {text: 'mondial'},
      ],
      droiteAt: 38,
      droiteStagger: 5,
      droiteX: 1100,
      droiteIndent: 70,
      shadow: true,
    },
    durationInFrames: 125,
    alpha: true,
  },
  {
    id: 'abonnez-vous',
    component: Appel,
    props: {text: 'Abonnez-vous', x: 240, y: 700, arrowAt: 6},
    durationInFrames: 100,
    alpha: true,
  },
  {
    id: 'chapitres',
    component: Chapitres,
    props: {
      chapitres: [
        'Le monde a perdu son gendarme',
        'La mondialisation des rapports de force',
        'Pourquoi l’Europe doit devenir une puissance',
        'Le plan pour l’UE : commerce, industrie, finance',
      ],
      barAt: 0,
      chaptersAt: 6,
      stagger: 5,
      exitAt: 100,
      exitOrder: [2, 0, 3, 1],
      barExitAt: 125,
    },
    durationInFrames: 130,
    alpha: true,
  },
  {
    id: 'denatalite',
    component: Diptyque,
    props: {
      gauche: [{text: 'la'}, {text: 'dénatalité', size: 200, color: '#138800'}],
      gaucheAt: 0,
      gaucheX: 120,
      gaucheY: 100,
      droite: [{text: 'très bonne'}, {text: 'nouvelle', size: 200, color: '#138800'}],
      droiteAt: 88, // 0,8 s (durée du mot « dénatalité » prononcé) + 2,7 s
      droiteStagger: 12, // « nouvelle » au rythme de la parole (0,48 s après « très »)
      droiteX: 1100,
      droiteY: 680,
      droiteIndent: 0,
    },
    durationInFrames: 150,
    alpha: true,
  },
  {
    id: 'ronde',
    component: Ronde,
    props: {pairs: 4, colorB: '#138800', turnFrames: 150, hopFrames: 25},
    durationInFrames: 150, // = turnFrames et multiple de hopFrames : boucle parfaite
    alpha: true,
  },
  {
    id: 'france-bonhommes',
    component: CarteFrance,
    props: {drawFrames: 25, figuresAt: 30, vanishAt: 100, vanishShare: 0.35},
    durationInFrames: 150,
    alpha: true,
  },
  {
    id: 'feministes-ecologistes',
    component: MotAMot,
    props: {
      blocs: [
        {
          lignes: ['Pourquoi les féministes', 'et les écologistes'],
          at: 0,
          stagger: 5,
          coin: 'haut-gauche',
          x: 120,
          y: 100,
          blurAt: 53, // au premier mot du second bloc
          blur: 8,
          gap: 16,
        },
        {
          lignes: ['ne se tiennent pas', 'par la main en chantant\u00A0?'],
          at: 53, // dernier mot du premier bloc en place à 28, plus 1 s
          stagger: 5,
          coin: 'bas-droite',
          x: 120,
          y: 100,
          gap: 16,
        },
      ],
      size: 140,
    },
    durationInFrames: 150,
    alpha: true,
  },
];
