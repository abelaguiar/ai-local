# AI Local

Stack local criada para esta maquina.

## Componentes

- `Ollama` rodando como servico de usuario em `127.0.0.1:11434`
- `Open WebUI` rodando em Docker em `0.0.0.0:38127`
- vhost Apache planejado para `local.chatbot`

## Modelos de codigo integrados

- `qwen2.5-coder:14b` como modelo padrao do stack
- `deepseek-coder-v2:16b` como segunda opcao para codigo
- `qwen2.5-coder:7b` mantido como alternativa mais leve

## Modelos gerais integrados

- `gemma4:e4b` como alternativa nova para uso geral, raciocinio e multimodal
- `gemma4:e2b` como alternativa Gemma 4 mais leve
- `qwen3.5:9b`, `gemma3:12b`, `gemma3:4b` e `qwen3:8b` mantidos para comparacao

O Open WebUI lista esses modelos automaticamente porque consulta o Ollama local em `127.0.0.1:11434`.

## Comandos

Criar o arquivo de ambiente local na primeira instalacao:

```bash
cp /home/abel-aguiar/projects/works/ai-local/.env.example /home/abel-aguiar/projects/works/ai-local/.env
```

Iniciar stack:

```bash
/home/abel-aguiar/projects/works/ai-local/start-stack.sh
```

Baixar ou trocar modelo:

```bash
/home/abel-aguiar/projects/works/ai-local/pull-model.sh
/home/abel-aguiar/projects/works/ai-local/pull-model.sh gemma4:e4b
/home/abel-aguiar/projects/works/ai-local/pull-model.sh gemma4:e2b
/home/abel-aguiar/projects/works/ai-local/pull-model.sh gemma3:4b
/home/abel-aguiar/projects/works/ai-local/pull-model.sh qwen2.5-coder:14b
/home/abel-aguiar/projects/works/ai-local/pull-model.sh deepseek-coder-v2:16b
```

## Pendencia de privilegio administrativo

Para `http://local.chatbot` funcionar de verdade no navegador, ainda falta:

```bash
echo '127.0.0.1 local.chatbot' | sudo tee -a /etc/hosts
sudo a2enmod proxy proxy_http headers
sudo cp /home/abel-aguiar/projects/works/ai-local/apache/local.chatbot.conf /etc/apache2/sites-available/local.chatbot.conf
sudo a2ensite local.chatbot.conf
sudo systemctl reload apache2
```
