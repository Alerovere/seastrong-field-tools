// =====================================================================================
// SEASTRONG - inputs for satellite-derived bathymetry (Bathymetrix-AI) - Google Earth Engine
// -------------------------------------------------------------------------------------
// One script, four products (switch them on / off in RUN):
//   S2_COMPOSITE   12-band Sentinel-2 composite for Bathymetrix-AI (+ QA raster, blue temporal std)
//   DEM            Copernicus DEM (DSM), FABDEM and DeltaDTM (bare earth), DSM - DEM, water mask
//   HABITATS       Allen Coral Atlas (benthic, geomorphic, reef mask), mangroves (GMW), canopy height
//   ICESAT2_FILES  land polygons (shoreline) and mangrove polygons for the ICESat-2 Colab tool
// and a quick chart (S2_MONTHS_CHART) of how often each month has clear Sentinel-2 images.
//
// All rasters share ONE grid (UTM, origin snapped to GRID_SNAP m), so 5, 10, 30 m products line
// up pixel on pixel in QGIS. Everything goes to the Drive folder DRIVE_FOLDER.
//
// WORKFLOW FOR THE COMPOSITE (three runs; each run takes seconds, the exports run in the Tasks tab)
//   Before: in the Wave climate Colab notebook, step "Sentinel-2 sea-state dates", copy the
//           SEA_STATE_EXCLUDE line it prints and paste it below (rough seas / strong wind at the
//           satellite overpass). Optional but recommended.
//   Run 1  EXCLUDE_DATES = null  -> screening run: two TABLE exports (Tasks tab > RUN).
//          S2_date_screening_*.csv  = one row per date (water NIR, water B5, rain, reasons);
//          S2_EXCLUDE_DATES_*.csv   = one line to paste over EXCLUDE_DATES.
//          Look at the table and adjust the thresholds if needed before pasting.
//   Run 2  EXCLUDE_DATES = [...] (or [] if nothing to drop), FIXED_OFFSETS = null
//          -> tile offsets are measured (Console, a few minutes) and a PREVIEW is shown.
//          Check the seams in the map, then copy the printed OFFSETS line over FIXED_OFFSETS.
//          (Only one tile in GROUPS, or GROUPS = []: no offsets needed, Run 2 exports directly.)
//   Run 3  -> exports: S2_..._12band_Float32, S2_..._QA, S2_..._B2_TemporalStd (Tasks tab > RUN).
//   Changing years, months, orbit, cloud threshold or excluded dates changes the composites:
//   measure the offsets again (FIXED_OFFSETS = null).
//
// OUTPUT BAND ORDER (= Bathymetrix-AI defaults): 1 B1 Coastal | 2 B2 Blue | 3 B3 Green | 4 B4 Red |
//   5 B5 | 6 B6 | 7 B7 | 8 B8 NIR | 9 B8A | 10 B9 | 11 B11 SWIR1 | 12 B12 SWIR2.
//   Reflectance 0-1, Float32, NoData -9999.  QA: band 1 clear observations of the tile used,
//   band 2 source tile (1 = first in GROUPS), band 3 = 1 where any band is < 0 or > 1 after matching.
//
// Revision 2026-11-05 (from composite.js, EarthDEM.js, Habitats.js):
//   - an observation is used only where ALL 12 bands are valid (one common mask);
//   - MIN_VALID is applied to each tile BEFORE the tiles are mosaicked (a tile with too few clear
//     observations no longer hides a better tile underneath);
//   - aligned export grid (crsTransform) shared by all products;
//   - screening: a check without data is reported ('no_rain_data', ...) and MISSING_POLICY decides;
//     sea-state dates from the Colab wave tool; wind from ERA5-Land is off by default (land cells
//     only; the Colab list uses ERA5 wind at sea);
//   - offsets: overlap pixel counts and large offsets reported; QA raster added;
//   - Copernicus DEM release GLO30_2024_1 (set COPDEM); land and mangrove polygons for ICESat-2.
// =====================================================================================


// ---------------------------------- SETTINGS: project ---------------------------------
var AOI_ASSET    = 'projects/ee-alessiorovere/assets/AOI';  // <-- your AOI table asset
var PREFIX       = 'Belize_south';                          // start of every file name
var CRS          = 'EPSG:32616';                            // UTM zone of the site (Belize: 16N)
var GRID_SNAP    = 60;          // m; grid origin = multiple of this -> 5/10/20/30/60 m grids nest
var DRIVE_FOLDER = 'SEASTRONG_SDB_inputs';   // create it in My Drive BEFORE exporting (otherwise
                                             // parallel tasks may each create their own copy)
