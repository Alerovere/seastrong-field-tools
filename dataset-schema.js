/* Satellite-derived datasets: a submission type for processed products (not field surveys).
   Records go to <Area>/Satellite datasets/<dataset ID>/ with an explicit ID, e.g. BZ-S2composite-2026-11-06. */

// Product codes appear in the dataset ID; keep them short, letters and digits only.
export const PRODUCTS = [
  ['S2composite', 'Sentinel-2 composite (Bathymetrix-AI input)'],
  ['ICESat2', 'ICESat-2 depths and ground heights'],
  ['SDBmap', 'Satellite-derived bathymetry map (Bathymetrix-AI output)'],
  ['DEM', 'Elevation (DSM, FABDEM, DeltaDTM)'],
  ['Habitats', 'Habitat layers (corals, seagrass, mangroves)'],
  ['WaveClimate', 'Wave, wind and tide climate / XBeach cases'],
  ['Other', 'Other satellite-derived dataset'],
];
export const PRODUCT_CODES = PRODUCTS.map(([code]) => code);
export const DATASET_FOLDER = 'Satellite datasets';

const common = [['readme', 'README, settings and processing notes'], ['figures', 'Figures']];
export const DATASET_FILE_GROUPS = {
  S2composite: [['main', 'Composite GeoTIFF (12-band)'], ['qa', 'QA raster and blue temporal std'], ['screening', 'Date screening and EXCLUDE_DATES tables'], ...common],
  ICESat2: [['train_valid', 'ATL24 training and validation GeoPackages'], ['all_flags', 'ATL24 all photons with QC flags'], ['lock', 'Hold-out lock file (JSON)'], ['atl08', 'ATL08 ground and canopy'], ['coverage', 'Download and coverage tables'], ...common],
  SDBmap: [['main', 'Depth map GeoTIFF'], ['uncertainty', 'Uncertainty / error rasters'], ['validation', 'Validation tables and statistics'], ['project', 'Bathymetrix-AI project and settings'], ...common],
  DEM: [['main', 'Elevation rasters'], ['masks', 'Water mask and land polygons'], ...common],
  Habitats: [['rasters', 'Habitat rasters'], ['vectors', 'Habitat polygons'], ...common],
  WaveClimate: [['tables', 'Climate tables and Excel workbook'], ['xbeach', 'XBeach case folders'], ['series', 'Downloaded point series'], ...common],
  Other: [['main', 'Main dataset files'], ...common],
};

export const REVIEW_STATUSES = [['draft', 'Draft · not reviewed'], ['checked', 'Checked'], ['approved', 'Approved']];
export const REVIEW_LABEL = Object.fromEntries(REVIEW_STATUSES);

/* Who may set a review status: 'checked' = anyone except the producer; 'approved' = only an approver
   (CONFIG.approvers); 'draft' (withdraw a review) = an approver. Returns '' if allowed, else the reason. */
export function reviewDenied(status, actor, producerId, approvers = []) {
  const email = String(actor?.emailAddress || '').toLowerCase();
  const isApprover = approvers.map(a => String(a).toLowerCase()).includes(email);
  if (!REVIEW_LABEL[status]) return 'Unknown review status.';
  if (!actor?.permissionId) return 'Sign in again to review.';
  if (status === 'approved' || status === 'draft') return isApprover ? '' : 'Only the dataset approver can set this status.';
  if (status === 'checked' && actor.permissionId === producerId && !isApprover) return 'A dataset must be checked by someone other than its producer.';
  return '';
}

/* Approved first, then checked, then drafts; newest first within each status. */
export function sortDatasets(groups) {
  const rank = {approved: 0, checked: 1, draft: 2};
  const st = v => rank[v[0].appProperties?.reviewStatus || 'draft'] ?? 2;
  return [...groups].sort((a, b) => st(a) - st(b) || String(b[0].modifiedTime || '').localeCompare(a[0].modifiedTime || ''));
}

export const DATASET = {
  name: 'Satellite-derived dataset',
  pdf: null,
  sourceVersion: '1.0',
  fields: [
    {id: 'aoi_name', label: 'Area of interest (name or file)', section: '1. What the dataset covers', help: 'e.g. Belize south AOI (aoi_belize_south.geojson)', options: [], kind: 'text'},
    {id: 'period', label: 'Data period', section: '1. What the dataset covers', help: 'First and last date of the data used, e.g. 2020-02-01 to 2026-04-30', options: [], kind: 'text'},
    {id: 'months', label: 'Months used', section: '1. What the dataset covers', help: 'e.g. Feb-Apr (dry season); all months', options: [], kind: 'text'},
    {id: 'crs', label: 'Map projection (CRS)', section: '1. What the dataset covers', help: 'e.g. EPSG:32616 (UTM 16N)', options: [], kind: 'text'},
    {id: 'resolution', label: 'Resolution', section: '1. What the dataset covers', help: 'e.g. 10 m; 100 m segments; point data', options: [], kind: 'text'},
    {id: 'vertical_datum', label: 'Vertical reference', section: '1. What the dataset covers', help: 'Heights and depths', options: ['EGM2008 geoid', 'Model mean sea level (GTSM 1986-2005)', 'Chart datum', 'Local survey datum', 'WGS84 ellipsoid', 'Not applicable'], kind: 'text'},
    {id: 'tool_version', label: 'Tool and version', section: '2. How it was made', help: 'e.g. seastrong_sdb_inputs.js (rev. 2026-11-05); icesat2_tool 0.1.0; wave_climate 0.2.0; Bathymetrix-AI 8.0', options: [], kind: 'text'},
    {id: 'settings', label: 'Key settings (description)', section: '2. How it was made', help: 'Options that differ from the defaults, or "see README"', options: [], kind: 'long'},
    {id: 'inputs', label: 'Inputs used (description)', section: '2. How it was made', help: 'Datasets and records it was made from, e.g. BZ-S2composite-2026-11-06 and BZ-ICESat2-2026-11-08', options: [], kind: 'long'},
    {id: 'qc_summary', label: 'Quality checks and results (description)', section: '3. Quality', help: 'e.g. QA clear observations P10/P50/P90; ICESat-2 photons kept; validation RMSE by depth band', options: [], kind: 'long'},
    {id: 'known_issues', label: 'Known issues and limitations (description)', section: '3. Quality', help: 'e.g. seam at tile 16PBC; turbid plume near river mouth', options: [], kind: 'long'},
  ],
  checklists: [
    {title: '4. Before submitting', items: [
      'Files open correctly (rasters in QGIS, tables in a spreadsheet)',
      'Map projection, resolution and NoData value checked',
      'README / settings file included, with tool version and date',
      'Vertical reference stated for any heights or depths',
      'Quality figures or tables included',
    ]},
  ],
};
