import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {COLORS, FONT_MANUSCRITE, TEXT_SHADOW} from '../config';
import {fontFamilyManuscrite} from '../fonts';

export type ManuscritProps = {
  text: string;
  startAt: number; // frame où le stylo se pose
  dureeEcriture: number; // frames pour écrire tout le texte, vitesse constante
  y: number; // haut de la ligne (px)
  size?: number;
  color?: string;
  shadow?: boolean; // ombre portée derrière le trait (lisibilité sur image)
};

// Texte manuscrit qui s'écrit de gauche à droite, comme sous un stylo : le trait est révélé par un
// bord légèrement incliné (suit la pente de l'écriture) qui avance à vitesse constante.
const PENTE = 6; // % de la largeur du texte

export const Manuscrit: React.FC<ManuscritProps> = ({
  text,
  startAt,
  dureeEcriture,
  y,
  size = 130,
  color = COLORS.accent,
  shadow = false,
}) => {
  const frame = useCurrentFrame();
  const p = Math.max(0, Math.min(1, (frame - startAt + 1) / dureeEcriture));
  const haut = p * (100 + PENTE); // bord de révélation, en haut de la ligne
  const bas = haut - PENTE; // et en bas : le bord penche comme les lettres
  return (
    <AbsoluteFill style={{backgroundColor: 'transparent'}}>
      <div style={{position: 'absolute', top: y, left: 0, width: '100%', textAlign: 'center'}}>
        <span
          style={{
            display: 'inline-block',
            fontFamily: fontFamilyManuscrite,
            fontWeight: 600,
            fontSize: size,
            color,
            letterSpacing: FONT_MANUSCRITE.letterSpacing,
            lineHeight: FONT_MANUSCRITE.lineHeight,
            whiteSpace: 'nowrap',
            textShadow: shadow ? TEXT_SHADOW : 'none',
            clipPath: `polygon(-5% -30%, ${haut}% -30%, ${bas}% 130%, -5% 130%)`,
          }}
        >
          {text}
        </span>
      </div>
    </AbsoluteFill>
  );
};
