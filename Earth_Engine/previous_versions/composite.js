// =====================================================================================
// Sentinel-2 L2A multi-year dry-season composite for Bathymetrix-AI
// with BRIGHTNESS MATCHING between MGRS tiles OR between orbits (removes seams)
// Southern Belize (SEASTRONG) - Google Earth Engine Code Editor
// -------------------------------------------------------------------------------------
// Output: one 12-band Float32 GeoTIFF, surface reflectance 0-1, NoData = -9999, UTM 16N.
// Band order = Bathymetrix-AI defaults:
//   1 B1 Coastal | 2 B2 Blue | 3 B3 Green | 4 B4 Red | 5 B5 | 6 B6 | 7 B7 | 8 B8 NIR
//   9 B8A | 10 B9 | 11 B11 SWIR1 | 12 B12 SWIR2
// Plus a ValidCount raster (clear observations per pixel) and a B2 temporal std raster.
//
// DATE / IMAGE SCREENING (before compositing, each switchable)
//   glint/haze (B8, B11 over water), turbidity/plumes (B5 over water), rain (CHIRPS, days
//   before the image), wind (ERA5-Land at overpass). Per-date table printed + CSV export;
//   the EXCLUDE_DATES line (exported as CSV) is pasted back; later runs skip the statistics.
//
// HOW IT WORKS (tile / orbit matching)
//   Images are split into GROUPS: by MGRS tile ('MGRS_TILE') or by relative orbit
//   ('SENSING_ORBIT_NUMBER'). One composite per group is made, then each group (in GROUPS
//   order) is shifted by the per-band median difference over WATER where it overlaps the
//   groups already matched. First group = reference, on top in the mosaic.
//   Offsets are measured ONCE at coarse resolution and applied as fixed numbers, so the map
//   preview and the export only compute the per-group composites (avoids memory errors).
//
// HOW TO USE
//   1. Set AOI_ASSET. Create the Drive folder DRIVE_FOLDER in My Drive.
//   2. Run with EXCLUDE_DATES = []: only two TABLE exports are created (Tasks tab > RUN).
//      Check S2_date_screening_*.csv (tune thresholds); paste the line from
//      S2_EXCLUDE_DATES_*.csv over EXCLUDE_DATES. (No dates to drop? Use ['none'].)
//   3. Run again: wait for 'OFFSETS' in the Console (a few minutes; preview layers appear).
//      Copy the printed OFFSETS into FIXED_OFFSETS.
//   4. Run a final time: exports are created. Tasks tab > RUN them.
//   (Changing the dates/screening changes the composites -> measure OFFSETS again.)
// =====================================================================================
 
 
// ---------------------------------- SETTINGS -----------------------------------------
var AOI_ASSET = 'projects/ee-alessiorovere/assets/AOI';  // <-- your asset ID
 
var YEARS  = [2020, 2026];   // first and last year
var MONTHS = [2, 4];         // February to April (southern Belize dry season)
 
var MAX_TILE_CLOUD = 70;     // loose tile pre-filter (%); Cloud Score+ does the pixel masking
var CS_THRESHOLD   = 0.65;   // Cloud Score+ clear threshold: 0.50 permissive ... 0.65 strict
 
// Matching groups, REFERENCE FIRST.  [] = no matching, plain composite.
var GROUP_BY = 'MGRS_TILE';                          // or 'SENSING_ORBIT_NUMBER'
var GROUPS   = ['16QCD', '16PCC', '16QBD', '16PBC'];  // tiles within ORBIT; empty ones are skipped
                                                     // (for orbit matching: [140, 40], ORBIT = null)
 
var FIXED_OFFSETS = {"16PBC":{"B1":0.0033077245199171637,"B11":0.00008640854380748249,"B12":0.000046579604641271034,"B2":0.0023401301697740227,"B3":0.00182052458167634,"B4":0.0007984723437111147,"B5":0.0007004217083888622,"B6":0.000875083632418229,"B7":0.0008306391149614462,"B8":0.0006154518119508816,"B8A":0.0006211959795313229,"B9":-0.00024651537153905434},"16PCC":{"B1":-0.0001427729529406969,"B11":0.00008843842436364658,"B12":0.00004657947827779074,"B2":0.00019144809767514484,"B3":0.0004220955348750829,"B4":0.00019855713079232882,"B5":0.00020257354003577952,"B6":0.00043021346045457256,"B7":0.00043837712233374507,"B8":0.000418835576347288,"B8A":0.00042596526841905894,"B9":-0.0009515673558982114},"16QBD":{"B1":0,"B11":0,"B12":0,"B2":0,"B3":0,"B4":0,"B5":0,"B6":0,"B7":0,"B8":0,"B8A":0,"B9":0},"16QCD":{"B1":0,"B11":0,"B12":0,"B2":0,"B3":0,"B4":0,"B5":0,"B6":0,"B7":0,"B8":0,"B8A":0,"B9":0}};    // null = measure + preview; paste printed OFFSETS here to EXPORT
 
