# Projeto RI — Busca em Projetos de Lei

Sistema de Recuperação de Informação sobre projetos de lei da Câmara dos
Deputados. Constrói um **índice invertido** a partir de ~50 mil documentos HTML e
oferece uma **busca web** com ranqueamento por **TF-IDF**.

## Visão geral

```
output_leis/  ──[indexador.py]──>  indice_projetos_lei.json  ──[buscador_web.py]──>  busca web
 (50k HTMLs)                            (~164 MB, baixar do Drive)
 só p/ regerar o índice                 basta isso para buscar
```

- **`indexador.py`** — lê os HTMLs de `output_leis/`, faz limpeza, tokenização,
  remoção de *stopwords* e *stemming* (NLTK/RSLP) e gera o índice invertido em
  `indice_projetos_lei.json`.
- **`buscador_web.py`** — interface web (Flask) que carrega o índice e responde
  consultas com ranqueamento TF-IDF. Os resultados linkam direto para a ficha de
  tramitação no site da Câmara.

## Pré-requisitos

- Python 3.8+

```bash
pip install flask nltk
```

> Os pacotes do NLTK (`stopwords` e `rslp`) são baixados automaticamente na
> primeira execução.

---

## Usar a busca (uso comum)

Para **apenas pesquisar**, você **NÃO precisa** baixar o `output_leis/`.
Basta o `indice_projetos_lei.json`.

1. Clone o repositório:

   ```bash
   git clone https://github.com/SamuelVitor227/projeto_ri.git
   cd projeto_ri
   ```

2. **Baixe o `indice_projetos_lei.json` (~164 MB) do Google Drive** e coloque-o
   **na mesma pasta** do projeto (mesmo nível do `buscador_web.py`):

   👉 https://drive.google.com/drive/folders/16D8lQeqwcW0Tswjb8h75HPiZx-H58MNe

   > O índice **não** está no repositório por causa do tamanho (~164 MB). Sem o
   > arquivo na pasta, o buscador avisa que não encontrou o índice e a busca não
   > funciona.

3. Rode a interface web:

   ```bash
   python buscador_web.py
   ```

4. Abra no navegador: <http://localhost:5000>

---

## Regerar o índice (opcional)

Só é necessário se você quiser **reconstruir** o `indice_projetos_lei.json` a
partir dos HTMLs originais.

1. **Baixe o `output_leis` do Google Drive:**

   👉 https://drive.google.com/drive/folders/16D8lQeqwcW0Tswjb8h75HPiZx-H58MNe

2. Coloque a pasta `output_leis/` **na mesma pasta deste projeto** (mesmo nível
   do `indexador.py`). A estrutura deve ficar assim:

   ```
   projeto_ri/
   ├── indexador.py
   ├── buscador_web.py
   ├── output_leis/          <-- baixada do Google Drive
   │   ├── projetoDeLei_2345643.html
   │   ├── projetoDeLei_2345644.html
   │   └── ...
   └── indice_projetos_lei.json
   ```

3. Rode o indexador:

   ```bash
   python indexador.py
   ```

   Ele gera/atualiza o `indice_projetos_lei.json` na própria pasta.

> A pasta `output_leis/` **não** está no repositório (é ignorada via
> `.gitignore`) por causa do volume de arquivos — por isso fica no Google Drive.

---

## Estrutura do repositório

| Arquivo | Descrição |
|---|---|
| `buscador_web.py` | Interface web de busca (Flask + TF-IDF) |
| `indexador.py` | Gera o índice invertido a partir dos HTMLs |
| `indice_projetos_lei.json` | Índice invertido (~164 MB) — **não versionado**, baixar do Google Drive |
| `output_leis/` | HTMLs originais — **não versionado**, baixar do Google Drive |
