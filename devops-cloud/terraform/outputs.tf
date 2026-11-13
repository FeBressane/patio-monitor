output "url_mvp" {
  value = "https://${azurerm_linux_web_app.patio.default_hostname}"
}

output "nome_app" {
  value = azurerm_linux_web_app.patio.name
}

output "resource_group" {
  value = azurerm_resource_group.patio.name
}
