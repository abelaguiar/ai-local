# AI Local

Stack local criada para esta maquina.

## Componentes

- `Ollama` rodando como servico do sistema em `127.0.0.1:11434`
- `Open WebUI` rodando em Docker com rede host em `127.0.0.1:38127`
- Imagem customizada do Open WebUI com `git`, `php`, `composer`, `node` e `npm` para scaffolding controlado em `/workspace`
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

Registrar bases de Conhecimento locais depois de recriar os dados da WebUI:

```bash
docker exec ai-local-open-webui python /host/projects/personal/ai-local/scripts/register-openwebui-knowledge.py
```

## Conhecimento local

A base `Padroes Laravel API - api-e-alece` fica na aba Conhecimento do Open WebUI e usa como fonte:

- `knowledge/api-e-alece-padroes-projetos-futuros.md`

Ela resume arquitetura, documentacao, testes, comandos e workflow do projeto `/home/abel-aguiar/projects/work/api-e-alece` para orientar projetos Laravel API futuros.

## Tools locais

A stack monta:

- `/home/abel-aguiar/projects` no container como `/host/projects:ro`
- `/home/abel-aguiar/projects/ai-generated` no container como `/workspace:rw`

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

A tool `Local Workspace Write Tools` tambem fica ativa por padrao para o usuario admin e expoe:

- `list_workspace`
- `read_workspace_file`
- `create_directory`
- `write_file`
- `append_file`
- `replace_in_file`
- `move_path`
- `delete_path`
- `run_workspace_command`

Essas ferramentas so podem escrever dentro de `/workspace`, que corresponde a `/home/abel-aguiar/projects/ai-generated` na maquina. Remocoes sao feitas movendo para `/workspace/.ai-local-trash`.

O `run_workspace_command` aceita apenas comandos com whitelist: `git_status`, `git_init`, `composer_create_laravel`, `composer_install`, `composer_update`, `npm_create_vite`, `npm_install`, `npm_run_build`, `npm_test` e `php_artisan`.

Exemplos de uso esperado pela IA:

- criar Laravel: `run_workspace_command(command="composer_create_laravel", args=["meu-app"])`
- criar Vite: `run_workspace_command(command="npm_create_vite", args=["meu-front", "--", "--template", "react"])`
- instalar dependencias: `run_workspace_command(command="npm_install", cwd="meu-front")`
- gerar artefatos Laravel: `run_workspace_command(command="php_artisan", cwd="meu-app", args=["make:controller", "Api/V1/ContaController"])`

## Pendencia de privilegio administrativo

Para `http://local.chatbot` funcionar de verdade no navegador, ainda falta:

```bash
echo '127.0.0.1 local.chatbot' | sudo tee -a /etc/hosts
sudo a2enmod proxy proxy_http headers
sudo cp /home/abel-aguiar/projects/personal/ai-local/apache/local.chatbot.conf /etc/apache2/sites-available/local.chatbot.conf
sudo a2ensite local.chatbot.conf
sudo systemctl reload apache2
```
