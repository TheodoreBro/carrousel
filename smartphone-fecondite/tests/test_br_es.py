"""Brésil et Espagne — lecteurs communs sur des fichiers synthétiques : JSON de l'API IBGE, microdonnées INE à largeur fixe,
PC-Axis du Padrón, groupes d'âge."""
import io
import json
import sys
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from common import br, es  # noqa: E402


def test_read_ibge_long_table(tmp_path):
    data = [{"id": "217", "variavel": "Nascidos vivos", "unidade": "Pessoas", "resultados": [
        {"classificacoes": [{"id": "232", "nome": "Ano de nascimento", "categoria": {"40289": "2015"}},
                            {"id": "240", "nome": "Idade da mãe", "categoria": {"5414": "15 a 19 anos"}}],
         "series": [{"localidade": {"id": "1100015", "nivel": {"id": "N6"}, "nome": "A"}, "serie": {"2015": "76"}},
                    {"localidade": {"id": "1100023", "nivel": {"id": "N6"}, "nome": "B"}, "serie": {"2015": "-"}},
                    {"localidade": {"id": "1100031", "nivel": {"id": "N6"}, "nome": "C"}, "serie": {"2015": "..."}}]}]}]
    p = tmp_path / "x.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    d = br.read_ibge(p)
    assert list(d.municipio) == ["1100015", "1100023", "1100031"] and list(d.year) == [2015] * 3
    assert d.value.tolist()[0] == 76 and np.isnan(d.value.iloc[1]) and np.isnan(d.value.iloc[2])
    assert d.raw.tolist() == ["76", "-", "..."] and d["Ano de nascimento"].iloc[0] == "2015" and d.cat_240.iloc[0] == "5414"


def _fw_line(fields: dict, values: dict, length: int) -> str:
    buf = [" "] * length
    for k, (a, b) in fields.items():
        v = values.get(k, "")
        buf[a - 1:a - 1 + len(v)] = list(v.rjust(b - a + 1) if k in ("EDADM", "NUMHV") else v)
    return "".join(buf)


def test_read_births_fixed_width(tmp_path):
    f = es.BIRTH_FIELDS_0715
    lines = [_fw_line(f, {"PROI": "28", "MUNI": "079", "ANOPAR": "2010", "PAISNXM": "108", "PROREM": "28", "MUNREM": "079", "ECIVM": "1", "NUMHV": " 0",
                          "TMUNRM": "6", "EDADM": "31", "NACVN": "1", "CLASIF": "3"}, 202),
             _fw_line(f, {"PROI": "28", "MUNI": "079", "ANOPAR": "2010", "PAISNXM": "228", "PROREM": "28", "MUNREM": "   ", "ECIVM": "2", "NUMHV": " 2",
                          "TMUNRM": "1", "EDADM": "17", "NACVN": "1", "CLASIF": "3"}, 202),
             _fw_line(f, {"PROI": "08", "MUNI": "019", "ANOPAR": "2010", "PAISNXM": "   ", "PROREM": "08", "MUNREM": "019", "ECIVM": "1", "NUMHV": " 1",
                          "TMUNRM": "6", "EDADM": "40", "NACVN": "2", "CLASIF": "2"}, 202)]
    p = tmp_path / "datos_nacimientos2010.zip"
    with zipfile.ZipFile(p, "w") as z:
        z.writestr("NACIMIENTOS A2010.txt", "\n".join(lines) + "\n")
    b = es.read_births(p)
    assert b.municipio.tolist()[0] == "28079" and pd.isna(b.municipio.iloc[1]) and b.municipio.iloc[2] == "08019"
    assert b.age.tolist() == [31, 17, 40] and b.married.tolist() == [1.0, 0.0, 1.0] and b.rank1.tolist() == [1.0, 0.0, 0.0]
    assert b.foreign_born.tolist() == [0.0, 1.0, 0.0] and b.live.tolist() == [True, True, False]
    assert list(es.age_group_of(b.age)) == ["30-34", "15-19", "40-49"]


def test_read_padron_px(tmp_path):
    head = ('CHARSET="ANSI";\nSTUB="Sexo","Municipios","Periodo";\nHEADING="Edad (grupos quinquenales)";\n'
            'VALUES("Sexo")="Total","Hombres","Mujeres";\nVALUES("Municipios")="Total Nacional","28079 Madrid";\n'
            'VALUES("Periodo")="1 de enero de 2022","1 de enero de 2021";\nVALUES("Edad (grupos quinquenales)")="Todas las edades","De 15 a 19 años";\n'
            'CODES("Municipios")="CA00","28079";\n')
    vals = np.arange(3 * 2 * 2 * 2, dtype=float)
    data = "DATA=\n" + " ".join(str(v) for v in vals) + ";\n"
    p = tmp_path / "padron.px"
    p.write_bytes((head + data).encode("iso-8859-15"))
    d = es.read_padron_px(p)
    assert set(d.municipio) == {"28079"} and set(d.year) == {2021, 2022} and set(d.sex) == {"total", "h", "f"}
    # ordre STUB × HEADING : Sexo=Mujeres (2), municipio index 1, période 2021 (index 1), âge 15-19 (index 1) → ((2*2+1)*2+1)*2+1 = 23
    row = d[(d.sex == "f") & (d.year == 2021) & (d.age_group == "De 15 a 19 años")]
    assert row["pop"].iloc[0] == 23.0
    assert es.padron_age_group("De 15 a 19 años") == "15-19" and es.padron_age_group("De 45 a 49 años") == "40-49" and es.padron_age_group("De 50 a 54 años") is None


def test_br_age_mapping():
    assert br.IBGE_GROUP_TO_AGE["45 a 49 anos"] == "40-49" and br.REGIONS["3"] == "Sudeste"
