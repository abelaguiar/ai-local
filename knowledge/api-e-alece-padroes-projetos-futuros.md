# Padroes Laravel API baseados no api-e-alece

Use este conhecimento como referencia para criar, revisar e evoluir projetos Laravel API futuros seguindo o estilo usado em `/home/abel-aguiar/projects/work/api-e-alece`.

## Stack padrao

- PHP 8.2+.
- Laravel 12+.
- PostgreSQL 15+.
- Redis para cache e filas.
- Laravel Sanctum para autenticacao token-based.
- Laravel Sail para ambiente Docker local.
- PHPUnit para testes.
- Laravel Pint para formatacao.
- L5-Swagger para documentacao OpenAPI.

## Arquitetura

O fluxo principal deve ser:

```text
Route -> Controller -> Form Request -> Service -> Repository -> Model -> Database
```

Responsabilidades:

- Routes definem prefixos, nomes, middlewares e versionamento.
- Controllers recebem HTTP, usam Form Requests e delegam a regra para Services.
- Form Requests validam e normalizam entrada antes do controller.
- Services concentram regra de negocio, orquestracao, autenticacao, envio de email, jobs e respostas.
- Repositories encapsulam consultas e persistencia Eloquent.
- Models representam tabelas, relacionamentos, accessors, mutators, casts e metodos de dominio.
- Exceptions expressam erros de dominio e evitam retornos soltos no meio da regra.

Evite colocar regra de negocio pesada em Controller, Model ou Route.

## Estrutura de pastas

Padrao recomendado:

```text
app/
  Console/
  Exceptions/
  Http/
    Controllers/V1/{Modulo}/
    Middleware/
    Requests/V1/{Modulo}/
    Response/
  Jobs/
  Listeners/
  Mail/
  Models/
  ModelsAlece/
  Observers/
  Providers/
  Repositories/Eloquent/{Modulo}/
  Rules/
  Services/V1/{Modulo}/
database/
  factories/
  migrations/
  seeders/
docs/
  INDEX.md
  PADROES.md
  COPILOT_INSTRUCTIONS.md
  BANCO_DE_DADOS.md
  MODULO_{NOME}.md
routes/
  api.php
tests/
  Feature/V1/{Modulo}/
  Unit/Services/V1/{Modulo}/
```

Modulos usados como referencia no api-e-alece:

- `Comum`
- `Conta`
- `Enquete`
- `Localizacao`
- `Opine`
- `Sugira`
- `Tribuna`
- `Usuarios`
- `Painel`

## Versionamento de API

Rotas publicas e autenticadas devem ficar sob `/api/v1`.

Organize o codigo por namespace `V1`:

- `App\Http\Controllers\V1\{Modulo}`
- `App\Http\Requests\V1\{Modulo}`
- `App\Services\V1\{Modulo}`

Use `Route::prefix('v1')->group(...)` e depois agrupe por modulo:

```php
Route::prefix('v1')->group(function () {
    Route::prefix('conta')->group(function () {
        Route::post('entrar', [ContaController::class, 'entrar'])->name('entrar');

        Route::middleware(['auth:sanctum'])->group(function () {
            Route::get('perfil', [ContaController::class, 'perfil'])->name('perfil');
        });
    });
});
```

## Controllers

Controllers devem ser finos.

Padrao:

- Injetar Service no construtor.
- Receber Form Request quando houver validacao.
- Usar `$request->validated()`.
- Retornar diretamente o resultado do Service.
- Manter annotations OpenAPI no controller quando o endpoint for publico/documentado.

Exemplo:

```php
class ContaController extends Controller
{
    public function __construct(
        private ContaService $contaService
    ) {
    }

    public function registrar(RegisterRequest $request)
    {
        $data = $request->validated();

        return $this->contaService->registrar($data);
    }
}
```

## Services

Services concentram a regra de negocio e retornam `JsonResponse` quando fazem parte do fluxo HTTP.

Padrao:

- Injetar repositories e outros services pelo construtor.
- Usar type hints e retorno explicito.
- Lidar com verificacoes de dominio.
- Disparar jobs, emails e eventos.
- Retornar via `ApiResponse::prepare()` ou `ApiResponse::success()`.
- Lancar excecoes customizadas para cenarios de erro.

Exemplo:

