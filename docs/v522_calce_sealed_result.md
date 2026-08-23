# V52.2 CALCE sealed result

## Verdict

The real-data experiment completed, but the frozen program failed the preregistered sealed criterion. No breakthrough or human-unknown law is claimed.

- Program commitment Git commit: `4e9e523`
- Sealed archive: `SOC_20-80_2C.zip`
- Sealed archive SHA-256: `3cdf036cb08df1663ee1ad5c8353fc7e37aae0e1579b76e3e57b3170d2a4a668`
- Sealed cells: 2
- Sealed diagnostic observations: 56
- Parameter refit after sealed access: none

## Frozen anonymous program

```text
response_hat = 1
  - 0.141097440053 * index
  - 0.671259934756 * square_throughput * control_1
  - 0.117593202900 * square_throughput * control_2
```

The program was selected from 6,675 behaviorally distinct candidates over 35 anonymous atoms. Its leave-one-protocol-group-out development RMSE was 0.0436627.

## Sealed prediction

| Metric | Current-time capacity | Logger capacity crosscheck |
|---|---:|---:|
| Frozen program RMSE | 0.0307446 | 0.0312242 |
| Last-observation baseline RMSE | 0.0106226 | 0.0106964 |
| Error ratio | 2.8943 | 2.9191 |
| Required ratio | < 0.80 | < 0.80 |

Both capacity channels independently produce the same failure. The parser crosscheck therefore preserves the scientific conclusion.

## Bounded relation recovered after unsealing

At a common equivalent-throughput coordinate, the matched 2C groups retained less normalized capacity than the corresponding C/2 groups in all three SOC windows:

| SOC window | 2C minus C/2 normalized capacity |
|---|---:|
| 40–60% | -0.00534 |
| 20–80% | -0.08597 |
| 0–100% | -0.21394 |

The direction is consistent and the magnitude grows with window width. This is an experimental total-effect pattern inside two graphite/LiCoO2 cells per condition. It does not separate current-density effects from internal heating.

## Prior-art audit

The pattern is not scientifically novel. CALCE's 2016 article on these pouch-cell experiments reports that mean SOC, change in SOC, and discharge rate all significantly affect capacity loss. The official experiment catalog also identifies the cell chemistry, assigned SOC windows, and C/2 versus 2C protocols.

- Official article: https://web.calce.umd.edu/articles/abstracts/2016/16_cycle_life_testing_modeling_li-ion_battery_different_SOC_ranges.html
- Official dataset catalog: https://calce.umd.edu/data

## What the failure teaches the architecture

The global three-term program beats the registered static linear and quadratic models on the sealed group, but it does not beat the online last-observation baseline. The missing capability is not a larger formula library. The next architecture must combine a transferable population mechanism with a persistent per-system latent state, calibrated uncertainty, and horizon-matched forecasting. Until that model beats the online baseline on a new sealed experiment, autonomous representation creation remains 9/10, causal mechanism reasoning remains 9/10, and human-unknown-law discovery remains 3/10.
