# Kenya location reference data

These JSON files provide the county, constituency, and county assembly ward
choices used by farmer profile and registration flows.

- Source: [nicanor-korir/kenya-regions](https://github.com/nicanor-korir/kenya-regions)
- The source repository identifies its code/data package as MIT licensed and
  describes the county, constituency, and ward hierarchy as based on IEBC
  records, with geographic references compiled from sources including OCHA.
- Counts in this snapshot: 47 counties, 290 constituencies, and 1,450 wards.
- County and constituency centroids are approximate lookup coordinates. They
  are a fallback for weather and environmental services, not farm locations.
  A farmer's web map pin takes precedence when available.
- The common “sub-county” field in the app uses electoral constituencies for
  selection. Constituencies and national-government sub-counties are not always
  the same units. This snapshot does not include sub-locations because their
  boundaries and names are older and less consistently maintained.

Refresh the snapshot from the source and review the hierarchy/counts before
updating these files. Run the database migration before running the seed command.
