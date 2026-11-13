// Front de demonstração: lê /posicoes e /alertas a cada 3 s e pergunta ao /assistente.
const API = new URLSearchParams(location.search).get("api") || "/api";
const $ = (id) => document.getElementById(id);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => "&#" + c.charCodeAt(0) + ";");

async function api(caminho, opts) {
  const r = await fetch(API + caminho, { headers: { "Content-Type": "application/json" }, ...opts });
  if (!r.ok) throw new Error(r.status + " em " + caminho);
  return r.json();
}

async function atualizar() {
  try {
    const [posicoes, alertas] = await Promise.all([api("/posicoes"), api("/alertas")]);
    $("alertas").innerHTML = alertas.length
      ? alertas.map((a) => `<li><b>${esc(a.status)}</b> · ${esc(a.prefixo_previsto || a.prefixo_registrado)} · ${esc(a.detalhe)}</li>`).join("")
      : "<li>Nenhuma pendência.</li>";
    $("veiculos").innerHTML = posicoes.map((p) => `<tr class="${p.status_conciliacao ? "alerta" : ""}">
      <td>${esc(p.prefixo)}</td><td>${esc(p.linha)}</td><td>${esc(p.local)}</td><td>${esc(p.estado)}</td>
      <td>${p.minutos_no_patio ?? "–"}</td><td>${esc(p.status_conciliacao || "ok")}</td>
      <td>${p.status_conciliacao ? `<button data-prefixo="${esc(p.prefixo)}" data-status="${esc(p.status_conciliacao)}">Por quê?</button>` : ""}</td></tr>`).join("");
    $("conexao").textContent = "atualizado " + new Date().toLocaleTimeString("pt-BR");
  } catch (e) {
    $("conexao").textContent = "sem conexão com a API (" + e.message + ")";
  }
}

$("veiculos").addEventListener("click", async (e) => {
  const b = e.target.closest("button");
  if (!b) return;
  $("resposta").hidden = false;
  $("texto-resposta").textContent = "Consultando…";
  try {
    const r = await api("/assistente", { method: "POST", body: JSON.stringify({
      pergunta: `Por que o ônibus ${b.dataset.prefixo} está com ${b.dataset.status}? O que faço?`, prefixo: b.dataset.prefixo }) });
    $("texto-resposta").innerHTML = `<p><b>${esc(r.acao)}</b></p><p>${esc(r.justificativa)}</p>
      <p class="meta">Fonte: ${esc(r.fonte || "–")} · confiança ${Math.round(r.confianca * 100)}% · ${esc(r.modo)}</p>`;
  } catch (err) {
    $("texto-resposta").textContent = "Assistente indisponível (" + err.message + ").";
  }
});

atualizar();
setInterval(atualizar, 3000);
