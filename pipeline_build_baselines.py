# pipeline_build_baselines.py
# Pipeline para generar baselines históricos

import pandas as pd
import sys
import logging
import auxiliary_functions
import config

# Configurar logging
logging.basicConfig(
    level=config.LOG_LEVEL,
    format=config.LOG_FORMAT
)

def main():
    """Pipeline completo de generación de baselines."""
    
    logging.info("="*60)
    logging.info("PIPELINE: Generación de Baselines Históricos")
    if config.ENABLE_PRICE_BUCKETS:
        logging.info("MODO: CON PRICE BUCKETS")
    else:
        logging.info("MODO: SIN PRICE BUCKETS (tradicional)")
    logging.info("="*60)
    
    # 1. Cargar datos históricos
    logging.info("[1/11] Cargando datos históricos...")
    df_raw = auxiliary_functions.load_all_historicals()
    
    # 2. Eliminar duplicados
    logging.info("[2/11] Eliminando duplicados...")
    initial_count = len(df_raw)
    df_raw = df_raw.drop_duplicates()
    logging.debug(f"Duplicados eliminados: {initial_count - len(df_raw):,}")
    
    # 2.5 Validar datos (filtrar erróneos)
    logging.info("[2.5/11] Validando datos...")
    df_valid = auxiliary_functions.validate_data(df_raw)
    
    # 3. Estandarizar precios
    logging.info("[3/11] Estandarizando precios...")
    df_std = auxiliary_functions.standardize_prices(df_valid)
    
    # 4. Expandir fechas
    logging.info("[4/11] Expandiendo fechas...")
    df_expanded = auxiliary_functions.expand_dates_dataframe(df_std)
    
    # 5. Agregar features temporales
    logging.info("[5/11] Generando features temporales...")
    df_features = auxiliary_functions.add_temporal_features(df_expanded)
    
    # 6. Mapear destinaciones
    logging.info("[6/11] Mapeando destinaciones...")
    mapping_df = auxiliary_functions.load_destination_mapping()
    df_mapped = auxiliary_functions.apply_destination_mapping(df_features, mapping_df)
    
    # 7. NUEVO: Calcular distribución de precios por destino
    if config.ENABLE_PRICE_BUCKETS:
        logging.info("[7/11] Calculando distribución de precios por destino...")
        price_dist = auxiliary_functions.calculate_price_distribution_by_destination(df_mapped)
        
        # Guardar distribución
        price_dist.to_csv(config.PRICE_DISTRIBUTION_FILE, index=False)
        logging.info(f"✓ Distribución guardada en: {config.PRICE_DISTRIBUTION_FILE}")
        
        # 8. NUEVO: Clasificar en buckets
        logging.info("[8/11] Clasificando observaciones en buckets de precio...")
        df_bucketed = auxiliary_functions.classify_observations_into_buckets(df_mapped, price_dist)
    else:
        logging.info("[7-8/11] Saltando distribución y clasificación de buckets (deshabilitado)")
        df_bucketed = df_mapped
        price_dist = None
    
    # 9. Calcular baselines (con o sin buckets según configuración)
    logging.info("[9/11] Calculando baselines...")
    baselines = auxiliary_functions.calculate_baselines(df_bucketed)
    
    # 10. Validar baselines
    logging.info("[10/11] Aplicando validaciones de robustez...")
    baselines_validated = auxiliary_functions.apply_robustness_checks(baselines)
    
    # 11. Guardar resultados
    logging.info("[11/11] Guardando resultados...")
    auxiliary_functions.save_baselines(baselines_validated)
    
    # Generar y guardar bucket summary
    if config.ENABLE_PRICE_BUCKETS:
        bucket_summary = auxiliary_functions.generate_bucket_summary(baselines_validated)
        if bucket_summary is not None:
            bucket_summary.to_csv(config.BUCKET_SUMMARY_FILE, index=False)
            logging.info(f"✓ Bucket summary guardado en: {config.BUCKET_SUMMARY_FILE}")
    
    # Estadísticas finales
    logging.info("="*60)
    logging.info("✓ PIPELINE COMPLETADO")
    logging.info("="*60)
    logging.info(f"Estadísticas finales:")
    logging.info(f"  Contextos totales: {len(baselines_validated):,}")
    logging.info(f"  Destinos únicos: {baselines_validated['destination_final'].nunique():,}")
    logging.info(f"  Meses cubiertos: {sorted(baselines_validated['month'].unique())}")
    
    if config.ENABLE_PRICE_BUCKETS and 'price_bucket' in baselines_validated.columns:
        logging.info(f"  Buckets implementados: {sorted(baselines_validated['price_bucket'].unique())}")
        for bucket in ['low', 'medium', 'high']:
            count = len(baselines_validated[baselines_validated['price_bucket'] == bucket])
            pct = (count / len(baselines_validated) * 100) if len(baselines_validated) > 0 else 0
            logging.info(f"    {bucket:8s}: {count:5,} contextos ({pct:5.1f}%)")
    
    logging.info(f"  Alta confianza: {(~baselines_validated['low_confidence']).sum():,} ({(~baselines_validated['low_confidence']).sum()/len(baselines_validated)*100:.1f}%)")
    logging.info(f"\nArchivos generados:")
    logging.info(f"  - {config.BASELINES_FILE}")
    if config.ENABLE_PRICE_BUCKETS:
        logging.info(f"  - {config.PRICE_DISTRIBUTION_FILE}")
        logging.info(f"  - {config.BUCKET_SUMMARY_FILE}")
    logging.info("="*60)
    
    return baselines_validated


if __name__ == "__main__":
    try:
        baselines = main()
        sys.exit(0)
    except Exception as e:
        logging.error(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
