# 🎓 Gestor Acadêmico — Sistema de Gestão de Cursos

Sistema web **clean e funcional** para gerenciar todos os cursos, com rastreabilidade
de quem inseriu e editou cada um, substituindo a planilha Excel por um sistema com
banco de dados, histórico de ações, controle de acesso por perfil e backup automático.

---

## 🚀 Como rodar no VS Code

### 1. Pré-requisitos
- Python 3.10+ instalado ([python.org](https://python.org))
- VS Code com extensão **Python** instalada

### 2. Instalar dependências

Abra o terminal no VS Code (`Ctrl + J`) e execute:

```bash
pip install flask flask-sqlalchemy openpyxl
```

### 3. Colocar o arquivo Excel na pasta do sistema

Copie o arquivo `CURSOS_INOVA_-_LINKS__1_.xlsx` para dentro da pasta `inova_system/`.
(O sistema importa todos os dados automaticamente na primeira execução.)

### 4. Rodar o sistema

```bash
cd inova_system
python app.py
```

### 5. Acessar no navegador

```
http://localhost:5000
```

---

## 🔑 Usuários padrão (criados automaticamente)

| Usuário       | Senha      | Perfil  | Permissões                        |
|---------------|------------|---------|-----------------------------------|
| `admin`       | `inova2024`| Admin   | Tudo (incluindo excluir, usuários)|
| `junior`      | `inova2024`| Editor  | Criar e editar, sem excluir       |
| `felipe`      | `inova2024`| Editor  | Criar e editar, sem excluir       |
| `visualizador`| `inova2024`| Leitor  | Somente visualizar                |

> ⚠️ **Troque as senhas após o primeiro acesso!** Em Usuários → Editar.

---

## 📋 O que o sistema faz

### Cursos
- Lista todos os cursos com filtros por tipo, área e status
- Tipos suportados: Pós-Graduação, Profissionalizante, Rápido, Pacote, Terceiros, Evento, Prática Conectada, Prática Estágio, Projeto Ambiental, GGBR, Integra Edu
- **Matriz Curricular** com editor de disciplinas (módulo, CH, professor, titulação)
- Busca instantânea (barra de busca no topo)

### Controle de Acesso
- **Admin**: acesso total — excluir, gerenciar usuários, backup
- **Editor**: criar e editar cursos/cupons/reembolsos, **não pode excluir**
- **Leitor**: somente visualização

### Histórico de Ações (Audit Trail)
- Todo criar / editar / arquivar / excluir / login fica registrado
- Mostra: usuário, data/hora, ação realizada, detalhe
- Acessível em `/historico`

### Backup Automático
- Backup automático **toda semana** (arquivo `.zip` comprimido)
- Backup manual a qualquer momento no Dashboard ou em `/backup/lista`
- Download do banco de dados pela interface
- Mantém os últimos 20 backups

### Cupons e Reembolsos
- Cadastro, edição e listagem de cupons e reembolsos

---

## 🗂️ Estrutura do Projeto

```
inova_system/
├── app.py              ← Aplicação principal (rotas, modelos, lógica)
├── requirements.txt    ← Dependências Python
├── backups/            ← Backups automáticos e manuais
├── instance/
│   └── inova.db        ← Banco de dados SQLite (gerado automaticamente)
├── static/
│   ├── css/style.css   ← Design do sistema
│   └── js/app.js       ← Busca instantânea, editor de matriz
└── templates/          ← Páginas HTML
    ├── base.html
    ├── login.html
    ├── dashboard.html
    ├── cursos.html
    ├── curso_detalhe.html
    ├── curso_form.html
    ├── cupons.html / cupom_form.html
    ├── reembolsos.html / reembolso_form.html
    ├── historico.html
    ├── usuarios.html / usuario_form.html
    └── backups.html
```

---

## 🌐 Para outras pessoas acessarem

Para que **sua equipe** acesse o sistema na rede local:

1. Rode com: `python app.py`
2. Descubra o IP da sua máquina: `ipconfig` (Windows) ou `ifconfig` (Mac/Linux)
3. Compartilhe o endereço: `http://SEU_IP:5000`
4. Todos na mesma rede Wi-Fi/cabo podem acessar

Para acesso pela **internet** (opcional), use serviços como **ngrok** ou coloque em um servidor.

---

## 📞 Suporte

Sistema desenvolvido com base na planilha `CURSOS_INOVA_-_LINKS__1_.xlsx`.
Abas importadas: Pós Matrizes, Profissionalizantes, Rápidos, Pacotes, Terceiros,
Eventos, Práticas Conectadas, Práticas Estágio, Proj. Ambientes Prof., GGBR,
Cupons e Reembolsos. Abas ocultas também foram lidas.
