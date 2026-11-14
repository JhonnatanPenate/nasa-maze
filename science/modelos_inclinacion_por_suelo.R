# =============================================================================
# modelos_inclinacion_por_suelo.R
# Planetary Explorer — modelos de inclinación (tilt) por tipo de suelo
#
# Entrada:  data/processed/gale_matriz_calibracion.xlsx|.xlsm|.csv
#           (también data_usar/01_datos_entrada/calibracion/...)
# Salida:   data/processed/modelos_por_suelo.json
# Consumidor: optimizador_rutas.py (minimiza la función objetivo de costo)
#
# Clasifica 4 regímenes con n >= 30 (rugosidad + pendiente + albedo).
# Ajusta OLS o GLS-AR1; si hay heterocedasticidad, reporta SE robustos HC3.
#
# Uso:  Rscript modelos_inclinacion_por_suelo.R [ruta_proyecto]
# =============================================================================

invisible(suppressWarnings(Sys.setlocale("LC_CTYPE", "C.UTF-8")))
suppressPackageStartupMessages({
  library(dplyr)
  library(car)       # vif
  library(lmtest)    # bptest, dwtest, coeftest
  library(sandwich)  # vcovHC
  library(nlme)      # gls + corAR1
  library(jsonlite)
})
if (!requireNamespace("readxl", quietly = TRUE)) {
  stop("Falta el paquete R 'readxl' para leer .xlsx/.xlsm. Instala con: install.packages('readxl')")
}

args <- commandArgs(trailingOnly = TRUE)
raiz <- if (length(args) >= 1) args[1] else "."
ruta_json <- file.path(raiz, "data", "processed", "modelos_por_suelo.json")

# Prioridad Excel (.xlsx/.xlsm); CSV solo si no hay Excel.
candidatos_matriz <- c(
  file.path(raiz, "data", "processed", "gale_matriz_calibracion.xlsx"),
  file.path(raiz, "data", "processed", "gale_matriz_calibracion.xlsm"),
  file.path(raiz, "data_usar", "01_datos_entrada", "calibracion", "gale_matriz_calibracion.xlsx"),
  file.path(raiz, "data_usar", "01_datos_entrada", "calibracion", "gale_matriz_calibracion.xlsm"),
  file.path(raiz, "data", "processed", "gale_matriz_calibracion.csv"),
  file.path(raiz, "data_usar", "01_datos_entrada", "calibracion", "gale_matriz_calibracion.csv")
)
ruta_matriz <- candidatos_matriz[file.exists(candidatos_matriz)][1]
if (is.na(ruta_matriz) || !nzchar(ruta_matriz)) {
  stop("No se encontró gale_matriz_calibracion (.xlsx/.xlsm/.csv). Candidatos:\n",
       paste(" -", candidatos_matriz, collapse = "\n"))
}

leer_tabla <- function(ruta) {
  ext <- tolower(tools::file_ext(ruta))
  if (ext %in% c("xlsx", "xlsm", "xls")) {
    df <- readxl::read_excel(ruta, .name_repair = "minimal")
    df <- as.data.frame(df, stringsAsFactors = FALSE)
  } else if (ext == "csv") {
    df <- read.csv(ruta, stringsAsFactors = FALSE, check.names = FALSE, sep = ",")
  } else {
    stop("Extensión no soportada: ", ruta)
  }
  names(df) <- trimws(names(df))
  if (ncol(df) < 2) {
    stop("Tabla mal formada (ncol < 2) en ", ruta,
         ". Usa el .xlsx/.xlsm con una columna por campo.")
  }
  df
}

OBSERVACIONES_MINIMAS <- 30
NIVEL_SIGNIFICANCIA   <- 0.05
VIF_MAXIMO_PERMITIDO  <- 5
PREDICTORES_CANDIDATOS <- c(
  "pendiente_grados", "rugosidad", "inercia_termica_tiu", "albedo",
  "indice_polvo", "dosis_rad_uGy_h", "temp_suelo_K_media"
)
# alias internos cortos
N_MIN <- OBSERVACIONES_MINIMAS
ALFA <- NIVEL_SIGNIFICANCIA
VIF_MAX <- VIF_MAXIMO_PERMITIDO
PREDICTORES <- PREDICTORES_CANDIDATOS