var WATER_NDWI   = 0.2;      // overlap pixels used for matching: NDWI > this ...
var WATER_NIR    = 0.05;     // ... and B8 < this (excludes land, cloud remnants, whitecaps)
var MATCH_BUFFER = 10000;    // m around the AOI where overlap water is searched
var OFFSET_SCALE = 100;      // m; resolution used to MEASURE offsets (coarse = light, robust)
var MIN_MATCH_PIXELS = 50;   // fewer overlap water pixels (at OFFSET_SCALE) -> fallback
var NO_WATER_FALLBACK = 'zero';  // 'zero' = leave group unchanged | 'all' = match on land+water
 
// ---- Date / image screening (each switchable). Water = Copernicus DEM water body mask ----
// (a) Glint / haze, measured in the image
var GLINT_FILTER     = true;
var PIXEL_MAX_SWIR   = 0.02;   // per pixel: water with B11 > this is masked (glint, whitecaps, haze)
var SCENE_MAX_NIR    = 0.03;   // per image: median B8 over water > this -> image dropped
// (b) Turbidity / river plumes, measured in the image (red edge B5 barely reaches the bottom)
var TURBIDITY_FILTER = true;
var SCENE_MAX_B5     = 0.03;   // per image: median B5 over water > this -> image dropped
// (c) Rain before the image (CHIRPS daily, mm averaged over RAIN_REGION)
var RAIN_FILTER      = true;
var RAIN_DAYS        = 5;      // days before the image summed
var RAIN_MAX_MM      = 25;     // area-mean rain over those days > this -> date dropped
var RAIN_BUFFER      = 40000;  // m around the AOI = catchments draining to the coast (Maya Mts.)
// (d) Wind at overpass time (ERA5-Land hourly 10 m wind, coastal land cells = local proxy)
var WIND_FILTER      = true;
var WIND_HOUR_UTC    = 16;     // Sentinel-2 overpass over Belize ~16:20 UTC
var WIND_MAX_MS      = 6;      // mean 10 m wind speed > this -> date dropped
var WIND_BUFFER      = 20000;  // m around the AOI
// Statistics
var SCENE_STAT_SCALE = 200;    // m, resolution of the per-image water statistics
// EXCLUDE_DATES = [] -> SCREENING RUN: only exports the per-date table + a ready-to-paste
var EXCLUDE_DATES = ['2020-03-10', '2020-04-14', '2020-04-19', '2020-04-24', '2020-04-29', '2021-02-03', '2021-02-13', '2021-03-10', '2021-03-20', '2021-03-25', '2021-04-09', '2021-04-14', '2021-04-19', '2021-04-24', '2021-04-29', '2022-02-18', '2022-03-15', '2022-03-20', '2022-03-25', '2022-03-30', '2022-04-24', '2022-04-29', '2023-02-23', '2023-03-15', '2023-03-30', '2023-04-04', '2023-04-14', '2023-04-19', '2023-04-24', '2023-04-29', '2024-03-14', '2024-03-24', '2024-03-29', '2024-04-03', '2024-04-18', '2024-04-28', '2025-02-12', '2025-02-22', '2025-03-24', '2025-03-29', '2025-04-03', '2025-04-13', '2025-04-18', '2026-03-09', '2026-03-14'];
//EXCLUDE_DATES line (CSV). Paste that line here and Run again for preview / offsets / export.
// Nothing to exclude? use ['none'].  To skip screening entirely: set all four filters false.
//var EXCLUDE_DATES = [];
 
var ORBIT      = 40;         // single orbit (avoids the orbit 40/140 seam); null = all orbits
var PERCENTILE = 30;         // 30th percentile: suppresses residual haze/glint (50 = median)
var MIN_VALID  = 5;          // min clear observations per pixel; fewer -> NoData (0 = off)
 
var CRS          = 'EPSG:32616';  // WGS 84 / UTM zone 16N
var SCALE        = 10;            // metres (export)
var DRIVE_FOLDER = 'GEE_Bathymetry_Inputs';  // create this folder in My Drive BEFORE exporting:
                                              // parallel tasks otherwise each create their own copy
