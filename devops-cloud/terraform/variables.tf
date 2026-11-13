variable "subscription_id" {
  description = "ID da assinatura Azure for Students (az account show --query id -o tsv)."
  type        = string
}

variable "regiao" {
  # A Azure permite só 1 plano F1 Linux por região, e o de brazilsouth já é da GS AgroSatélite.
  # A política do Azure for Students libera: brazilsouth, chilecentral, canadacentral, eastus2, centralus.
  description = "Região do App Service F1. eastus2 porque o F1 Linux de brazilsouth já está em uso."
  type        = string
  default     = "eastus2"
}

variable "nome_app" {
  description = "Nome global único do App Service (vira <nome_app>.azurewebsites.net)."
  type        = string
  default     = "patio-monitor-gs-97688"
}
