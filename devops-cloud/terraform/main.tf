# Pátio Monitor na Azure com CUSTO ZERO:
#   App Service Plan F1 (Free) + Linux Web App Python (front e API no mesmo app, SQLite em /home).
# Nada aqui cobra da assinatura. Não adicione recursos pagos (VM, IP público, Postgres gerenciado,
# alert rules do Azure Monitor) sem combinar com a equipe.
terraform {
  required_version = ">= 1.6"
  required_providers {
    azurerm = { source = "hashicorp/azurerm", version = "~> 4.14" }
  }
  # State LOCAL (terraform.tfstate), bloqueado pelo .gitignore: fica fora do repositório e não custa nada.
  # Um backend remoto num Storage Account também funcionaria, mas consome crédito (centavos por mês).
}

provider "azurerm" {
  features {}
  subscription_id = var.subscription_id
}

locals {
  tags = { projeto = "patio-monitor", disciplina = "devops-gs-2026", custo = "zero-f1" }
}

resource "azurerm_resource_group" "patio" {
  name     = "rg-patio-monitor"
  location = var.regiao
  tags     = local.tags
}

resource "azurerm_service_plan" "patio" {
  name                = "asp-patio-monitor"
  resource_group_name = azurerm_resource_group.patio.name
  location            = azurerm_resource_group.patio.location
  os_type             = "Linux"
  sku_name            = "F1" # Free: US$ 0, 60 min de CPU/dia, 1 GB de RAM, sem Always On
  tags                = local.tags
}

resource "azurerm_linux_web_app" "patio" {
  name                = var.nome_app # vira https://<nome_app>.azurewebsites.net
  resource_group_name = azurerm_resource_group.patio.name
  location            = azurerm_service_plan.patio.location
  service_plan_id     = azurerm_service_plan.patio.id
  https_only          = true
  tags                = local.tags

  # Porta de administração (Kudu/SCM e FTP) sem usuário e senha: só entra quem tem login Entra ID
  # com permissão (RBAC), como o service principal do GitHub Actions. FTP fica desligado.
  ftp_publish_basic_authentication_enabled       = false
  webdeploy_publish_basic_authentication_enabled = false

  site_config {
    always_on                         = false # obrigatório no F1
    ftps_state                        = "Disabled"
    minimum_tls_version               = "1.2"
    http2_enabled                     = true
    health_check_path                 = "/health"
    health_check_eviction_time_in_min = 10
    app_command_line                  = "python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers"
    application_stack {
      python_version = "3.12"
    }
  }

  # Só configurações NÃO secretas. INGEST_API_KEY, METRICS_TOKEN e ASSISTENTE_URL são gravadas pelo
  # pipeline a partir do GitHub Secrets, para não passarem pelo state do Terraform.
  app_settings = {
    SCM_DO_BUILD_DURING_DEPLOYMENT = "true"
    WEBSITES_PORT                  = "8000"                          # porta do uvicorn no app_command_line
    DATABASE_URL                   = "sqlite:////home/data/patio.db" # /home é persistente no App Service
    DEMO                           = "true"
    OURO_CSV                       = "/home/site/wwwroot/data/ouro/fato_permanencia.csv"
  }

  logs {
    http_logs {
      file_system {
        retention_in_days = 3
        retention_in_mb   = 35
      }
    }
  }

  lifecycle {
    ignore_changes = [
      app_settings["INGEST_API_KEY"],
      app_settings["METRICS_TOKEN"],
      app_settings["ASSISTENTE_URL"],
    ]
  }
}
