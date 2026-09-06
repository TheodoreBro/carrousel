import {AbsoluteFill, useCurrentFrame, useVideoConfig} from 'remotion';
import {COLORS, CUT_FRAMES, EU_COLORS} from '../config';
import {EUROPE} from '../data/europe';

export type CarteEuropeProps = {
  // Durée du tracé des contours, en frames (linéaire, tous les pays en même temps).
  drawFrames: number;
  // Frame à laquelle les 27 se remplissent (en CUT_FRAMES).
  fillAt: number;
  strokeColor?: string;
  strokeWidth?: number;
  fillColor?: string;
};

// Carte de l'Europe : contours tracés au trait, puis remplissage sec des États membres.
export const CarteEurope: React.FC<CarteEuropeProps> = ({
  drawFrames,
  fillAt,
  strokeColor = COLORS.white,
  strokeWidth = 2,
  fillColor = EU_COLORS.blue,
}) => {
  const frame = useCurrentFrame();
  const {width, height} = useVideoConfig();

  const draw = Math.min(1, (frame + 1) / drawFrames);
  const fill = Math.max(0, Math.min(1, (frame - fillAt + 1) / CUT_FRAMES));

  return (
    <AbsoluteFill style={{backgroundColor: 'transparent'}}>
      <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`}>
        {EUROPE.map((c) => (
          <path
            key={c.name}
            d={c.d}
            pathLength={1}
            fill={c.eu ? fillColor : 'none'}
            fillOpacity={c.eu ? fill : 0}
            stroke={strokeColor}
            strokeWidth={strokeWidth}
            strokeLinejoin="round"
            strokeLinecap="round"
            strokeDasharray={1}
            strokeDashoffset={1 - draw}
          />
        ))}
      </svg>
    </AbsoluteFill>
  );
};
