import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {COLORS, CUT_FRAMES, FONT} from '../config';
import {fontFamily} from '../fonts';

export type Morceau = {
  text: string;
  color?: string;
};

export type UnParUnProps = {
  // Chaque mot est une suite de morceaux (pour un mot bicolore : « l'» + « oreillette »).
  mots: Morceau[][];
  startAt: number; // frame du premier mot
  dureeMot: number; // frames par mot, entrée et sortie (CUT_FRAMES chacune) comprises ; peut être fractionnaire (9,5)
  dernierTient?: boolean; // le dernier mot reste à l'écran jusqu'à la fin (sinon il sort comme les autres)
  size?: number;
  color?: string;
};

// Mots seuls au centre de l'écran, l'un après l'autre : chacun entre, tient, sort, puis le suivant entre.
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
  if (t < 0) return <AbsoluteFill style={{backgroundColor: 'transparent'}} />;

  let i = Math.floor(t / dureeMot);
  let local = t - i * dureeMot;
  if (i >= mots.length) {
    if (!dernierTient) return <AbsoluteFill style={{backgroundColor: 'transparent'}} />;
    i = mots.length - 1;
    local = dureeMot; // entrée terminée depuis longtemps
  }
  const dernier = i === mots.length - 1;

  const enter = Math.min(1, (local + 1) / CUT_FRAMES);
  const exit = dernier && dernierTient ? 1 : Math.max(0, Math.min(1, (dureeMot - local) / CUT_FRAMES));
  const visible = Math.min(enter, exit);

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
          clipPath: `inset(-40% -80px ${(1 - visible) * 100}% -80px)`, // marge haute : accents
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