# -----------------------------------------------------------------------------
# 1. Datos y clasificación de suelo (rugosidad + pendiente + albedo)
# -----------------------------------------------------------------------------
# Reglas calibradas para Gale (corredor 90 m) con n >= 30 en cada régimen:
#   arena_dunas        : sobre duna o fracción oscura alta
#   lecho_rocoso_firme : baja rugosidad, pendiente moderada, albedo más claro
#   rocoso_fracturado  : alta rugosidad, pendiente fuerte o albedo oscuro
#   regolito_compacto  : resto del corredor
df <- leer_tabla(ruta_matriz)
nombres_esperados <- c("tilt_real_grados", "pendiente_grados", "rugosidad", "albedo")
faltan <- setdiff(nombres_esperados, names(df))
if (length(faltan)) stop("Faltan columnas en la matriz: ", paste(faltan, collapse = ", "))
df <- df %>% filter(!is.na(tilt_real_grados))
if ("sol" %in% names(df)) df <- df %>% arrange(sol)
if (!("fraccion_oscura" %in% names(df))) df$fraccion_oscura <- 0
cat(sprintf("Matriz leída desde %s: %d filas x %d columnas\n",
            ruta_matriz, nrow(df), ncol(df)))

df <- df %>% mutate(
  tipo_suelo = case_when(
    distancia_duna_m == 0 | fraccion_oscura >= 0.5 ~ "arena_dunas",
    rugosidad <= 0.60 & pendiente_grados <= 7.0 & albedo >= 0.2294 ~ "lecho_rocoso_firme",
    rugosidad >= 1.10 | pendiente_grados >= 8.0 | albedo < 0.2291 ~ "rocoso_fracturado",
    TRUE ~ "regolito_compacto"
  ),
  riesgo_alto = nivel_riesgo_real == "alto"
)
SUELOS <- c("arena_dunas", "lecho_rocoso_firme", "rocoso_fracturado", "regolito_compacto")

cat("\n=== Resumen por tipo de suelo ===\n")
resumen <- df %>%
  group_by(tipo_suelo) %>%
  summarise(
    n_obs             = n(),
    tilt_media        = round(mean(tilt_real_grados), 2),
    tilt_sd           = round(sd(tilt_real_grados), 2),
    vel_media_m_sol   = round(mean(velocidad_efectiva_m_sol, na.rm = TRUE), 1),
    vel_mediana_m_sol = round(median(velocidad_efectiva_m_sol, na.rm = TRUE), 1),
    rad_media_uGy_h   = round(mean(dosis_rad_uGy_h, na.rm = TRUE), 2),
    pct_riesgo_alto   = round(100 * mean(riesgo_alto, na.rm = TRUE), 1),
    .groups = "drop"
  ) %>%
  arrange(desc(tilt_media))
print(as.data.frame(resumen))
faltantes <- setdiff(SUELOS, resumen$tipo_suelo)
if (length(faltantes)) cat("Suelos sin observaciones:", paste(faltantes, collapse = ", "), "\n")
bajo_n <- resumen %>% filter(n_obs < N_MIN)
if (nrow(bajo_n)) cat("AVISO: suelos con n <", N_MIN, ":", paste(bajo_n$tipo_suelo, collapse = ", "), "\n")

# -----------------------------------------------------------------------------
# 2. Utilidades
# -----------------------------------------------------------------------------
predictores_utiles <- function(d) {
  Filter(function(v) v %in% names(d) && sum(!is.na(d[[v]])) >= N_MIN &&
           length(unique(na.omit(d[[v]]))) > 2, PREDICTORES)
}

podar_vif <- function(d, preds) {
  quitados <- character(0)
  repeat {
    if (length(preds) < 2) break
    m <- lm(reformulate(preds, "tilt_real_grados"), data = d)
    v <- tryCatch(car::vif(m), error = function(e) NULL)
    if (is.null(v)) {
      al <- names(which(is.na(coef(m))))
      if (!length(al)) break
      preds <- setdiff(preds, al); quitados <- c(quitados, al); next
    }
    if (max(v) < VIF_MAX) break
    peor <- names(which.max(v))
    preds <- setdiff(preds, peor); quitados <- c(quitados, peor)
  }
  list(preds = preds, quitados = quitados)
}

