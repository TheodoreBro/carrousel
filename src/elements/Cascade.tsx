import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {COLORS, CUT_FRAMES, FONT} from '../config';
import {fontFamily} from '../fonts';

export type Segment = {
  text: string;
  size?: number; // px
  color?: string;
};

export type CascadeProps = {
  // Chaque ligne est une suite de segments (tailles et couleurs mixtes, alignés sur la ligne de base).
  lignes: Segment[][];
  startAt: number; // frame de la première ligne
  stagger: number; // frames entre deux lignes
  indent: number; // décalage vers la droite ajouté à chaque ligne (px)
  size?: number; // taille par défaut (px)
  gap?: number; // espace entre les lignes (px)
};

const reveal = (frame: number, at: number) => Math.max(0, Math.min(1, (frame - at + 1) / CUT_FRAMES));

export const Cascade: React.FC<CascadeProps> = ({lignes, startAt, stagger, indent, size = 90, gap = 0}) => {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill style={{backgroundColor: 'transparent'}}>
      <div
        style={{
          position: 'absolute',
          left: '50%',
          top: '50%',
          transform: 'translate(-50%, -50%)',
          fontFamily,
          fontSize: size,
          color: COLORS.white,
          letterSpacing: FONT.letterSpacing,
          lineHeight: FONT.lineHeight,
          textTransform: FONT.textTransform,
          whiteSpace: 'nowrap',
        }}
      >
        {lignes.map((segments, i) => (
          <div
            key={i}
            style={{
              marginLeft: i * indent,
              marginTop: i === 0 ? 0 : gap,
              clipPath: `inset(-40% 0 ${(1 - reveal(frame, startAt + i * stagger)) * 100}% 0)`, // marge haute : accents
            }}
          >
            {segments.map((s, j) => (
              <span key={j} style={{fontSize: s.size ?? size, color: s.color ?? COLORS.white}}>
                {s.text}
              </span>
            ))}
          </div>
        ))}
      </div>
    </AbsoluteFill>
  );
};
