# Front estático servido por nginx sem root (porta 8080 dentro do container)
FROM nginxinc/nginx-unprivileged:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY index.html app.js style.css /usr/share/nginx/html/
USER 101
EXPOSE 8080
