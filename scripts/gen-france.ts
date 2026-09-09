// Génère src/data/france.ts : tracé SVG de la France métropolitaine (Natural Earth 10m, projection
// conique conforme type Lambert-93) et positions d'une trame de bonhommes à l'intérieur du contour.
// À relancer seulement si le cadrage ou la trame change : npx tsx scripts/gen-france.ts
import {geoConicConformal, geoPath} from 'd3-geo';
import {writeFileSync} from 'node:fs';
import {feature} from 'topojson-client';
import type {Topology, GeometryCollection, Polygon, MultiPolygon} from 'topojson-specification';
import {VIDEO} from '../src/config';

// eslint-disable-next-line @typescript-eslint/no-require-imports
const topo = require('world-atlas/countries-10m.json') as Topology<{countries: GeometryCollection<{name: string}>}>;

type Geom = Polygon<{name: string}> | MultiPolygon<{name: string}>;
const geoms = topo.objects.countries.geometries as Geom[];
const france = geoms.find((g) => (g.properties as {name?: string} | undefined)?.name === 'France');
if (!france) throw new Error('France introuvable');

// Métropole + Corse : on écarte l'outre-mer (polygones dont le centre sort de ce cadre lon/lat).
const [W, E, S, N] = [-6, 10.5, 41, 51.5];
const raw = (feature(topo, france) as GeoJSON.Feature).geometry as GeoJSON.MultiPolygon | GeoJSON.Polygon;
const polys = raw.type === 'MultiPolygon' ? raw.coordinates : [raw.coordinates];
const inside = (ring: GeoJSON.Position[]) => {
  const lon = ring.reduce((a, c) => a + c[0], 0) / ring.length;
  const lat = ring.reduce((a, c) => a + c[1], 0) / ring.length;
  return lon >= W && lon <= E && lat >= S && lat <= N;
};
const geom: GeoJSON.MultiPolygon = {type: 'MultiPolygon', coordinates: polys.filter((p) => inside(p[0]))};

const MARGIN = 60;
const projection = geoConicConformal()
  .rotate([-3, 0])
  .parallels([44, 49])
  .fitExtent([[MARGIN, MARGIN], [VIDEO.width - MARGIN, VIDEO.height - MARGIN]], geom);
const d = geoPath(projection).digits(1)(geom);
if (!d) throw new Error('Tracé vide');

// Anneaux projetés en coordonnées écran (extérieurs et trous), pour le test point-dans-polygone.
const rings: [number, number][][] = geom.coordinates.flatMap((poly) =>
  poly.map((ring) => ring.map((p) => projection(p as [number, number]) as [number, number])),
);

const contains = (x: number, y: number) => {
  let inside = false;
  for (const ring of rings) {
    for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
      const [xi, yi] = ring[i];
      const [xj, yj] = ring[j];
      if (yi > y !== yj > y && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) inside = !inside;
    }
  }
  return inside;
};

const distToOutline = (x: number, y: number) => {
  let best = Infinity;
  for (const ring of rings) {
    for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
      const [x1, y1] = ring[j];
      const [x2, y2] = ring[i];
      const dx = x2 - x1;
      const dy = y2 - y1;
      const len2 = dx * dx + dy * dy || 1;
      const t = Math.max(0, Math.min(1, ((x - x1) * dx + (y - y1) * dy) / len2));
      const px = x1 + t * dx - x;
      const py = y1 + t * dy - y;
      best = Math.min(best, px * px + py * py);
    }
  }
  return Math.sqrt(best);
};

// Trame en quinconce. Un bonhomme est retenu si son centre est dans le contour et à bonne distance
// du trait (le bonhomme fait FIGURE px de haut ; on garde un dégagement d'un quart en plus).
const FIGURE = 20;
const STEP_X = 26;
const STEP_Y = 24;
const CLEARANCE = FIGURE * 0.7;
const figures: [number, number][] = [];
for (let row = 0, y = MARGIN; y <= VIDEO.height - MARGIN; y += STEP_Y, row++) {
  for (let x = MARGIN + (row % 2 ? STEP_X / 2 : 0); x <= VIDEO.width - MARGIN; x += STEP_X) {
    if (contains(x, y) && distToOutline(x, y) >= CLEARANCE) figures.push([Math.round(x), Math.round(y)]);
  }
}

const out = `// Généré par scripts/gen-france.ts — ne pas éditer à la main.
// Contour de la France métropolitaine (Corse comprise), en coordonnées écran ${VIDEO.width}x${VIDEO.height}.
export const FRANCE_D = ${JSON.stringify(d)};
// Hauteur de bonhomme pour laquelle la trame a été calculée (px).
export const FIGURE_HEIGHT = ${FIGURE};
// Centres des bonhommes, trame en quinconce ${STEP_X}x${STEP_Y} px.
export const FIGURES: [number, number][] = ${JSON.stringify(figures)};
`;
writeFileSync('src/data/france.ts', out);
console.log(`${geom.coordinates.length} polygones, ${figures.length} bonhommes, ${(out.length / 1024).toFixed(0)} Ko`);