var RUN = {
  S2_MONTHS_CHART: true,   // chart of clear Sentinel-2 images per month (metadata only, instant)
  S2_COMPOSITE:    true,   // composite workflow (see above)
  DEM:             false,  // DEM exports (run once)
  HABITATS:        false,  // habitat exports (run once)
  ICESAT2_FILES:   false   // land + mangrove polygons for the ICESat-2 tool (run once)
};

// ---------------------------------- SETTINGS: Sentinel-2 composite --------------------
var YEARS  = [2020, 2026];      // first and last year
var MONTHS = [2, 4];            // first and last month (Feb-Apr: southern Belize dry season);
                                // November-April works too: [11, 4]
var ORBIT  = 40;                // single relative orbit (avoids seams between orbits 40 / 140); null = all
var MAX_TILE_CLOUD = 70;        // tile images above this cloud % are not used (metadata pre-filter)
var CS_THRESHOLD   = 0.65;      // Cloud Score+ clear threshold: 0.50 permissive ... 0.65 strict
var PERCENTILE     = 30;        // per-pixel percentile: 30 suppresses residual haze / glint; 50 = median
var MIN_VALID      = 5;         // clear observations needed per pixel and tile; fewer -> NoData (0 = off)
var SCALE          = 10;        // m
var B1_FROM_B2     = false;     // true = band 1 is a copy of B2 (if the 60 m coastal band shows seams)

// Tile matching, REFERENCE FIRST ([] = no matching). Tiles not in ORBIT are skipped automatically.
var GROUP_BY = 'MGRS_TILE';                              // or 'SENSING_ORBIT_NUMBER'
var GROUPS   = ['16QCD', '16PCC', '16PBC', '16QBD'];     // each tile should overlap water of an earlier one
var FIXED_OFFSETS = null;       // null = measure + preview (Run 2); paste the printed OFFSETS here (Run 3)
var WATER_NDWI   = 0.2;         // overlap pixels used for matching: NDWI > this ...
var WATER_NIR    = 0.05;        // ... and B8 < this (no land, cloud remnants, whitecaps)
var MATCH_BUFFER = 10000;       // m around the AOI where overlap water is searched
var OFFSET_SCALE = 100;         // m; resolution used to MEASURE offsets (coarse = light, robust)
var MIN_MATCH_PIXELS = 50;      // fewer overlap water pixels -> offset not measured (see fallback)
var NO_WATER_FALLBACK = 'zero'; // 'zero' = leave the tile unchanged | 'all' = match over land + water
var OFFSET_WARN  = 0.01;        // offsets larger than this (reflectance) are reported

// Date screening. Water = Copernicus DEM water body mask.
var GLINT_FILTER     = true;
var PIXEL_MAX_SWIR   = 0.02;    // per pixel: water with B11 > this is masked (glint, whitecaps, haze)
var SCENE_MAX_NIR    = 0.03;    // per date: median B8 of clear water > this -> date dropped
var TURBIDITY_FILTER = true;
var SCENE_MAX_B5     = 0.03;    // per date: median B5 of clear water > this -> date dropped (plumes)
var RAIN_FILTER      = true;
var RAIN_DAYS        = 5;       // CHIRPS rain summed over these whole days before the image ...
var RAIN_MAX_MM      = 25;      // ... above this (mm, mean over AOI + RAIN_BUFFER) -> dropped
var RAIN_BUFFER      = 40000;   // m: catchments draining to the coast (Maya Mountains)
var WIND_FILTER      = false;   // ERA5-Land wind (land cells near the coast); the Colab list is better
var WIND_HOUR_UTC    = 16;      // overpass hour (Belize ~16:20 UTC)
var WIND_MAX_MS      = 6;
var WIND_BUFFER      = 20000;
var MISSING_POLICY   = 'drop';  // a check without data: 'drop' the date or 'keep' it
var SCENE_STAT_SCALE = 200;     // m; resolution of the per-date water statistics

// Rough-sea / windy dates from the Wave climate Colab notebook (step "Sentinel-2 sea-state dates").
var SEA_STATE_EXCLUDE = [];     // e.g. ['2021-02-13', '2023-03-30']

// null = SCREENING RUN (Run 1). Then paste the line from S2_EXCLUDE_DATES_*.csv here; [] = drop none.
var EXCLUDE_DATES = null;

