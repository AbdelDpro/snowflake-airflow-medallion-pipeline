"""Charge un fichier public de la TLC dans la couche RAW de Snowflake.

Usage :
    python ingestion/charger.py 2025-01   # trajets d'un mois
    python ingestion/charger.py zones     # liste des zones

Variables d'environnement attendues :
    SNOWFLAKE_ACCOUNT, SNOWFLAKE_USER, SNOWFLAKE_PRIVATE_KEY_PATH
"""
import argparse
import os
import re
from pathlib import Path

import requests
import snowflake.connector
from cryptography.hazmat.primitives import serialization

URL_TRAJETS = "https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_{mois}.parquet"
URL_ZONES = "https://d37ci6vzurychx.cloudfront.net/misc/taxi_zone_lookup.csv"

# Dossier data/ à la racine du projet
DOSSIER_DONNEES = Path(__file__).resolve().parent.parent / "data"
STAGE = "@NYC_TAXI.RAW.TLC_STAGE"


def charger_cle_privee(chemin):
    """Lit la clé privée PEM et la renvoie au format attendu par le connecteur."""
    with open(chemin, "rb") as fichier:
        cle = serialization.load_pem_private_key(fichier.read(), password=None)
    return cle.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )


def connecter():
    """Ouvre une connexion avec l'utilisateur de service (rôle, warehouse et schéma par défaut)."""
    return snowflake.connector.connect(
        account=os.environ["SNOWFLAKE_ACCOUNT"],
        user=os.environ["SNOWFLAKE_USER"],
        private_key=charger_cle_privee(
            os.path.expanduser(os.environ["SNOWFLAKE_PRIVATE_KEY_PATH"])
        ),
    )


def telecharger(url, destination):
    """Télécharge le fichier par blocs, sauf s'il est déjà présent en local."""
    if destination.exists():
        print(f"Déjà téléchargé : {destination.name}")
        return
    print(f"Téléchargement : {url}")
    with requests.get(url, stream=True, timeout=120) as reponse:
        reponse.raise_for_status()
        with open(destination, "wb") as fichier:
            for bloc in reponse.iter_content(chunk_size=1024 * 1024):
                fichier.write(bloc)


def deposer_sur_stage(curseur, chemin):
    """Envoie le fichier à la racine du stage, sans compression ni écrasement."""
    curseur.execute(
        f"PUT 'file://{chemin}' {STAGE} AUTO_COMPRESS = FALSE OVERWRITE = FALSE"
    )
    for ligne in curseur.fetchall():
        print(f"PUT : {ligne[0]} -> {ligne[6]}")


def copier(curseur, table, nom_fichier, format_fichier):
    """Copie le fichier du stage dans la table RAW, colonne par colonne."""
    curseur.execute(
        f"""
        COPY INTO NYC_TAXI.RAW.{table}
        FROM {STAGE}
        FILES = ('{nom_fichier}')
        FILE_FORMAT = (FORMAT_NAME = 'NYC_TAXI.RAW.{format_fichier}')
        MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE
        INCLUDE_METADATA = (
            _source_file = METADATA$FILENAME,
            _loaded_at = METADATA$START_SCAN_TIME
        )
        ON_ERROR = ABORT_STATEMENT
        """
    )
    for ligne in curseur.fetchall():
        print(f"COPY : {ligne}")


def main():
    parser = argparse.ArgumentParser(description="Charge un fichier TLC dans NYC_TAXI.RAW")
    parser.add_argument("cible", help="un mois au format AAAA-MM, ou 'zones'")
    args = parser.parse_args()

    if args.cible == "zones":
        url, table, format_fichier = URL_ZONES, "TAXI_ZONE_LOOKUP", "FF_CSV"
    elif re.fullmatch(r"\d{4}-\d{2}", args.cible):
        url, table, format_fichier = (
            URL_TRAJETS.format(mois=args.cible), "YELLOW_TRIPDATA", "FF_PARQUET"
        )
    else:
        parser.error("cible attendue : un mois au format AAAA-MM, ou 'zones'")

    DOSSIER_DONNEES.mkdir(exist_ok=True)
    nom_fichier = url.rsplit("/", 1)[-1]
    chemin = DOSSIER_DONNEES / nom_fichier

    telecharger(url, chemin)

    connexion = connecter()
    try:
        curseur = connexion.cursor()
        deposer_sur_stage(curseur, chemin)
        copier(curseur, table, nom_fichier, format_fichier)
    finally:
        connexion.close()


if __name__ == "__main__":
    main()