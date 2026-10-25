# Estimativa da taxa de aprovação dos anos finais em Goiás

Protótipo do **Projeto Integrador de Inteligência Artificial**, Projeto 2 (Educação).
Universidade Estadual de Goiás · Câmpus Metropolitano · Unidade Universitária de Trindade · Sistemas de Informação · 2026/2

**Integrantes:** João Manoel Silva Morais, Hayyra Eduarda Rocha, Ruan Silva Carvalho e Pedro Lucas Hipólito de Oliveira
**Professor:** Rafael Viana

## O que o protótipo faz

Usa uma **árvore de decisão para regressão** para estimar a taxa de aprovação dos anos finais do Ensino Fundamental (6º ao 9º ano) de cada escola de Goiás, a partir de:

- rede administrativa (estadual, municipal ou privada);
- localização (urbana ou rural);
- taxas de aprovação dos anos iniciais e do ensino médio, quando a escola oferece essas etapas;
- tamanho do município (número de escolas na base).

Depois calcula o **resíduo** (taxa real − taxa estimada). Escolas com resíduo de **−5 pontos ou menos** aprovam bem menos do que escolas de perfil parecido e entram numa **lista de alerta** para a gestão investigar.

## Resultados

Avaliação por validação cruzada (cada escola estimada por um modelo que não a viu no treino), com 1.739 escolas:

| Estimativa | MAE (p.p.) | RMSE (p.p.) | R² | Erro nas escolas abaixo de 95% (p.p.) |
|---|---|---|---|---|
| Sempre 100% | 1,42 | 3,45 | −0,20 | 10,13 |
| Média do treino | 1,80 | 3,15 | 0,00 | 8,72 |
| Regressão linear | 1,36 | 2,54 | 0,35 | 5,93 |
| **Árvore de decisão** | **1,32** | **2,52** | **0,36** | **5,87** |

- A árvore reduz o erro nas escolas críticas de cerca de 10 para cerca de 6 pontos, em relação às estimativas ingênuas.
- Árvore e regressão linear ficam próximas em erro; a árvore foi escolhida pelas **regras interpretáveis** e pelo tratamento natural das etapas não oferecidas.
- A lista de alerta tem **58 escolas**, e **todas** têm aprovação real abaixo de 95% (42 municipais, 11 privadas e 5 estaduais).
- Regra mais crítica encontrada: escola **municipal**, com aprovação nos anos iniciais até 98,9%, em município com mais de 14 escolas → taxa estimada de **92%** (113 escolas).

Os resultados são um **sinal de alerta**, não um diagnóstico: o modelo aprende associações, não causas.

## Estrutura

```
dados/02_educacao_regressao.csv          base reconstruída a partir do PDF (1.742 escolas, 2025)
notebooks/prototipo_arvore_regressao.ipynb  demonstração passo a passo, já executada
src/prototipo.py                         pipeline completo (treino, avaliação, alertas e gráficos)
src/extrair_pdf.py                       conversão do PDF original para CSV
saidas/                                  métricas, lista de alertas, regras da árvore e gráficos
docs/                                    relatório do projeto (PDF)
```

## Como executar

Com Python 3.10 ou mais recente:

```bash
pip install -r requirements.txt
python src/prototipo.py
```

O script mostra as métricas no terminal e grava os arquivos em `saidas/`.

Para a demonstração passo a passo, abra o notebook (ele já está executado, então os resultados aparecem mesmo sem rodar):

```bash
cd notebooks
jupyter notebook prototipo_arvore_regressao.ipynb
```

Também funciona no Google Colab: envie o notebook e as pastas `src/` e `dados/` mantendo a mesma estrutura.

## Limitações

- Base de um único ano, sem número de matrículas, nível socioeconômico ou histórico.
- Com 53% das escolas em 100% de aprovação, o erro médio sozinho engana; por isso medimos o erro nas escolas abaixo de 95%.
- Só 140 escolas estão abaixo de 95%, então os resultados variam com a divisão treino/teste.
- O PDF original tinha nomes de escolas cortados; a conversão recupera a maior parte deles, mas alguns nomes continuam incompletos.
