// =====================================================================================
// Coastal habitat layers for the AOI (corals, seagrass, mangroves) - Google Earth Engine
// Southern Belize (SEASTRONG)
// -------------------------------------------------------------------------------------
// Exports to Google Drive (UTM 16N):
//   1. ACA_benthic     Allen Coral Atlas v2.0 benthic habitat, 5 m, UInt8 (0 = unmapped)
//        11 Sand | 12 Rubble | 13 Rock | 14 Seagrass | 15 Coral/Algae | 18 Microalgal Mats
//   2. ACA_geomorphic  Allen Coral Atlas v2.0 geomorphic zonation, 5 m, UInt8 (0 = unmapped)
//        11 Shallow Lagoon | 12 Deep Lagoon | 13 Inner Reef Flat | 14 Outer Reef Flat
//        15 Reef Crest | 16 Terrestrial Reef Flat | 21 Sheltered Reef Slope | 22 Reef Slope
//        23 Plateau | 24 Back Reef Slope | 25 Patch Reef
//   3. ACA_reef_mask   0 not reef | 1 reef, 5 m
//   4. GMW_v4_2020     Global Mangrove Watch v4.0.19 mangrove extent 2020 (~10 m), 1 = mangrove
//   5. GMW_v4_2020_vec same as polygons (GeoJSON, polygons touching the AOI)
//   6. Mangrove_hmax95 max mangrove canopy height (m), Simard et al. 2019, year ~2000, 30 m
//
// Notes
//   - ACA: PlanetScope 2018-2020, mapped only in the ACA reef extent (shallow, clear water).
//     Seagrass = benthic class 14 there; deeper / turbid seagrass beds may be unmapped (0).
//   - Global seagrass polygons (UNEP-WCMC) are not in Earth Engine: download from
//     UNEP-WCMC Ocean Data Viewer if needed.
//
// Credits / licences
//   Allen Coral Atlas (2020) doi:10.5281/zenodo.3833242, CC BY 4.0
//     (c) 2023 Allen Coral Atlas Partnership and Vulcan, Inc.
//   Global Mangrove Watch: Bunting et al. (2022) Remote Sensing; GMW v4.0, CC BY 4.0
//   Mangrove canopy height: Simard et al. (2019) Nat. Geosci. 12:40-45,
//     doi:10.1038/s41561-018-0279-1, ORNL DAAC doi:10.3334/ORNLDAAC/1665, CC0
//   GMW and Simard layers are from the GEE community catalogue (gee-community-catalog.org).
// =====================================================================================
 
 
// ---------------------------------- SETTINGS -----------------------------------------
var AOI_ASSET    = 'projects/ee-alessiorovere/assets/AOI';  // <-- your asset ID
var CRS          = 'EPSG:32616';   // WGS 84 / UTM zone 16N
var DRIVE_FOLDER = 'GEE_Bathymetry_Inputs';  // create this folder in My Drive BEFORE exporting
var PREFIX       = 'Belize_south';
var EXPORT_ACA = true, EXPORT_GMW = true, EXPORT_GMW_VECTOR = true, EXPORT_CANOPY = true;
// -------------------------------------------------------------------------------------
 
 
var aoiFc = ee.FeatureCollection(AOI_ASSET);
var roi = aoiFc.geometry();
 
// 1-3. Allen Coral Atlas
var aca = ee.Image('ACA/reef_habitat/v2_0');
var benthic    = aca.select('benthic').unmask(0).clip(roi);
var geomorphic = aca.select('geomorphic').unmask(0).clip(roi);
var reefMask   = aca.select('reef_mask').unmask(0).clip(roi);
 
// 4-5. Global Mangrove Watch v4 (2020)
var gmw = ee.ImageCollection('projects/sat-io/open-datasets/GMW/annual-extent/GMW_MNG_2020')
            .filterBounds(roi).mosaic().select(['b1'], ['mangrove']).unmask(0).clip(roi);
