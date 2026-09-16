import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {COLORS, CUT_FRAMES, FONT} from '../config';
import {fontFamily} from '../fonts';

export type Coin = 'haut-gauche' | 'haut-droite' | 'bas-gauche' | 'bas-droite' | 'centre';

export type Segment = {
  // Les espaces comptent : « Qui me » + « parle » se collent en « Qui meparle » ; écrire « Qui me ».
  // Un mot peut changer de couleur en son milieu : « l'» + « oreillette » = un seul mot bicolore.
  text: string;
  color?: string;
};

export type Bloc = {
  // Lignes du bloc, chacune faite de segments ; les mots arrivent un par un, dans l'ordre de lecture.
  lignes: Segment[][];
  at: number; // frame du premier mot
  stagger: number; // frames entre deux mots
  coin: Coin; // ancrage : un coin de l'écran (texte aligné du même côté) ou le centre
  x?: number; // distance au bord vertical du coin (px) ; ignoré au centre
  y?: number; // distance au bord horizontal du coin (px) ; ignoré au centre
  blurAt?: number; // frame à laquelle le bloc se floute (jamais si absent)
  blur?: number; // flou maximal (px)
  hideAt?: number; // frame à laquelle le bloc disparaît d'un coup (jamais si absent)
  gap?: number; // espace entre les lignes (px), p. ex. pour dégager les accents
  size?: number;
  color?: string;
};

export type MotAMotProps = {
  blocs: Bloc[];
  size?: number;
  color?: string;
};

type Morceau = {text: string; color?: string};
type Mot = Morceau[];

// Découpe une ligne en mots ; un mot peut être fait de plusieurs morceaux de couleurs différentes.
const mots = (ligne: Segment[]): Mot[] => {
  const out: Mot[] = [];
  let ouvert = false; // un mot est en cours (pas d'espace depuis son début)
  for (const seg of ligne) {
    const parts = seg.text.split(' ');
    parts.forEach((part, i) => {
      if (i > 0) ouvert = false;
      if (part === '') return;
      if (ouvert) out[out.length - 1].push({text: part, color: seg.color});
      else out.push([{text: part, color: seg.color}]);
      ouvert = true;
    });
    if (seg.text.endsWith(' ')) ouvert = false;
  }
  return out;
};

const progress = (frame: number, at: number) => Math.max(0, Math.min(1, (frame - at + 1) / CUT_FRAMES));

const BlocMots: React.FC<{bloc: Bloc; frame: number; size: number; color: string}> = ({bloc, frame, size, color}) => {
  if (bloc.hideAt !== undefined && frame >= bloc.hideAt) return null;
  const centre = bloc.coin === 'centre';
  const droite = bloc.coin.endsWith('droite');
  const bas = bloc.coin.startsWith('bas');
  const flou = bloc.blurAt === undefined ? 0 : progress(frame, bloc.blurAt) * (bloc.blur ?? 8);
  const position = centre
    ? {left: '50%', top: '50%', transform: 'translate(-50%, -50%)'}
    : {[droite ? 'right' : 'left']: bloc.x ?? 0, [bas ? 'bottom' : 'top']: bloc.y ?? 0};
  let index = 0; // rang du mot dans le bloc, toutes lignes confondues
  return (
    <div
      style={{
        position: 'absolute',
        ...position,
        fontFamily,
        fontSize: bloc.size ?? size,
        color: bloc.color ?? color,
        letterSpacing: FONT.letterSpacing,
        lineHeight: FONT.lineHeight,
        textTransform: FONT.textTransform,
        textAlign: centre ? 'center' : droite ? 'right' : 'left',
        whiteSpace: 'nowrap',
        filter: flou > 0 ? `blur(${flou}px)` : 'none',
      }}
    >
      {bloc.lignes.map((ligne, i) => (
        <div key={i} style={{marginTop: i === 0 ? 0 : (bloc.gap ?? 0)}}>
          {mots(ligne).map((mot, j) => {
            const p = progress(frame, bloc.at + index++ * bloc.stagger);
            return (
              <span key={j}>
                {j > 0 && ' '}
                <span style={{display: 'inline-block', clipPath: `inset(-40% 0 ${(1 - p) * 100}% 0)`}}>
                  {mot.map((m, k) => (
                    <span key={k} style={{color: m.color}}>
                      {m.text}
                    </span>
                  ))}
                </span>
              </span>
            );
          })}
        </div>
      ))}
    </div>
  );
};

// Phrase en blocs ancrés aux coins ou au centre de l'écran, mots révélés un par un ; un bloc peut se flouter puis disparaître.
export const MotAMot: React.FC<MotAMotProps> = ({blocs, size = 140, color = COLORS.white}) => {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill style={{backgroundColor: 'transparent'}}>
      {blocs.map((b, i) => (
        <BlocMots key={i} bloc={b} frame={frame} size={size} color={color} />
      ))}
    </AbsoluteFill>
  );
};
