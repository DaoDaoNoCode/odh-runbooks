---
name: Runbook bug / incorrect steps
about: A runbook creates resources that don't appear correctly in the dashboard, or Claude can't find a standard fix
labels: runbook-bug
---

## Which runbook?

<!-- e.g. evalhub/create-evaluation-run -->

## RHOAI/ODH version

<!-- e.g. RHOAI 2.16, ODH 3.4.0-ea.1 -->

## What happened?

<!-- What did Claude try? What failed? -->

## Error output

```
<!-- paste the odh run output here, including what Claude said it checked -->
```

## What source_repos were configured?

<!-- Run: odh show <runbook-name> and paste the source_repos section -->

## Did Claude report "CANNOT_FIX"?

- [ ] Yes — Claude said no standard fix was found
- [ ] No — Claude applied a fix but it didn't work / created wrong resources
- [ ] Claude applied a workaround instead of a standard fix

## Suggested fix

<!-- If you know the correct CRD field / label / annotation / GitHub source, include it here.
     Ideally: the exact file/line in the source repo that shows the correct approach. -->
