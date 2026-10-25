"""
Protótipo - Projeto Integrador de Inteligência Artificial (UEG, 2026/2)
Projeto 2 - Educação: estimativa da taxa de aprovação dos anos finais do
Ensino Fundamental em escolas de Goiás com árvore de decisão para regressão.

Uso (a partir da raiz do repositório):
    python src/prototipo.py

Gera em saidas/: métricas, lista de escolas em alerta, regras da árvore e gráficos.
"""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GridSearchCV, KFold, cross_val_predict, train_test_split
from sklearn.tree import DecisionTreeRegressor, export_text, plot_tree

RAIZ = Path(__file__).resolve().parents[1]
DADOS = RAIZ / "dados" / "02_educacao_regressao.csv"
SAIDAS = RAIZ / "saidas"
SEMENTE = 42
LIMIAR_CRITICO = 95.0   # escolas abaixo disso são o grupo de atenção
LIMIAR_ALERTA = -5.0    # resíduo (real - estimada) abaixo disso gera alerta
GRADE = {"max_depth": [2, 3, 4, 5, 6, 8], "min_samples_leaf": [10, 20, 30, 50]}
AZUL, AZUL_CLARO, CINZA = "#3B82C4", "#9CC4EA", "#B0B7C3"


def carregar_dados(caminho=DADOS):
    """Lê a base e aplica a limpeza descrita no relatório."""
    d = pd.read_csv(caminho)
    n0 = len(d)
    # escolas com 0% de aprovação são prováveis erros de registro
    zero = (d.aprovacao_anos_finais_pct == 0) | (d.aprovacao_anos_iniciais_pct == 0)
    # a rede federal tem uma única escola: não há como aprender um padrão para ela
    federal = d.dependencia_administrativa == "Federal"
    d = d[~zero & ~federal].copy()
    print(f"Base: {n0} escolas | removidas {zero.sum()} com 0% e {federal.sum()} federal | restam {len(d)}")
    return d


def preparar_atributos(d):
    """Transforma as colunas da base nas entradas numéricas do modelo."""
    n_mun = d.groupby("codigo_municipio").codigo_escola.transform("count")
    X = pd.DataFrame({
        "rede_municipal": (d.dependencia_administrativa == "Municipal").astype(int),
        "rede_privada": (d.dependencia_administrativa == "Privada").astype(int),
        "rural": (d.localizacao == "Rural").astype(int),
        "oferece_anos_iniciais": d.aprovacao_anos_iniciais_pct.notna().astype(int),
        "aprov_anos_iniciais": d.aprovacao_anos_iniciais_pct.fillna(-1),
        "oferece_ensino_medio": d.aprovacao_ensino_medio_pct.notna().astype(int),
        "aprov_ensino_medio": d.aprovacao_ensino_medio_pct.fillna(-1),
        "escolas_no_municipio": n_mun,
    }, index=d.index)
    y = d.aprovacao_anos_finais_pct
    return X, y


def metricas(y, p):
    """MAE, RMSE, R² e o erro só nas escolas abaixo de 95%."""
    y, p = np.asarray(y), np.asarray(p)
    crit = y < LIMIAR_CRITICO
    return {
        "MAE": mean_absolute_error(y, p),
        "RMSE": float(np.sqrt(mean_squared_error(y, p))),
        "R2": r2_score(y, p),
        "MAE_abaixo_95": mean_absolute_error(y[crit], p[crit]),
        "escolas_abaixo_95": int(crit.sum()),
    }


def busca_arvore(semente=SEMENTE):
    """Árvore com profundidade e mínimo por folha escolhidos por validação cruzada."""
    return GridSearchCV(
        DecisionTreeRegressor(random_state=semente), GRADE,
        cv=KFold(5, shuffle=True, random_state=semente),
        scoring="neg_mean_squared_error",
    )


def desenhar_arvore(arvore, nomes, ax):
    """Desenha a árvore em tons de azul: quanto menor a taxa estimada, mais escuro."""
    plot_tree(arvore, feature_names=nomes, filled=False, impurity=False,
                    rounded=True, precision=1, fontsize=9, ax=ax)
    import re
    valores = arvore.tree_.value.ravel()
    lo, hi = valores.min(), valores.max()
    cmap = plt.get_cmap("Blues")
    for no in ax.texts:
        texto = no.get_text()
        m = re.search(r"value = ([\d.]+)", texto)
        caixa = no.get_bbox_patch()
        if m and caixa is not None:
            v = float(m.group(1))
            caixa.set_facecolor(cmap(0.12 + 0.55 * (hi - v) / (hi - lo)))
        no.set_text(texto.replace("samples", "escolas").replace("value", "taxa estimada")
                    .replace("True", "sim").replace("False", "não"))
    ax.set_title("Árvore simplificada (profundidade 3): à esquerda de cada pergunta = sim")


