import {AbsoluteFill, Html5Audio, Sequence, staticFile, useCurrentFrame} from 'remotion';
import {COLORS, CUT_FRAMES, FONT} from '../config';
import {fontFamily} from '../fonts';

export type MotFrappe = {
  text: string;
  at: number; // frame d'apparition, d'un coup
  size?: number; // px
  color?: string;
  bandes?: string[]; // remplissage en bandes verticales égales, de gauche à droite (drapeau) ; remplace color
  blurAt?: number; // frame à laquelle le mot se floute (en CUT_FRAMES)
  blur?: number; // flou maximal (px)
  son?: string; // fichier dans public/, joué à l'apparition du mot
  sonVolume?: number; // 1 = niveau du fichier
};

export type LigneFrappe = {
  mots: MotFrappe[]; // mots de la ligne, alignés sur la ligne de base
  indent?: number; // décalage vers la droite (px)
};

export type FrappeProps = {
  lignes: LigneFrappe[];
  size?: number; // taille par défaut (px)
  gap?: number; // espace au-dessus de chaque ligne sauf la première (px), p. ex. pour dégager les accents
};

const progress = (frame: number, at: number) => Math.max(0, Math.min(1, (frame - at + 1) / CUT_FRAMES));

// Remplissage en bandes verticales à bords nets, découpé dans les lettres.
const remplissage = (bandes: string[]) => {
  const pas = 100 / bandes.length;
  const stops = bandes.map((c, i) => `${c} ${i * pas}% ${(i + 1) * pas}%`).join(', ');
  return {
    backgroundImage: `linear-gradient(90deg, ${stops})`,
    WebkitBackgroundClip: 'text',
    backgroundClip: 'text',
    color: 'transparent',
    // Le fond ne se peint que dans la boîte du mot : on l'agrandit en hauteur (accents, cédille)
    // sans rien déplacer.
    padding: '0.35em 0',
    margin: '-0.35em 0',
  };
};

// Bloc de lignes centré à l'écran. Chaque mot apparaît d'un coup, sans volet ; un mot peut se flouter
// et déclencher un son au moment exact où il apparaît.
export const Frappe: React.FC<FrappeProps> = ({lignes, size = 120, gap = 0}) => {
  const frame = useCurrentFrame();
  const mots = lignes.flatMap((l) => l.mots);
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
              fontSize: Math.max(...l.mots.map((m) => m.size ?? size)),
              marginLeft: l.indent ?? 0,
              marginTop: i === 0 ? 0 : gap,
            }}
          >
            {l.mots.map((m, j) => {
              const flou = m.blurAt === undefined ? 0 : progress(frame, m.blurAt) * (m.blur ?? 8);
              return (
                <span key={j}>
                  {j > 0 && ' '}
                  <span
                    style={{
                      display: 'inline-block',
                      fontSize: m.size ?? size,
                      color: m.color ?? COLORS.white,
                      ...(m.bandes ? remplissage(m.bandes) : {}),
                      filter: flou > 0 ? `blur(${flou}px)` : 'none',
                      // La place est réservée dès le début : rien ne bouge quand un mot apparaît.
                      visibility: frame >= m.at ? 'visible' : 'hidden',
                    }}
                  >
                    {m.text}
                  </span>
                </span>
              );
            })}
          </div>
        ))}
      </div>
      {mots.map((m, i) =>
        m.son ? (
          <Sequence key={i} from={m.at} layout="none">
            <Html5Audio src={staticFile(m.son)} volume={m.sonVolume ?? 1} />
          </Sequence>
        ) : null,
      )}
    </AbsoluteFill>
  );
};
