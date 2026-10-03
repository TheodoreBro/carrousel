// Sons livrés seuls (WAV 48 kHz, 24 bits, stéréo) : npm run build -- --nom=<id> → out/<id>.wav.
// Chaque son est généré par son script scripts/gen-*.ts dans public/sons/ (versionné).
export type SonDef = {
  id: string; // nom passé à --nom ; sert aussi de nom de fichier
  fichier: string; // chemin dans public/
};

export const SONS: SonDef[] = [{id: 'pierre-ravin', fichier: 'sons/pierre-ravin.wav'}];
