import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {COLORS, CUT_FRAMES, FONT} from '../config';
import {fontFamily} from '../fonts';

export type AppelProps = {
  text: string;
  x: number; // bord gauche du texte (px)
  y: number; // haut du texte (px)
  fontSize?: number;
  color?: string;
  // Flèche : part sous le début du texte, vers le bas à gauche.
  arrowAt: number; // frame d'apparition de la flèche (le texte entre à 0)
  arrowLength?: number; // px
  arrowAngle?: number; // degrés depuis l'horizontale, vers le bas (45 = diagonale bas-gauche)
  strokeWidth?: number;
};

export const Appel: React.FC<AppelProps> = ({
  text,
  x,
  y,
  fontSize = 110,
  color = COLORS.white,
  arrowAt,
  arrowLength = 170,
  arrowAngle = 45,
  strokeWidth = 8,
}) => {
  const frame = useCurrentFrame();
  const textReveal = Math.min(1, (frame + 1) / CUT_FRAMES);
  const arrowReveal = Math.max(0, Math.min(1, (frame - arrowAt + 1) / CUT_FRAMES));

  const a = (arrowAngle * Math.PI) / 180;
  const x0 = x + fontSize * 0.45;
  const y0 = y + fontSize * FONT.lineHeight + 30;
  const x1 = x0 - arrowLength * Math.cos(a);
  const y1 = y0 + arrowLength * Math.sin(a);
  // Pointe : deux segments à ±35° de la direction.
  const head = 44;
  const dir = Math.atan2(y1 - y0, x1 - x0);
  const h1 = [x1 - head * Math.cos(dir - 0.61), y1 - head * Math.sin(dir - 0.61)];
  const h2 = [x1 - head * Math.cos(dir + 0.61), y1 - head * Math.sin(dir + 0.61)];
  const d = `M${x0},${y0}L${x1},${y1}M${h1[0]},${h1[1]}L${x1},${y1}L${h2[0]},${h2[1]}`;

  return (
    <AbsoluteFill style={{backgroundColor: 'transparent'}}>
      <div
        style={{
          position: 'absolute',
          left: x,
          top: y,
          fontFamily,
          fontSize,
          color,
          letterSpacing: FONT.letterSpacing,
          lineHeight: FONT.lineHeight,
          textTransform: FONT.textTransform,
          whiteSpace: 'nowrap',
          clipPath: `inset(-40% 0 ${(1 - textReveal) * 100}% 0)`,
        }}
      >
        {text}
      </div>
      <svg width={1920} height={1080} style={{position: 'absolute', left: 0, top: 0}}>
        <path
          d={d}
          fill="none"
          stroke={color}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeLinejoin="round"
          pathLength={1}
          strokeDasharray={1}
          strokeDashoffset={1 - arrowReveal}
        />
      </svg>
    </AbsoluteFill>
  );
};
