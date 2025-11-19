# install.packages(c("sf", "ggplot2"))  # if needed

library(sf)
library(ggplot2)
library(tidyverse)

# 1) Set the URL to the layer (1 = "Catch Record Card Area")
base_url <- "https://geodataservices.wdfw.wa.gov/arcgis/rest/services/FP_Projects/CatchRecordCardArea/MapServer"

# 2) Build a query URL to pull everything as GeoJSON
query_url <- paste0(
  base_url,
  "/query?",
  "where=1=1&",        # no filter, grab all features
  "outFields=*&",      # all attributes
  "f=geojson&",        # GeoJSON output
  "outSR=2927"         # keep in source coord system (WA state plane feet)
)

# 3) Read into sf
#crc <- st_read(base_url, quiet = FALSE)
crc <- st_read("CRC.gdb.zip", quiet = FALSE)

# Optional: set CRS if not picked up
st_crs(crc) <- 2927

ggplot(crc) +
  geom_sf() +
  geom_sf_text(aes(label=CatchRecordCode),size=2)+
  theme_minimal() +
  labs(
    title = "Catch Record Card Areas",
    x="long",
    y="lat"
  )

crc%>%
  distinct(CatchRecordCode)%>%
  arrange(CatchRecordCode)



# 4) Simple static map with ggplot2
crc_ll <- st_transform(crc, 4326)

# Bounding box
lon_min <- -123
lon_max <- -122
lat_min <- 47.2
lat_max <- 46.7

ggplot(crc_ll) +
  geom_sf(fill = "steelblue", alpha = 0.4, color = "black", size = 0.2) +
  coord_sf(
    xlim = c(lon_min, lon_max),
    ylim = c(lat_min, lat_max),
    expand = FALSE
  ) +
  geom_sf_text(aes(label=CatchRecordCode),size=2)+
  theme_minimal() +
  labs(
    y="lat",
    x="long",
    title = "Catch Record Card Areas"
  )
