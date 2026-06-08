"""
Sistema de Recuperação de Proposições Legislativas
Etapa 3 - Interface Web (Flask)

Disciplina: Recuperação de Informação na Web
PUC Minas - Sistemas de Informação - 2026

Como rodar:
    pip install flask nltk
    python buscador_web.py

Depois abra no navegador: http://localhost:5000
"""

import json
import math
import os
import re
import time
import urllib.request

import nltk
from flask import Flask, jsonify, render_template_string, request
from nltk.corpus import stopwords
from nltk.stem import RSLPStemmer

nltk.download("stopwords", quiet=True)
nltk.download("rslp", quiet=True)

# =========================================================================== #
#  1. PROCESSADOR DE CONSULTA                                                  #
# =========================================================================== #
class ProcessadorConsulta:
    """
    Aplica o mesmo pipeline de pré-processamento utilizado na indexação:
      1. Limpeza de HTML
      2. Tokenização / lowercase
      3. Remoção de stopwords em português (NLTK)
      4. Stemming RSLP (Removedor de Sufixos da Língua Portuguesa)
    Usar o mesmo pipeline da indexação garante que os termos da consulta
    sejam comparados com os mesmos radicais armazenados no índice.
    """
    def __init__(self):
        self.stopwords = set(stopwords.words("portuguese"))
        self.stemmer = RSLPStemmer()

    def processar(self, texto: str) -> list:
        texto = re.sub(r"<.*?>", " ", texto)
        tokens = re.split(r"[\s\.\,\;\:\!\?\n\r\"\'\(\)\-\/\[\]]+", texto.lower())
        termos = []
        for tok in tokens:
            if len(tok) < 3 or tok in self.stopwords:
                continue
            termos.append(self.stemmer.stem(tok))
        return termos


# =========================================================================== #
#  2. MOTOR DE BUSCA (TF-IDF)                                                  #
# =========================================================================== #
class MotorBusca:
    """
    Carrega o índice invertido e executa buscas com ranking TF-IDF.

    Fórmulas:
        TF(t, d)    = frequência do termo t no documento d (armazenada no índice)
        IDF(t)      = log10( N / df(t) )
        score(d, q) = Σ TF(t,d) × IDF(t)  para cada t ∈ q ∩ d

    O IDF é pré-computado no carregamento para que cada busca
    seja respondida em tempo sub-segundo.
    """
    def __init__(self):
        self.indice = {}
        self.N = 0
        self.idf_cache = {}
        self.docs = {}
        self.processador = ProcessadorConsulta()
        self.carregado = False
        self.stats = {}

    def carregar_indice(self, caminho: str):
        inicio = time.time()
        with open(caminho, "r", encoding="utf-8") as f:
            self.indice = json.load(f)

        todos_docs = set()
        for postings in self.indice.values():
            todos_docs.update(postings.keys())
        self.N = len(todos_docs)

        self.docs = {}
        for doc_id in todos_docs:
            m = re.search(r"(\d+)", doc_id)
            if m:
                self.docs[m.group(1)] = doc_id

        self.idf_cache = {}
        for termo, postings in self.indice.items():
            df = len(postings)
            self.idf_cache[termo] = math.log10(self.N / df) if df else 0.0

        fim = time.time()
        self.carregado = True
        self.stats = {
            "termos": len(self.indice),
            "documentos": self.N,
            "tempo_carga": round(fim - inicio, 2),
        }

    def buscar(self, consulta: str, top_k: int = 20):
        if not self.carregado:
            return [], 0.0, []

        inicio = time.time()
        stems = self.processador.processar(consulta)
        if not stems:
            return [], 0.0, []

        scores = {}
        for stem in stems:
            if stem not in self.indice:
                continue
            idf = self.idf_cache[stem]
            for doc_id, tf in self.indice[stem].items():
                scores[doc_id] = scores.get(doc_id, 0.0) + tf * idf

        ordenados = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]

        resultados = []
        for rank, (doc_id, score) in enumerate(ordenados, start=1):
            match = re.search(r"(\d+)", doc_id)
            prop_id = match.group(1) if match else doc_id
            resultados.append({
                "rank": rank,
                "doc_id": doc_id,
                "prop_id": prop_id,
                "score": round(score, 4),
                "url": f"https://www.camara.leg.br/proposicoesWeb/fichadetramitacao?idProposicao={prop_id}",
            })

        tempo = round((time.time() - inicio) * 1000, 1)
        return resultados, tempo, stems


