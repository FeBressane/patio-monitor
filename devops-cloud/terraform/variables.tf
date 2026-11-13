variable "subscription_id" {
  description = "ID da assinatura Azure for Students (az account show --query id -o tsv)."
  type        = string
}

variable "regiao" {
  description = "Mesma região usada na GS Cloud do AgroSatélite."
  type        = string
  default     = "brazilsouth"
}

variable "nome_app" {
  description = "Nome global único do App Service (vira <nome_app>.azurewebsites.net)."
  type        = string
  default     = "patio-monitor-gs-97688"
}
