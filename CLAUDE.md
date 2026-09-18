# Gestor Acadêmico — SITE VERDADEIRO (produção)

Você está na pasta do **site real**, em produção. Usuários reais, e-mails reais,
dados reais. Qualquer mudança aqui vai direto pro ar em https://gestor-insercao-zeta.vercel.app/
assim que for feito `git push origin main` (deploy automático via Vercel).

## O par produção/teste

Este projeto tem um ambiente de teste **totalmente isolado**, numa pasta irmã:

- Pasta: `../gestor-academico-teste`
- Repositório GitHub próprio: `Nathy1234/gestor-insercao-teste`
- Projeto Vercel próprio (mesmo time `gestao-pessoal`),
  no ar em https://gestor-inseercao-teste.vercel.app/
- Banco de dados Supabase próprio, em conta separada — nunca compartilha
  dados, credenciais nem `.env` com a produção.

Sempre teste mudanças arriscadas lá primeiro. Só traga pra cá depois de validar.

### Remote já configurado
Este repo tem um remote `teste` apontando pro repositório de teste:
```
git remote -v          # mostra "teste" -> gestor-insercao-teste.git
```

### Como levar uma mudança feita no ambiente teste para cá (produção)
Prefira sempre trazer **só o commit específico** já validado, não tudo que
estiver pendente de experimentação no teste:
```
git fetch teste
git log teste/main --oneline -5     # acha o hash do commit
git cherry-pick <hash>
git push origin main
```

## Regras de segurança — não regredir

- Senhas: sempre hash (`hash_pw`/`check_pw` em `app.py`), nunca texto puro,
  nunca devolvidas em template/JSON.
- Login exige e-mail institucional `@fatecie.edu.br` (`EMAIL_DOMINIO_PERMITIDO`).
- Toda rota que apaga ou sobrescreve dados deve ser `POST` (nunca `GET`) e
  proteção CSRF já está ativa globalmente via `CSRFProtect`.
- Não criar rotas de debug/admin sem link nenhum na interface — se não tem
  uso real, não deve existir (já foi removido `/admin/reimportar`,
  `/admin/excel-debug`, `/admin/status` por esse motivo).
- Erros de conexão com banco nunca devem expor traceback ao navegador
  (ver `ensure_db()`).
- Não commitar scripts soltos com senha/connection string em texto puro na
  raiz do projeto — usar a pasta de scratchpad da sessão, nunca o repo.

## Backup e disponibilidade

- Backup automático diário via Vercel Cron (`vercel.json` → `/cron/backup`,
  protegido por `CRON_SECRET`). O mesmo cron também funciona como "ping" pra
  evitar que o Supabase free-tier pause o projeto por inatividade.
- Restauração de backup: rotas `/backup/<id>/restaurar` e
  `/backup/restaurar-upload`, exigem frase de confirmação.

## Versão exibida no site

`VERSAO` e `NO_AR_DESDE` no topo de `app.py` (context processor `inject_versao`).
Atualize `VERSAO` a cada mudança relevante publicada em produção.
