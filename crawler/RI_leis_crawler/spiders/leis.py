import scrapy
from pathlib import Path

class ProposicoesSpider(scrapy.Spider):
    name = "leis"
    # inicia na primeira página da api
    start_urls = ["https://dadosabertos.camara.leg.br/api/v2/proposicoes?ano=2026,2025,2024,2023&pagina=1&itens=100&ordem=ASC&ordenarPor=id"]
    pagina = 1

    def parse(self, response):
        data = response.json()
        # extrai as proposições da resposta da api
        proposicoes = data["dados"]
        # se a resposta estiver vazia, termina a busca
        if not proposicoes:
            return
        
        for prop in proposicoes:
            
            # extrai apenas o id de cada proposição de lei
            prop_id = prop["id"]
            
            # utilizando o id da proposição, entra na página da lei no site da câmara de deputados
            prop_lei_url = f"https://www.camara.leg.br/proposicoesWeb/fichadetramitacao?idProposicao={prop_id}"
            yield scrapy.Request(url=prop_lei_url, callback=self.parse_prop_lei)

        # Passa para próxima página de proposições de lei da api
        self.pagina += 1
        next_url = f"https://dadosabertos.camara.leg.br/api/v2/proposicoes?ano=2026,2025,2024,2023&pagina={self.pagina}&itens=100&ordem=ASC&ordenarPor=id"
        if next_url:
            yield scrapy.Request(url=next_url, callback=self.parse)

    def parse_prop_lei(self, response):
        self.log(f"Extraindo html de: {response.url}")
        # cria pasta se não existe
        Path("output_leis").mkdir(exist_ok=True)
        # o arquivo é salvo como .html
        prop_id = response.url.split("=")[-1]
        filename = f"output_leis/projetoDeLei_{prop_id}.html"
        #extrai apenas o conteúdo principal na página da proposição de lei
        projeto = response.css("div#content").get()
        # salva o arquivo localmente
        with open(filename, "w", encoding="utf-8") as f:
            f.write(projeto)
        
        self.log(f"Arquivo salvo em: {filename}")
