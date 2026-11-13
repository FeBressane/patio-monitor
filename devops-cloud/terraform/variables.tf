variable "subscription_id" {
  description = "ID da assinatura Azure for Students (az account show --query id -o tsv)."
  type        = string
}

variable "regiao" {
  # A Azure permite só 1 plano F1 Linux por região na assinatura.
  # A política do Azure for Students libera: brazilsouth, chilecentral, canadacentral, eastus2, centralus.
  description = "Região do App Service F1 (mesma da GS Cloud do AgroSatélite)."
  type        = string
  default     = "brazilsouth"
}

variable "nome_app" {
  description = "Nome global único do App Service (vira <nome_app>.azurewebsites.net)."
  type        = string
  default     = "patio-monitor-gs-97688"
}
