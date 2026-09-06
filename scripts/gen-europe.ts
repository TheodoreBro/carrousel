// Génère src/data/europe.ts : tracés SVG des pays d'Europe (Natural Earth 10m, projection conique conforme).
// À relancer seulement si la sélection de pays ou le cadrage change : npx tsx scripts/gen-europe.ts
import {geoConicConformal, geoPath} from 'd3-geo';
import {writeFileSync} from 'node:fs';
import {feature, merge} from 'topojson-client';
import type {Topology, GeometryCollection, Polygon, MultiPolygon} from 'topojson-specification';
import {VIDEO} from '../src/config';

// eslint-disable-next-line @typescript-eslint/no-require-imports
const topo = require('world-atlas/countries-10m.json') as Topology<{countries: GeometryCollection<{name: string}>}>;

const EU = new Set([
  'Austria', 'Belgium', 'Bulgaria', 'Croatia', 'Cyprus', 'Czechia', 'Denmark', 'Estonia', 'Finland',
  'France', 'Germany', 'Greece', 'Hungary', 'Ireland', 'Italy', 'Latvia', 'Lithuania', 'Luxembourg',
  'Malta', 'Netherlands', 'Poland', 'Portugal', 'Romania', 'Slovakia', 'Slovenia', 'Spain', 'Sweden',
]);
const OTHERS = new Set([
  'United Kingdom', 'Norway', 'Iceland', 'Switzerland', 'Liechtenstein', 'Andorra', 'Monaco',
  'San Marino', 'Vatican', 'Ukraine', 'Belarus', 'Moldova', 'Serbia', 'Bosnia and Herz.',
  'Montenegro', 'Macedonia', 'Albania', 'Kosovo', 'Isle of Man', 'Jersey', 'Guernsey',
]);

// Cadrage géographique (lon/lat) : Islande → Chypre, Portugal → Ukraine.
// Anneau densifié (d3 relie les sommets par grands cercles) et en sens horaire (convention d3).
const [W, E, S, N] = [-24, 40.5, 34.5, 71.5];
const ring: [number, number][] = [];
for (let lat = S; lat < N; lat++) ring.push([W, lat]);
for (let lon = W; lon < E; lon++) ring.push([lon, N]);
for (let lat = N; lat > S; lat--) ring.push([E, lat]);
for (let lon = E; lon > W; lon--) ring.push([lon, S]);
ring.push([W, S]);
const BBOX: GeoJSON.Polygon = {type: 'Polygon', coordinates: [ring]};

const MARGIN = 60;
const projection = geoConicConformal()
  .rotate([-10, 0])
  .parallels([40, 65])
  .fitExtent([[MARGIN, MARGIN], [VIDEO.width - MARGIN, VIDEO.height - MARGIN]], BBOX)
  .clipExtent([[0, 0], [VIDEO.width, VIDEO.height]]);
const path = geoPath(projection).digits(1);

type Geom = Polygon<{name: string}> | MultiPolygon<{name: string}>;
const geoms = topo.objects.countries.geometries as Geom[];
const nameOf = (g: Geom) => (g.properties as {name?: string} | undefined)?.name ?? '';
const byName = (n: string) => geoms.filter((g) => nameOf(g) === n);

// Retire les polygones dont le centre sort du cadrage (Açores, Canaries, Svalbard, outre-mer…).
const inBbox = (geom: GeoJSON.Geometry): GeoJSON.Geometry => {
  const inside = (ring: GeoJSON.Position[]) => {
    const lon = ring.reduce((a, c) => a + c[0], 0) / ring.length;
    const lat = ring.reduce((a, c) => a + c[1], 0) / ring.length;
    return lon >= W && lon <= E && lat >= S && lat <= N;
  };
  if (geom.type === 'MultiPolygon') {
    return {type: 'MultiPolygon', coordinates: geom.coordinates.filter((poly) => inside(poly[0]))};
  }
  return geom;
};

type Entry = {name: string; eu: boolean; d: string};
const entries: Entry[] = [];
for (const g of geoms) {
  const name = nameOf(g);
  if (name === 'N. Cyprus') continue; // fusionné avec Chypre ci-dessous
  if (!EU.has(name) && !OTHERS.has(name)) continue;
  const geom = name === 'Cyprus' ? merge(topo, [...byName('Cyprus'), ...byName('N. Cyprus')]) : (feature(topo, g) as GeoJSON.Feature).geometry;
  const d = path(inBbox(geom));
  if (!d) continue;
  entries.push({name, eu: EU.has(name), d});
}

const missing = [...EU, ...OTHERS].filter((n) => !entries.some((e) => e.name === n));
if (missing.length) throw new Error('Pays introuvables : ' + missing.join(', '));

const out = `// Généré par scripts/gen-europe.ts — ne pas éditer à la main.
export type Country = {name: string; eu: boolean; d: string};
export const EUROPE: Country[] = ${JSON.stringify(entries, null, 0).replace(/\},\{/g, '},\n{')};
`;
writeFileSync('src/data/europe.ts', out);
console.log(`${entries.length} pays, ${(out.length / 1024).toFixed(0)} Ko`);