// -------------------------------------------------------------------------------------
 
 
var aoiFc = ee.FeatureCollection(AOI_ASSET);
var roi = aoiFc.geometry();
var matchArea = roi.bounds().buffer(MATCH_BUFFER);
var MATCH = (GROUPS.length > 1);
var KEYS = GROUPS.map(function (g) { return String(g); });   // dictionary keys
 
var BANDS = ['B1','B2','B3','B4','B5','B6','B7','B8','B8A','B9','B11','B12'];
var MONTH_NAMES = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
var TAG = YEARS[0] + '_' + MONTH_NAMES[MONTHS[0] - 1] + '_' +
          YEARS[1] + '_' + MONTH_NAMES[MONTHS[1] - 1] +
          (PERCENTILE === 50 ? '_Median' : '_P' + PERCENTILE) +
          (ORBIT !== null ? '_R' + ORBIT : '') +
          (MATCH ? (GROUP_BY === 'MGRS_TILE' ? '_TileMatched' : '_OrbitMatched') : '');
 
 
// 1. Sentinel-2 L2A (2A + 2B + 2C). HARMONIZED = the post-2022 +1000 DN offset is removed.
var s2 = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
  .filterBounds(roi)
  .filterDate(YEARS[0] + '-01-01', (YEARS[1] + 1) + '-01-01')
  .filter(ee.Filter.calendarRange(MONTHS[0], MONTHS[1], 'month'))
  .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', MAX_TILE_CLOUD));
if (ORBIT !== null) { s2 = s2.filter(ee.Filter.eq('SENSING_ORBIT_NUMBER', ORBIT)); }
 
print('AOI area (km2):', roi.area(1).divide(1e6));
print('Tiles (images per tile):', s2.aggregate_histogram('MGRS_TILE'));
print('Orbits (images per orbit):', s2.aggregate_histogram('SENSING_ORBIT_NUMBER'));
print('Satellites:', s2.aggregate_histogram('SPACECRAFT_NAME'));
 
 
// 2. Cloud Score+ masking and scaling to reflectance
var csPlus = ee.ImageCollection('GOOGLE/CLOUD_SCORE_PLUS/V1/S2_HARMONIZED');
function prep(img) {
  var clear = img.select('cs_cdf').gte(CS_THRESHOLD);
  return img.select(BANDS).updateMask(clear).divide(10000).toFloat()
            .copyProperties(img, ['system:time_start', 'MGRS_TILE', 'SENSING_ORBIT_NUMBER']);
}
var col = s2.linkCollection(csPlus, ['cs_cdf']).map(prep);
 
// 2b. Date / image screening.
//     Clear water absorbs NIR, SWIR and most red-edge light (even over shallow sand), so raised
//     B8 / B11 over water = glint, whitecaps, haze; raised B5 = suspended sediment / plumes.
//     Rain and wind are external proxies for runoff and wind-stirred water.
//     The per-date statistics are too heavy for the interactive Console, so with
//     EXCLUDE_DATES = [] the script ONLY creates two table exports (run on Google's batch
//     servers): the per-date table and a one-line EXCLUDE_DATES list to paste back.
var waterRef = ee.ImageCollection('COPERNICUS/DEM/GLO30').filterBounds(roi)
                 .select('WBM').mosaic().gt(0);                 // 1 = ocean, lake or river
var rainRegion = roi.bounds().buffer(RAIN_BUFFER);
var windRegion = roi.bounds().buffer(WIND_BUFFER);
var chirps = ee.ImageCollection('UCSB-CHG/CHIRPS/DAILY').select('precipitation');
var era5l  = ee.ImageCollection('ECMWF/ERA5_LAND/HOURLY')
               .select(['u_component_of_wind_10m', 'v_component_of_wind_10m']);
 
// date label + per-pixel glint mask (cheap, always applied when GLINT_FILTER)
col = col.map(function (img) {
  var out = GLINT_FILTER
    ? img.updateMask(waterRef.and(img.select('B11').gt(PIXEL_MAX_SWIR)).not()) : img;
  return out.set('date', ee.Date(img.get('system:time_start')).format('YYYY-MM-dd'));
});
var dateList = col.aggregate_array('date').distinct().sort();
var ANY_SCREEN = GLINT_FILTER || TURBIDITY_FILTER || RAIN_FILTER || WIND_FILTER;
var SCREEN_ONLY = false;   // true = this run only measures the screening table
 