# =========================================================================== #
#  3. HTML DA INTERFACE                                                         #
# =========================================================================== #
HTML = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>Sistema de Recuperação de Proposições Legislativas</title>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    body {
      font-family: 'Segoe UI', Arial, sans-serif;
      background: #0f1923;
      color: #e0e6ed;
      min-height: 100vh;
    }

    /* ── Cabeçalho ── */
    header {
      background: #152030;
      border-bottom: 2px solid #1e3a5f;
      padding: 18px 40px;
      display: flex;
      align-items: center;
      gap: 16px;
    }
    header .icone { font-size: 28px; }
    header h1 {
      font-size: 18px;
      font-weight: 700;
      color: #e0e6ed;
      line-height: 1.2;
    }
    header p {
      font-size: 12px;
      color: #6b8096;
      margin-top: 2px;
    }
    /* ── Status do índice ── */
    #status-bar {
      background: #152030;
      border-bottom: 1px solid #1e3a5f;
      padding: 8px 40px;
      display: flex;
      align-items: center;
      gap: 10px;
      font-size: 12px;
      color: #6b8096;
    }
    #status-bar .dot {
      width: 8px; height: 8px;
      border-radius: 50%;
      background: #e05252;
      flex-shrink: 0;
    }
    #status-bar .dot.ok { background: #3ecf8e; }
    #status-stats {
      margin-left: auto;
      display: flex;
      gap: 20px;
    }
    #status-stats span { color: #4a9edd; font-weight: 600; }

    /* ── Área de busca ── */
    main { max-width: 960px; margin: 0 auto; padding: 40px 20px; }

    .search-box {
      display: flex;
      gap: 10px;
      margin-bottom: 12px;
    }
    .search-box input {
      flex: 1;
      background: #1a2a3a;
      border: 1px solid #1e3a5f;
      border-radius: 8px;
      padding: 14px 18px;
      font-size: 15px;
      color: #e0e6ed;
      outline: none;
      transition: border-color .2s;
    }
    .search-box input:focus { border-color: #2e6da4; }
    .search-box input::placeholder { color: #3d5166; }

    .search-box button {
      background: #1e5fa4;
      color: #fff;
      border: none;
      border-radius: 8px;
      padding: 14px 28px;
      font-size: 14px;
      font-weight: 600;
      cursor: pointer;
      transition: background .2s;
      white-space: nowrap;
    }
    .search-box button:hover { background: #2472be; }
    .search-box button:disabled { background: #1a3a5c; cursor: not-allowed; }

    .search-box select {
      background: #1a2a3a;
      border: 1px solid #1e3a5f;
      border-radius: 8px;
      padding: 14px 12px;
      font-size: 14px;
      color: #e0e6ed;
      outline: none;
      cursor: pointer;
      transition: border-color .2s;
    }
    .search-box select:focus { border-color: #2e6da4; }
    .search-box select:disabled { opacity: .4; cursor: not-allowed; }

    /* ── Stems ── */
    #stems-info {
      font-size: 12px;
      color: #4a6a84;
      margin-bottom: 20px;
      min-height: 18px;
    }
    #stems-info span { color: #4a9edd; }

    /* ── Resultados ── */
    #results-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 12px;
      font-size: 13px;
      color: #6b8096;
      min-height: 20px;
    }
    #results-header strong { color: #e0e6ed; }

    #results { display: flex; flex-direction: column; gap: 8px; }

    .result-card {
      background: #152030;
      border: 1px solid #1e3a5f;
      border-radius: 10px;
      padding: 14px 18px;
      display: grid;
      grid-template-columns: 36px 1fr auto;
      gap: 12px;
      align-items: center;
      transition: border-color .2s, background .2s;
      text-decoration: none;
      color: inherit;
    }
    .result-card:hover {
      border-color: #2e6da4;
      background: #1a2e42;
    }
    .rank {
      font-size: 18px;
      font-weight: 800;
      color: #1e4a7a;
      text-align: center;
    }
    .result-card:hover .rank { color: #2e6da4; }
    .result-info { overflow: hidden; }
    .result-id {
      font-size: 13px;
      font-weight: 600;
      color: #4a9edd;
      margin-bottom: 4px;
    }
    .result-url {
      font-size: 11px;
      color: #3d5166;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    .result-score {
      text-align: right;
      white-space: nowrap;
    }
    .score-value {
      font-size: 15px;
      font-weight: 700;
      color: #3ecf8e;
    }
    .score-label {
      font-size: 10px;
      color: #3d5166;
    }

    /* ── Mensagens ── */
    .msg {
      text-align: center;
      padding: 50px 20px;
      color: #3d5166;
      font-size: 14px;
    }
    .msg .emoji { font-size: 40px; display: block; margin-bottom: 12px; }

    /* ── Loading spinner ── */
    #loading {
      display: none;
      text-align: center;
      padding: 30px;
      color: #4a6a84;
      font-size: 13px;
    }

    footer {
      text-align: center;
      padding: 30px;
      font-size: 11px;
      color: #2a3a4a;
    }
  </style>
</head>
<body>

<header>
  <span class="icone">⚖️</span>
  <div>
    <h1>Sistema de Recuperação de Proposições Legislativas</h1>
    <p>Câmara dos Deputados — Recuperação de Informação na Web · PUC Minas 2026</p>
  </div>
</header>

<div id="status-bar">
  <div class="dot" id="status-dot"></div>
  <span id="status-text">Índice não carregado</span>
  <div id="status-stats" style="display:none">
    <div>Termos: <span id="stat-termos">—</span></div>
    <div>Documentos: <span id="stat-docs">—</span></div>
    <div>Carga: <span id="stat-tempo">—</span>s</div>
  </div>
</div>

<main>

  <!-- Busca -->
  <div class="search-box">
    <input
      type="text"
      id="query-input"
      placeholder="Ex: reforma tributária imposto renda..."
      disabled
      onkeydown="if(event.key==='Enter') buscar()"
    />
    <select id="top-k" disabled>
      <option value="5">5</option>
      <option value="10">10</option>
      <option value="20" selected>20</option>
      <option value="50">50</option>
    </select>
    <button id="btn-search" onclick="buscar()" disabled>🔍 Pesquisar</button>
  </div>

  <div id="stems-info"></div>

  <div id="results-header"></div>
  <div id="loading">⏳ Buscando...</div>
  <div id="results">
    <div class="msg">
      <span class="emoji">📋</span>
      Carregue o índice e realize uma busca para ver os resultados.
    </div>
  </div>

</main>

<footer>
  PUC Minas · Sistemas de Informação · Recuperação de Informação na Web · 2026
</footer>

<script>
  // ── Verifica status do índice ao carregar a página ─────────────────────── //
  async function verificarStatus() {
    try {
      const resp = await fetch('/status');
      const data = await resp.json();
      if (data.carregado) {
        document.getElementById('status-dot').classList.add('ok');
        document.getElementById('status-text').textContent = 'Índice carregado automaticamente';
        document.getElementById('stat-termos').textContent = data.termos.toLocaleString('pt-BR');
        document.getElementById('stat-docs').textContent = data.documentos.toLocaleString('pt-BR');
        document.getElementById('stat-tempo').textContent = data.tempo_carga;
        document.getElementById('status-stats').style.display = 'flex';
        document.getElementById('query-input').disabled = false;
        document.getElementById('btn-search').disabled = false;
        document.getElementById('top-k').disabled = false;
        document.getElementById('query-input').focus();
        document.getElementById('results').innerHTML =
          '<div class="msg"><span class="emoji">✅</span>Índice pronto. Digite sua busca acima.</div>';
      } else {
        document.getElementById('status-text').textContent = 'Carregando índice, aguarde…';
        setTimeout(verificarStatus, 2000);
      }
    } catch (err) {
      document.getElementById('status-text').textContent = 'Erro ao verificar índice: ' + err.message;
    }
  }

  verificarStatus();

  // ── Helpers de UI ─────────────────────────────────────────────────────── //
  function iniciarLoading() {
    document.getElementById('results').innerHTML = '';
    document.getElementById('results-header').innerHTML = '';
    document.getElementById('stems-info').innerHTML = '';
    document.getElementById('loading').style.display = 'block';
    document.getElementById('btn-search').disabled = true;
  }

  function pararLoading() {
    document.getElementById('loading').style.display = 'none';
    document.getElementById('btn-search').disabled = false;
  }

  function mostrarErro(msg) {
    document.getElementById('results').innerHTML =
      '<div class="msg"><span class="emoji">⚠️</span>Erro: ' + msg + '</div>';
  }

  function mostrarResultadoUnico(data, label) {
    const titulo = label || ('ID ' + data.prop_id);
    document.getElementById('results-header').innerHTML = '<strong>Proposição encontrada</strong>';
    const container = document.getElementById('results');
    const card = document.createElement('a');
    card.className = 'result-card';
    card.href = data.url;
    card.target = '_blank';
    card.rel = 'noopener noreferrer';
    card.innerHTML =
      '<div class="rank">1</div>' +
      '<div class="result-info">' +
        '<div class="result-id">' + titulo + ' &nbsp;·&nbsp; ID: ' + data.prop_id + '</div>' +
        '<div class="result-url">' + (data.ementa || data.url) + '</div>' +
      '</div>' +
      '<div class="result-score">' +
        '<div class="score-value">↗</div>' +
        '<div class="score-label">acesso direto</div>' +
      '</div>';
    container.appendChild(card);
  }

  // ── Busca por ID numérico (ex: 2345678) ───────────────────────────────── //
  async function buscarPorId(propId) {
    iniciarLoading();
    try {
      const resp = await fetch('/proposicao/' + propId);
      const data = await resp.json();
      pararLoading();
      if (data.encontrado) {
        mostrarResultadoUnico(data);
      } else {
        document.getElementById('results').innerHTML =
          '<div class="msg"><span class="emoji">🔍</span>' +
          'ID <strong>' + propId + '</strong> não encontrado no índice.</div>';
      }
    } catch (err) {
      pararLoading();
      mostrarErro(err.message);
    }
  }

  // ── Busca por sigla (ex: PL 1038/2025) ────────────────────────────────── //
  async function buscarPorSigla(tipo, numero, ano) {
    iniciarLoading();
    const label = tipo.toUpperCase() + ' ' + numero + '/' + ano;
    try {
      const resp = await fetch(
        '/resolucao?tipo=' + encodeURIComponent(tipo) +
        '&numero=' + encodeURIComponent(numero) +
        '&ano=' + encodeURIComponent(ano)
      );
      const data = await resp.json();
      pararLoading();
      if (data.encontrado) {
        mostrarResultadoUnico(data, label);
      } else {
        document.getElementById('results').innerHTML =
          '<div class="msg"><span class="emoji">🔍</span>' +
          '<strong>' + label + '</strong> não encontrado na API da Câmara.' +
          (data.erro ? '<br><small>' + data.erro + '</small>' : '') + '</div>';
      }
    } catch (err) {
      pararLoading();
      mostrarErro(err.message);
    }
  }

  // ── Busca principal ────────────────────────────────────────────────────── //
  async function buscar() {
    const query = document.getElementById('query-input').value.trim();
    if (!query) return;

    // Padrão "PL 1038/2025", "PEC 45/2019", etc.
    const siglMatch = query.match(/^([A-Za-z]+)\\s+(\\d+)\\s*\\/\\s*(\\d{4})$/);
    if (siglMatch) {
      buscarPorSigla(siglMatch[1], siglMatch[2], siglMatch[3]);
      return;
    }

    // ID numérico puro
    if (/^\\d+$/.test(query)) {
      buscarPorId(query);
      return;
    }

    // Busca TF-IDF normal
    const topK = parseInt(document.getElementById('top-k').value, 10);
    iniciarLoading();
    try {
      const resp = await fetch('/buscar', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, top_k: topK }),
      });
      const data = await resp.json();
      pararLoading();

      if (data.stems && data.stems.length > 0) {
        document.getElementById('stems-info').innerHTML =
          'Radicais utilizados na busca: ' +
          data.stems.map(s => '<span>' + s + '</span>').join(', ');
      }

      if (data.resultados && data.resultados.length > 0) {
        document.getElementById('results-header').innerHTML =
          '<strong>' + data.resultados.length + ' resultado(s)</strong> &nbsp;·&nbsp; ' +
          'Tempo de busca: <strong>' + data.tempo_ms + ' ms</strong>';

        const container = document.getElementById('results');
        data.resultados.forEach(r => {
          const card = document.createElement('a');
          card.className = 'result-card';
          card.href = r.url;
          card.target = '_blank';
          card.rel = 'noopener noreferrer';
          card.innerHTML =
            '<div class="rank">' + r.rank + '</div>' +
            '<div class="result-info">' +
              '<div class="result-id">Proposição ID: ' + r.prop_id + '</div>' +
              '<div class="result-url">' + r.url + '</div>' +
            '</div>' +
            '<div class="result-score">' +
              '<div class="score-value">' + r.score + '</div>' +
              '<div class="score-label">score TF-IDF</div>' +
            '</div>';
          container.appendChild(card);
        });
      } else {
        document.getElementById('results').innerHTML =
          '<div class="msg"><span class="emoji">🔍</span>' +
          'Nenhum resultado encontrado. Tente palavras diferentes.</div>';
      }
    } catch (err) {
      pararLoading();
      mostrarErro(err.message);
    }
  }