var gmwVec = ee.FeatureCollection('projects/sat-io/open-datasets/GMW/annual-extent/GMW_MNG_VEC_2020')
               .filterBounds(roi);
 
// 6. Mangrove maximum canopy height (Simard et al. 2019)
var hmax = ee.ImageCollection('projects/sat-io/open-datasets/global_mangrove_distribution/hmax95')
             .filterBounds(roi).mosaic().select([0], ['hmax95_m']).clip(roi);
 
 
// Quick checks (area in km2 at 30 m, light)
function areaKm2(maskImg) {
  return ee.Image.pixelArea().divide(1e6).updateMask(maskImg).reduceRegion({
    reducer: ee.Reducer.sum(), geometry: roi, scale: 30, maxPixels: 1e10, bestEffort: true,
    tileScale: 4}).values().get(0);
}
print('Seagrass (ACA class 14), km2:', areaKm2(benthic.eq(14)));
print('Coral/Algae (ACA class 15), km2:', areaKm2(benthic.eq(15)));
print('Mangrove (GMW 2020), km2:', areaKm2(gmw.eq(1)));
print('GMW 2020 polygons touching AOI:', gmwVec.size());
 
 
// Map
var benthicVis = {min: 0, max: 18, palette: [
  '000000',                               // 0 unmapped
  '000000','000000','000000','000000','000000','000000','000000','000000','000000','000000',
  'ffffbe',  // 11 Sand
  'e0d05e',  // 12 Rubble
  'b19c3a',  // 13 Rock
  '668438',  // 14 Seagrass
  'ff6161',  // 15 Coral/Algae
  '000000','000000',
  '9bcc4f'   // 18 Microalgal Mats
]};
Map.centerObject(roi, 11);
Map.addLayer(benthic.selfMask(), benthicVis, 'ACA benthic (seagrass = dark green, coral = red)');
Map.addLayer(geomorphic.selfMask().randomVisualizer(), {}, 'ACA geomorphic (random colours)', false);
Map.addLayer(gmw.selfMask(), {palette: ['228B22']}, 'Mangroves GMW 2020');
Map.addLayer(hmax, {min: 0, max: 25, palette: ['ffffcc','a1dab4','41b6c4','2c7fb8','253494']},
             'Mangrove max canopy height (m, ~2000)', false);
Map.addLayer(ee.Image().paint(aoiFc, 0, 2), {palette: ['ff00ff']}, 'AOI');
 
 
// Exports
function exportClass(img, name, scale) {
  Export.image.toDrive({
    image: img.toUint8(), description: PREFIX + '_' + name,
    folder: DRIVE_FOLDER, region: roi, scale: scale, crs: CRS, maxPixels: 1e13,
    formatOptions: {cloudOptimized: true}
  });
}
if (EXPORT_ACA) {
  exportClass(benthic,    'ACA_v2_benthic_5m',    5);
  exportClass(geomorphic, 'ACA_v2_geomorphic_5m', 5);
  exportClass(reefMask,   'ACA_v2_reef_mask_5m',  5);
}
if (EXPORT_GMW) {
  exportClass(gmw, 'GMW_v4_mangrove_2020_10m', 10);
}
if (EXPORT_GMW_VECTOR) {
  Export.table.toDrive({collection: gmwVec, description: PREFIX + '_GMW_v4_mangrove_2020_polygons',
                        folder: DRIVE_FOLDER, fileFormat: 'GeoJSON'});
}
if (EXPORT_CANOPY) {
  Export.image.toDrive({
    image: hmax.unmask(-9999).toFloat(), description: PREFIX + '_Mangrove_hmax95_Simard2019_30m',
    folder: DRIVE_FOLDER, region: roi, scale: 30, crs: CRS, maxPixels: 1e13,
    formatOptions: {cloudOptimized: true, noData: -9999}   // remove noData if GEE complains
  });
}