# install.packages(c("sf", "ggplot2", "ggspatial"))  # if needed

library(sf)
library(ggplot2)
library(tidyverse)
library(ggspatial)

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
    title = "Washington Catch Record Card Areas",
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

# 5) read in .csv with CRCs with creel from MS Forms survey

crc_creel <- read_csv("crc_areas_creeled.csv") |> 
  mutate(catch_area_code = as.character(catch_area_code)) |> 
  distinct(data_source, catch_area_code) |> # collapse rows to distinct CRCs with either salmon or steelhead creel in 2023-24
  rename(CatchRecordCode = catch_area_code)

# 6) join CRCs with creel to spatial CRC layer

crc <- crc |> 
  left_join(crc_creel, by = "CatchRecordCode") |> 
  rename(Coverage = data_source) |> 
  mutate(Coverage = replace_na(Coverage, "No creel"))

# 7) plot again with creel mapping and base layer

ggplot() +
  annotation_map_tile(type = "cartolight", zoomin = 1, progress = "none") +
  geom_sf(data = crc, aes(fill = Coverage), alpha = 0.65, color = "gray20", size = 0.3) +
  coord_sf(xlim = c(600000, 2550000), ylim = c(80000, 1350000), crs = 2927) +
  theme_minimal() +
  theme(
    plot.caption = element_text(hjust = 0, size = 8)
  ) +
  labs(
    title = "Washington Catch Record Card Areas",
    x = "long",
    y = "lat",
    caption = str_wrap("Assessment of Catch Record Card Areas with creel coverage based on a survey of WDFW salmon and steelhead creel programs for the 2023-24 fishing year. This map is not exhaustive of all creel surveys conducted statewide.", width = 80)
  )

# 8) export map 

ggsave("crc_coverage_map.png", 
       plot = ggplot() +
         annotation_map_tile(type = "cartolight", zoomin = 1, progress = "none") +
         geom_sf(data = crc, aes(fill = Coverage), alpha = 0.65, color = "gray20", size = 0.3) +
         coord_sf(xlim = c(600000, 2550000), ylim = c(80000, 1350000), crs = 2927) +
         theme_minimal() +
         theme(
           plot.caption = element_text(hjust = 0, size = 8)
         ) +
         labs(
           title = "Washington Catch Record Card Areas",
           x = "long",
           y = "lat",
           caption = str_wrap("Assessment of Catch Record Card Areas with creel coverage based on survey of WDFW salmon and steelhead creel programs for the 2023-24 fishing year. This map is not exhaustive of all creel surveys conducted statewide.", width = 80)
         ), 
       width = 10, height = 8, dpi = 800)
