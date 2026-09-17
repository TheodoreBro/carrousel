import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {COLORS, FONT_MANUSCRITE, TEXT_SHADOW} from '../config';
import {fontFamilyManuscrite} from '../fonts';

export type Signature = {
  text: string;
  startAt: number; // frame où le stylo se pose pour signer
  dureeEcriture: number; // frames pour écrire la signature
  size?: number;
  color?: string;
};

export type ManuscritProps = {
  text: string;
  startAt: number; // frame où le stylo se pose
  dureeEcriture: number; // frames pour écrire tout le texte, vitesse constante
  y: number; // haut de la ligne (px)
  size?: number;
  color?: string;
  shadow?: boolean; // ombre portée derrière le trait (lisibilité sur image)
  // Signature sous la phrase, alignée sur son bord droit, écrite de la même façon.
  signature?: Signature;
};

// Bord de révélation légèrement incliné (suit la pente de l'écriture) qui avance à vitesse constante.
const PENTE = 6; // % de la largeur du texte
const clip = (frame: number, at: number, duree: number) => {
  const p = Math.max(0, Math.min(1, (frame - at + 1) / duree));
  const haut = p * (100 + PENTE);
  return `polygon(-5% -30%, ${haut}% -30%, ${haut - PENTE}% 130%, -5% 130%)`;
};

// Texte manuscrit qui s'écrit de gauche à droite, comme sous un stylo.
export const Manuscrit: React.FC<ManuscritProps> = ({
  text,
  startAt,
  dureeEcriture,
  y,
  size = 130,
  color = COLORS.accent,
  shadow = false,
  signature,
}) => {
  const frame = useCurrentFrame();
  const commun = {
    fontFamily: fontFamilyManuscrite,
    fontWeight: 600,
    letterSpacing: FONT_MANUSCRITE.letterSpacing,
    lineHeight: FONT_MANUSCRITE.lineHeight,
    whiteSpace: 'nowrap' as const,
    textShadow: shadow ? TEXT_SHADOW : 'none',
  };
  return (
    <AbsoluteFill style={{backgroundColor: 'transparent'}}>
      <div style={{position: 'absolute', top: y, left: 0, width: '100%', textAlign: 'center'}}>
        <div style={{display: 'inline-block', textAlign: 'right'}}>
          <div style={{textAlign: 'left'}}>
            <span style={{...commun, display: 'inline-block', fontSize: size, color, clipPath: clip(frame, startAt, dureeEcriture)}}>
              {text}
            </span>
          </div>
          {signature && (
            <div>
              <span
                style={{
                  ...commun,
                  display: 'inline-block',
                  fontSize: signature.size ?? size * 0.7,
                  color: signature.color ?? color,
                  clipPath: clip(frame, signature.startAt, signature.dureeEcriture),
                }}
              >
                {signature.text}
              </span>
            </div>
          )}
        </div>
      </div>
    </AbsoluteFill>
  );
};