```php
class ContaService
{
    public function __construct(
        private DoisFatoresService $doisFatoresService,
        private UsuariosRepository $usuariosRepository
    ) {
    }

    public function entrar(array $credentials): JsonResponse
    {
        $usuario = $this->usuariosRepository->findEmail($credentials['email']);

        if (!$usuario->verificarSenha($credentials['senha'])) {
            throw new UsuarioCredenciaisInvalidasException();
        }

        return ApiResponse::prepare(
            message: 'Login realizado com sucesso.',
            data: [
                'token' => $usuario->criaTokenAutenticacao(),
                'usuario' => $usuario->formatarParaResposta(),
            ]
        );
    }
}
```

## Repositories

Repositories devem encapsular persistencia e consultas.

Padrao:

- Ficar em `App\Repositories\Eloquent\{Modulo}`.
- Receber Model pelo construtor.
- Retornar Models, Collections, Paginators ou arrays conforme contrato do Service.
- Lancar excecao quando um registro obrigatorio nao existir.
- Evitar regra de negocio dentro do repository.

Exemplo:

```php
class UsuariosRepository
{
    public function __construct(
        private User $model
    ) {
    }

    public function findEmail(string $email): User
    {
        $user = $this->model->where('email', $email)->first();

        if (!$user) {
            throw new UsuarioNaoEncontradoException();
        }

        return $user;
    }
}
```

## Form Requests

Valide e normalize entrada nos Form Requests.

Padrao:

- Ficar em `App\Http\Requests\V1\{Modulo}`.
- Usar `authorize(): bool`.
- Usar `prepareForValidation()` para normalizacao.
- Usar `rules(): array`.
- Usar `messages(): array` com mensagens claras em portugues.
- Usar `Rule::unique`, `Rule::exists` e `Rule::in` quando a regra depender do banco ou de listas fechadas.

Exemplo de normalizacao:

```php
protected function prepareForValidation(): void
{
    $cpf = $this->input('cpf');

    if ($cpf !== null) {
        $cpf = preg_replace('/\D/', '', $cpf);
        $this->merge(['cpf' => $cpf]);
    }

    $this->merge([
        'email' => strtolower($this->email),
    ]);
}
```

## Respostas da API

Use `App\Http\Response\ApiResponse`.

Formato base:

```json
{
  "message": "Mensagem",
  "status": 200,
  "data": {}
}
```

Padrao:

```php
return ApiResponse::prepare(
    message: 'Operacao realizada com sucesso.',
    status: 200,
    data: [
        'item' => $item,
    ]
);
```

Evite montar `response()->json()` manualmente em cada service/controller quando o padrao do projeto puder ser usado.

## Excecoes

Use excecoes customizadas por dominio em `App\Exceptions\{Dominio}`.

Padrao:

- `UsuarioNaoEncontradoException`
- `UsuarioCredenciaisInvalidasException`
- `UsuarioInativoException`
- `UsuarioNaoAceitouTermosException`

Principio: erro de dominio deve ter nome de dominio, nao ser apenas `Exception` generica espalhada no codigo.

## Autenticacao e seguranca

Padroes:

- Laravel Sanctum para bearer token.
- Rotas protegidas com `auth:sanctum`.
- Rate limiter no `routes/api.php`.
- Dados sensiveis sempre validados por Form Request.
- Senhas sempre com hash.
- Email em lowercase antes da validacao.
- CPF normalizado antes de persistir.
- Regras de perfil/permissao documentadas em `docs/PERFIS_DOCUMENTACAO.md`.

## Banco de dados

Padroes observados:

- PostgreSQL como banco principal.
- Uso de schemas para organizar dominio, como `utils`, `opine` e `sugira`.
- Documentar tabelas, colunas, indices e relacionamentos em `docs/BANCO_DE_DADOS.md`.
- Atualizar a documentacao de banco sempre que migration alterar schema.
- Testes usam database separado, por exemplo `api_e_alece_testing`.

Ao criar migration:

1. Definir schema/tabela conforme dominio.
2. Criar indices e uniques explicitamente.
3. Criar foreign keys quando aplicavel.
4. Atualizar factories/seeders se o dado for usado em teste.
5. Atualizar docs de banco.

## Emails, jobs e observers

Use:

- `App\Mail` para emails.
- `App\Jobs` para trabalho assincrono.
- `App\Observers` para efeitos de eventos de models.

Padroes:

- Envio de email deve ficar no Service ou Job.
- Testes devem usar `Mail::fake()`.
- Jobs devem ser testados quando carregarem regra de negocio ou integrarem notificacoes.

## Swagger/OpenAPI

