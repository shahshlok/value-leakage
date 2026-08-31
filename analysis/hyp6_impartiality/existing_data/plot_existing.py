"""Render the completed offline H6 diagnostics; no network calls."""
import csv
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

OUT=Path(__file__).resolve().parent


def main():
    rows=list(csv.DictReader((OUT/'direction_comparisons.csv').open()))
    fig,axes=plt.subplots(1,2,figsize=(12.5,6),gridspec_kw={'width_ratios':[1.65,1]})
    ax=axes[0]
    y=np.arange(len(rows))
    values=np.array([float(r['geometric_mean_shift_pct']) for r in rows])
    low=np.array([float(r['ci_low_pct']) for r in rows])
    high=np.array([float(r['ci_high_pct']) for r in rows])
    names=[r['model_dir'].split('_2026')[0]+f"  ({r['n_below']}/{r['n_above']})" for r in rows]
    ax.errorbar(values,y,xerr=[values-low,high-values],fmt='o',color='#21618c',ecolor='#7ba7c6',capsize=3)
    ax.axvline(0,color='#555555',lw=1,ls='--')
    ax.set_yticks(y,names,fontsize=9)
    ax.invert_yaxis()
    ax.set_xlabel('Above-good vs below-good: geometric-mean change (%)')
    ax.set_title('Answer shifts across the 10 selected models',loc='left',fontsize=12)
    ax.grid(axis='x',alpha=.18)
    ax=axes[1]
    q=next(r for r in rows if r['model_dir'].startswith('qwen3.5'))
    counts=[int(q['above_threshold_below_good']),int(q['above_threshold_above_good'])]
    bars=ax.bar(['Below-good','Above-good'],np.array(counts)*2,color=['#777777','#21618c'],width=.55)
    for bar,count in zip(bars,counts):
        ax.text(bar.get_x()+bar.get_width()/2,bar.get_height()+2,f'{count}/50',ha='center',fontsize=12)
    ax.set_ylim(0,100)
    ax.set_ylabel('Answers above the fixed 41M threshold (%)')
    ax.set_title('Qwen 3.5: identical threshold, reversed donation',loc='left',fontsize=11)
    ax.text(.5,.91,'50/50 impartiality-commitment labels\nin each condition',transform=ax.transAxes,ha='center',fontsize=10)
    for ax in axes:
        ax.spines[['top','right']].set_visible(False)
    fig.suptitle('Impartiality commitments coexist with donation-direction answer shifts',fontsize=14,x=.02,ha='left')
    fig.text(.02,.02,'Historical selected cohort. Left: marginal 95% bootstrap intervals; parentheses show usable below/above counts.\nMissing answers and judge errors remain; this is behavioral evidence, not a causal verdict about CoT faithfulness.',fontsize=9)
    fig.tight_layout(rect=[0,.10,1,.93])
    for ext in ('png','svg'):
        fig.savefig(OUT/f'commitments_and_behavior.{ext}',dpi=180,bbox_inches='tight')
    plt.close(fig)
    print('Saved PNG and SVG figures.')


if __name__=='__main__':main()
