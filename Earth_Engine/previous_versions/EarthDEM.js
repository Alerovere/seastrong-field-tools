// =====================================================================================
// Copernicus DSM (GLO-30) + FABDEM bare-earth DEM for the AOI - Google Earth Engine
// Southern Belize (SEASTRONG)
// -------------------------------------------------------------------------------------
// Exports (GeoTIFF, Float32, UTM 16N, 30 m, NoData = -9999) to Google Drive:
//   1. DSM   - Copernicus DEM GLO-30 'DEM' band: top surface (mangrove canopy, buildings)
//   2. DEM   - FABDEM: bare-earth version of GLO-30 (trees and buildings removed)
//   3. DSM - DEM: approximate canopy / object height (m)
//   4. WBM   - Copernicus water body mask (0 land, 1 ocean, 2 lake, 3 river)  [UInt8]
//   5. DeltaDTM - coastal bare-earth DTM (Copernicus DEM corrected with ICESat-2 + GEDI lidar,
//                 vegetation/buildings removed; only land < 30 m; best available ground under
//                 mangroves at 30 m; reported MAE ~0.4 m)
// Vertical datum of DSM and DEM: EGM2008 geoid (same as ICESat-2 ATL24 'ortho_h').
//
// Data credits / licences:
//   Copernicus DEM GLO-30: (c) DLR e.V. 2010-2014 and (c) Airbus Defence and Space GmbH
//     2014-2018, provided under COPERNICUS by the European Union and ESA.
//   FABDEM: Hawker et al. (2022), Environ. Res. Lett. 17 024016, CC BY-NC-SA 4.0
//     (non-commercial use). GEE community catalogue: projects/sat-io/open-datasets/FABDEM
//   DeltaDTM: Pronk et al. (2024) Sci. Data 11:273, doi:10.1038/s41597-024-03091-9, CC BY 4.0.
//     GEE community catalogue: projects/sat-io/open-datasets/DELTARES/deltadtm_v1-1
// =====================================================================================
 
 
// ---------------------------------- SETTINGS -----------------------------------------
var AOI_ASSET    = 'projects/ee-alessiorovere/assets/AOI';  // <-- your asset ID
var CRS          = 'EPSG:32616';   // WGS 84 / UTM zone 16N
var SCALE        = 30;             // m (native ~30 m)
var DRIVE_FOLDER = 'GEE_Bathymetry_Inputs';  // create this folder in My Drive BEFORE exporting:
                                              // parallel tasks otherwise each create their own copy
var PREFIX       = 'Belize_south';
// -------------------------------------------------------------------------------------
 
 
var aoiFc = ee.FeatureCollection(AOI_ASSET);
var roi = aoiFc.geometry();
 
// Copernicus GLO-30 (tiles -> mosaic). Heights resampled bilinearly, masks nearest.
var glo30 = ee.ImageCollection('COPERNICUS/DEM/GLO30').filterBounds(roi);
var dsm = glo30.select('DEM')
  .map(function (i) { return i.resample('bilinear'); })
  .mosaic().rename('DSM').clip(roi);
var wbm = glo30.select('WBM').mosaic().rename('WBM').clip(roi);
 
// FABDEM bare-earth DEM
var fab = ee.ImageCollection('projects/sat-io/open-datasets/FABDEM').filterBounds(roi);
var dem = fab.select('b1')
  .map(function (i) { return i.resample('bilinear'); })
  .mosaic().rename('DEM').clip(roi);
 
// DeltaDTM coastal bare-earth DTM (values of 30 = clipped / above 30 m -> masked)
var deltaDtm = ee.Image('projects/sat-io/open-datasets/DELTARES/deltadtm_v1-1').select(0)
  .rename('DeltaDTM').resample('bilinear');
deltaDtm = deltaDtm.updateMask(deltaDtm.neq(30)).clip(roi);
 
// Canopy / object height
var height = dsm.subtract(dem).rename('DSM_minus_DEM');
 
// Quick checks
print('GLO-30 tiles:', glo30.size(), '  FABDEM tiles:', fab.size());
print('Stats over AOI (m): DSM, DEM, DSM-DEM, DeltaDTM', ee.Image.cat(dsm, dem, height, deltaDtm).reduceRegion({
  reducer: ee.Reducer.percentile([2, 50, 98]),
  geometry: roi, scale: 90, maxPixels: 1e9, bestEffort: true, tileScale: 4}));
 
// Map
var elevVis = {min: 0, max: 30, palette: ['08306b','2171b5','6baed6','c7e9c0','74c476','238b45','fdae61','d7191c']};
Map.centerObject(roi, 11);
Map.addLayer(dsm, elevVis, 'DSM (Copernicus GLO-30)');
Map.addLayer(dem, elevVis, 'DEM (FABDEM bare earth)', false);
Map.addLayer(deltaDtm, elevVis, 'DeltaDTM (coastal bare earth, < 30 m)', false);
Map.addLayer(deltaDtm.subtract(dem).updateMask(ee.ImageCollection('projects/sat-io/open-datasets/GMW/annual-extent/GMW_MNG_2020')
               .filterBounds(roi).mosaic().select(0).eq(1)),
             {min: -3, max: 3, palette: ['b2182b','f7f7f7','2166ac']},
             'DeltaDTM - FABDEM inside mangroves (m)', false);
Map.addLayer(height, {min: 0, max: 20, palette: ['ffffcc','a1dab4','41b6c4','2c7fb8','253494']},
             'DSM - DEM (canopy / object height)', false);
Map.addLayer(wbm.selfMask(), {min: 1, max: 3, palette: ['0000ff','00ffff','00ff00']},
             'Water body mask (1 ocean, 2 lake, 3 river)', false);
Map.addLayer(ee.Image().paint(aoiFc, 0, 2), {palette: ['ff00ff']}, 'AOI');
 
// Exports
function exportFloat(img, name) {
  Export.image.toDrive({
    image: img.unmask(-9999).toFloat(),
    description: PREFIX + '_' + name,
    folder: DRIVE_FOLDER, region: roi, scale: SCALE, crs: CRS, maxPixels: 1e13,
    formatOptions: {cloudOptimized: true, noData: -9999}   // remove noData if GEE complains
  });
}
exportFloat(dsm,    'CopDEM_GLO30_DSM_EGM08');
exportFloat(dem,    'FABDEM_DEM_EGM08');
exportFloat(height, 'DSM_minus_DEM');
exportFloat(deltaDtm, 'DeltaDTM_v1-1');
 
Export.image.toDrive({
  image: wbm.unmask(255).toUint8(),
  description: PREFIX + '_CopDEM_WaterBodyMask',
  folder: DRIVE_FOLDER, region: roi, scale: SCALE, crs: CRS, maxPixels: 1e13
});
