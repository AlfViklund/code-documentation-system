
## docify Workflow
This project uses docify for feature documentation and staleness checking. Please follow these guidelines:
1. Run `docify check` to see if any feature documentation is stale.
2. When modifying code linked to a feature, update its documentation in `docs/features/<feature-id>.md`.
3. After updating, run `docify mark-updated <feature-id>` to acknowledge and reset its staleness status.
