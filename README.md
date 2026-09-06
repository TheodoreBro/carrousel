# carrousel — atelier motion design

Éléments visuels isolés (Remotion + TypeScript) à importer un par un dans Premiere Pro.

## Rendu ciblé

    npm install
    npm run build -- --nom=<id>

Sortie dans `./out/<id>.mov` (ProRes 4444, alpha) ou `./out/<id>.mp4` (H.264 opaque, fonds plein cadre).
Le script vérifie au ffprobe la résolution, le fps et le canal alpha ; sans alpha, rien n'est livré.

Liste des éléments : `src/elements/registry.ts`. Réglages globaux : `src/config.ts`.

## Variables optionnelles

- `REMOTION_BROWSER=/chemin/vers/chrome-headless-shell` : évite le téléchargement du navigateur.
- `REMOTION_IGNORE_CERT=1` : uniquement derrière un proxy TLS d'entreprise.

Prévisualisation : `npm run studio`.
