# D20 Before/After Comparison Summary

## Comparison target

- Initial design: delta closest to 0 mm
- Best design: selected from D19 `best_design.json`
- Current criterion: MTF-only weighted score

## Initial design

- case_index: 5
- delta_mm: -0.2
- actual_thickness_mm: 0.799974567
- mtf_30_avg: 0.424941
- mtf_40_avg: 0.181809
- mtf_50_avg: 0.031166
- final_score: 0.1944913999999999

## Best design

- case_index: 7
- delta_mm: 0.2
- actual_thickness_mm: 1.199974567
- mtf_30_avg: 0.794333
- mtf_40_avg: 0.710434
- mtf_50_avg: 0.6288
- final_score: 0.7029501

## Improvement

- mtf_30_avg_improvement_percent: 86.93%
- mtf_40_avg_improvement_percent: 290.76%
- mtf_50_avg_improvement_percent: 1917.58%
- final_score_improvement_percent: 261.43%

## Note

This before/after comparison is based on the current MTF-only score. A more rigorous optical evaluation should also include RMS Spot, field-dependent metrics, Tangential/Sagittal curves, distortion, and focal length constraints.