r2_ajustado <- function(y, yhat, p) {
  n <- length(y)
  r2 <- 1 - sum((y - yhat)^2) / sum((y - mean(y))^2)
  1 - (1 - r2) * (n - 1) / (n - p - 1)
}

ajustar_suelo <- function(d, etiqueta) {
  preds0 <- predictores_utiles(d)
  d <- d[complete.cases(d[, c("tilt_real_grados", preds0)]), ]
  n <- nrow(d)
  if (n < N_MIN || length(preds0) == 0) {
    return(list(suelo = etiqueta, n = n, estado = "insuficiente",
                nota = sprintf("n=%d < %d o sin predictores con variación; el motor usa el modelo global", n, N_MIN)))
  }
  pv <- podar_vif(d, preds0)
  preds <- pv$preds
  f <- reformulate(preds, "tilt_real_grados")
  m_lm <- lm(f, data = d)
  res  <- residuals(m_lm)

  sw <- if (n <= 5000) shapiro.test(res) else list(statistic = NA, p.value = NA)
  bp <- bptest(m_lm)
  dw <- dwtest(m_lm)
  vifs <- if (length(preds) >= 2) car::vif(m_lm) else setNames(1, preds)

  metodo <- "lm"; rho <- NA_real_; modelo <- m_lm
  coefs <- coef(m_lm); se <- sqrt(diag(vcov(m_lm)))
  yhat <- fitted(m_lm)
  se_robusto <- NULL
  p_robusto <- NULL
  usa_hc <- FALSE

  # Errores estándar robustos HC (heterocedasticidad) siempre se calculan para lm;
  # si BP falla, se adoptan como se/p oficiales del reporte.
  if (TRUE) {
    Vhc <- tryCatch(sandwich::vcovHC(m_lm, type = "HC3"), error = function(e) NULL)
    if (!is.null(Vhc)) {
      ct <- lmtest::coeftest(m_lm, vcov. = Vhc)
      se_robusto <- setNames(as.numeric(ct[, "Std. Error"]), rownames(ct))
      p_robusto  <- setNames(as.numeric(ct[, "Pr(>|t|)"]), rownames(ct))
      if (isTRUE(bp$p.value < ALFA)) {
        se <- se_robusto
        pvals_lm <- p_robusto
        usa_hc <- TRUE
      }
    }
  }

  if (dw$p.value < ALFA) {
    d$orden <- seq_len(n)
    m_gls <- tryCatch(gls(f, data = d, correlation = corAR1(form = ~ orden), method = "REML"),
                      error = function(e) NULL)
    if (!is.null(m_gls)) {
      metodo <- "gls_AR1"; modelo <- m_gls
      coefs <- coef(m_gls); se <- sqrt(diag(vcov(m_gls)))
      rho <- as.numeric(coef(m_gls$modelStruct$corStruct, unconstrained = FALSE))
      yhat <- as.numeric(fitted(m_gls))
      usa_hc <- FALSE  # GLS AR(1) ya corrige dependencia; HC queda como referencia lm
    }
  }
  r2a <- r2_ajustado(d$tilt_real_grados, yhat, length(preds))
  sigma <- sqrt(sum((d$tilt_real_grados - yhat)^2) / (n - length(preds) - 1))
  if (metodo == "lm" && usa_hc && !is.null(p_robusto)) {
    pvals <- p_robusto[names(coefs)]
  } else {
    pvals <- 2 * pt(-abs(coefs / se), df = n - length(preds) - 1)
  }

  list(
    suelo = etiqueta, n = n, estado = "ajustado", metodo = metodo,
    formula = paste(deparse(f), collapse = ""),
    predictores = preds,
    predictores_descartados_vif = pv$quitados,
    coeficientes = as.list(coefs),
    error_estandar = as.list(se),
    error_estandar_robusto_HC3 = if (is.null(se_robusto)) NULL else as.list(se_robusto),
    p_valores = as.list(pvals),
    p_valores_robustos_HC3 = if (is.null(p_robusto)) NULL else as.list(p_robusto),
    se_tipo = if (usa_hc) "HC3" else if (metodo == "gls_AR1") "GLS_AR1" else "OLS",
    r2_ajustado = round(r2a, 4),
    sigma_residual = round(sigma, 3),
    rho_ar1 = if (is.na(rho)) NULL else round(rho, 3),
    rango_predictores = lapply(setNames(preds, preds), function(v) round(range(d[[v]]), 4)),
    velocidad_mediana_m_sol = round(median(d$velocidad_efectiva_m_sol, na.rm = TRUE), 2),
    supuestos = list(
      shapiro_W = unname(round(sw$statistic, 4)), shapiro_p = signif(sw$p.value, 4),
      normalidad_ok = isTRUE(sw$p.value >= ALFA),
      breusch_pagan = unname(round(bp$statistic, 3)), bp_p = signif(bp$p.value, 4),
      homocedasticidad_ok = bp$p.value >= ALFA,
      durbin_watson = unname(round(dw$statistic, 3)), dw_p = signif(dw$p.value, 4),
      independencia_ok = dw$p.value >= ALFA,
      vif_max = round(max(vifs), 2),
      se_robustos_aplicados = usa_hc
    )
  )
}

