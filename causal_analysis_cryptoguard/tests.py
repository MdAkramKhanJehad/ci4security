
import numpy as np
import pandas as pd
import scipy.stats as stats
import statsmodels.api as sm
import statsmodels.formula.api as smf
from scipy.stats import mannwhitneyu, kruskal
from scipy.stats import spearmanr



ALPHA = 0.05


def kruskal_test_continuous_by_groups(df, group_col, continuous_col):
    groups = [g[continuous_col].values for _, g in df.groupby(group_col)]
    H, p = kruskal(*groups)
    print(f"\n{group_col} -> {continuous_col} (Kruskal–Wallis)")
    print(f"H = {H:.3f}, p = {p:.4f}")
    print("Edge is not rejected (p < 0.05)" if p < ALPHA else "Edge is rejected (p >= 0.05)")
    return H, p


def logistic_regression_numeric_to_binary(df, numeric_col, binary_col):
    X = sm.add_constant(df[numeric_col])
    y = df[binary_col]
    model = sm.Logit(y, X).fit(disp=False)
    p = float(model.pvalues[numeric_col])
    coef = float(model.params[numeric_col])
    print(f"\n{numeric_col} -> {binary_col} (Logistic regression)")
    print(f"coef = {coef:.4f}, p = {p:.4f}")
    print("Edge is not rejected (p < 0.05)" if p < ALPHA else "Edge is rejected (p >= 0.05)")
    return model


def logistic_regression_binary_to_binary(df, binary_treatment, binary_outcome):
    X = sm.add_constant(df[binary_treatment])
    y = df[binary_outcome]
    model = sm.Logit(y, X).fit(disp=False)
    p = float(model.pvalues[binary_treatment])
    coef = float(model.params[binary_treatment])
    print(f"\n{binary_treatment} -> {binary_outcome} (Logistic regression)")
    print(f"coef = {coef:.4f}, p = {p:.4f}")
    print("Edge is not rejected (p < 0.05)" if p < ALPHA else "Edge is rejected (p >= 0.05)")
    return model


def chi_square_test_cat_to_binary(df, cat_col, binary_col):
    table = pd.crosstab(df[cat_col], df[binary_col])
    chi2, p, dof, _ = stats.chi2_contingency(table)
    print(f"\n{cat_col} -> {binary_col} (Chi-square)")
    print(f"chi2 = {chi2:.3f}, dof = {dof}, p = {p:.4f}")
    print("Edge is not rejected (p < 0.05)" if p < ALPHA else "Edge is rejected (p >= 0.05)")
    return chi2, p


def mann_whitney_test(df, numeric_col, binary_col):
    g0 = df[df[binary_col] == 0][numeric_col]
    g1 = df[df[binary_col] == 1][numeric_col]
    U, p = mannwhitneyu(g0, g1, alternative="two-sided")
    print(f"\n{numeric_col} -> {binary_col} (Mann–Whitney U)")
    print(f"U = {U:.3f}, p = {p:.4f}")
    print("Edge is not rejected (p < 0.05)" if p < ALPHA else "Edge is rejected (p >= 0.05)")
    return U, p


def correlation_test_treatment_to_outcome(df):
    rho, p = spearmanr( df["combined"], df["verdict"])
    print(f"\n\ncombined -> verdict (Spearman)")
    print(f"rho = {rho:.4f}, p = {p:.4f}")

