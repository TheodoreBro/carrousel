import {useMemo} from 'react';
import {AbsoluteFill, random, useCurrentFrame, useVideoConfig} from 'remotion';
import {COLORS} from '../config';
import {FIGURES, FIGURE_HEIGHT, FRANCE_D} from '../data/france';

export type CarteFranceProps = {
  // Durée du tracé du contour, en frames (linéaire).
  drawFrames: number;
  // Frame à laquelle les bonhommes apparaissent (tous d'un coup).
  figuresAt: number;
  // Frame à laquelle une part des bonhommes disparaît (d'un coup).
  vanishAt: number;
  // Part des bonhommes qui disparaît (0,35 = 35 %).
  vanishShare: number;
  strokeColor?: string;
  strokeWidth?: number;
  figureColor?: string;
  // Graine du tirage : change les bonhommes qui disparaissent, pas leur nombre.
  seed?: string;
};

// Carte de France au trait, trame de bonhommes, puis disparition sèche d'une part d'entre eux.
export const CarteFrance: React.FC<CarteFranceProps> = ({
  drawFrames,
  figuresAt,
  vanishAt,
  vanishShare,
  strokeColor = COLORS.white,
  strokeWidth = 3,
  figureColor = COLORS.white,
  seed = 'france',
}) => {
  const frame = useCurrentFrame();
  const {width, height} = useVideoConfig();

  const draw = Math.min(1, (frame + 1) / drawFrames);
  const shown = frame >= figuresAt;
  const vanished = frame >= vanishAt;

  // Tirage déterministe : ordre aléatoire fixe, les N premiers disparaissent.
  const gone = useMemo(() => {
    const order = FIGURES.map((_, i) => i).sort((a, b) => random(`${seed}-${a}`) - random(`${seed}-${b}`));
    return new Set(order.slice(0, Math.round(FIGURES.length * vanishShare)));
  }, [seed, vanishShare]);

  const h = FIGURE_HEIGHT;

  return (
    <AbsoluteFill style={{backgroundColor: 'transparent'}}>
      <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`}>
        <defs>
          {/* Pictogramme : tête, épaules arrondies, jambes. Boîte 1x1, x de -0,5 à 0,5. */}
          <symbol id="bonhomme" viewBox="-0.5 0 1 1">
            <circle cx="0" cy="0.13" r="0.13" />
            <path d="M-0.27,0.44 Q-0.27,0.32 -0.15,0.32 L0.15,0.32 Q0.27,0.32 0.27,0.44 L0.27,0.66 L0.17,0.66 L0.17,1 L0.04,1 L0.04,0.74 L-0.04,0.74 L-0.04,1 L-0.17,1 L-0.17,0.66 L-0.27,0.66 Z" />
          </symbol>
        </defs>
        <path
          d={FRANCE_D}
          pathLength={1}
          fill="none"
          stroke={strokeColor}
          strokeWidth={strokeWidth}
          strokeLinejoin="round"
          strokeLinecap="round"
          strokeDasharray={1}
          strokeDashoffset={1 - draw}
        />
        {shown &&
          FIGURES.map(([x, y], i) =>
            vanished && gone.has(i) ? null : (
              <use key={i} href="#bonhomme" x={x - h / 2} y={y - h / 2} width={h} height={h} fill={figureColor} />
            ),
          )}
      </svg>
    </AbsoluteFill>
  );
};
