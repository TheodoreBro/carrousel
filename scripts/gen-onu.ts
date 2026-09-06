// Génère src/data/onu.ts : carte de l'emblème de l'ONU (azimutale équidistante centrée sur le pôle Nord,
// jusqu'à 60° S), graticule et cercle extérieur, dans un repère de rayon 200 centré en (0,0).
// À relancer seulement si le rayon change : npx tsx scripts/gen-onu.ts
import {geoAzimuthalEquidistant, geoGraticule, geoPath} from 'd3-geo';
import {writeFileSync} from 'node:fs';
import {feature} from 'topojson-client';
import type {Topology, GeometryCollection} from 'topojson-specification';

// eslint-disable-next-line @typescript-eslint/no-require-imports
const topo = require('world-atlas/land-50m.json') as Topology<{land: GeometryCollection}>;

const R = 200;
// Le méridien de Greenwich pointe vers le bas (Afrique en bas, Amériques à gauche), comme sur l'emblème.
const projection = geoAzimuthalEquidistant()
  .rotate([0, -90])
  .clipAngle(150)
  .translate([0, 0])
  .scale(R / (150 * (Math.PI / 180)));
const path = geoPath(projection).digits(1);

const land = path(feature(topo, topo.objects.land) as GeoJSON.FeatureCollection);
// 8 méridiens (tous les 45°) et parallèles tous les 30° : 60°N, 30°N, équateur, 30°S, 60°S (bord).
const graticule = path(geoGraticule().step([45, 30]).extentMinor([[-180, -59.9], [180, 90]])());

const out = `// Généré par scripts/gen-onu.ts — ne pas éditer à la main.
export const ONU_R = ${R};
export const ONU_LAND = ${JSON.stringify(land)};
export const ONU_GRATICULE = ${JSON.stringify(graticule)};
`;
writeFileSync('src/data/onu.ts', out);
console.log(`${(out.length / 1024).toFixed(0)} Ko`);
