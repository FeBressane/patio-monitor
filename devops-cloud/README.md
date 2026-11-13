# DevOps & Cloud

| Item | Onde fica |
|---|---|
| Infraestrutura como código (Azure App Service F1, custo zero) | [`terraform/`](terraform/) |
| Pipeline CI/CD DevSecOps (testes, Gitleaks, Semgrep, Trivy, deploy) | [`../.github/workflows/ci-cd.yml`](../.github/workflows/ci-cd.yml) (o GitHub exige essa pasta na raiz) |
| Containers (API multi-stage, front nginx) | [`../api/Dockerfile`](../api/Dockerfile), [`../front/Dockerfile`](../front/Dockerfile) |
| Stack local completa (front + API + Postgres + monitoramento) | [`../docker-compose.yml`](../docker-compose.yml) (na raiz para `docker compose up` funcionar direto) |
| Observabilidade: Prometheus, alertas e Grafana (4 sinais de ouro) | [`monitoramento/`](monitoramento/) |

Passo a passo do deploy e custos: seção **Deploy (DevOps)** do [README principal](../README.md#deploy-devops--custo-zero).
