-- Couche RAW : formats de fichier, stage et tables
-- Exécuté avec le rôle des outils, qui devient propriétaire
USE ROLE TRANSFORMER;
USE DATABASE NYC_TAXI;
USE SCHEMA RAW;


-- 1. Formats de fichier

CREATE FILE FORMAT IF NOT EXISTS FF_PARQUET
  TYPE = PARQUET
  USE_LOGICAL_TYPE = TRUE
  COMMENT = 'Fichiers mensuels des trajets TLC';

CREATE FILE FORMAT IF NOT EXISTS FF_CSV
  TYPE = CSV
  PARSE_HEADER = TRUE
  FIELD_OPTIONALLY_ENCLOSED_BY = '"'
  ERROR_ON_COLUMN_COUNT_MISMATCH = FALSE  -- le fichier a 4 colonnes, la table 6 (colonnes techniques)
  COMMENT = 'Liste des zones TLC';


-- 2. Stage interne : zone de dépôt avant COPY INTO

CREATE STAGE IF NOT EXISTS TLC_STAGE
  COMMENT = 'Fichiers TLC déposés par PUT, à la racine';


-- 3. Tables RAW (noms et colonnes imposés par CONTRAT_RAW.md)

CREATE TABLE IF NOT EXISTS YELLOW_TRIPDATA (
  vendorid               NUMBER,
  tpep_pickup_datetime   TIMESTAMP_NTZ,
  tpep_dropoff_datetime  TIMESTAMP_NTZ,
  passenger_count        NUMBER,
  trip_distance          FLOAT,
  ratecodeid             NUMBER,
  store_and_fwd_flag     VARCHAR,
  pulocationid           NUMBER,
  dolocationid           NUMBER,
  payment_type           NUMBER,
  fare_amount            FLOAT,
  extra                  FLOAT,
  mta_tax                FLOAT,
  tip_amount             FLOAT,
  tolls_amount           FLOAT,
  improvement_surcharge  FLOAT,
  total_amount           FLOAT,
  congestion_surcharge   FLOAT,
  airport_fee            FLOAT,
  cbd_congestion_fee     FLOAT,

  _source_file           VARCHAR,
  _loaded_at             TIMESTAMP_NTZ
);

CREATE TABLE IF NOT EXISTS TAXI_ZONE_LOOKUP (
  locationid     NUMBER,
  borough        VARCHAR,
  zone           VARCHAR,
  service_zone   VARCHAR,

  _source_file   VARCHAR,
  _loaded_at     TIMESTAMP_NTZ
);