</script>

</body>
</html>
"""


# =========================================================================== #
#  4. ROTAS FLASK                                                               #
# =========================================================================== #
app = Flask(__name__)
motor = MotorBusca()


@app.route("/")
def index():
    return render_template_string(HTML)


@app.route("/status")
def status():
    """Informa ao navegador se o índice já foi carregado."""
    if motor.carregado:
        return jsonify({"carregado": True, **motor.stats})
    return jsonify({"carregado": False})


@app.route("/buscar", methods=["POST"])
def buscar():
    """Executa a busca e retorna os resultados em JSON."""
    try:
        corpo = request.get_json()
        query = corpo.get("query", "").strip()
        if not query:
            return jsonify({"resultados": [], "tempo_ms": 0, "stems": []})

        top_k = max(1, min(int(corpo.get("top_k", 20)), 100))
        resultados, tempo_ms, stems = motor.buscar(query, top_k=top_k)
        return jsonify({"resultados": resultados, "tempo_ms": tempo_ms, "stems": stems})
    except Exception as e:
        return jsonify({"erro": str(e)}), 500


@app.route("/proposicao/<prop_id>")
def proposicao(prop_id):
    """Busca direta por ID numérico interno da Câmara."""
    if not motor.carregado:
        return jsonify({"encontrado": False})
    doc_id = motor.docs.get(prop_id)
    if doc_id:
        return jsonify({
            "encontrado": True,
            "prop_id": prop_id,
            "url": f"https://www.camara.leg.br/proposicoesWeb/fichadetramitacao?idProposicao={prop_id}",
        })
    return jsonify({"encontrado": False})


@app.route("/resolucao")
def resolucao():
    """Resolve 'PL 1038/2025' → ID interno via API da Câmara."""
    tipo = request.args.get("tipo", "").strip().upper()
    numero = request.args.get("numero", "").strip()
    ano = request.args.get("ano", "").strip()
    if not tipo or not numero or not ano:
        return jsonify({"encontrado": False})
    try:
        api_url = (
            "https://dadosabertos.camara.leg.br/api/v2/proposicoes"
            f"?siglaTipo={tipo}&numero={numero}&ano={ano}&ordem=ASC&ordenarPor=id"
        )
        req = urllib.request.Request(api_url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
        dados = data.get("dados", [])
        if not dados:
            return jsonify({"encontrado": False})
        prop = dados[0]
        prop_id = str(prop["id"])
        return jsonify({
            "encontrado": True,
            "prop_id": prop_id,
            "ementa": prop.get("ementa", ""),
            "url": f"https://www.camara.leg.br/proposicoesWeb/fichadetramitacao?idProposicao={prop_id}",
        })
    except Exception as e:
        return jsonify({"encontrado": False, "erro": str(e)})


# =========================================================================== #
#  5. PONTO DE ENTRADA                                                         #
# =========================================================================== #
def carregar_indice_automatico():
    """Procura o indice_projetos_lei.json na mesma pasta do script e carrega."""
    pasta = os.path.dirname(os.path.abspath(__file__))
    caminho = os.path.join(pasta, "indice_projetos_lei.json")
    if os.path.exists(caminho):
        print(f"  Carregando índice: {caminho}")
        motor.carregar_indice(caminho)
        print(f"  OK {motor.stats['documentos']:,} documentos | {motor.stats['termos']:,} termos | {motor.stats['tempo_carga']}s")
    else:
        print(f"  AVISO: indice_projetos_lei.json não encontrado em {pasta}")
        print("  Coloque o arquivo na mesma pasta que este script e reinicie.")


if __name__ == "__main__":
    print("\n" + "="*55)
    print("  Sistema de Recuperação de Proposições Legislativas")
    print("="*55)
    carregar_indice_automatico()
    print("  Acesse no navegador: http://localhost:5000")
    print("  Para encerrar:       Ctrl + C")
    print("="*55 + "\n")
    app.run(debug=False, port=5000)
