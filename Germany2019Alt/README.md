# Germany 2019 Example

Historical simulation of the German day-ahead market in 2019 using 18 competing storage units

## Time Series

| File                        | Description                                                                      | Unit       |
|-----------------------------|----------------------------------------------------------------------------------|------------|
| `biomass_profile.csv`       | Normalized profile of biomass generation                                         | 1          |
| `co2_price.csv`             | Price of CO2 emission allowances                                                 | EUR/t_CO2  |
| `hard_coal_must_run.csv`    | Normalized must-run factor of hard coal power plants                             | 1          |
| `hard_coal_outage.csv`      | Normalized outage factor of hard coal power plants                               | 1          |
| `hard_coal_price.csv`       | Delivery price to power plant per thermal MWH of hard coal                       | EUR/MWh_th |
| `lignite_must_run.csv`      | Normalized must-run factor of lignite power plants                               | 1          |
| `lignite_outage.csv`        | Normalized outage of lignite power plants                                        | 1          |
| `load.csv`                  | Hourly electricity demand to be served                                           | MWh/h      |
| `natural_gas_must_run.csv`  | Normalized must-run factor of natural gas power plants                           | 1          |
| `natural_gas_outage.csv`    | Normalized outage of natural gas power plants                                    | 1          |
| `natural_gas_price.csv`     | Delivery price to power plant per thermal MWH of natural gas                     | EUR/MWh_th |
| `nuclear_outage.csv`        | Normalized outage of nuclear power plants                                        | 1          |
| `nuclear_must_run.csv`      | Normalized must-run factor of nuclear power plants                               | 1          |
| `oil_price.csv`             | Delivery price to power plant per thermal MWH of oil                             | EUR/MWh_th |
| `other_res_profile.csv`     | Normalized profile of generation for power plants declared as "other renewables" | 1          |
| `run_of_river_profile.csv`  | Normalized profile of generation for run-of-river power plants                   | 1          |
| `solar_profile.csv`         | Normalized profile of generation for PV power plants                             | 1          |
| `wind_offshore_profile.csv` | Normalized profile of generation for off-shore wind power plants                 | 1          |
| `wind_onshore_profile.csv`  | Normalized profile of generation for on-shore wind power plants                  | 1          |
