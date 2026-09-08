import {AbsoluteFill, useCurrentFrame, useVideoConfig} from 'remotion';
import {COLORS, CUT_FRAMES, FONT_SECONDARY} from '../config';
import {fontFamilySecondary} from '../fonts';

export type ChapitresProps = {
  chapitres: string[];
  label?: string; // "Chapitre" → "Chapitre 1", "Chapitre 2"…
  barY?: number; // ordonnée de la ligne (px)
  // Entrée : la barre monte à barAt, puis les chapitres dans l'ordre à partir de chaptersAt.
  barAt: number;
  chaptersAt: number;
  stagger: number;
  // Sortie : les chapitres redescendent dans l'ordre exitOrder (indices 0-based), puis la barre.
  exitAt: number;
  exitOrder: number[];
  barExitAt: number;
  labelSize?: number;
  titleSize?: number;
  color?: string;
};

const lin = (frame: number, at: number) => Math.max(0, Math.min(1, (frame - at + 1) / CUT_FRAMES));

export const Chapitres: React.FC<ChapitresProps> = ({
  chapitres,
  label = 'Chapitre',
  barY = 800,
  barAt,
  chaptersAt,
  stagger,
  exitAt,
  exitOrder,
  barExitAt,
  labelSize = 28,
  titleSize = 36,
  color = COLORS.white,
}) => {
  const frame = useCurrentFrame();
  const {width, height} = useVideoConfig();
  const n = chapitres.length;
  const seg = width / n;
  const below = height + 40; // hors cadre, en bas

  // Position verticale d'un élément : entre depuis le bas, ressort vers le bas.
  const offset = (enterAt: number, leaveAt: number, restY: number) => {
    const inP = lin(frame, enterAt);
    const outP = lin(frame, leaveAt);
    return restY + (below - restY) * (1 - inP) + (below - restY) * outP;
  };

  const barOffset = offset(barAt, barExitAt, barY) - barY;

  return (
    <AbsoluteFill style={{backgroundColor: 'transparent'}}>
      <svg width={width} height={height} style={{position: 'absolute', left: 0, top: 0}}>
        <g transform={`translate(0,${barOffset.toFixed(2)})`}>
          <line x1={0} y1={barY} x2={width} y2={barY} stroke={color} strokeWidth={5} />
          {Array.from({length: n + 1}, (_, i) => (
            <circle key={`b${i}`} cx={i * seg} cy={barY} r={13} fill={color} />
          ))}
          {Array.from({length: n}, (_, i) =>
            [0.2, 0.4, 0.6, 0.8].map((f) => (
              <circle key={`s${i}-${f}`} cx={i * seg + f * seg} cy={barY} r={5.5} fill={color} />
            )),
          )}
        </g>
      </svg>
      {chapitres.map((titre, i) => {
        const rank = exitOrder.indexOf(i);
        const top = offset(chaptersAt + i * stagger, exitAt + rank * stagger, barY + 36);
        return (
          <div
            key={i}
            style={{
              position: 'absolute',
              left: i * seg + 48,
              top,
              width: seg - 70,
              fontFamily: fontFamilySecondary,
              color,
              letterSpacing: FONT_SECONDARY.letterSpacing,
              lineHeight: FONT_SECONDARY.lineHeight,
            }}
          >
            <div style={{fontSize: labelSize, fontWeight: 500, opacity: 0.7}}>
              {label} {i + 1}
            </div>
            <div style={{fontSize: titleSize, fontWeight: 600, marginTop: 6}}>{titre}</div>
          </div>
        );
      })}
    </AbsoluteFill>
  );
};
