# California Public Schools Data Dictionary

## Source

- Publisher: California Department of Education
- Dataset: Public Schools and Districts Data Files
- Raw snapshot: `data/raw/cde/public_schools/public_schools_2026-10-16.txt`

## Snapshot summary

- Source rows: **18,409**
- Source columns: **46**
- Unique `CDSCode`: **18,409**
- Active school rows after removing `School = No Data`: **10,537**
- Active school rows with valid coordinates: **10,537**
- Active rows with source city `San Jose`: **214**
- Active schools spatially inside the neighborhood polygons: **220**

## Field inventory

| Source field | Proposed database field | Source type | Missing % | Unique non-missing |
|---|---|---:|---:|---:|
| `CDSCode` | `cds_code` | `object` | 0.00% | 18409 |
| `NCESDist` | `nces_district_id` | `object` | 5.54% | 1184 |
| `NCESSchool` | `nces_school_id` | `object` | 26.72% | 13111 |
| `StatusType` | `status_type` | `object` | 0.00% | 4 |
| `County` | `county_name` | `object` | 0.00% | 58 |
| `District` | `district_name` | `object` | 0.00% | 1409 |
| `School` | `school_name` | `object` | 7.57% | 14586 |
| `Street` | `street` | `object` | 1.56% | 13994 |
| `StreetAbr` | `street_abbreviated` | `object` | 1.56% | 14039 |
| `City` | `city` | `object` | 1.56% | 1147 |
| `Zip` | `zip_code` | `object` | 1.56% | 11479 |
| `State` | `state` | `object` | 1.56% | 1 |
| `MailStreet` | `mail_street` | `object` | 1.56% | 12838 |
| `MailStrAbr` | `mail_street_abbreviated` | `object` | 1.56% | 12878 |
| `MailCity` | `mail_city` | `object` | 1.56% | 1113 |
| `MailZip` | `mail_zip_code` | `object` | 1.56% | 10534 |
| `MailState` | `mail_state` | `object` | 1.56% | 1 |
| `Phone` | `phone` | `object` | 37.01% | 10511 |
| `Ext` | `phone_extension` | `object` | 96.48% | 488 |
| `FaxNumber` | `fax_number` | `object` | 41.58% | 9828 |
| `WebSite` | `website` | `object` | 44.08% | 6418 |
| `OpenDate` | `open_date` | `object` | 7.57% | 1711 |
| `ClosedDate` | `closed_date` | `object` | 64.83% | 1104 |
| `Charter` | `charter_code` | `object` | 7.57% | 2 |
| `CharterNum` | `charter_number` | `object` | 88.85% | 1997 |
| `FundingType` | `funding_type` | `object` | 92.39% | 3 |
| `DOC` | `district_ownership_code` | `object` | 0.00% | 11 |
| `DOCType` | `district_ownership_type` | `object` | 0.00% | 11 |
| `SOC` | `school_ownership_code` | `object` | 7.57% | 20 |
| `SOCType` | `school_ownership_type` | `object` | 7.57% | 20 |
| `EdOpsCode` | `education_option_code` | `object` | 30.82% | 14 |
| `EdOpsName` | `education_option_name` | `object` | 30.82% | 14 |
| `EILCode` | `education_level_code` | `object` | 7.57% | 7 |
| `EILName` | `education_level_name` | `object` | 7.57% | 7 |
| `GSoffered` | `grades_offered` | `object` | 21.04% | 94 |
| `GSserved` | `grades_served` | `object` | 31.16% | 85 |
| `Virtual` | `virtual_code` | `object` | 37.04% | 5 |
| `Magnet` | `magnet_code` | `object` | 38.48% | 2 |
| `YearRoundYN` | `year_round_code` | `object` | 7.57% | 2 |
| `FederalDFCDistrictID` | `federal_district_id` | `object` | 94.57% | 999 |
| `Latitude` | `latitude` | `object` | 25.90% | 12224 |
| `Longitude` | `longitude` | `object` | 25.90% | 12033 |
| `AdmFName` | `administrator_first_name` | `object` | 37.05% | 2709 |
| `AdmLName` | `administrator_last_name` | `object` | 37.05% | 6253 |
| `LastUpDate` | `source_last_updated` | `object` | 0.00% | 1769 |
| `Multilingual` | `multilingual_code` | `object` | 43.40% | 2 |

## Transformation rules

- Preserve `CDSCode` as a 14-character string; never parse it as a number.
- Convert the literal `No Data` to SQL `NULL` during the normalized load, while retaining the raw snapshot unchanged.
- Parse `OpenDate`, `ClosedDate`, and `LastUpDate` as dates.
- Build a PostGIS point from numeric longitude and latitude.
- Exclude rows where `School = No Data` from the school entity view because those rows represent district or non-school entities.
- Use `StatusType = Active` for the active-school view, but retain all source rows in staging if historical analysis is desired.
- Administrator names are not required for this project and should be omitted from the curated application view.
