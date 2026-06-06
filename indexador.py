import os
import json
import time
import re
import nltk
from nltk.corpus import stopwords
from nltk.stem import RSLPStemmer

# Garante que os pacotes do NLTK necessários para o português sejam baixados
nltk.download('stopwords', quiet=True)
nltk.download('rslp', quiet=True)

class IndiceInvertido:
    def __init__(self):
        # Dicionário: Termo -> Dicionário {ID_Documento: Frequencia (TF)}
        self.mapa = {}

    def adicionar_termos(self, id_documento, termos):
        for termo in termos:
            if termo not in self.mapa:
                self.mapa[termo] = {}
            
            # Calcula a Frequência do Termo (TF) no documento atual
            if id_documento not in self.mapa[termo]:
                self.mapa[termo][id_documento] = 1
            else:
                self.mapa[termo][id_documento] += 1

    def contar_termos_unicos(self):
        return len(self.mapa)

class ProcessadorTexto:
    def __init__(self):
        # Stopwords em português usando NLTK
        self.stopwords = set(stopwords.words('portuguese'))
        # Stemmer RSLP (Específico para português)
        self.stemmer = RSLPStemmer()

    def processar(self, conteudo_bruto):
        # 1. Limpeza de HTML (Remove tags)
        texto_limpo = re.sub(r'<.*?>', ' ', conteudo_bruto)

        # 2. Análise Léxica (Lowercase e Tokenização por pontuação/espaços)
        tokens = re.split(r'[\s\.\,\;\:\!\?\n\r\"\'\(\)\-\/\[\]]+', texto_limpo.lower())

        termos_processados = []

        # 3. Filtragem (Stopwords) e Transformação (Stemming)
        for token in tokens:
            if len(token) < 3 or token in self.stopwords:
                continue
            
            # Aplica stemming do NLTK
            radical = self.stemmer.stem(token)
            termos_processados.append(radical)

        return termos_processados

class GerenciadorPersistencia:
    def salvar(self, indice, caminho_arquivo):
        # Salva em JSON de forma compactada para economizar espaço
        with open(caminho_arquivo, 'w', encoding='utf-8') as f:
            json.dump(indice.mapa, f, separators=(',', ':'))

class MotorIndexacao:
    def __init__(self):
        self.processador = ProcessadorTexto()
        self.indice = IndiceInvertido()

    def executar(self, diretorio_origem):
        inicio = time.time()
        
        # Verifica se o diretório existe
        if not os.path.exists(diretorio_origem):
            print(f"ERRO: O diretório não foi encontrado: {diretorio_origem}")
            print("Certifique-se de extrair o arquivo .zip!")
            return None

        # Lista todos os arquivos HTML no diretório
        arquivos = [f for f in os.listdir(diretorio_origem) if f.endswith('.html')]
        bytes_processados = 0

        print(f"Iniciando o processamento de {len(arquivos)} arquivos...")

        for nome_arquivo in arquivos:
            caminho_completo = os.path.join(diretorio_origem, nome_arquivo)
            bytes_processados += os.path.getsize(caminho_completo)
            
            # Leitura do documento
            with open(caminho_completo, 'r', encoding='utf-8', errors='ignore') as f:
                conteudo = f.read()
            
            # Processamento
            termos = self.processador.processar(conteudo)
            
            # Adiciona ao Índice Invertido
            self.indice.adicionar_termos(nome_arquivo, termos)

        fim = time.time()
        tempo_ms = int((fim - inicio) * 1000)

        self._log_metricas(len(arquivos), bytes_processados, tempo_ms)
        return self.indice

    def _log_metricas(self, qtd_arquivos, bytes_proc, tempo_ms):
        tempo_formatado = f"{tempo_ms / 1000:.2f} segundos" if tempo_ms > 1000 else f"{tempo_ms} ms"
        print("\n--- MÉTRICAS DE INDEXAÇÃO ---")
        print(f"Documentos processados: {qtd_arquivos}")
        print(f"Tamanho bruto lido: {bytes_proc / (1024 * 1024):.2f} MB")
        print(f"Tempo de processamento: {tempo_formatado}")
        print(f"Vocabulário (termos únicos): {self.indice.contar_termos_unicos()}")
        print("-----------------------------\n")

def main():
    # Pasta com os HTMLs (baixe o output_leis do Google Drive e coloque na mesma
    # pasta deste script). Veja o README.
    pasta_script = os.path.dirname(os.path.abspath(__file__))
    diretorio_entrada = os.path.join(pasta_script, "output_leis")
    arquivo_saida = os.path.join(pasta_script, "indice_projetos_lei.json")

    # Executa a extração e o processamento de texto
    motor = MotorIndexacao()
    indice_gerado = motor.executar(diretorio_entrada)

    if indice_gerado:
        # Persiste a estrutura de dados (JSON)
        persistencia = GerenciadorPersistencia()
        persistencia.salvar(indice_gerado, arquivo_saida)

        # Afere o tamanho final
        if os.path.exists(arquivo_saida):
            tamanho_json = os.path.getsize(arquivo_saida)
            print(f"Tamanho do Índice salvo no disco (JSON): {tamanho_json / (1024 * 1024):.2f} MB")
            print(f"Arquivo salvo em: {os.path.abspath(arquivo_saida)}")

if __name__ == '__main__':
    main()