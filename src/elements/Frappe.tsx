import {AbsoluteFill, Html5Audio, Sequence, staticFile, useCurrentFrame} from 'remotion';
import {COLORS, FONT} from '../config';
import {fontFamily} from '../fonts';

export type LigneFrappe = {
  text: string;
  at: number; // frame d'apparition, d'un coup
  size?: number; // px
  color?: string;
  indent?: number; // décalage vers la droite (px)
  son?: string; // fichier dans public/, joué à l'apparition de la ligne
  sonVolume?: number; // 1 = niveau du fichier
};

export type FrappeProps = {
  lignes: LigneFrappe[];
  size?: number; // taille par défaut (px)
  gap?: number; // espace au-dessus de chaque ligne sauf la première (px), p. ex. pour dégager les accents
};

// Bloc de lignes centré à l'écran. Chaque ligne apparaît d'un coup, sans volet ;
// une ligne peut déclencher un son au moment exact où elle apparaît.
export const Frappe: React.FC<FrappeProps> = ({lignes, size = 120, gap = 0}) => {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill style={{backgroundColor: 'transparent'}}>
      <div
        style={{
          position: 'absolute',
          left: '50%',
          top: '50%',
          transform: 'translate(-50%, -50%)',
          fontFamily,
          letterSpacing: FONT.letterSpacing,
          lineHeight: FONT.lineHeight,
          textTransform: FONT.textTransform,
          whiteSpace: 'nowrap',
        }}
      >
        {lignes.map((l, i) => (
          <div
            key={i}
            style={{
              fontSize: l.size ?? size,
              color: l.color ?? COLORS.white,
              marginLeft: l.indent ?? 0,
              marginTop: i === 0 ? 0 : gap,
              // La place est réservée dès le début : le bloc ne bouge pas quand une ligne apparaît.
              visibility: frame >= l.at ? 'visible' : 'hidden',
            }}
          >
            {l.text}
          </div>
        ))}
      </div>
      {lignes.map((l, i) =>
        l.son ? (
          <Sequence key={i} from={l.at} layout="none">
            <Html5Audio src={staticFile(l.son)} volume={l.sonVolume ?? 1} />
          </Sequence>
        ) : null,
      )}
    </AbsoluteFill>
  );
};
