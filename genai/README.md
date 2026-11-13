# Generative AI — Gabriel Teixeira (RM 551570)

Pasta do assistente de IA (LLM local + RAG sobre o POP do pátio).

**O que vai aqui:** código do serviço do assistente, base de documentos do RAG (POP simulado), prompts, avaliação e o PDF da disciplina.

**Integração com a API:** a API repassa `POST /assistente` para o serviço configurado em `ASSISTENTE_URL` (secret do GitHub).
Formato de entrada e saída em [`docs/contrato-api.md`](../docs/contrato-api.md#assistente-de-genai-post-assistente).
Sem o serviço no ar, a API responde com regras do POP (`"modo": "fallback_regras"`).

> Pendente: código do Gabriel.