# -----------------------------------------------------------------------------
# 3. Ajuste por suelo + modelo global de respaldo
# -----------------------------------------------------------------------------
modelos <- lapply(SUELOS, function(s) ajustar_suelo(df[df$tipo_suelo == s, ], s))
names(modelos) <- SUELOS
global <- ajustar_suelo(df, "global")

cat("\n=== Supuestos y R² por suelo ===\n")
tabla <- do.call(rbind, lapply(c(modelos, list(global = global)), function(m) {
  if (m$estado != "ajustado")
    return(data.frame(suelo = m$suelo, n = m$n, metodo = "-", R2_aj = NA, sigma = NA,
                      shapiro_p = NA, bp_p = NA, DW = NA, dw_p = NA, VIF_max = NA, rho = NA,
                      se_tipo = NA))
  s <- m$supuestos
  data.frame(suelo = m$suelo, n = m$n, metodo = m$metodo, R2_aj = m$r2_ajustado,
             sigma = m$sigma_residual, shapiro_p = s$shapiro_p, bp_p = s$bp_p,
             DW = s$durbin_watson, dw_p = s$dw_p, VIF_max = s$vif_max,
             rho = ifelse(is.null(m$rho_ar1), NA, m$rho_ar1),
             se_tipo = m$se_tipo)
}))
rownames(tabla) <- NULL
print(tabla)

for (m in c(modelos, list(global = global))) if (m$estado == "ajustado") {
  cat(sprintf("\n[%s] %s  (R²aj=%.3f, SE=%s)\n", m$suelo, m$metodo, m$r2_ajustado, m$se_tipo))
  cf <- unlist(m$coeficientes); pv <- unlist(m$p_valores)
  print(data.frame(coef = round(cf, 5), p = signif(pv, 3)))
  if (length(m$predictores_descartados_vif))
    cat("  descartados por VIF/alias:", paste(m$predictores_descartados_vif, collapse = ", "), "\n")
}

ranking <- tabla %>% filter(!is.na(R2_aj), suelo != "global") %>% arrange(desc(R2_aj)) %>% pull(suelo)

salida <- list(
  generado = format(Sys.time(), "%Y-%m-%dT%H:%M:%S"),
  fuente = ruta_matriz,
  variable_respuesta = "tilt_real_grados",
  reglas_suelo = list(
    arena_dunas = "distancia_duna_m == 0 | fraccion_oscura >= 0.5",
    lecho_rocoso_firme = "rugosidad <= 0.60 & pendiente_grados <= 7.0 & albedo >= 0.2294",
    rocoso_fracturado = "rugosidad >= 1.10 | pendiente_grados >= 8.0 | albedo < 0.2291",
    regolito_compacto = "resto"
  ),
  parametros = list(n_min = N_MIN, alfa = ALFA, vif_max = VIF_MAX, se_robusto = "HC3"),
  resumen = resumen,
  modelos = modelos,
  modelo_global = global,
  ranking_r2 = ranking
)
dir.create(dirname(ruta_json), showWarnings = FALSE, recursive = TRUE)
write_json(salida, ruta_json, auto_unbox = TRUE, pretty = TRUE, digits = NA, null = "null", na = "null")
cat("\nExportado:", ruta_json, "\n")
