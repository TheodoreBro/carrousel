import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {COLORS, CUT_FRAMES, FONT, TEXT_SHADOW} from '../config';
import {fontFamily} from '../fonts';

export type LigneBandeau = {
  text: string;
  size?: number; // px
  color?: string;
};

export type BandeauProps = {
  lignes: LigneBandeau[];
  at: number; // frame où le bloc commence à entrer (en CUT_FRAMES, linéaire)
  x: number; // bord gauche du bloc une fois en place (px)
  y: number; // distance entre le bas du bloc et le bas de l'écran (px)
  size?: number; // taille par défaut (px)
  gap?: number; // espace au-dessus de chaque ligne sauf la première (px)
  shadow?: boolean; // ombre portée derrière les mots (lisibilité sur image)
};

// Bloc de lignes calé en bas à gauche, qui entre d'un seul tenant depuis le bord gauche de l'écran.
export const Bandeau: React.FC<BandeauProps> = ({lignes, at, x, y, size = 96, gap = 0, shadow = false}) => {
  const frame = useCurrentFrame();
  const p = Math.max(0, Math.min(1, (frame - at + 1) / CUT_FRAMES));
  // Hors cadre à gauche au départ : sa propre largeur + sa marge + 40 px (ombre, débords de lettres).
  const decalage = `calc(${1 - p} * (-100% - ${x + 40}px))`;
  return (
    <AbsoluteFill style={{backgroundColor: 'transparent'}}>
      <div
        style={{
          position: 'absolute',
          left: x,
          bottom: y,
          transform: `translateX(${decalage})`,
          fontFamily,
          letterSpacing: FONT.letterSpacing,
          lineHeight: FONT.lineHeight,
          textTransform: FONT.textTransform,
          whiteSpace: 'nowrap',
          textShadow: shadow ? TEXT_SHADOW : 'none',
        }}
      >
        {lignes.map((l, i) => (
          <div key={i} style={{fontSize: l.size ?? size, color: l.color ?? COLORS.white, marginTop: i === 0 ? 0 : gap}}>
            {l.text}
          </div>
        ))}
      </div>
    </AbsoluteFill>
  );
};