// ---------------------------------- SETTINGS: DEM, habitats, ICESat-2 files ----------
var COPDEM        = 'COPERNICUS/DEM/GLO30_2024_1';   // Copernicus DEM release (DSM + water mask)
var DEM_SCALE     = 30;         // m
var LAND_BUFFER   = 2000;       // m beyond the AOI for the land polygons (coasts just outside count)
var EXPORT_DELTADTM = true, EXPORT_FABDEM = true;
// -------------------------------------------------------------------------------------


var aoiFc = ee.FeatureCollection(AOI_ASSET);
var roi = aoiFc.geometry();
Map.centerObject(roi, 11);
Map.addLayer(ee.Image().paint(aoiFc, 0, 2), {palette: ['ff00ff']}, 'AOI');

// Shared grid: origin snapped to GRID_SNAP (one small request).
var bnd = ee.List(roi.bounds(1, CRS).coordinates().get(0)).getInfo();
var xs = bnd.map(function (p) { return p[0]; }), ys = bnd.map(function (p) { return p[1]; });
var GX0 = Math.floor(Math.min.apply(null, xs) / GRID_SNAP) * GRID_SNAP;
var GY1 = Math.ceil(Math.max.apply(null, ys) / GRID_SNAP) * GRID_SNAP;
function grid(scale) { return [scale, 0, GX0, 0, -scale, GY1]; }
print('AOI area (km2):', roi.area(1).divide(1e6), 'Grid origin (' + CRS + '):', GX0, GY1);

function exportImage(img, name, scale, nodata, region) {
  var params = {image: img, description: (PREFIX + '_' + name).slice(0, 100), fileNamePrefix: PREFIX + '_' + name,
                folder: DRIVE_FOLDER, region: region || roi, crs: CRS, crsTransform: grid(scale), maxPixels: 1e13,
                formatOptions: {cloudOptimized: true}};
  if (nodata !== null) params.formatOptions.noData = nodata;
  Export.image.toDrive(params);
}

// Water body mask of the chosen Copernicus DEM release: 1 = water (ocean, lake, river).
// Outside DEM tiles there is open sea -> unmask(1).
var copdem = ee.ImageCollection(COPDEM).filterBounds(roi.buffer(LAND_BUFFER + 5000));
var waterRef = copdem.select('WBM').mosaic().gt(0).unmask(1);


