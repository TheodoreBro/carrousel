import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {COLORS, FONT} from '../config';
import {fontFamily} from '../fonts';

export type Morceau = {
  text: string;
  color?: string;
};

export type UnParUnProps = {
  // Chaque mot est une suite de morceaux (pour un mot bicolore : « l'» + « oreillette »).
  mots: Morceau[][];
  startAt: number; // frame du premier mot
  dureeMot: number; // frames par mot ; peut être fractionnaire (9,5)
  dernierTient?: boolean; // le dernier mot reste à l'écran jusqu'à la fin (sinon il disparaît comme les autres)
  size?: number;
  color?: string;
};

// Mots seuls au centre de l'écran, l'un après l'autre. Chaque mot apparaît d'un coup et disparaît d'un coup.
export const UnParUn: React.FC<UnParUnProps> = ({
  mots,
  startAt,
  dureeMot,
  dernierTient = true,
  size = 160,
  color = COLORS.white,
}) => {
  const frame = useCurrentFrame();
  const t = frame - startAt;
  let i = t < 0 ? -1 : Math.floor(t / dureeMot);
  if (i >= mots.length) i = dernierTient ? mots.length - 1 : -1;
  if (i < 0) return <AbsoluteFill style={{backgroundColor: 'transparent'}} />;

  return (
    <AbsoluteFill style={{backgroundColor: 'transparent', justifyContent: 'center', alignItems: 'center'}}>
      <div
        style={{
          fontFamily,
          fontSize: size,
          color,
          letterSpacing: FONT.letterSpacing,
          lineHeight: FONT.lineHeight,
          textTransform: FONT.textTransform,
          whiteSpace: 'nowrap',
        }}
      >
        {mots[i].map((m, k) => (
          <span key={k} style={{color: m.color}}>
            {m.text}
          </span>
        ))}
      </div>
    </AbsoluteFill>
  );
};
