import {AbsoluteFill, useCurrentFrame, useVideoConfig} from 'remotion';
import {COLORS} from '../config';

export type RondeProps = {
  pairs: number; // nombre de couples (figure A + figure B) sur la ronde
  colorA?: string; // figures féminines
  colorB?: string; // petits hommes verts
  cx?: number;
  cy?: number; // ordonnée du centre de l'ellipse (pieds)
  rx?: number;
  ry?: number;
  height?: number; // hauteur d'une figure féminine au premier plan (px)
  turnFrames: number; // durée d'un tour complet (mettre = durationInFrames pour boucler)
  hopFrames: number; // période du sautillement
  hopHeight?: number; // px
};

// Pictogrammes dessinés dans un repère de 100 unités de haut, pieds en y = 100, centre x = 0.
const Femme: React.FC<{color: string}> = ({color}) => (
  <g fill={color}>
    <circle cx={0} cy={12} r={12} />
    <path d="M-9,26 L9,26 L23,74 L-23,74 Z" />
    <rect x={-15} y={72} width={9} height={28} />
    <rect x={6} y={72} width={9} height={28} />
  </g>
);

const HommeVert: React.FC<{color: string}> = ({color}) => (
  <g fill={color} stroke={color}>
    <line x1={-8} y1={40} x2={-14} y2={24} strokeWidth={3} strokeLinecap="round" />
    <line x1={8} y1={40} x2={14} y2={24} strokeWidth={3} strokeLinecap="round" />
    <circle cx={-14} cy={22} r={3.5} stroke="none" />
    <circle cx={14} cy={22} r={3.5} stroke="none" />
    <circle cx={0} cy={50} r={15} stroke="none" />
    <rect x={-10} y={64} width={20} height={22} rx={6} stroke="none" />
    <rect x={-10} y={84} width={7} height={16} stroke="none" />
    <rect x={3} y={84} width={7} height={16} stroke="none" />
  </g>
);

export const Ronde: React.FC<RondeProps> = ({
  pairs,
  colorA = COLORS.white,
  colorB = '#138800',
  cx = 960,
  cy = 640,
  rx = 520,
  ry = 130,
  height = 230,
  turnFrames,
  hopFrames,
  hopHeight = 10,
}) => {
  const frame = useCurrentFrame();
  const {width, height: H} = useVideoConfig();
  const n = pairs * 2;

  const figures = Array.from({length: n}, (_, i) => {
    const a = (2 * Math.PI * i) / n + (2 * Math.PI * frame) / turnFrames;
    const x = cx + rx * Math.cos(a);
    const y = cy + ry * Math.sin(a);
    const depth = (Math.sin(a) + 1) / 2; // 0 au fond, 1 devant
    const s = (height / 100) * (0.72 + 0.5 * depth);
    // Sautillement alterné : les figures paires et impaires sont en opposition de phase.
    const hop = hopHeight * Math.abs(Math.sin((Math.PI * frame) / hopFrames + (i % 2) * (Math.PI / 2)));
    const isA = i % 2 === 0;
    return {i, x, y, s, hop, isA, shoulderY: isA ? 30 : 67};
  });

  // Bras : chaque figure tend la main à la suivante, chaque moitié dans la couleur de son propriétaire.
  const arms = figures.map((f, k) => {
    const g = figures[(k + 1) % n];
    const dir = Math.sign(g.x - f.x) || 1;
    const p0 = [f.x + dir * 9 * f.s, f.y - f.hop - (100 - f.shoulderY) * f.s];
    const p1 = [g.x - dir * 9 * g.s, g.y - g.hop - (100 - g.shoulderY) * g.s];
    const m = [(p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2];
    const zOrder = Math.max(f.y, g.y);
    return {p0, p1, m, zOrder, c0: f.isA ? colorA : colorB, c1: g.isA ? colorA : colorB, w: 5.5 * Math.max(f.s, g.s)};
  });

  const drawables = [
    ...figures.map((f) => ({z: f.y, node: (
      <g key={`f${f.i}`} transform={`translate(${f.x.toFixed(1)},${(f.y - f.hop - 100 * f.s).toFixed(1)}) scale(${f.s.toFixed(3)})`}>
        {f.isA ? <Femme color={colorA} /> : <HommeVert color={colorB} />}
      </g>
    )})),
    ...arms.map((a, k) => ({z: a.zOrder - 0.5, node: (
      <g key={`a${k}`} strokeWidth={a.w} strokeLinecap="round" fill="none">
        <line x1={a.p0[0]} y1={a.p0[1]} x2={a.m[0]} y2={a.m[1]} stroke={a.c0} />
        <line x1={a.m[0]} y1={a.m[1]} x2={a.p1[0]} y2={a.p1[1]} stroke={a.c1} />
      </g>
    )})),
  ].sort((p, q) => p.z - q.z);

  return (
    <AbsoluteFill style={{backgroundColor: 'transparent'}}>
      <svg width={width} height={H}>{drawables.map((d) => d.node)}</svg>
    </AbsoluteFill>
  );
};
