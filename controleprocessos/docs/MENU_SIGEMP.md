# SIGEMP
# Documento de Arquitetura do Menu

---

# Objetivo

Este documento descreve a arquitetura oficial de navegação do SIGEMP.

Seu objetivo é registrar as decisões arquitetônicas relacionadas ao menu principal da aplicação, preservando o histórico de evolução do sistema e servindo como referência para futuras implementações.

Este documento deve crescer juntamente com o SIGEMP.

---

# Princípios Arquiteturais

A arquitetura do menu deverá seguir os seguintes princípios:

- A navegação será orientada pelos módulos de negócio da aplicação e não pelas telas individuais.
- Cada componente possuirá apenas uma única responsabilidade.
- A Sidebar será apenas o container visual da navegação.
- O Menu será responsável pela estrutura lógica.
- Os Flyouts serão responsáveis apenas pela apresentação dos níveis.
- A implementação deverá priorizar baixo acoplamento e alta coesão.
- Novos módulos deverão ser adicionados sem necessidade de alterar a estrutura principal da Sidebar.

---

# Arquitetura Funcional

A arquitetura funcional atualmente aprovada é a seguinte.

```text
SIGEMP

├── 🏛 Arquitetura
│
├── 📂 Processos
│     ├── Cadastro
│     └── A Mapear
│
├── 📊 Estatísticas
│     ├── Dashboard
│     ├── Processos a Mapear
│     ├── Processos
│     └── Comparativos
│
├── ⚙ Estrutura de Documentos
│     ├── 📁 Processos
│     │      ├── Definição
│     │      ├── Classificação
│     │      ├── Macroprocesso N1
│     │      ├── Macroprocesso N2
│     │      └── Áreas Responsáveis
│     │
│     └── 📄 Normas de Procedimento
│            ├── Definição
│            ├── Sistemas
│            └── Normas
│
└── 👥 Administração
      ├── Usuários
      └── Logs
```

---

# Arquitetura Técnica

A navegação será composta pelas seguintes camadas.

```text
base.html
        │
        ▼
sidebar.html
        │
        ▼
menu.html
        │
        ├── item.html
        ├── group.html
        └── flyout.html
```

Responsabilidade de cada componente.

## base.html

Responsável apenas pela composição do layout principal.

Não deverá possuir regras de navegação.

---

## sidebar.html

Container visual da navegação.

Não deverá conhecer URLs nem regras de negócio.

---

## menu.html

Representa a estrutura lógica do menu principal.

É responsável pela composição dos módulos da aplicação.

---

## item.html

Representa um item simples de navegação.

Exemplos:

- Arquitetura
- Cadastro
- Usuários

---

## group.html

Representa um módulo que possui filhos.

Exemplos:

- Processos
- Estrutura de Documentos
- Administração

---

## flyout.html

Responsável exclusivamente pela apresentação dos níveis da navegação.

---

# Diretrizes de Implementação

Durante o desenvolvimento deverão ser observadas as seguintes regras.

- Nunca alterar mais de uma responsabilidade por unidade de trabalho.
- Toda refatoração deverá manter o comportamento existente.
- Componentes deverão ser reutilizáveis sempre que possível.
- A navegação deverá ser preparada para crescimento futuro.
- Sempre que houver dúvida sobre uma abordagem técnica, um experimento simples deverá ser realizado antes de alterar a arquitetura ou abandonar uma solução.

## Comportamento da Sidebar

A Sidebar do SIGEMP utiliza o padrão de painel sobreposto (overlay), não deslocando o conteúdo da aplicação.

Regras:

- Ao abrir a Sidebar, o conteúdo permanece fixo.
- Um overlay semitransparente cobre a aplicação.
- Clicar fora da Sidebar fecha o menu.
- Clicar em qualquer item do menu fecha a Sidebar.
- Ao fechar, permanece visível apenas a barra reduzida com os ícones.
- No modo reduzido, o nome dos módulos é exibido por hover.

### Persistência do estado da Sidebar

Toda alteração no estado de abertura da Sidebar deverá atualizar imediatamente o `localStorage` (`gpp_sidebar_open`), garantindo consistência entre mudanças de página e recargas da aplicação.

### Templates Django

- As tags `{% include %}` que utilizam parâmetros (`with`) deverão ser escritas em uma única linha.
- Evitar quebras de linha na instrução `{% include ... with ... %}`, mantendo um padrão único de escrita em todo o projeto.
- Sempre que houver dúvida sobre o comportamento de um recurso do framework, deverá ser realizado um experimento simples antes de alterar a arquitetura ou abandonar uma solução.

---

# Estado Atual

## Concluído

- Refatoração do base.html
- Extração das Flash Messages
- Extração do Modal de Perfil
- Extração da Sidebar
- Separação do Menu

## Em desenvolvimento

- Componentização do Menu

## Planejado

- Item de Menu
- Grupo de Menu
- Flyout
- Estrutura orientada por dados
- Encerramento automático dos Flyouts
- Sidebar fixa sem deslocamento do conteúdo

---

# Decisões Arquiteturais

## DA-001

A navegação do SIGEMP será orientada pelos módulos de negócio da aplicação e não pelas telas individuais.

Status: Aprovada

---

## DA-002

A Sidebar será apenas um componente estrutural.

Status: Aprovada

---

## DA-003

Os Flyouts substituirão os submenus expansivos atuais.

Status: Aprovada

---

## DA-004

O desenvolvimento seguirá a metodologia "Jack, o das partes".

Cada unidade deverá ser pequena, validável e reversível.

Status: Aprovada

---

# Histórico

## Versão 1

Menu lateral expansivo com dois níveis.

---

## Versão 2

Refatoração do Layout.

Separação entre:

- Base
- Sidebar
- Menu

---

## Próxima versão

Implementação do novo sistema de Flyouts.

---

Documento iniciado em julho de 2026.

Este documento deverá acompanhar permanentemente a evolução arquitetural do SIGEMP.