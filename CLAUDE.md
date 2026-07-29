# Gestor Acadêmico — AMBIENTE DE TESTE

Você está na pasta do **ambiente de teste**. Este é um clone isolado do site
real, criado para testar mudanças com segurança antes de ir para produção.

Isolamento (não deve nunca ser misturado com o site real):
- Repositório GitHub próprio: `Nathy1234/gestor-academico-teste`
- Projeto Vercel próprio: `gestor-academico-teste` (mesmo time `gestao-pessoal`
  do site real, mas projeto separado)
- Banco de dados Supabase próprio, em **conta separada** da produção — nunca
  compartilha dados, credenciais nem `.env` com o site real.
- Usuários deste banco **não são os usuários reais**. Ao subir pela primeira
  vez, `seed_data()` em `app.py` cria 4 contas de exemplo (`admin`, `junior`,
  `felipe`, `visualizador`, senha inicial `inova2024`, troca obrigatória no
  primeiro login) — não os 5 usuários reais que existem em produção.

## O site verdadeiro (produção)

- Pasta irmã: `../inova_system`
- Repositório GitHub: `Nathy1234/inova_system`
- URL: https://inova-system.vercel.app

### Remote já configurado
Este repo tem um remote `producao` apontando pro repositório real:
```
git remote -v          # mostra "producao" -> inova_system.git
```

## Fluxo de trabalho

1. Mexa e teste livremente aqui. `git push origin main` sobe pro GitHub de
   teste e o Vercel de teste redeploya sozinho — zero risco pro site real.
2. Quando validar que está pronto, leve **só aquele commit específico** para
   produção (não tudo que estiver pendente/experimental aqui):
   ```
   cd ../inova_system
   git fetch teste
   git log teste/main --oneline -5     # acha o hash do commit
   git cherry-pick <hash>
   git push origin main
   ```
3. Nunca copie dados reais de usuários/cursos de produção para este banco de
   teste — o isolamento é proposital, para não expor dados reais num
   ambiente de testes.

## Regras de segurança — mesmas do site real, não regredir aqui também

- Senhas sempre com hash (`hash_pw`/`check_pw`), nunca texto puro.
- Toda rota que apaga ou sobrescreve dados deve ser `POST`, nunca `GET`.
- Não criar rotas de debug/admin sem link nenhum na interface.
- Não commitar scripts soltos com senha/connection string em texto puro na
  raiz do projeto — usar a pasta de scratchpad da sessão, nunca o repo.
