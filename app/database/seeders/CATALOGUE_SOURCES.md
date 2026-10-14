# Catalogue seed sources and data policy

The starter records in `catalogue.py` were compiled on 2026-10-14 from public sources:

- KEPHIS, [National Crop Variety List 2025](https://www.kephis.go.ke/sites/default/files/2025-02/NATIONAL%20CROP%20VARIETY%20LIST-%202025%20EDITION.pdf): Kenyan registered variety names, altitude, maturity and stated agronomic attributes.
- KALRO, [maize agronomy](https://www.kalro.org/maize/maize-agronomy/) and [sorghum varieties](https://www.kalro.org/divisions/crops/sorghum/): regional suitability and drought/maturity notes.
- KALRO, [bean production guidance](https://kalroerepository.kalro.org/bitstreams/90823533-117d-42c4-ac0f-5b42646202b7/download): bean variety adaptation and attributes.
- Agricultural Development Corporation, [sheep and goats](https://adc.go.ke/goats-and-sheep/) and KALRO [research-centre report](https://kalroerepository.kalro.org/bitstreams/8d6f3ef8-7be0-4a84-b613-f6b15f0cee0d/download): named Kenyan livestock breeds and regional production context.
- Veterinary Medicine Directorate, [authorized retailer directory](https://www.vmd.go.ke/retailers): agrovet/vendor names and published location strings. The directory may change; `source_checked_on` is the date checked.
- MavunoVet, [online shop](https://mavunovet.co.ke/shop.html): two displayed maize-seed prices and published Eldoret address/contact/hours. Prices are observations from the check date, not guaranteed quotes; stock is not shown and is left unknown.
- Nakuru County market study, [market list and coordinates](https://cdn.unisg.it/assets/FontefrancescoZocchi_2020_Indigenous-crops-and-cultural-dynamics-in-the-markets-of-Nakuru-County-Kenya.pdf), and OpenStreetMap records for [Nairobi Wakulima](https://www.openstreetmap.org/way/125300906) and [Kisumu Kibuye](https://www.openstreetmap.org/way/262027048).
- Kenya Trade Portal, [wholesale and retail markets](https://kenyatradeportal.go.ke/wholesale-retail-markets): Nairobi Wakulima Market ward/location and all-week trading days.

Unknown values are intentionally NULL. In particular, rainfall bounds are only recorded when a source gives a defensible numeric range; breed altitude/rainfall/maturity values, most vendor phone/hours/precise coordinates, and product stock are not inferred. Vendor product price is a dated public listing snapshot, not a live quote. The VMD source establishes retailer authorization, not each outlet's seed/feed inventory.
