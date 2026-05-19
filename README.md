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

- `apply_workspace_prompt`
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

Use `apply_workspace_prompt` para pedidos gerais, por exemplo: mudar cores, melhorar frontend, corrigir comportamento, aplicar padroes ou ajustar um projeto a partir de um prompt. Essa tool faz o ciclo completo em uma unica chamada: seleciona arquivos relevantes, envia contexto ao Ollama local e grava os arquivos retornados pelo modelo.

O `run_workspace_command` aceita apenas comandos com whitelist: `git_status`, `git_init`, `composer_create_laravel`, `composer_install`, `composer_update`, `npm_create_vite`, `npm_install`, `npm_run_build`, `npm_test` e `php_artisan`.

Exemplos de uso esperado pela IA:

- criar Laravel: `run_workspace_command(command="composer_create_laravel", args=["meu-app"])`
- criar Vite: `run_workspace_command(command="npm_create_vite", args=["meu-front", "--", "--template", "react"])`
- instalar dependencias: `run_workspace_command(command="npm_install", cwd="meu-front")`
- gerar artefatos Laravel: `run_workspace_command(command="php_artisan", cwd="meu-app", args=["make:controller", "Api/V1/ContaController"])`

A tool `Internet Search Tools` fica ativa por padrao para permitir pesquisa web quando o usuario pedir informacoes atuais. Ela expoe:

- `web_search`

Essa tool usa DuckDuckGo HTML e retorna titulo, URL e resumo dos resultados. Use para noticias, documentacao recente, releases, precos, comparacoes atuais ou qualquer informacao que possa ter mudado.

## Preset recomendado

O script `scripts/register-openwebui-tools.py` tambem registra o modelo customizado `AI Local Workspace (Qwen Coder)`, baseado em `qwen2.5-coder:1.5b`.

Use esse preset quando quiser que a IA altere projetos em `/home/abel-aguiar/projects/ai-generated`. Ele ja vem com as tools locais anexadas e com instrucao para mapear:

- `/home/abel-aguiar/projects/ai-generated/...`
- `/workspace/...`
- caminhos relativos como `abel-lorem/...`

O mesmo script tambem grava esse preset como modelo padrao da WebUI e aplica as tools locais como metadata padrao dos modelos. Assim, mesmo se um modelo base como `qwen2.5-coder:7b` for aberto diretamente, a conversa nova tende a carregar as tools locais.

Depois de atualizar tools/modelos, reinicie o container, recarregue a pagina do Open WebUI e abra uma conversa nova. Se uma conversa antiga continuar dizendo que nao acessa arquivos, descarte essa conversa e use o preset `AI Local Workspace (Qwen Coder)`.

Tambem fica disponivel o prompt atalho `/workspace-ajustar`, que serve como base para pedir ajustes em projetos dentro de `/home/abel-aguiar/projects/ai-generated`.

## Pendencia de privilegio administrativo

Para `http://local.chatbot` funcionar de verdade no navegador, ainda falta:

```bash
echo '127.0.0.1 local.chatbot' | sudo tee -a /etc/hosts
sudo a2enmod proxy proxy_http headers
sudo cp /home/abel-aguiar/projects/personal/ai-local/apache/local.chatbot.conf /etc/apache2/sites-available/local.chatbot.conf
sudo a2ensite local.chatbot.conf
sudo systemctl reload apache2
```