if (EXCLUDE_DATES.length > 0) {
  var nB = col.size();
  col = col.filter(ee.Filter.inList('date', EXCLUDE_DATES).not());
  print('Using EXCLUDE_DATES (' + EXCLUDE_DATES.length + ' dates dropped). Images kept:', col.size(), 'of', nB);
 
} else if (ANY_SCREEN) {
  SCREEN_ONLY = true;
  // One row per DATE: all tiles of that date mosaicked -> one statistic (light)
  var nullable = function (v, max, label) {   // '' if ok or missing, label if v > max
    return ee.Algorithms.If(ee.Algorithms.IsEqual(v, null), '',
                            ee.Algorithms.If(ee.Number(v).gt(max), label, ''));
  };
  var dateTable = ee.FeatureCollection(dateList.map(function (d) {
    var day = ee.Date(d);
    var imgs = col.filter(ee.Filter.eq('date', d));
    var st = imgs.mosaic().select(['B8', 'B5']).updateMask(waterRef).reduceRegion({
      reducer: ee.Reducer.median(), geometry: roi, scale: SCENE_STAT_SCALE,
      maxPixels: 1e9, bestEffort: true, tileScale: 16});
    var nir = st.get('B8'), b5 = st.get('B5');
    var rain = chirps.filterDate(day.advance(-RAIN_DAYS, 'day'), day).sum()
      .reduceRegion({reducer: ee.Reducer.mean(), geometry: rainRegion, scale: 5566,
                     maxPixels: 1e9, bestEffort: true}).get('precipitation');
    var w = era5l.filterDate(day.advance(WIND_HOUR_UTC, 'hour'), day.advance(WIND_HOUR_UTC + 1, 'hour'));
    var wind = ee.Algorithms.If(w.size().gt(0),
      ee.Image(w.first()).expression('hypot(b("u_component_of_wind_10m"), b("v_component_of_wind_10m"))')
        .reduceRegion({reducer: ee.Reducer.mean(), geometry: windRegion, scale: 11132,
                       maxPixels: 1e9, bestEffort: true}).values().get(0),
      null);
    var r = [ee.Algorithms.If(ee.Algorithms.IsEqual(nir, null), 'no_clear_water', '')];
    if (GLINT_FILTER)     { r.push(nullable(nir,  SCENE_MAX_NIR, 'glint')); }
    if (TURBIDITY_FILTER) { r.push(nullable(b5,   SCENE_MAX_B5,  'turbid')); }
    if (RAIN_FILTER)      { r.push(nullable(rain, RAIN_MAX_MM,   'rain')); }
    if (WIND_FILTER)      { r.push(nullable(wind, WIND_MAX_MS,   'wind')); }
    var reasons = ee.List(r).removeAll(['']);
    return ee.Feature(null, {date: d, tiles: imgs.size(), water_nir: nir, water_b5: b5,
                             rain_mm: rain, wind_ms: wind,
                             kept: reasons.size().eq(0), reason: reasons.join(',')});
  }));
  var dropped = dateTable.filter(ee.Filter.eq('kept', 0)).aggregate_array('date');
  var excludeLine = ee.String('var EXCLUDE_DATES = [').cat(
    dropped.map(function (d) { return ee.String("'").cat(d).cat("'"); }).join(', ')).cat('];');
 
  Export.table.toDrive({collection: dateTable,
    description: 'S2_date_screening_' + YEARS[0] + '_' + YEARS[1] + (ORBIT !== null ? '_R' + ORBIT : ''),
    folder: DRIVE_FOLDER, fileFormat: 'CSV',
    selectors: ['date', 'tiles', 'kept', 'reason', 'water_nir', 'water_b5', 'rain_mm', 'wind_ms']});
  Export.table.toDrive({
    collection: ee.FeatureCollection([ee.Feature(null, {
      n_dates: dateList.size(), n_dropped: dropped.size(), paste_this: excludeLine})]),
    description: 'S2_EXCLUDE_DATES_' + YEARS[0] + '_' + YEARS[1] + (ORBIT !== null ? '_R' + ORBIT : ''),
    folder: DRIVE_FOLDER, fileFormat: 'CSV', selectors: ['n_dates', 'n_dropped', 'paste_this']});
 
  print('Dates to screen:', dateList.size());
  print('SCREENING RUN: start the two table exports in the Tasks tab.',
        'Open S2_EXCLUDE_DATES_*.csv, paste its line over EXCLUDE_DATES, and Run again.',
        'Check S2_date_screening_*.csv to tune the thresholds.');
}
 
