# Front estático servido por nginx sem root (porta 8080 dentro do container)
FROM nginxinc/nginx-unprivileged:1.30-alpine
# Aplica as correções de segurança do Alpine (o Trivy do pipeline reprova CVEs HIGH/CRITICAL com correção)
USER root
RUN apk upgrade --no-cache
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY index.html app.js style.css /usr/share/nginx/html/
USER 101
EXPOSE 8080
