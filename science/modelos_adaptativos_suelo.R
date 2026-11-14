# Compatibilidad: el script canónico es modelos_inclinacion_por_suelo.R
args_cli <- commandArgs(trailingOnly = FALSE)
file_arg <- grep("^--file=", args_cli, value = TRUE)
script_dir <- if (length(file_arg)) dirname(sub("^--file=", "", file_arg[1])) else "."
source(file.path(script_dir, "modelos_inclinacion_por_suelo.R"))