// Temporal variability of Blue: seabed is stable (low), clouds / haze / glint are transient (high)
var temporalStd = col.select('B2').reduce(ee.Reducer.stdDev()).rename('B2_temporal_std').toFloat();
 
 
// 3. Helpers
var EMPTY = ee.Image.constant(BANDS.map(function () { return 0; })).rename(BANDS)
              .updateMask(0).toFloat();
function makeComposite(c) {      // empty collection (e.g. tile not in this orbit) -> fully masked
  var comp = (PERCENTILE === 50) ? c.median().select(BANDS)
             : c.reduce(ee.Reducer.percentile([PERCENTILE])).rename(BANDS);
  return ee.Image(ee.Algorithms.If(c.size().gt(0), comp.toFloat(), EMPTY));
}
function makeCount(c) {
  return ee.Image(ee.Algorithms.If(c.size().gt(0),
    c.select('B2').count().rename('valid_count').toInt16(),
    ee.Image.constant(0).rename('valid_count').toInt16().updateMask(0)));
}
function priorityMosaic(arr) { return ee.ImageCollection(arr.slice().reverse()).mosaic(); }
function groupCol(g) { return col.filter(ee.Filter.eq(GROUP_BY, g)); }
function isNull(v) { return ee.Algorithms.IsEqual(v, null); }
function zeros() { var o = {}; BANDS.forEach(function (b) { o[b] = 0; }); return o; }
 
 
// 4. Measure offsets (server side, coarse) -> {group: {band: offset}}
function measureOffsets() {
  var comps = GROUPS.map(function (g) { return makeComposite(groupCol(g)); });
  var matched = [comps[0]];
  var result = ee.Dictionary({}).set(KEYS[0], ee.Dictionary(zeros()));
  var nPix = ee.Dictionary({});
  var R = {geometry: matchArea, scale: OFFSET_SCALE, crs: CRS,
           maxPixels: 1e9, bestEffort: true, tileScale: 16};
 
  for (var i = 1; i < GROUPS.length; i++) {
    var comp = comps[i];
    var current = priorityMosaic(matched);
    var bothValid = current.select('B2').mask().and(comp.select('B2').mask());
    var water = current.normalizedDifference(['B3', 'B8']).gt(WATER_NDWI)
                       .and(current.select('B8').lt(WATER_NIR));
    var diff = current.subtract(comp);
 
    var nWater = ee.Number(bothValid.and(water).selfMask().rename('n').reduceRegion({
      reducer: ee.Reducer.count(), geometry: R.geometry, scale: R.scale, crs: R.crs,
      maxPixels: R.maxPixels, bestEffort: R.bestEffort, tileScale: R.tileScale}).get('n'));
    var offWater = diff.updateMask(bothValid.and(water)).reduceRegion({
      reducer: ee.Reducer.median(), geometry: R.geometry, scale: R.scale, crs: R.crs,
      maxPixels: R.maxPixels, bestEffort: R.bestEffort, tileScale: R.tileScale});
    var fallback = (NO_WATER_FALLBACK === 'all')
      ? diff.updateMask(bothValid).reduceRegion({
          reducer: ee.Reducer.median(), geometry: R.geometry, scale: R.scale, crs: R.crs,
          maxPixels: R.maxPixels, bestEffort: R.bestEffort, tileScale: R.tileScale})
      : ee.Dictionary(zeros());
 
    var chosen = ee.Dictionary(ee.Algorithms.If(nWater.gte(MIN_MATCH_PIXELS), offWater, fallback));
    var clean = ee.Dictionary.fromLists(BANDS, BANDS.map(function (b) {
      return ee.Algorithms.If(isNull(chosen.get(b)), 0, chosen.get(b));   // null -> 0
    }));
 
    result = result.set(KEYS[i], clean);
    nPix = nPix.set(KEYS[i], nWater);
    matched.push(comp.add(ee.Image.constant(clean.values(BANDS))).rename(BANDS).toFloat());
  }
  return ee.Dictionary({offsets: result, overlap_water_pixels: nPix});
}
 
 
// 5. Build composite from FIXED (client-side) offsets -> light to render and export
function build(offsets) {
  var adj = [], counts = [], raw = [];
  GROUPS.forEach(function (g, i) {
    var c = groupCol(g);
    var comp = makeComposite(c);
    var o = offsets[KEYS[i]] || zeros();
    raw.push(comp);
    adj.push(comp.add(ee.Image.constant(BANDS.map(function (b) { return o[b] || 0; })))
                 .rename(BANDS).toFloat());
    counts.push(makeCount(c));
  });
  var source = priorityMosaic(raw.map(function (c, i) {
    return ee.Image.constant(i + 1).toInt8().updateMask(c.select('B2').mask()).rename('group');
  }));
  return {composite: priorityMosaic(adj), count: priorityMosaic(counts),
          before: priorityMosaic(raw), source: source};
}
 
 
// 6. Display + export
function finish(res, doExport) {
  var composite = res.composite, validCount = res.count;
  if (MIN_VALID > 0) { composite = composite.updateMask(validCount.gte(MIN_VALID)); }
  composite = composite.select(BANDS).clip(roi);
  validCount = validCount.clip(roi);
 
  var rgb = {bands: ['B4','B3','B2'], min: 0, max: 0.15, gamma: 1.3};
  if (res.before) {
    Map.addLayer(res.before.clip(roi), rgb, 'BEFORE matching', false);
    Map.addLayer(res.source.clip(roi), {min: 1, max: Math.max(GROUPS.length, 2),
                 palette: ['1b9e77','d95f02','7570b3','e7298a','66a61e','e6ab02'].slice(0, Math.max(GROUPS.length, 2))},
                 'Group supplying each pixel (' + KEYS.join(', ') + ')', false);
  }
  Map.addLayer(composite, rgb, 'Composite ' + TAG);
  Map.addLayer(composite.select('B2'), {min: 0.02, max: 0.10,
               palette: ['000004','3b0f70','8c2981','de4968','fe9f6d','fcfdbf']},
               'B2 Blue (look for steps / seams)', false);
  Map.addLayer(validCount, {min: 0, max: 20, palette: ['d7191c','fdae61','ffffbf','a6d96a','1a9641']},
               'Valid observations', false);
  Map.addLayer(temporalStd.clip(roi), {min: 0, max: 0.02, palette: ['000000','ffff00','ff0000']},
               'B2 temporal std (bright = transient: cloud/haze/glint)', false);
  Map.addLayer(ee.Image().paint(aoiFc, 0, 2), {palette: ['ff00ff']}, 'AOI');
 
  if (!doExport) {
    print('Preview only. To EXPORT: copy the OFFSETS line above into FIXED_OFFSETS and Run again.');
    return;
  }
  Export.image.toDrive({
    image: composite.unmask(-9999).toFloat(),
    description: 'S2_' + TAG + '_12band_Float32',
    folder: DRIVE_FOLDER, region: roi, scale: SCALE, crs: CRS, maxPixels: 1e13,
    formatOptions: {cloudOptimized: true, noData: -9999}   // remove noData if GEE complains
  });
  Export.image.toDrive({
    image: validCount.unmask(0).toInt16(),
    description: 'S2_' + TAG + '_ValidCount',
    folder: DRIVE_FOLDER, region: roi, scale: SCALE, crs: CRS, maxPixels: 1e13
  });
  Export.image.toDrive({
    image: temporalStd.clip(roi).unmask(-9999),
    description: 'S2_' + TAG + '_B2_TemporalStd',
    folder: DRIVE_FOLDER, region: roi, scale: SCALE, crs: CRS, maxPixels: 1e13
  });
  print('Done: layers added, exports ready in the Tasks tab.');
}
 
 
// 7. Run
// Exports are created only in synchronous runs (no matching, or FIXED_OFFSETS set): creating
// them inside the asynchronous evaluate() callback fails in the Code Editor.
Map.centerObject(roi, 11);
if (SCREEN_ONLY) {
  // screening run: only the table exports above, no composites
} else if (!MATCH) {
  finish({composite: makeComposite(col), count: makeCount(col)}, true);
} else if (FIXED_OFFSETS !== null) {
  print('Using FIXED_OFFSETS:', FIXED_OFFSETS);
  finish(build(FIXED_OFFSETS), true);
} else {
  print('Measuring offsets at ' + OFFSET_SCALE + ' m ... (may take a few minutes)');
  measureOffsets().evaluate(function (r, err) {
    if (err) {
      print('Offset measurement failed:', err,
            'Try OFFSET_SCALE = 200, a smaller MATCH_BUFFER, or fewer YEARS.');
      return;
    }
    print('Overlap water pixels per group (at ' + OFFSET_SCALE + ' m):', r.overlap_water_pixels);
    print('OFFSETS (copy into FIXED_OFFSETS to reuse):', JSON.stringify(r.offsets));
    finish(build(r.offsets), false);
  });
}
