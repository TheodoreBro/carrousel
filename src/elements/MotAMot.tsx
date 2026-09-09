import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {COLORS, CUT_FRAMES, FONT} from '../config';
import {fontFamily} from '../fonts';

export type Coin = 'haut-gauche' | 'haut-droite' | 'bas-gauche' | 'bas-droite';

export type Bloc = {
  // Lignes du bloc ; les mots arrivent un par un, dans l'ordre de lecture.
  lignes: string[];
  at: number; // frame du premier mot
  stagger: number; // frames entre deux mots
  coin: Coin; // coin de l'écran auquel le bloc est accroché (aligne le texte du même côté)
  x: number; // distance au bord vertical du coin (px)
  y: number; // distance au bord horizontal du coin (px)
  blurAt?: number; // frame à laquelle le bloc se floute (jamais si absent)
  blur?: number; // flou maximal (px)
  gap?: number; // espace entre les lignes (px), p. ex. pour dégager les accents
  size?: number;
  color?: string;
};

export type MotAMotProps = {
  blocs: Bloc[];
  size?: number;
  color?: string;
};

const progress = (frame: number, at: number) => Math.max(0, Math.min(1, (frame - at + 1) / CUT_FRAMES));

const BlocMots: React.FC<{bloc: Bloc; frame: number; size: number; color: string}> = ({bloc, frame, size, color}) => {
  const droite = bloc.coin.endsWith('droite');
  const bas = bloc.coin.startsWith('bas');
  const flou = bloc.blurAt === undefined ? 0 : progress(frame, bloc.blurAt) * (bloc.blur ?? 8);
  let index = 0; // rang du mot dans le bloc, toutes lignes confondues
  return (
    <div
      style={{
        position: 'absolute',
        [droite ? 'right' : 'left']: bloc.x,
        [bas ? 'bottom' : 'top']: bloc.y,
        fontFamily,
        fontSize: bloc.size ?? size,
        color: bloc.color ?? color,
        letterSpacing: FONT.letterSpacing,
        lineHeight: FONT.lineHeight,
        textTransform: FONT.textTransform,
        textAlign: droite ? 'right' : 'left',
        whiteSpace: 'nowrap',
        filter: flou > 0 ? `blur(${flou}px)` : 'none',
      }}
    >
      {bloc.lignes.map((ligne, i) => (
        <div key={i} style={{marginTop: i === 0 ? 0 : (bloc.gap ?? 0)}}>
          {ligne.split(' ').map((mot, j) => {
            const p = progress(frame, bloc.at + index++ * bloc.stagger);
            return (
              <span key={j}>
                {j > 0 && ' '}
                <span style={{display: 'inline-block', clipPath: `inset(-40% 0 ${(1 - p) * 100}% 0)`}}>{mot}</span>
              </span>
            );
          })}
        </div>
      ))}
    </div>
  );
};

// Phrase en blocs accrochés aux coins de l'écran, mots révélés un par un ; un bloc peut se flouter.
export const MotAMot: React.FC<MotAMotProps> = ({blocs, size = 140, color = COLORS.white}) => {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill style={{backgroundColor: 'transparent'}}>
      {blocs.map((b, i) => (
        <BlocMots key={i} bloc={b} frame={frame} size={size} color={color} />
      ))}
    </AbsoluteFill>
  );
};