def main():
    SAIDAS.mkdir(exist_ok=True)
    d = carregar_dados()
    X, y = preparar_atributos(d)

    # 1) divisão 80% treino / 20% teste, mantendo a proporção de cada rede
    Xtr, Xte, ytr, yte = train_test_split(
        X, y, test_size=0.2, random_state=SEMENTE, stratify=d.dependencia_administrativa)

    modelos = {
        "Sempre 100%": np.full(len(yte), 100.0),
        "Média do treino": np.full(len(yte), ytr.mean()),
        "Regressão linear": np.clip(LinearRegression().fit(Xtr, ytr).predict(Xte), 0, 100),
    }
    busca = busca_arvore().fit(Xtr, ytr)
    arvore = busca.best_estimator_
    modelos["Árvore de decisão"] = arvore.predict(Xte)
    print("Melhores parâmetros da árvore:", busca.best_params_)

    tab_teste = pd.DataFrame({k: metricas(yte, p) for k, p in modelos.items()}).T
    print("\nResultados no conjunto de teste (20%):\n", tab_teste.round(2))

    # 2) validação cruzada aninhada: cada escola é prevista por um modelo que não a viu
    cv = KFold(5, shuffle=True, random_state=SEMENTE)
    oof = {
        "Sempre 100%": np.full(len(y), 100.0),
        "Média do treino": cross_val_predict(DecisionTreeRegressor(max_depth=1, min_samples_leaf=len(y)), X, y, cv=cv),
        "Regressão linear": np.clip(cross_val_predict(LinearRegression(), X, y, cv=cv), 0, 100),
        "Árvore de decisão": cross_val_predict(busca_arvore(), X, y, cv=cv),
    }
    tab_cv = pd.DataFrame({k: metricas(y, p) for k, p in oof.items()}).T
    print("\nResultados na validação cruzada (todas as escolas):\n", tab_cv.round(2))
    pd.concat({"teste_20pct": tab_teste, "validacao_cruzada": tab_cv}).round(3).to_csv(SAIDAS / "metricas.csv")

    # 3) resíduos e lista de alertas (previsões fora da amostra)
    res = pd.DataFrame({
        "codigo_escola": d.codigo_escola, "escola": d.escola, "municipio": d.municipio,
        "rede": d.dependencia_administrativa, "localizacao": d.localizacao,
        "taxa_real": y, "taxa_estimada": oof["Árvore de decisão"].round(1),
    })
    res["residuo"] = (res.taxa_real - res.taxa_estimada).round(1)
    alertas = res[res.residuo <= LIMIAR_ALERTA].sort_values("residuo")
    alertas.to_csv(SAIDAS / "escolas_em_alerta.csv", index=False)
    print(f"\nEscolas em alerta (resíduo <= {LIMIAR_ALERTA}): {len(alertas)}")
    print(alertas.head(10).to_string(index=False))

    # 4) modelo final com todas as escolas, regras e importância dos atributos
    final = busca_arvore().fit(X, y).best_estimator_
    (SAIDAS / "regras_arvore.txt").write_text(
        export_text(final, feature_names=list(X.columns), decimals=1), encoding="utf-8")
    imp = pd.Series(final.feature_importances_, index=X.columns).sort_values()

    # 5) gráficos
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.barh(imp.index, imp.values, color=[AZUL if v == imp.max() else AZUL_CLARO for v in imp.values])
    ax.set_title("Importância dos atributos na árvore final")
    ax.set_xlabel("Importância")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout(); fig.savefig(SAIDAS / "importancia_atributos.png", dpi=150); plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 4.5))
    t = tab_cv["MAE_abaixo_95"]
    ax.bar(t.index, t.values, color=[AZUL if k == "Árvore de decisão" else CINZA for k in t.index])
    for i, v in enumerate(t.values):
        ax.text(i, v + 0.15, f"{v:.1f}", ha="center")
    ax.set_title("Erro médio nas escolas abaixo de 95% (pontos percentuais)")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout(); fig.savefig(SAIDAS / "comparacao_modelos.png", dpi=150); plt.close(fig)

    simples = DecisionTreeRegressor(max_depth=3, min_samples_leaf=30, random_state=SEMENTE).fit(X, y)
    fig, ax = plt.subplots(figsize=(16, 7))
    desenhar_arvore(simples, list(X.columns), ax)
    fig.tight_layout(); fig.savefig(SAIDAS / "arvore_simplificada.png", dpi=130); plt.close(fig)
    print(f"\nArquivos gerados em {SAIDAS}")


if __name__ == "__main__":
    main()
