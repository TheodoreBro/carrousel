import {AbsoluteFill, useCurrentFrame, useVideoConfig} from 'remotion';
import {COLORS, CUT_FRAMES, FLAG_COLORS} from '../config';
import {ONU_GRATICULE, ONU_LAND, ONU_R} from '../data/onu';

export type DrapeauOnuProps = {
  // Frame à laquelle le fond passe de la couleur initiale à la couleur finale (en CUT_FRAMES).
  recolorAt: number;
  fromColor?: string;
  toColor?: string;
  emblemColor?: string;
  flagWidth?: number; // ratio 2:3
  // Ondoiement : amplitude max (px) au bord flottant, longueur d'onde (px), période (frames).
  waveAmplitude?: number;
  waveLength?: number;
  wavePeriod?: number;
};

// Rameau d'olivier stylisé : tige en arc autour du globe, feuilles en ellipses par paires.
// side = -1 (gauche, du bas vers 10 h) ou 1 (droite, du bas vers 2 h).
const Branch: React.FC<{side: number; color: string}> = ({side, color}) => {
  const n = 9;
  const r = ONU_R * 1.28;
  const a0 = Math.PI / 2 + side * 0.12;
  const a1 = side < 0 ? (7 * Math.PI) / 6 : -Math.PI / 6;
  const at = (t: number) => a0 + (a1 - a0) * t;
  const pt = (t: number): [number, number] => [r * Math.cos(at(t)), r * Math.sin(at(t))];
  const stem = Array.from({length: 25}, (_, i) => pt(i / 24))
    .map((p, i) => `${i === 0 ? 'M' : 'L'}${p[0].toFixed(1)},${p[1].toFixed(1)}`)
    .join('');
  const leaves: React.ReactNode[] = [];
  for (let i = 1; i <= n; i++) {
    const t = i / n;
    const [x, y] = pt(t);
    const tangent = (at(t) * 180) / Math.PI - 90 * side; // vers la pointe du rameau
    const len = ONU_R * (0.24 - t * 0.06);
    for (const s of [-1, 1]) {
      leaves.push(
        <ellipse
          key={`${i}-${s}`}
          cx={len * 0.5}
          cy={0}
          rx={len * 0.5}
          ry={len * 0.19}
          fill={color}
          transform={`translate(${x.toFixed(1)},${y.toFixed(1)}) rotate(${(tangent + s * 38).toFixed(1)})`}
        />,
      );
    }
  }
  return (
    <g>
      <path d={stem} fill="none" stroke={color} strokeWidth={ONU_R * 0.03} strokeLinecap="round" />
      {leaves}
    </g>
  );
};

export const DrapeauOnu: React.FC<DrapeauOnuProps> = ({
  recolorAt,
  fromColor = FLAG_COLORS.onuBlue,
  toColor = FLAG_COLORS.chinaRed,
  emblemColor = COLORS.white,
  flagWidth = 1200,
  waveAmplitude = 22,
  waveLength = 640,
  wavePeriod = 32,
}) => {
  const frame = useCurrentFrame();
  const {width, height} = useVideoConfig();

  const mix = Math.max(0, Math.min(1, (frame - recolorAt + 1) / CUT_FRAMES));
  const flagHeight = (flagWidth * 2) / 3;
  const x0 = (width - flagWidth) / 2;
  const y0 = (height - flagHeight) / 2;
  const cx = x0 + flagWidth / 2;
  const cy = y0 + flagHeight / 2;

  // Ondoiement : bandes verticales décalées en y, amplitude croissante de la hampe vers le bord flottant,
  // cisaillement égal à la pente locale pour effacer les raccords.
  const strip = 6;
  const nStrips = Math.ceil(flagWidth / strip);
  const phase = (2 * Math.PI * frame) / wavePeriod;
  const wave = (x: number) => {
    const u = x / flagWidth;
    const amp = waveAmplitude * u * u;
    const k = (2 * Math.PI) / waveLength;
    return {y: amp * Math.sin(k * x - phase), dy: amp * k * Math.cos(k * x - phase)};
  };

  return (
    <AbsoluteFill style={{backgroundColor: 'transparent'}}>
      <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`}>
        <defs>
          <g id="drapeau">
            <rect x={x0} y={y0} width={flagWidth} height={flagHeight} fill={fromColor} />
            <rect x={x0} y={y0} width={flagWidth} height={flagHeight} fill={toColor} fillOpacity={mix} />
            <g transform={`translate(${cx},${cy - ONU_R * 0.1}) scale(0.95)`}>
              <circle r={ONU_R} fill="none" stroke={emblemColor} strokeWidth={5} />
              <path d={ONU_LAND} fill={emblemColor} />
              {/* Graticule couleur du fond, par-dessus les terres (comme sur l'emblème). */}
              <path d={ONU_GRATICULE} fill="none" stroke={fromColor} strokeWidth={2.5} />
              <path d={ONU_GRATICULE} fill="none" stroke={toColor} strokeOpacity={mix} strokeWidth={2.5} />
              <Branch side={-1} color={emblemColor} />
              <Branch side={1} color={emblemColor} />
            </g>
          </g>
          {Array.from({length: nStrips}, (_, i) => (
            <clipPath key={i} id={`b${i}`}>
              <rect x={x0 + i * strip} y={y0 - 200} width={strip + 0.5} height={flagHeight + 400} />
            </clipPath>
          ))}
        </defs>
        {Array.from({length: nStrips}, (_, i) => {
          const xs = i * strip + strip / 2;
          const {y, dy} = wave(xs);
          const px = x0 + xs;
          return (
            <use
              key={i}
              href="#drapeau"
              clipPath={`url(#b${i})`}
              transform={`translate(${px},${(y0 + y).toFixed(2)}) matrix(1,${dy.toFixed(4)},0,1,0,0) translate(${-px},${-y0})`}
            />
          );
        })}
      </svg>
    </AbsoluteFill>
  );
};
