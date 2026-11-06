import {DATASET_FILE_GROUPS} from './dataset-schema.js';
export const TABLES={
  reef:[
    {id:'targets',name:'Scale-bar targets',help:'Three depth readings at the centre of each target; record the time for tide correction.',columns:['Target code','Tape position (m)','Side (L/R)','Depth 1 (m)','Depth 2 (m)','Depth 3 (m)','Time'],seed:[['T01','','','','','','']]},
    {id:'depth_profile',name:'Depth profile',help:'Every 2 m, at both sensors, and 5–10 m beyond 30 m.',columns:['Tape position (m)','Depth (m)','Time'],seed:[...Array.from({length:21},(_,i)=>[String(i*2),'','']),['sensor 1','',''],['sensor 2','','']]},
  ],
  mangrove:[
    {id:'topography',name:'Topography',help:'Cumulative slope distance from low water; inclination of the segment leading to the station, positive uphill landward. At most 2 m between stations.',columns:['Station','Distance (m)','Inclination (degrees)','Label'],seed:[['1','','','low water']]},
    {id:'scale_bars',name:'Method A · Scale bars',method:'A',columns:['Bar','Target codes','Tape position (m)','Side (L/R)'],seed:[['1','','','']]},
    {id:'tree_b',name:'Method B · Tree measurements',method:'B',help:'All heights and lengths in cm; diameters in cm. W1–W6 are trunk-to-outermost-root distances in six directions; d20 is mean root diameter at 20 cm.',columns:['Plot','Tree','Height (cm)','Crown base (cm)','DBH (cm)','D1 (cm)','Root-system height (cm)','W1 (cm)','W2 (cm)','W3 (cm)','W4 (cm)','W5 (cm)','W6 (cm)','Prop roots reaching ground (n)','d20 (cm)','Photos (Y/N)'],seed:[['front','1',...Array(14).fill('')]]},
    {id:'plots_c',name:'Method C · Plots',method:'C',help:'Record the measurement height for DBH if above the highest prop root. Pneumatophore quadrats: record size and heights/diameters of up to 20.',columns:['Plot','Trees (n)','Species','DBH of each tree (cm)','Quadrat size','Pneumatophores (n)','Pneumatophore heights/diameters (cm)'],seed:['front','centre','back'].map(p=>[p,...Array(6).fill('')])},
    {id:'roots_c',name:'Method C · Roots by height',method:'C',help:'Repeat all five heights for each sampled tree. Root-system, crown-base and tree heights in cm.',columns:['Plot / tree','Hroot / CB / H (cm)','Height (cm)','Roots crossing (n)','Root diameters (cm)','Trunk diameter (cm)'],seed:['25','50','75','100','150'].map(h=>['front 1','',h,'','',''])},
  ],
  seagrass:[
    {id:'depth_cover',name:'Depth and cover',help:'Every 2 m and at both sensors. Cover: bare, patchy or continuous; optional if assessed later from photos.',columns:['Tape position (m)','Depth (m)','Time','Photo taken (Y/N)','Cover'],seed:[...Array.from({length:21},(_,i)=>[String(i*2),'','','','']),['sensor 1','','','',''],['sensor 2','','','','']]},
    {id:'quadrats',name:'Quadrat records',help:'Front: 2.5 m; centre: 15 m; back: 27.5 m. Left/right are 2 m off the tape. Record the actual position and movement to reach seagrass.',columns:['Quadrat','Tape position (m)','Moved (m)','Photo 1 (Y/N)','Photo 2 (Y/N)','Canopy 1 (cm)','Canopy 2 (cm)','Canopy 3 (cm)','Other species','Thickness stack (mm)','Blades in stack (n)'],seed:[['F','2.5'],['C','15'],['B','27.5']].flatMap(([p,d])=>['L','C','R'].map(side=>[p+'-'+side,d,...Array(9).fill('')]))},
    {id:'shoots',name:'Shoot measurements',help:'Five shoots per quadrat: longest blade held straight; width at mid-length. Plants remain in place.',columns:['Quadrat','Shoot','Blades (n)','Longest blade length (cm)','Longest blade width (mm)'],seed:['F-L','F-C','F-R','C-L','C-C','C-R','B-L','B-C','B-R'].flatMap(q=>Array.from({length:5},(_,i)=>[q,String(i+1),'','','']))},
  ],
  bathy:[],
  drone:[
    {id:'flights',name:'Flights',help:'One row per battery. Altitude above take-off; overlap along/across track in percent.',columns:['Flight','Start','End','Altitude (m)','Overlap along/across (%)','Photos (n)','Notes'],seed:[['1','','','','','','']]},
    {id:'ground_targets',name:'Ground targets',help:'4–5 targets spread across the area; position with handheld GNSS, averaged for about a minute.',columns:['Target','Latitude','Longitude','Notes'],seed:Array.from({length:5},(_,i)=>['T'+(i+1),'','',''])},
  ],
  waves:[
    {id:'deployment',name:'Sensor deployment',help:'Start and depth observation times are UTC. Port height above bottom; T/S are water temperature and salinity if measured.',columns:['Position','Sensor ID','Start (UTC)','Depth (m)','Depth time (UTC)','Port (cm)','Fixing','Photo','Temperature / salinity'],seed:[]},
    {id:'retrieval',name:'Sensor retrieval',help:'Use ISO date YYYY-MM-DD. End and depth observation times are UTC. Record whether sensor remained in place.',columns:['Position','Retrieval date','End (UTC)','Depth (m)','Depth time (UTC)','Data filename','OK (Y/N)','Notes'],seed:[]},
  ],
};
const positions=['Reef S1 (0 m)','Reef S2 (30 m)','Reef PC (post-crest)','Seagrass S1 (0 m)','Seagrass S2 (30 m)','Mangrove S1 (0 m)','Mangrove S2 (30 m)'];
TABLES.waves[0].seed=positions.map(p=>[p,...Array(8).fill('')]);
TABLES.waves[1].seed=positions.map(p=>[p,...Array(7).fill('')]);
export const FILE_GROUPS={
  reef:[['camA','Camera A photos'],['camB','Camera B photos'],['field_sheets','Slate / field-sheet photos']],
  mangrove:[['camA','Camera A photos'],['camB','Camera B photos'],['structure','Structure / tree photos'],['topography','Topography files'],['field_sheets','Slate / field-sheet photos']],
  seagrass:[['cover','Depth / cover photos'],['quadrats','Quadrat photos'],['field_sheets','Slate photos']],
  bathy:[['scan','Depth scan CSV'],['gps','GPS track GPX'],['photos','Bottom photos'],['reference','Clock reference photos']],
  drone:[['photos','Survey photos'],['targets','Ground target positions'],['field_sheets','Field-sheet photos']],
  waves:[['sensors','Sensor data'],['barometric','Barometric data'],['deployment','Deployment / retrieval photos'],['field_sheets','Field-sheet photos']],
};
TABLES.sat=[];
/* File categories of a draft: per survey type, or per product for satellite-derived datasets. */
export function fileGroupsFor(state){return state.type==='sat'?(DATASET_FILE_GROUPS[state.values?.product]||DATASET_FILE_GROUPS.Other):FILE_GROUPS[state.type];}
export function visibleTables(type,values){return TABLES[type].filter(t=>!t.method||String(values.structure_method||'').includes(t.method));}
