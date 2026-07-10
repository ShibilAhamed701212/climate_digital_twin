# India Meteorological Department Weather Data

## Data Network

The India Meteorological Department operates a network of weather observation stations across Karnataka. Data sources include automatic weather stations (AWS), manual observatories, and rain gauge stations. Karnataka has approximately 150 AWS stations and 200 rain gauge stations providing daily observations. Gridded datasets at 0.25° x 0.25° resolution are available for the period 1981-present.

## Variables

Key observed variables include daily rainfall (mm), maximum temperature (°C), minimum temperature (°C), relative humidity (%), wind speed (km/h), and sunshine hours. Rainfall is measured using tipping bucket rain gauges and weighing bucket gauges. Temperature is measured using platinum resistance thermometers and mercury thermometers at standard screen height (1.5m).

## Data Quality

IMD data undergoes multi-stage quality control including range checks (physical bounds), step checks (temporal consistency), spatial consistency (comparison with neighboring stations), and climatological checks (comparison with historical norms). Data flags indicate quality status: 0=verified, 1=suspect, 2=erroneous. Approximately 2-5% of observations fail quality control and are flagged as suspect or erroneous.

## Data Access

Gridded data is available from the IMD Data Portal (dataportal.imd.gov.in) and the India Water Portal (indiawater.gov.in). Historical archives extend back to 1901 for rainfall and 1951 for temperature. Real-time data has a latency of 24-48 hours for quality-controlled products. Forecast data from GFS and IMD NWP models provides predictions up to 7 days ahead.
