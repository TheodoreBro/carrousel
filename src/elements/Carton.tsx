import {AbsoluteFill, useCurrentFrame, useVideoConfig} from 'remotion';
import {COLORS, CUT_FRAMES, FONT} from '../config';
import {fontFamily} from '../fonts';

export type CartonProps = {
  text: string;
  fontSize?: number;
  color?: string;
};

// Carton plein cadre, texte centré, fond transparent.
// Entrée : révélation verticale sèche en CUT_FRAMES. Sortie : inverse.
export const Carton: React.FC<CartonProps> = ({
  text,
  fontSize = 240,
  color = COLORS.white,
}) => {
  const frame = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();

  const enter = Math.min(1, (frame + 1) / CUT_FRAMES);
  const exit = Math.min(1, (durationInFrames - frame) / CUT_FRAMES);
  const reveal = Math.min(enter, exit);
  const hidden = (1 - reveal) * 100;

  return (
    <AbsoluteFill
      style={{
        backgroundColor: 'transparent',
        justifyContent: 'center',
        alignItems: 'center',
      }}
    >
      <div
        style={{
          fontFamily,
          fontSize,
          color,
          letterSpacing: FONT.letterSpacing,
          lineHeight: FONT.lineHeight,
          textTransform: FONT.textTransform,
          textAlign: 'center',
          whiteSpace: 'pre-wrap',
          clipPath: `inset(0 0 ${hidden}% 0)`,
        }}
      >
        {text}
      </div>
    </AbsoluteFill>
  );
};
