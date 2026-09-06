import {AbsoluteFill, useCurrentFrame, useVideoConfig} from 'remotion';
import {COLORS, CUT_FRAMES, EU_COLORS} from '../config';
import {EUROPE, EU_CENTER} from '../data/europe';

export type CarteEuropeProps = {
  // Durée du tracé des contours, en frames (linéaire, tous les pays en même temps).
  drawFrames: number;
  // Frame à laquelle les 27 se remplissent (en CUT_FRAMES).
  fillAt: number;
  strokeColor?: string;
  strokeWidth?: number;
  fillColor?: string;
  // Rayon du cercle d'étoiles (px). Proportions du drapeau : étoile = rayon / 6.
  starsRadius?: number;
  starsColor?: string;
};

// Étoile à cinq branches, une pointe vers le haut, rayon extérieur r.
const star = (cx: number, cy: number, r: number) => {
  const pts: string[] = [];
  for (let i = 0; i < 10; i++) {
    const a = -Math.PI / 2 + (i * Math.PI) / 5;
    const rr = i % 2 === 0 ? r : r * 0.382;
    pts.push(`${(cx + rr * Math.cos(a)).toFixed(1)},${(cy + rr * Math.sin(a)).toFixed(1)}`);
  }
  return pts.join(' ');
};

// Carte de l'Europe : contours tracés au trait, puis remplissage sec des États membres.
export const CarteEurope: React.FC<CarteEuropeProps> = ({
  drawFrames,
  fillAt,
  strokeColor = COLORS.white,
  strokeWidth = 2,
  fillColor = EU_COLORS.blue,
  starsRadius = 150,
  starsColor = EU_COLORS.yellow,
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
        {Array.from({length: 12}, (_, i) => {
          const a = (i * Math.PI) / 6;
          return (
            <polygon
              key={i}
              points={star(EU_CENTER[0] + starsRadius * Math.cos(a), EU_CENTER[1] + starsRadius * Math.sin(a), starsRadius / 6)}
              fill={starsColor}
              fillOpacity={fill}
            />
          );
        })}
      </svg>
    </AbsoluteFill>
  );
};
