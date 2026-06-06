# Web Crawler Câmara de Deputados
Trabalho acadêmico da disciplina: Recuperação de Informação na Web e Redes Sociais

Curso: Sistemas de Informação - PUC Minas

Feito em python com Scrapy

# Como Funciona
O sistema coleta proposições de lei do site da câmara de deputados ([Link🔗](https://www.camara.leg.br/busca-portal/proposicoes/pesquisa-simplificada)).

Isso é feito em duas etapas:

Primeiro são coletadas os códigos de id das propostas de leis atravé da api Dados Abertos ([Link🔗](https://dadosabertos.camara.leg.br/swagger/api.html)) do governo.

então usando estas id's, o sistema acessa a página da lei no site da câmara de deputados, e salva o conteúdo principal localmente em um arquivo .html

os arquivos são salvos na pasta "output_leis" e tem o nome projetoDeLei_{id}

# Como Rodar localmente

É necessário ter o python instalado para rodar o programa, instale primeiro antes de rodar os comandos

1. Instale o Scrapy: execute o comando
   ```Bash
     pip install scrapy
   ```
2. Navegue até a página do projeto e rode o comando:
   ```
     scrapy crawl leis
   ```
