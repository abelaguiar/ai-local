# AI Local

Stack local criada para esta maquina.

## Componentes

- `Ollama` rodando como servico do sistema em `127.0.0.1:11434`
- `Open WebUI` rodando em Docker com rede host em `127.0.0.1:38127`
- vhost Apache planejado para `local.chatbot`

## Modelos integrados

- `qwen2.5-coder:7b` como modelo padrao do stack para uso diario
- `deepseek-coder-v2:16b` como opcao mais forte para refactor, debug e comparacao
- `codellama:latest` como fallback leve

O Open WebUI lista esses modelos automaticamente porque consulta o Ollama local em `127.0.0.1:11434`.

## Comandos

Criar o arquivo de ambiente local na primeira instalacao:

```bash
cp /home/abel-aguiar/projects/personal/ai-local/.env.example /home/abel-aguiar/projects/personal/ai-local/.env
```

Iniciar stack:

```bash
/home/abel-aguiar/projects/personal/ai-local/start-stack.sh
```

Baixar ou trocar modelo:

```bash
/home/abel-aguiar/projects/personal/ai-local/pull-model.sh
/home/abel-aguiar/projects/personal/ai-local/pull-model.sh deepseek-coder-v2:16b
/home/abel-aguiar/projects/personal/ai-local/pull-model.sh codellama:latest
/home/abel-aguiar/projects/personal/ai-local/pull-model.sh qwen2.5-coder:7b
```

Registrar Skills/Tools locais depois de recriar os dados da WebUI:

```bash
docker exec ai-local-open-webui python /host/projects/personal/ai-local/scripts/register-openwebui-tools.py
```

## Tools locais

A stack monta `/home/abel-aguiar/projects` no container como `/host/projects:ro`.

A tool `Local Project Readonly Tools` fica ativa por padrao para o usuario admin e expoe:

- `list_projects`
- `project_search`
- `read_project_file`
- `git_status_diff`
- `composer_info`
- `package_info`
- `laravel_routes`
- `migration_schema_reader`
- `php_lint`

Essas ferramentas sao somente leitura. O `php_lint` so executa se PHP existir dentro do container da WebUI; na imagem atual ele informa essa limitacao.

## Pendencia de privilegio administrativo

Para `http://local.chatbot` funcionar de verdade no navegador, ainda falta:

```bash
echo '127.0.0.1 local.chatbot' | sudo tee -a /etc/hosts
sudo a2enmod proxy proxy_http headers
sudo cp /home/abel-aguiar/projects/personal/ai-local/apache/local.chatbot.conf /etc/apache2/sites-available/local.chatbot.conf
sudo a2ensite local.chatbot.conf
sudo systemctl reload apache2
```
