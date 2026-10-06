"""Teste la connexion de l'utilisateur de service à Snowflake par paire de clés."""
import os

import snowflake.connector
from cryptography.hazmat.primitives import serialization


def charger_cle_privee(chemin):
    """Lit la clé privée PEM et la renvoie au format attendu par le connecteur."""
    with open(chemin, "rb") as fichier:
        cle = serialization.load_pem_private_key(fichier.read(), password=None)
    return cle.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )


connexion = snowflake.connector.connect(
    account=os.environ["SNOWFLAKE_ACCOUNT"],
    user=os.environ["SNOWFLAKE_USER"],
    private_key=charger_cle_privee(
        os.path.expanduser(os.environ["SNOWFLAKE_PRIVATE_KEY_PATH"])
    ),
)

try:
    curseur = connexion.cursor()
    curseur.execute(
        "SELECT CURRENT_USER(), CURRENT_ROLE(), CURRENT_WAREHOUSE(), "
        "CURRENT_DATABASE(), CURRENT_SCHEMA()"
    )
    print(curseur.fetchone())
finally:
    connexion.close()