// =====================================================================================
// A. Clear Sentinel-2 images per month (tile metadata only)
// =====================================================================================
if (RUN.S2_MONTHS_CHART) {
  var allS2 = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED').filterBounds(roi).filterDate('2017-04-01', ee.Date(Date.now()));
  if (ORBIT !== null) { allS2 = allS2.filter(ee.Filter.eq('SENSING_ORBIT_NUMBER', ORBIT)); }
  var monthFc = ee.FeatureCollection(ee.List.sequence(1, 12).map(function (m) {
    var c = allS2.filter(ee.Filter.calendarRange(m, m, 'month'));
    var n = c.size();
    var share = function (lim) {
      return ee.Number(c.filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', lim)).size()).divide(n.max(1)).multiply(100);
    };
    return ee.Feature(null, {month: m, tile_images: n, 'tile cloud < 10 %': share(10), 'tile cloud < 30 %': share(30)});
  }));
  print(ui.Chart.feature.byFeature(monthFc, 'month', ['tile cloud < 10 %', 'tile cloud < 30 %'])
    .setChartType('ColumnChart')
    .setOptions({title: 'Sentinel-2 tile images with little cloud, by month (2017-now' + (ORBIT !== null ? ', orbit ' + ORBIT : '') + ')',
                 hAxis: {title: 'month'}, vAxis: {title: '% of tile images'}}));
  print('Use with the Wave climate notebook (calm months) to choose MONTHS. Tile cloud describes 110 km tiles, not the AOI.');
}


// =====================================================================================
// B. Sentinel-2 composite
// =====================================================================================
if (RUN.S2_COMPOSITE) {
  var BANDS = ['B1','B2','B3','B4','B5','B6','B7','B8','B8A','B9','B11','B12'];
  var MATCH = (GROUPS.length > 1);
  var KEYS = GROUPS.map(function (g) { return String(g); });
  var MN = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  var TAG = YEARS[0] + '_' + MN[MONTHS[0] - 1] + '_' + YEARS[1] + '_' + MN[MONTHS[1] - 1] +
            (PERCENTILE === 50 ? '_Median' : '_P' + PERCENTILE) + (ORBIT !== null ? '_R' + ORBIT : '') +
            (B1_FROM_B2 ? '_B1isB2' : '') +
            (MATCH ? (GROUP_BY === 'MGRS_TILE' ? '_TileMatched' : '_OrbitMatched') : '');

  var s2 = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
    .filterBounds(roi)
    .filterDate(YEARS[0] + '-01-01', (YEARS[1] + 1) + '-01-01')
    .filter(ee.Filter.calendarRange(MONTHS[0], MONTHS[1], 'month'))     // wraps the year if MONTHS[0] > MONTHS[1]
    .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', MAX_TILE_CLOUD));
  if (ORBIT !== null) { s2 = s2.filter(ee.Filter.eq('SENSING_ORBIT_NUMBER', ORBIT)); }
  print('Composite ' + TAG + ': images per tile', s2.aggregate_histogram('MGRS_TILE'),
        'per orbit', s2.aggregate_histogram('SENSING_ORBIT_NUMBER'));

  // Cloud Score+ mask, reflectance, glint mask over water, ONE common mask for all 12 bands
  var csPlus = ee.ImageCollection('GOOGLE/CLOUD_SCORE_PLUS/V1/S2_HARMONIZED');
  var col = s2.linkCollection(csPlus, ['cs_cdf']).map(function (img) {
    var out = img.select(BANDS).updateMask(img.select('cs_cdf').gte(CS_THRESHOLD)).divide(10000).toFloat();
    if (GLINT_FILTER) { out = out.updateMask(waterRef.and(out.select('B11').gt(PIXEL_MAX_SWIR)).not()); }
    out = out.updateMask(out.mask().reduce(ee.Reducer.min()));
    return out.copyProperties(img, ['system:time_start', 'MGRS_TILE', 'SENSING_ORBIT_NUMBER'])
              .set('date', ee.Date(img.get('system:time_start')).format('YYYY-MM-dd'));
  });

  var ANY_SCREEN = GLINT_FILTER || TURBIDITY_FILTER || RAIN_FILTER || WIND_FILTER || SEA_STATE_EXCLUDE.length > 0;

  if (EXCLUDE_DATES === null && ANY_SCREEN) {
    // ---------------- Run 1: per-date screening table (batch export) ----------------
    var dateList = col.aggregate_array('date').distinct().sort();
    var rainRegion = roi.bounds().buffer(RAIN_BUFFER), windRegion = roi.bounds().buffer(WIND_BUFFER);
    var chirps = ee.ImageCollection('UCSB-CHG/CHIRPS/DAILY').select('precipitation');
    var era5l = ee.ImageCollection('ECMWF/ERA5_LAND/HOURLY').select(['u_component_of_wind_10m', 'v_component_of_wind_10m']);
    var check = function (v, max, label) {      // label if v > max; 'no_<label>_data' if missing and policy drop
      return ee.Algorithms.If(ee.Algorithms.IsEqual(v, null),
                              MISSING_POLICY === 'drop' ? 'no_' + label + '_data' : '',
                              ee.Algorithms.If(ee.Number(v).gt(max), label, ''));
    };
    var seaList = ee.List(SEA_STATE_EXCLUDE);
    var table = ee.FeatureCollection(dateList.map(function (d) {
      var day = ee.Date(d);
      var imgs = col.filter(ee.Filter.eq('date', d));
      var st = imgs.mosaic().select(['B8', 'B5']).updateMask(waterRef).reduceRegion({
        reducer: ee.Reducer.median().combine(ee.Reducer.count(), null, true), geometry: roi,
        scale: SCENE_STAT_SCALE, maxPixels: 1e9, bestEffort: true, tileScale: 16});
      var nir = st.get('B8_median'), b5 = st.get('B5_median');
      var rcol = chirps.filterDate(day.advance(-RAIN_DAYS, 'day'), day);
      var rain = ee.Algorithms.If(rcol.size().eq(RAIN_DAYS),
        rcol.sum().reduceRegion({reducer: ee.Reducer.mean(), geometry: rainRegion, scale: 5566,
                                 maxPixels: 1e9, bestEffort: true}).get('precipitation'), null);
      var w = era5l.filterDate(day.advance(WIND_HOUR_UTC, 'hour'), day.advance(WIND_HOUR_UTC + 1, 'hour'));
      var wind = WIND_FILTER ? ee.Algorithms.If(w.size().gt(0),
        ee.Image(w.first()).expression('hypot(b("u_component_of_wind_10m"), b("v_component_of_wind_10m"))')
          .reduceRegion({reducer: ee.Reducer.mean(), geometry: windRegion, scale: 11132, maxPixels: 1e9, bestEffort: true})
          .values().get(0), null) : null;
      var r = [ee.Algorithms.If(ee.Algorithms.IsEqual(nir, null), 'no_clear_water', '')];
      if (GLINT_FILTER)     { r.push(check(nir,  SCENE_MAX_NIR, 'glint')); }
      if (TURBIDITY_FILTER) { r.push(check(b5,   SCENE_MAX_B5,  'turbid')); }
      if (RAIN_FILTER)      { r.push(check(rain, RAIN_MAX_MM,   'rain')); }
      if (WIND_FILTER)      { r.push(check(wind, WIND_MAX_MS,   'wind')); }
      r.push(ee.Algorithms.If(seaList.contains(d), 'sea_state', ''));
      var reasons = ee.List(r).removeAll(['']).distinct();
      return ee.Feature(null, {date: d, tiles: imgs.size(), clear_water_px: st.get('B8_count'), water_nir: nir,
                               water_b5: b5, rain_mm: rain, wind_ms: wind, kept: reasons.size().eq(0),
                               reason: reasons.join(',')});
    }));
    var dropped = table.filter(ee.Filter.eq('kept', 0)).aggregate_array('date');
    var line = ee.String('var EXCLUDE_DATES = [').cat(
      dropped.map(function (d) { return ee.String("'").cat(d).cat("'"); }).join(', ')).cat('];');
    var suffix = '_' + YEARS[0] + '_' + YEARS[1] + '_' + MN[MONTHS[0] - 1] + '-' + MN[MONTHS[1] - 1] + (ORBIT !== null ? '_R' + ORBIT : '');
    Export.table.toDrive({collection: table, description: PREFIX + '_S2_date_screening' + suffix, folder: DRIVE_FOLDER,
      fileFormat: 'CSV', selectors: ['date', 'tiles', 'kept', 'reason', 'clear_water_px', 'water_nir', 'water_b5', 'rain_mm', 'wind_ms']});
    Export.table.toDrive({collection: ee.FeatureCollection([ee.Feature(null, {
        n_dates: dateList.size(), n_dropped: dropped.size(), paste_this: line})]),
      description: PREFIX + '_S2_EXCLUDE_DATES' + suffix, folder: DRIVE_FOLDER, fileFormat: 'CSV',
      selectors: ['n_dates', 'n_dropped', 'paste_this']});
    print('SCREENING RUN (' + (SEA_STATE_EXCLUDE.length ? SEA_STATE_EXCLUDE.length + ' sea-state dates from Colab' : 'no sea-state dates pasted') +
          '): run the two table exports in the Tasks tab, then paste the line of S2_EXCLUDE_DATES_*.csv over EXCLUDE_DATES and Run again.');
  } else {
    // ---------------- Runs 2 and 3 ----------------
    var drop = (EXCLUDE_DATES || []).concat(SEA_STATE_EXCLUDE);
    var nAll = col.size();
    if (drop.length) { col = col.filter(ee.Filter.inList('date', drop).not()); }
    print('Dates dropped: ' + drop.length + ' (screening + sea state). Images kept:', col.size(), 'of', nAll);

    var EMPTY = ee.Image.constant(BANDS.map(function () { return 0; })).rename(BANDS).updateMask(0).toFloat();
    var zeros = function () { var o = {}; BANDS.forEach(function (b) { o[b] = 0; }); return o; };
    var groupCol = function (g) { return MATCH ? col.filter(ee.Filter.eq(GROUP_BY, g)) : col; };
    var makeComposite = function (c) {
      var comp = (PERCENTILE === 50) ? c.median().select(BANDS) : c.reduce(ee.Reducer.percentile([PERCENTILE])).rename(BANDS);
      comp = comp.updateMask(comp.mask().reduce(ee.Reducer.min()));
      return ee.Image(ee.Algorithms.If(c.size().gt(0), comp.toFloat(), EMPTY));
    };
    var makeCount = function (c) {
      return ee.Image(ee.Algorithms.If(c.size().gt(0), c.select('B2').count().rename('valid_count').toInt16(),
                                       ee.Image.constant(0).rename('valid_count').toInt16().updateMask(0)));
    };
    var priorityMosaic = function (arr) { return ee.ImageCollection(arr.slice().reverse()).mosaic(); };
    // Per tile: composite, count, temporal std and source index, all masked by the tile's OWN MIN_VALID
    var parts = function (offsets) {
      var groups = MATCH ? GROUPS : [null];
      return groups.map(function (g, i) {
        var c = groupCol(g), cnt = makeCount(c);
        var elig = MIN_VALID > 0 ? cnt.gte(MIN_VALID) : cnt.gt(0);
        var o = (offsets && MATCH) ? (offsets[KEYS[i]] || zeros()) : zeros();
        var comp = makeComposite(c).add(ee.Image.constant(BANDS.map(function (b) { return o[b] || 0; })))
                                   .rename(BANDS).toFloat();
        return {comp: comp.updateMask(elig), count: cnt.updateMask(elig),
                src: ee.Image.constant(i + 1).toInt16().rename('source_tile').updateMask(elig),
                tstd: c.select('B2').reduce(ee.Reducer.stdDev()).rename('B2_temporal_std').toFloat().updateMask(elig)};
      });
    };
    var measureOffsets = function () {
      var p = parts(null), matched = [p[0].comp];
      var res = ee.Dictionary({}).set(KEYS[0], ee.Dictionary(zeros())), nPix = ee.Dictionary({});
      var R = {geometry: roi.bounds().buffer(MATCH_BUFFER), scale: OFFSET_SCALE, crs: CRS, maxPixels: 1e9,
               bestEffort: true, tileScale: 16};
      var rr = function (img, reducer) { return img.reduceRegion({reducer: reducer, geometry: R.geometry, scale: R.scale,
        crs: R.crs, maxPixels: R.maxPixels, bestEffort: R.bestEffort, tileScale: R.tileScale}); };
      for (var i = 1; i < GROUPS.length; i++) {
        var comp = p[i].comp, cur = priorityMosaic(matched);
        var both = cur.select('B2').mask().and(comp.select('B2').mask());
        var wat = cur.normalizedDifference(['B3', 'B8']).gt(WATER_NDWI).and(cur.select('B8').lt(WATER_NIR));
        var diff = cur.subtract(comp);
        var n = ee.Number(rr(both.and(wat).selfMask().rename('n'), ee.Reducer.count()).get('n'));
        var offW = rr(diff.updateMask(both.and(wat)), ee.Reducer.median());
        var fb = (NO_WATER_FALLBACK === 'all') ? rr(diff.updateMask(both), ee.Reducer.median()) : ee.Dictionary(zeros());
        var ch = ee.Dictionary(ee.Algorithms.If(n.gte(MIN_MATCH_PIXELS), offW, fb));
        var clean = ee.Dictionary.fromLists(BANDS, BANDS.map(function (b) {
          return ee.Algorithms.If(ee.Algorithms.IsEqual(ch.get(b), null), 0, ch.get(b)); }));
        res = res.set(KEYS[i], clean); nPix = nPix.set(KEYS[i], n);
        matched.push(comp.add(ee.Image.constant(clean.values(BANDS))).rename(BANDS).toFloat());
      }
      return ee.Dictionary({offsets: res, overlap_water_pixels: nPix});
    };
    var finish = function (offsets, doExport) {
      var p = parts(offsets);
      var comp = priorityMosaic(p.map(function (x) { return x.comp; })).select(BANDS);
      if (B1_FROM_B2) { comp = comp.addBands(comp.select(['B2'], ['B1']), null, true).select(BANDS); }
      var count = priorityMosaic(p.map(function (x) { return x.count; }));
      var src = priorityMosaic(p.map(function (x) { return x.src; }));
      var tstd = priorityMosaic(p.map(function (x) { return x.tstd; }));
      var invalid = comp.lt(0).or(comp.gt(1)).reduce(ee.Reducer.max()).rename('invalid_reflectance').toInt16();
      var qa = ee.Image.cat([count.rename('valid_count'), src, invalid]).toInt16();
      var rgb = {bands: ['B4', 'B3', 'B2'], min: 0, max: 0.15, gamma: 1.3};
      Map.addLayer(comp.clip(roi), rgb, 'Composite ' + TAG);
      Map.addLayer(comp.select('B2').clip(roi), {min: 0.02, max: 0.10, palette: ['000004','3b0f70','8c2981','de4968','fe9f6d','fcfdbf']},
                   'B2 blue (look for steps at tile edges)', false);
      Map.addLayer(src.clip(roi), {min: 1, max: Math.max(GROUPS.length, 2), palette: ['1b9e77','d95f02','7570b3','e7298a']},
                   'Source tile (' + KEYS.join(', ') + ')', false);
      Map.addLayer(count.clip(roi), {min: 0, max: 20, palette: ['d7191c','fdae61','ffffbf','a6d96a','1a9641']}, 'Clear observations', false);
      Map.addLayer(tstd.clip(roi), {min: 0, max: 0.02, palette: ['000000','ffff00','ff0000']},
                   'B2 temporal std (bright = water changed between dates)', false);
      if (!doExport) {
        print('PREVIEW. Check the seams (layer "B2 blue"), then copy the OFFSETS line into FIXED_OFFSETS and Run again to export.');
        return;
      }
      exportImage(comp.clip(roi).unmask(-9999).toFloat(), 'S2_' + TAG + '_12band_Float32', SCALE, -9999);
      exportImage(qa.clip(roi).unmask(-1), 'S2_' + TAG + '_QA', SCALE, -1);
      exportImage(tstd.clip(roi).unmask(-9999).toFloat(), 'S2_' + TAG + '_B2_TemporalStd', SCALE, -9999);
      print('Exports ready in the Tasks tab: 12-band composite, QA (clear obs, source tile, invalid flag), B2 temporal std.');
    };

    if (!MATCH) {
      finish(null, true);
    } else if (FIXED_OFFSETS !== null) {
      print('Using FIXED_OFFSETS', FIXED_OFFSETS);
      finish(FIXED_OFFSETS, true);
    } else {
      print('Measuring tile offsets at ' + OFFSET_SCALE + ' m ... (a few minutes)');
      measureOffsets().evaluate(function (r, err) {
        if (err) { print('Offset measurement failed:', err, 'Try OFFSET_SCALE = 200 or a smaller MATCH_BUFFER.'); return; }
        print('Overlap water pixels per tile (at ' + OFFSET_SCALE + ' m; < ' + MIN_MATCH_PIXELS + ' = offset not measured):',
              r.overlap_water_pixels);
        KEYS.slice(1).forEach(function (k) {
          var big = BANDS.filter(function (b) { return Math.abs(r.offsets[k][b]) > OFFSET_WARN; });
          if (big.length) { print('! ' + k + ': offset > ' + OFFSET_WARN + ' in ' + big.join(', ') + ' - check this seam'); }
        });
        print('OFFSETS (copy this line over FIXED_OFFSETS):', 'var FIXED_OFFSETS = ' + JSON.stringify(r.offsets) + ';');
        finish(r.offsets, false);
      });
    }
  }
}


// =====================================================================================
// C. Elevation: Copernicus DEM (DSM), FABDEM and DeltaDTM (bare earth); heights EGM2008
// =====================================================================================
if (RUN.DEM) {
  var dsm = copdem.select('DEM').map(function (i) { return i.resample('bilinear'); }).mosaic().rename('DSM');
  var wbm = copdem.select('WBM').mosaic().rename('WBM');
  var fab = ee.ImageCollection('projects/sat-io/open-datasets/FABDEM').filterBounds(roi)
              .select('b1').map(function (i) { return i.resample('bilinear'); }).mosaic().rename('FABDEM');
  var ddtm = ee.Image('projects/sat-io/open-datasets/DELTARES/deltadtm_v1-1').select(0).rename('DeltaDTM').resample('bilinear');
  ddtm = ddtm.updateMask(ddtm.neq(30));        // 30 = above the 30 m coastal range (clipped)
  print('DEM stats over the AOI (m: P2, P50, P98)', ee.Image.cat(dsm, fab, ddtm).reduceRegion({
    reducer: ee.Reducer.percentile([2, 50, 98]), geometry: roi, scale: 90, maxPixels: 1e9, bestEffort: true, tileScale: 4}));
  var ev = {min: 0, max: 30, palette: ['08306b','2171b5','6baed6','c7e9c0','74c476','238b45','fdae61','d7191c']};
  Map.addLayer(dsm.clip(roi), ev, 'DSM Copernicus DEM', false);
  Map.addLayer(fab.clip(roi), ev, 'FABDEM bare earth', false);
  Map.addLayer(ddtm.clip(roi), ev, 'DeltaDTM coastal bare earth', false);
  exportImage(dsm.clip(roi).unmask(-9999).toFloat(), 'CopDEM_' + COPDEM.split('/').pop() + '_DSM_EGM08', DEM_SCALE, -9999);
  exportImage(wbm.clip(roi).unmask(255).toUint8(), 'CopDEM_WaterBodyMask', DEM_SCALE, 255);
  if (EXPORT_FABDEM) {
    exportImage(fab.clip(roi).unmask(-9999).toFloat(), 'FABDEM_EGM08', DEM_SCALE, -9999);
    exportImage(dsm.subtract(fab).rename('DSM_minus_FABDEM').clip(roi).unmask(-9999).toFloat(), 'DSM_minus_FABDEM', DEM_SCALE, -9999);
  }
  if (EXPORT_DELTADTM) { exportImage(ddtm.clip(roi).unmask(-9999).toFloat(), 'DeltaDTM_v1-1_EGM08', DEM_SCALE, -9999); }
  print('DEM exports ready (EGM2008 heights). FABDEM comes from an earlier GLO-30 release than ' + COPDEM + '.');
}


// =====================================================================================
// D. Habitats: Allen Coral Atlas, Global Mangrove Watch, mangrove canopy height
// =====================================================================================
var gmwImg = ee.ImageCollection('projects/sat-io/open-datasets/GMW/annual-extent/GMW_MNG_2020')
               .filterBounds(roi).mosaic().select([0], ['mangrove']).unmask(0);
if (RUN.HABITATS) {
  var aca = ee.Image('ACA/reef_habitat/v2_0');
  var hmax = ee.ImageCollection('projects/sat-io/open-datasets/global_mangrove_distribution/hmax95')
               .filterBounds(roi).mosaic().select([0], ['hmax95_m']);
  var area = function (m) { return ee.Image.pixelArea().divide(1e6).updateMask(m).reduceRegion({
    reducer: ee.Reducer.sum(), geometry: roi, scale: 30, maxPixels: 1e10, bestEffort: true, tileScale: 4}).values().get(0); };
  print('km2 in the AOI: seagrass (ACA 14)', area(aca.select('benthic').eq(14)), 'coral/algae (ACA 15)',
        area(aca.select('benthic').eq(15)), 'mangrove (GMW 2020)', area(gmwImg.eq(1)));
  Map.addLayer(aca.select('benthic').clip(roi), {min: 11, max: 18,
               palette: ['ffffbe','e0d05e','b19c3a','668438','ff6161','000000','000000','9bcc4f']}, 'ACA benthic', false);
  Map.addLayer(gmwImg.selfMask().clip(roi), {palette: ['228B22']}, 'Mangroves GMW 2020', false);
  exportImage(aca.select('benthic').unmask(0).clip(roi).toUint8(), 'ACA_v2_benthic_5m', 5, null);
  exportImage(aca.select('geomorphic').unmask(0).clip(roi).toUint8(), 'ACA_v2_geomorphic_5m', 5, null);
  exportImage(aca.select('reef_mask').unmask(0).clip(roi).toUint8(), 'ACA_v2_reef_mask_5m', 5, null);
  exportImage(gmwImg.clip(roi).toUint8(), 'GMW_v4_mangrove_2020_10m', 10, null);
  exportImage(hmax.clip(roi).unmask(-9999).toFloat(), 'Mangrove_hmax95_Simard2019_30m', 30, -9999);
  print('Habitat exports ready. ACA benthic: 11 sand, 12 rubble, 13 rock, 14 seagrass, 15 coral/algae, 18 microalgal mats, 0 unmapped.');
}


// =====================================================================================
// E. Files for the ICESat-2 Colab tool: land polygons (SHORELINE_FILE), mangroves (MANGROVE_FILE)
// =====================================================================================
if (RUN.ICESAT2_FILES) {
  var landArea = roi.bounds().buffer(LAND_BUFFER);
  var land = waterRef.not().selfMask().rename('land');
  var landVec = land.reduceToVectors({geometry: landArea, crs: CRS, crsTransform: grid(DEM_SCALE), geometryType: 'polygon',
                                     eightConnected: false, maxPixels: 1e10, tileScale: 4});
  Export.table.toDrive({collection: landVec, description: PREFIX + '_land_polygons_CopDEM', folder: DRIVE_FOLDER,
                        fileFormat: 'GeoJSON'});
  var mgVec = ee.FeatureCollection('projects/sat-io/open-datasets/GMW/annual-extent/GMW_MNG_VEC_2020').filterBounds(landArea);
  Export.table.toDrive({collection: mgVec, description: PREFIX + '_GMW_v4_mangrove_2020_polygons', folder: DRIVE_FOLDER,
                        fileFormat: 'GeoJSON'});
  Map.addLayer(land.clip(landArea), {palette: ['8c6d31']}, 'Land (Copernicus DEM water mask)', false);
  print('ICESat-2 files ready: land polygons (30 m, AOI + ' + LAND_BUFFER + ' m) -> ATL24 SHORELINE_FILE;',
        'GMW 2020 mangrove polygons -> ATL08 MANGROVE_FILE.');
}
