import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {COLORS, CUT_FRAMES, FONT} from '../config';
import {fontFamily} from '../fonts';

export type Ligne = {
  text: string;
  size?: number; // px
  color?: string;
  gap?: number; // espace au-dessus de la ligne (px), p. ex. pour dégager des accents
};

export type DiptyqueProps = {
  // Bloc gauche : entre à `gaucheAt`, toutes les lignes ensemble.
  gauche: Ligne[];
  gaucheAt: number;
  gaucheX: number; // bord gauche du bloc (px)
  // Bloc droit : une ligne après l'autre, chaque ligne décalée vers la droite.
  droite: Ligne[];
  droiteAt: number;
  droiteStagger: number; // frames entre deux lignes
  droiteX: number; // bord gauche de la première ligne (px)
  droiteIndent: number; // décalage supplémentaire par ligne (px)
};

const reveal = (frame: number, at: number) => Math.max(0, Math.min(1, (frame - at + 1) / CUT_FRAMES));

const Mot: React.FC<{ligne: Ligne; progress: number; indent: number}> = ({ligne, progress, indent}) => (
  <div
    style={{
      fontFamily,
      fontSize: ligne.size ?? 90,
      color: ligne.color ?? COLORS.white,
      letterSpacing: FONT.letterSpacing,
      lineHeight: FONT.lineHeight,
      textTransform: FONT.textTransform,
      marginLeft: indent,
      marginTop: ligne.gap ?? 0,
      clipPath: `inset(-40% 0 ${(1 - progress) * 100}% 0)`, // marge haute : accents et ascendantes
    }}
  >
    {ligne.text}
  </div>
);

export const Diptyque: React.FC<DiptyqueProps> = ({
  gauche,
  gaucheAt,
  gaucheX,
  droite,
  droiteAt,
  droiteStagger,
  droiteX,
  droiteIndent,
}) => {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill style={{backgroundColor: 'transparent'}}>
      <div style={{position: 'absolute', left: gaucheX, top: '50%', transform: 'translateY(-50%)'}}>
        {gauche.map((l, i) => (
          <Mot key={i} ligne={l} progress={reveal(frame, gaucheAt)} indent={0} />
        ))}
      </div>
      <div style={{position: 'absolute', left: droiteX, top: '50%', transform: 'translateY(-50%)'}}>
        {droite.map((l, i) => (
          <Mot key={i} ligne={l} progress={reveal(frame, droiteAt + i * droiteStagger)} indent={i * droiteIndent} />
        ))}
      </div>
    </AbsoluteFill>
  );
};