Padrao:

- Usar L5-Swagger.
- Manter annotations `@OA` nos Controllers.
- Documentar path, tag, summary, description, request body, security e responses.
- Rodar `./vendor/bin/sail artisan l5-swagger:generate` depois de alterar endpoints documentados.

Evite criar endpoint sem atualizar Swagger quando ele fizer parte da API publica.

## Testes

Estrutura:

- `tests/Feature/V1/{Modulo}` para HTTP, integracao, validacao, banco e efeitos externos fakeados.
- `tests/Unit/Services/V1/{Modulo}` para regra de negocio em Services.

Padroes:

- Usar `RefreshDatabase`.
- Usar factories.
- Usar `Mail::fake()` para emails.
- Usar `Sanctum::actingAs($user)` para autenticacao.
- Testar sucesso e falhas de validacao.
- Testar efeitos no banco com `assertDatabaseHas`.
- Testar excecoes de dominio com `expectException`.

Exemplos de cenarios esperados:

- Deve registrar com dados validos.
- Deve validar campos obrigatorios.
- Nao deve aceitar email duplicado.
- Nao deve aceitar senha invalida.
- Deve enviar email quando a regra exige.
- Deve retornar erro quando o usuario nao existe/inativo/sem permissao.

## Documentacao do projeto

Todo projeto futuro deve ter pelo menos:

- `README.md`: visao geral, stack, instalacao, comandos, URLs locais, testes.
- `docs/INDEX.md`: indice da documentacao e guia rapido por tarefa.
- `docs/PADROES.md`: arquitetura, estrutura de pastas, convencoes e exemplos.
- `docs/COPILOT_INSTRUCTIONS.md`: workflow para agentes IA, comandos e checklist.
- `docs/BANCO_DE_DADOS.md`: schemas, tabelas, colunas, indices e relacionamentos.
- `docs/MODULO_{NOME}.md`: documentacao por dominio.

Para agentes IA, a primeira leitura deve ser:

1. `docs/PADROES.md`
2. `docs/COPILOT_INSTRUCTIONS.md`
3. Documento do modulo envolvido.
4. Exemplos similares no codigo existente.

## Workflow para novo endpoint

1. Identificar modulo e prefixo de rota.
2. Criar ou atualizar Form Request.
3. Criar ou atualizar Service.
4. Criar ou atualizar Repository.
5. Criar ou atualizar Controller.
6. Registrar rota em `routes/api.php`.
7. Adicionar/atualizar Swagger.
8. Criar testes Feature.
9. Criar testes Unit quando houver regra relevante no Service.
10. Rodar testes e geracao do Swagger.
11. Atualizar docs do modulo e docs de banco se necessario.

## Comandos padrao

Usar Sail:

```bash
./vendor/bin/sail up -d
./vendor/bin/sail artisan migrate
./vendor/bin/sail artisan db:seed
./vendor/bin/sail artisan test
./vendor/bin/sail artisan l5-swagger:generate
./vendor/bin/sail artisan cache:clear
./vendor/bin/sail artisan config:clear
./vendor/bin/sail logs
```

Sem Sail, quando aplicavel:

```bash
php artisan test
php artisan l5-swagger:generate
php artisan pint
```

## Checklist de qualidade

Antes de considerar pronto:

- Leu os padroes do projeto.
- Reusou exemplos existentes.
- Controller continua fino.
- Validacao ficou em Form Request.
- Regra ficou em Service.
- Consulta ficou em Repository.
- Respostas usam `ApiResponse`.
- Excecoes de dominio foram usadas quando apropriado.
- Type hints e retornos foram declarados.
- Swagger foi atualizado.
- Testes cobrem sucesso e falha.
- `dd()`, `var_dump()` e debug temporario foram removidos.
- Imports estao organizados.
- Documentacao do modulo foi atualizada.
- Banco foi documentado se houve migration.

## Como a IA local deve usar este conhecimento

Quando o usuario pedir para criar projeto Laravel API, modulo, endpoint, teste, migration ou documentacao:

1. Aplicar a arquitetura Service-Repository.
2. Criar estrutura versionada em `V1`.
3. Escrever documentacao desde o inicio.
4. Preferir exemplos similares do projeto atual.
5. Usar ferramentas locais para ler arquivos antes de alterar.
6. Sugerir `qwen2.5-coder:7b` para tarefas comuns e `deepseek-coder-v2:16b` para refactor/debug mais pesado.

