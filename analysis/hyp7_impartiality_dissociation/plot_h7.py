"""Scientific H7 figures derived only from the saved numeric tables."""
import csv

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from prepare_h7 import OUT


def contrast_row(all_rows, dataset, tier, model, stratum):
    return next(r for r in all_rows if r['dataset'] == dataset and r['tier'] == tier
                and r['model_dir'] == model and r['metric'] == 'log' and r['stratum'] == stratum)


def plot_contrast_point(ax, row, y, offset, color, marker, label=None):
    point = float(row['geometric_shift_pct'])
    if row['geometric_ci95_low_pct']:
        low, high = float(row['geometric_ci95_low_pct']), float(row['geometric_ci95_high_pct'])
        ax.errorbar(point, y + offset, xerr=[[point - low], [high - point]], fmt=marker, color=color,
                    capsize=2, label=label)
    else:
        ax.plot(point, y + offset, marker='D', markerfacecolor='none', color=color, linestyle='none')
        ax.plot(point, y + offset, marker=marker, markersize=3, color='#000000', linestyle='none')


def main():
    all_rows = list(csv.DictReader((OUT / 'contrasts.csv').open()))
    rows = [r for r in all_rows if r['dataset'] == 'h6_corrected']
    all_differences = list(csv.DictReader((OUT / 'paired_differences.csv').open()))
    differences = [r for r in all_differences if r['dataset'] == 'h6_corrected']
    models = sorted({r['model_dir'] for r in rows if r['tier'] == 'per_model'})
    sensitivity = [
        ('h6_excluding_confirmed_audited_disclosures', 'Excl. 8 confirmed disclosures'),
        ('h6_excluding_confirmed_or_uncertain_audited_disclosures', 'Excl. 18 confirmed/uncertain'),
    ]
    model_labels = [m.rsplit('_', 2)[0] for m in models]
    labels = model_labels + ['PRIMARY: equal-weight 9 models'] + [name for _, name in sensitivity]
    plt.rcParams.update({'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False})
    fig, axes = plt.subplots(1, 2, figsize=(13.5, 8.2), sharey=True, gridspec_kw={'width_ratios': [1.25, 1]})
    strata_style = [
        ('all', -.12, '#0072B2', 'o', 'All usable answers'),
        ('positive', .12, '#E69F00', 's', 'Claim-positive answers'),
    ]
    primary_idx = len(models)
    for i, model in enumerate(models + ['']):
        tier = 'per_model' if model else 'primary_9'
        for stratum, offset, color, marker, name in strata_style:
            row = contrast_row(all_rows if not model else rows, 'h6_corrected', tier, model, stratum)
            plot_contrast_point(axes[0], row, i, offset, color, marker, name if i == 0 else None)
        dtier = f'model:{model}' if model else 'primary_9'
        row = next(r for r in differences if r['tier'] == dtier and r['metric'] == 'log' and r['comparison'] == 'positive_minus_all')
        p = 100 * float(row['estimate'])
        if row['ci95_low']:
            lo, hi = [100 * float(row[k]) for k in ('ci95_low', 'ci95_high')]
            axes[1].errorbar(p, i, xerr=[[p-lo], [hi-p]], fmt='o', color='#000000', capsize=2)
        else:
            axes[1].plot(p, i, marker='D', markerfacecolor='none', color='#000000')
    for j, (dataset, _) in enumerate(sensitivity):
        i = primary_idx + 1 + j
        for stratum, offset, color, marker, _ in strata_style:
            row = contrast_row(all_rows, dataset, 'primary_9', '', stratum)
            plot_contrast_point(axes[0], row, i, offset, color, marker)
        row = next((r for r in all_differences if r['dataset'] == dataset and r['tier'] == 'primary_9'
                     and r['metric'] == 'log' and r['comparison'] == 'positive_minus_all'), None)
        if row:
            p = 100 * float(row['estimate'])
            if row['ci95_low']:
                lo, hi = [100 * float(row[k]) for k in ('ci95_low', 'ci95_high')]
                axes[1].errorbar(p, i, xerr=[[p-lo], [hi-p]], fmt='o', color='#000000', capsize=2)
            else:
                axes[1].plot(p, i, marker='D', markerfacecolor='none', color='#000000')
    axes[0].set_yticks(range(len(labels)), labels)
    axes[0].invert_yaxis()
    axes[0].set_xlabel('Above-good / below-good geometric mean − 1 (%)')
    axes[1].set_xlabel('Claim-positive minus all contrast (100 × log units)')
    axes[0].set_title('Condition contrast persists in claim-positive traces')
    axes[1].set_title('Paired change after filtering on the claim')
    for ax in axes:
        ax.axvline(0, color='#000000', alpha=.55, lw=1, ls='--')
        ax.axhline(len(models) - .5, color='#000000', alpha=.15, lw=1)
        ax.axhline(primary_idx + .5, color='#000000', alpha=.15, lw=1, ls=':')
        ax.grid(axis='x', color='#000000', alpha=.15)
    axes[0].legend(loc='lower right', frameon=False, fontsize=9)
    fig.suptitle('H7 · Impartiality language and incentive sensitivity', fontsize=15)
    fig.text(.02, .02, '10,000 paired within-cell record bootstraps; marginal 95% intervals. Hollow diamonds: CI withheld after empty bootstrap cells.\nPrimary excludes DeepSeek Pro; Claude text is a summary. Observational filtering, not causal moderation; no equivalence margin.', fontsize=9, color='#000000')
    fig.tight_layout(rect=[0, .075, 1, .94])
    for ext in ('png', 'svg'):
        fig.savefig(OUT / f'forest_contrasts.{ext}', dpi=180)
    plt.close(fig)
    rates = list(csv.DictReader((OUT / 'threshold_rates.csv').open()))
    rates = [r for r in rates if r['dataset'] == 'h6_corrected']
    fig, axes = plt.subplots(1, 2, figsize=(12, 6.6), sharey=True)
    for ax, stratum, title in zip(axes, ('all', 'positive'), ('All usable answers', 'Claim-positive answers')):
        for i, model in enumerate(models):
            pair = {c: float(next(r for r in rates if r['model_dir'] == model and r['condition'] == c and r['stratum'] == stratum)['above_threshold_rate']) * 100 for c in ('below_good', 'above_good')}
            ax.plot(list(pair.values()), [i, i], color='#000000', alpha=.3, lw=2)
            ax.scatter(pair['below_good'], i, color='#0072B2', marker='o',
                       label='Below-good condition' if i == 0 else None)
            ax.scatter(pair['above_good'], i, color='#E69F00', marker='^',
                       label='Above-good condition' if i == 0 else None)
        ax.set_xlim(-3, 103)
        ax.set_xlabel('Answers strictly above the same model threshold (%)')
        ax.set_title(title)
        ax.grid(axis='x', color='#000000', alpha=.15)
    axes[0].set_yticks(range(len(models)), model_labels)
    axes[0].invert_yaxis()
    axes[1].legend(loc='lower right', frameon=False, fontsize=9)
    fig.suptitle('H7 · Threshold crossing by incentive direction', fontsize=15)
    fig.text(.02, .02, 'Same binary outcome in both arms; equality is below. Descriptive observed-answer rates; missing-Y bounds are in missing_y_bounds.csv.', fontsize=9)
    fig.tight_layout(rect=[0, .05, 1, .94])
    for ext in ('png', 'svg'):
        fig.savefig(OUT / f'crossing_rate_dumbbell.{ext}', dpi=180)
    plt.close(fig)


if __name__ == '__main__':
    main()
