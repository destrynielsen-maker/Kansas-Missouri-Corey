"use strict";

const DATA_URL = "./data/permits.json";
const BUILDERS_URL = "./data/builders.json";
const BUILDER_RANKINGS_URL = "./data/builder_rankings.json";
const SALES_COVERAGE_URL = "./data/sales_field_coverage.json";
const COVERAGE_URL = "./data/coverage.json";
const LENEXA_PLANNING_URL = "./data/lenexa_planning.json";
const LENEXA_PORTAL_URL = "https://aca-prod.accela.com/LENEXA/Default.aspx";
const SOURCE_MONITOR_URL = "./data/source_health.json";
const WORKFLOW_URL = "https://github.com/destrynielsen-maker/Kansas-Missouri-Corey/actions/workflows/refresh.yml";
const els = {};
const fields = ["search","state","city","category","days","score","sort","activity","followup","viewmode","builderstatus"];
let snapshot = null;
let filtered = [];
let filteredPermits = [];
let siteRowsById = new Map();
let builderResearch = new Map();
let builderResearchLoaded = false;
let lenexaPlanning = null;
let lenexaFiltered = [];

function el(id){ return document.getElementById(id); }
function text(id,value){ el(id).textContent = value; }
function asString(v){ return v == null ? "" : String(v); }
function safeLink(url){ return typeof url === "string" && /^https:\/\/[A-Za-z0-9.-]+(?=[:/]|$)/.test(url) ? url : null; }
function dateLocal(iso){
  if (!iso || !/^\d{4}-\d{2}-\d{2}$/.test(iso)) return null;
  const p=iso.split("-").map(Number);
  return new Date(p[0],p[1]-1,p[2]);
}
function money(n){ return typeof n === "number" && Number.isFinite(n) ? "$" + Math.round(n).toLocaleString("en-US") : "—"; }
function toast(message){
  const t=el("toast"); t.textContent=message; t.style.display="block";
  clearTimeout(toast.timer); toast.timer=setTimeout(function(){t.style.display="none";},3200);
}
function cell(row,value,className){
  const c=document.createElement("td");
  if(className)c.className=className;
  c.textContent=asString(value);
  row.appendChild(c);
  return c;
}
function linkCell(row,url,label,kind,permitNo){
  const c=document.createElement("td");
  const target=safeLink(url);
  if(target){
    const a=document.createElement("a");
    a.href=target; a.target="_blank"; a.rel="noopener noreferrer"; a.textContent=label;
    a.className=kind==="source"?"source-link":"primary-permit";
    a.title=kind==="source"?"Official agency data; may open the full dataset, not a single permit record":kind==="search"?"Public portal search: enter permit number; not a direct record":"Agency-published direct record";
    c.appendChild(a);
  }else c.textContent="Not available";
  if(kind==="search" && permitNo){
    const copy=document.createElement("button");
    copy.type="button";copy.className="copy";copy.textContent="Copy " + permitNo;
    copy.addEventListener("click",function(){
      if(navigator.clipboard && navigator.clipboard.writeText){
        navigator.clipboard.writeText(permitNo).then(function(){toast("Copied permit " + permitNo);}).catch(function(){toast("Permit number: " + permitNo);});
      }else toast("Permit number: " + permitNo);
    });
    c.appendChild(copy);
  }
  row.appendChild(c);
}
function daysSinceIssued(issued){
  const date=dateLocal(issued);
  if(!date)return null;
  const now=new Date();now.setHours(0,0,0,0);
  return Math.max(0,Math.floor((now-date)/86400000));
}
function followupBand(age){
  if(age==null)return {key:"unknown",text:"Date unavailable",className:"later"};
  if(age<=7)return {key:"0-7",text:"Contact now",className:""};
  if(age<=30)return {key:"8-30",text:"Contact this week",className:""};
  if(age<=90)return {key:"31-90",text:"Follow up",className:"middle"};
  return {key:"91+",text:"Older prospect",className:"later"};
}
function evidenceKind(item){
  if(item.inspection_evidence==="inspection_recorded" && item.last_inspection_date)return "inspection_recorded";
  if(item.inspection_evidence==="date_not_reported")return "date_not_reported";
  return "field_not_published";
}
function followupCell(row,item){
  const td=cell(row,"");
  const badge=document.createElement("span");
  const bucket=followupBand(daysSinceIssued(item.issued));
  badge.className="followup-tag "+bucket.className;
  badge.textContent=bucket.text;td.appendChild(badge);
  const note=document.createElement("span");
  note.className="activity-note";
  const age=daysSinceIssued(item.issued);
  note.textContent=age===null?"Issue date unknown":age+" day"+(age===1?"":"s")+" since issued";
  td.appendChild(note);
}
function officialActivityCell(row,item){
  const td=cell(row,"");
  const label=document.createElement("span");
  const note=document.createElement("span");
  note.className="activity-note";
  if(evidenceKind(item)==="inspection_recorded"){
    label.className="activity-label";label.textContent="Inspection recorded";
    note.textContent="Last: "+item.last_inspection_date;
  }else if(evidenceKind(item)==="date_not_reported"){
    label.className="activity-muted";label.textContent="No inspection date";
    note.textContent="Agency field is blank";
  }else{
    label.className="activity-muted";label.textContent="Not published";
    note.textContent="No inspection field in source";
  }
  td.appendChild(label);td.appendChild(note);
}
function otherDatesCell(row,item){
  const td=cell(row,"");
  const parts=[];
  if(item.application_date)parts.push("Applied "+item.application_date);
  if(item.expiration_date)parts.push("Expires "+item.expiration_date);
  if(!parts.length){td.textContent="Not published";td.className="city";return;}
  for(const part of parts){
    const span=document.createElement("span");
    span.className="activity-note";span.textContent=part;td.appendChild(span);
  }
}

function siteKey(item){
  // The server refuses fuzzy matches. Without a vetted server site ID,
  // do NOT merge different permits based on a guess in the browser.
  return typeof item.site_group_id==="string" && item.site_group_id.startsWith("site-")
    ? item.site_group_id : "permit:"+asString(item.id);
}
function groupSiteRows(rows){
  const groups=new Map();
  for(const row of rows){
    const key=siteKey(row);
    if(!groups.has(key))groups.set(key,[]);
    groups.get(key).push(row);
  }
  return groups;
}
function siteMatchCell(row,item){
  const td=cell(row,"");
  const members=siteRowsById.get(siteKey(item))||[item];
  if(item.site_group_basis==="unverified_address"){
    td.textContent="Address unverified";
    td.className="city";return;
  }
  const label=document.createElement("span");
  label.className=members.length>1?"sitecount":"activity-muted";
  label.textContent=members.length===1?"1 permit in filter":members.length+" permits at same address";
  td.appendChild(label);
  if(members.length>1){
    const details=document.createElement("details");
    details.className="sitedetails";
    const summary=document.createElement("summary");
    summary.textContent="Show matching permit numbers";
    details.appendChild(summary);
    const list=document.createElement("ul");
    for(const member of members){
      const li=document.createElement("li");
      li.textContent=member.permit_number+(member.id===item.id?" (displayed)":"");
      list.appendChild(li);
    }
    details.appendChild(list);
    td.appendChild(details);
  }
}


function normalizedBuilderAddress(v){
  return asString(v).trim().toUpperCase().replace(/[.,]/g,"").replace(/\s+/g," ");
}
function builderForPermit(item){
  const b=builderResearch.get(asString(item?.id));
  if(!b || typeof b.builder!=="string" || !b.builder.trim())return null;
  if(b.id!==item.id || b.issued!==item.issued || b.jurisdiction!==item.jurisdiction)return null;
  if(normalizedBuilderAddress(b.address)!==normalizedBuilderAddress(item.address))return null;
  return b;
}
function salesDetailUrl(item){
  return "./permit.html?id="+encodeURIComponent(asString(item.id));
}
function builderBasisLabel(b){
  if(!b)return "Not established";
  return b.evidence_type==="project_gc_announcement"?"GC in project announcement"
    :b.evidence_type==="planning_drawing"?"Planning drawing attribution"
    :b.evidence_type==="exact_address_listing"?"Exact-address listing":"Independent research";
}
function builderCell(row,item){
  const td=cell(row,"");
  const match=builderForPermit(item);
  if(!match){
    const label=document.createElement("span");
    label.className="builder-missing";label.textContent="Builder not verified";
    td.appendChild(label);
    const hint=document.createElement("span");hint.className="activity-note";
    hint.textContent=builderResearchLoaded?"Check official permit search":"Research overlay unavailable";
    td.appendChild(hint);return;
  }
  const name=document.createElement("span");name.className="builder-name";name.textContent=match.builder;
  td.appendChild(name);
  const provenance=document.createElement("span");provenance.className="activity-note";
  provenance.textContent=builderBasisLabel(match)+" · not permit-verified";
  td.appendChild(provenance);
  const evidence=safeLink(match.evidence_url);
  if(evidence){
    const link=document.createElement("a");link.href=evidence;link.target="_blank";link.rel="noopener noreferrer";
    link.className="builder-evidence";link.textContent="Evidence ↗";td.appendChild(link);
  }
}
async function loadBuilderResearch(){
  builderResearch=new Map();
  builderResearchLoaded=false;
  try{
    const r=await fetch(BUILDERS_URL+"?v="+Date.now(),{cache:"no-store"});
    if(!r.ok)throw new Error("Builder research unavailable");
    const data=await r.json();
    if(!data || !Array.isArray(data.entries) || data.entries.length>5000)throw new Error("Unexpected builder research shape");
    for(const item of data.entries){
      if(!item || typeof item.id!=="string" || typeof item.builder!=="string" ||
         typeof item.issued!=="string" || typeof item.jurisdiction!=="string" ||
         typeof item.address!=="string" || !safeLink(item.evidence_url) ||
         !["project_gc_announcement","planning_drawing","exact_address_listing"].includes(item.evidence_type) ||
         builderResearch.has(item.id))throw new Error("Builder research evidence invalid or duplicated");
      builderResearch.set(item.id,item);
    }
    builderResearchLoaded=true;
  }catch(e){
    builderResearch=new Map();
    builderResearchLoaded=false;
  }
}

function renderTable(rows){
  const tbody=el("leadrows"); tbody.replaceChildren();
  if (!rows.length){
    const tr=document.createElement("tr");
    const td=cell(tr,snapshot && snapshot.generated_at?"No permits match these filters. Try a larger date window or a different city.":"No verified data snapshot yet. Run the GitHub refresh workflow to populate this dashboard.","empty");
    td.colSpan=14; tbody.appendChild(tr); text("row-limit","");return;
  }
  const display=rows.slice(0,300);
  const frag=document.createDocumentFragment();
  for (const item of display){
    const tr=document.createElement("tr");
    const score=cell(tr,"");
    const mark=document.createElement("span");
    mark.className="score " + (item.score>=75?"high":item.score>=50?"mid":"");
    mark.textContent=asString(item.score);score.appendChild(mark);
    cell(tr,item.issued || "—");
    const idCell=cell(tr,"");
    const number=document.createElement("div");
    number.className="permitno";
    const detail=document.createElement("a");
    detail.href=salesDetailUrl(item);detail.textContent=item.permit_number||"View project";
    detail.title="Open this project's formatted permit details";number.appendChild(detail);
    idCell.appendChild(number);
    if(item.project){
      const project=document.createElement("div");
      project.className="project";project.textContent=item.project;project.title=item.project;
      idCell.appendChild(project);
    }
    siteMatchCell(tr,item);
    cell(tr,item.address || "Address not published");
    builderCell(tr,item);
    cell(tr,item.jurisdiction || "—","city");
    const typecell=cell(tr,"");
    const pill=document.createElement("span");
    pill.className="type " + (item.category==="Single-family"?"Single-family":item.category==="Multifamily"?"Multifamily":item.category==="Commercial"?"Commercial":"");
    pill.textContent=item.category||"Other";
    typecell.appendChild(pill);
    cell(tr,money(item.valuation));
    officialActivityCell(tr,item);
    otherDatesCell(tr,item);
    followupCell(tr,item);
    linkCell(tr,item.permit_url,item.link_kind==="record"?"View permit ↗":"Search permit ↗",item.link_kind,item.permit_number);
    linkCell(tr,item.source_url,item.source_url_scope==="dataset"?"Raw dataset ↗":"Raw source ↗","source");
    frag.appendChild(tr);
  }
  tbody.appendChild(frag);
  text("row-limit",rows.length>300?"Showing first 300; CSV export includes all " + rows.length.toLocaleString() + " filtered permits.":"Showing all " + rows.length.toLocaleString() + " matching permits.");
}
function setCityOptions(){
  const select=el("city");
  const prev=select.value;
  const state=el("state").value;
  select.replaceChildren();
  const o=document.createElement("option");o.value="";o.textContent="All cities";select.appendChild(o);
  const names=Array.from(new Set((snapshot?.permits||[]).filter(function(x){return !state||x.state===state;}).map(function(x){return x.jurisdiction;}))).sort();
  for(const name of names){const opt=document.createElement("option");opt.value=name;opt.textContent=name;select.appendChild(opt);}
  if(names.includes(prev))select.value=prev;
}
function applyFilters(){
  if(!snapshot || !snapshot.generated_at){
    renderTable([]);text("resultcount","Awaiting initial validated feed run."); return;
  }
  const q=el("search").value.trim().toLowerCase();
  const state=el("state").value;
  const city=el("city").value;
  const cat=el("category").value;
  const days=Number(el("days").value);
  const score=Number(el("score").value);
  const activity=el("activity").value;
  const followup=el("followup").value;
  const builderStatus=el("builderstatus").value;
  const today=new Date();today.setHours(0,0,0,0);
  filteredPermits=(snapshot.permits||[]).filter(function(p){
    if(state && p.state!==state) return false;
    if(city && p.jurisdiction!==city) return false;
    if(cat && p.category!==cat) return false;
    if((p.score||0)<score) return false;
    if(builderStatus==="sourced" && !builderForPermit(p))return false;
    if(builderStatus==="missing" && builderForPermit(p))return false;
    if(activity && evidenceKind(p)!==activity)return false;
    if(followup && followupBand(daysSinceIssued(p.issued)).key!==followup)return false;
    const d=dateLocal(p.issued);
    if(!d || Math.floor((today-d)/86400000)>days) return false;
    if(q && ![p.permit_number,p.address,p.jurisdiction,p.project,p.work_class,p.permit_type,p.county,builderForPermit(p)?.builder].some(function(x){return asString(x).toLowerCase().includes(q);}))return false;
    return true;
  });
  const order=el("sort").value;
  filteredPermits.sort(function(a,b){
    if(order==="newest") return asString(b.issued).localeCompare(asString(a.issued))||b.score-a.score;
    if(order==="value") return (b.valuation||0)-(a.valuation||0)||b.score-a.score;
    if(order==="activity") return asString(b.last_inspection_date||b.issued).localeCompare(asString(a.last_inspection_date||a.issued))||b.score-a.score;
    if(order==="followup") return asString(b.issued).localeCompare(asString(a.issued))||b.score-a.score;
    return b.score-a.score||asString(b.issued).localeCompare(asString(a.issued));
  });
  siteRowsById=groupSiteRows(filteredPermits);
  filtered=(el("viewmode").value==="site")
    ? Array.from(siteRowsById.values()).map(function(group){return group[0];})
    : filteredPermits.slice();
  const viewName=el("viewmode").value==="site"?"site opportunities":"permit records";
  text("resultcount",filtered.length.toLocaleString()+" "+viewName+" from "+
       filteredPermits.length.toLocaleString()+" permits • "+days+"-day view");
  text("metric-total",filteredPermits.length.toLocaleString());
  text("metric-sites",siteRowsById.size.toLocaleString());
  text("metric-total-sub","Official permit records after filters");
  text("metric-homes",filteredPermits.filter(function(x){return x.category==="Single-family";}).length.toLocaleString());
  text("metric-multis",filteredPermits.filter(function(x){return x.category==="Multifamily";}).length.toLocaleString());
  text("metric-priority",filteredPermits.filter(function(x){return x.score>=75;}).length.toLocaleString());
  text("metric-inspections",filteredPermits.filter(function(x){return evidenceKind(x)==="inspection_recorded";}).length.toLocaleString());
  renderTable(filtered);el("export").disabled=!filtered.length;
}
function csvEsc(v){
  let str=asString(v);
  if(/^\s*[=+\-@]/.test(str))str="'"+str;
  return '"' + str.replace(/"/g,'""') + '"';
}
function exportCsv(){
  if(!filtered.length)return;
  const columns=[
    ["Score","score"],["Issued","issued"],["State","state"],["Jurisdiction","jurisdiction"],["County","county"],
    ["Permit number","permit_number"],["Site group ID","site_group_id"],["Site match evidence","site_group_basis"],
    ["Site permits - 120 day source","site_permit_count"],["Site permits in selected filters","_site_count"],
    ["Related permit numbers in selected filters","_site_numbers"],["Builder / GC (independent source)","_builder"],["Builder evidence basis","_builder_basis"],["Builder evidence URL","_builder_url"],["Builder qualification","_builder_caveat"],["Formatted permit details","_details"],["Project","project"],["Address","address"],["Category","category"],
    ["Permit type","permit_type"],["Work class","work_class"],["Status","status"],["Valuation","valuation"],
    ["Units","units"],["Square feet","square_feet"],["Application date","application_date"],["Last inspection","last_inspection_date"],["Expiration date","expiration_date"],["Activity evidence","inspection_evidence"],["Start date - verified only","start_date"],["Timeline warnings","timeline_warnings"],["Public permit / search","permit_url"],
    ["Link type","link_kind"],["Raw data scope","source_url_scope"],["Permit status evidence","status_source"],["Raw source data","source_url"]];
  columns.push(["Sales follow-up suggestion","_followup"]);
  const lines=[columns.map(function(x){return csvEsc(x[0]);}).join(",")];
  for(const r of filtered)lines.push(columns.map(function(x){
    const key=x[1], members=siteRowsById.get(siteKey(r))||[r];
    const val=key==="_followup"?followupBand(daysSinceIssued(r.issued)).text
      :key==="_site_count"?members.length
      :key==="_site_numbers"?members.map(function(p){return p.permit_number;}).join("; ")
      :key==="_builder"?(builderForPermit(r)?.builder||"")
      :key==="_builder_basis"?builderBasisLabel(builderForPermit(r))
      :key==="_builder_url"?(builderForPermit(r)?.evidence_url||"")
      :key==="_builder_caveat"?(builderForPermit(r)?.qualification||"")
      :key==="_details"?new URL(salesDetailUrl(r),document.baseURI).href
      :key==="timeline_warnings"?(r.timeline_warnings||[]).join("; ")
      :r[key];
    return csvEsc(val);
  }).join(","));
  const blob=new Blob(["\ufeff"+lines.join("\r\n")],{type:"text/csv;charset=utf-8"});
  const url=URL.createObjectURL(blob);
  const a=document.createElement("a");a.href=url;a.download="kc-metro-"+el("viewmode").value+"-leads-"+new Date().toISOString().slice(0,10)+".csv";
  document.body.appendChild(a);a.click();a.remove();URL.revokeObjectURL(url);
}

function reportEmpty(tbody,message,colspan){
  const row=document.createElement("tr"),td=cell(row,message,"empty");
  td.colSpan=colspan;tbody.appendChild(row);
}
function renderBuilderReport(rankings, coverage){
  const leaders=el("builder-rankings"),fields=el("field-coverage");
  leaders.replaceChildren();fields.replaceChildren();
  if(!rankings || !coverage || rankings.source_snapshot!==snapshot?.generated_at ||
     coverage.source_snapshot!==snapshot?.generated_at ||
     !Array.isArray(rankings.builders) || !coverage.jurisdictions){
    reportEmpty(leaders,"No matching, current builder report. The permit list remains available.",6);
    reportEmpty(fields,"No current source-coverage report.",9);
    text("builder-report-status","Coverage report unavailable or stale.");
    text("builder-coverage-date","");return;
  }
  for(const company of rankings.builders){
    const tr=document.createElement("tr");
    const name=cell(tr,"");
    const action=document.createElement("button");
    action.type="button";action.className="builder-focus";action.textContent=company.builder;
    action.title="Find this builder's sourced permit matches";
    action.addEventListener("click",function(){
      el("search").value=company.builder;
      el("builderstatus").value="sourced";
      el("days").value="120";
      el("state").value="";setCityOptions();el("city").value="";
      el("category").value="";el("score").value="0";el("activity").value="";el("followup").value="";
      el("viewmode").value="permit";
      applyFilters();el("leads").scrollIntoView({behavior:"smooth",block:"start"});
    });
    name.appendChild(action);
    cell(tr,company.issued_last_30_days);
    cell(tr,company.issued_last_90_days);
    cell(tr,company.permit_count);
    cell(tr,company.estimated_distinct_project_groups);
    cell(tr,company.last_issued_date);
    leaders.appendChild(tr);
  }
  if(!rankings.builders.length)reportEmpty(leaders,"No source-matched company names yet.",6);
  for(const [city,entry] of Object.entries(coverage.jurisdictions).sort(function(a,b){return a[0].localeCompare(b[0]);})){
    const tr=document.createElement("tr"),v=entry.fields_available||{};
    cell(tr,city,"city");cell(tr,entry.permits);
    for(const k of ["independent_builder_company","project_description","valuation","units","square_feet","last_inspection_date","parcel_number"]){
      const count=Number.isInteger(v[k])?v[k]:0;
      cell(tr,count.toLocaleString("en-US")+" / "+entry.permits);
    }
    fields.appendChild(tr);
  }
  text("builder-report-status",coverage.builder_research_matched_permits+
       " of "+coverage.total_permits+" permits have a separately sourced company match · "+
       rankings.builder_companies+" companies");
  text("builder-coverage-date","Research last checked "+(coverage.research_reviewed_on||"unknown"));
}
async function loadSalesReports(){
  if(!snapshot || !snapshot.generated_at)return;
  let rankings=null,coverage=null;
  try{
    const responses=await Promise.all([
      fetch(BUILDER_RANKINGS_URL+"?v="+Date.now(),{cache:"no-store"}),
      fetch(SALES_COVERAGE_URL+"?v="+Date.now(),{cache:"no-store"})
    ]);
    if(responses[0].ok)rankings=await responses[0].json();
    if(responses[1].ok)coverage=await responses[1].json();
  }catch(err){ /* A missing summary must not prevent primary permit viewing. */ }
  renderBuilderReport(rankings,coverage);
}

function renderCoverage(data, monitor=null){
  const panel=el("coverage-grid");panel.replaceChildren();
  const statuses=new Map((snapshot?.sources||[]).map(function(s){return [s.key,s];}));
  for(const source of data.sources||[]){
    const box=document.createElement("article");box.className="coverage-card";
    const head=document.createElement("div");head.className="coverage-head";
    const names=document.createElement("div");const name=document.createElement("strong");name.textContent=source.name;names.appendChild(name);
    const sub=document.createElement("small");sub.textContent=source.region;names.appendChild(sub);head.appendChild(names);
    const status=document.createElement("span");
    const live=statuses.get(source.key);
    status.className="status "+(live?"good":(source.mode==="automated"||source.mode==="candidate")?"pending":"");
    status.textContent=live?"Snapshot loaded":source.mode==="automated"?"Feed configured":source.mode==="candidate"?"API verification":source.mode==="planning"?"Planning leads · not permits":"Public source only";
    head.appendChild(status);box.appendChild(head);
    const desc=document.createElement("p");
    desc.textContent=live ? (live.count+" recent records • latest issue "+(live.latest_issue||"unknown")) : source.note;
    box.appendChild(desc);
    if(source.key==="kck" && monitor && monitor.jurisdiction==="Kansas City, KS / Wyandotte County"){
      const m=document.createElement("p");
      m.className="activity-note";
      const count=monitor.catalogs&&Array.isArray(monitor.catalogs)
        ? monitor.catalogs.reduce(function(n,c){return n+(Number.isInteger(c.services_checked)?c.services_checked:0);},0):0;
      const stamp=typeof monitor.checked_at_utc==="string"?monitor.checked_at_utc.slice(0,10):"unknown";
      const label=monitor.source_status==="no_permit_named_service_in_reviewed_public_catalogs"
        ? "No permit-named API found in checked GIS folders"
        : monitor.source_status==="candidate_service_names_require_validation"
        ? "Possible GIS permit service requires validation"
        : "Public GIS review incomplete";
      m.textContent="GIS check "+stamp+": "+label+" ("+count+" services examined). Not an exhaustive search.";
      box.appendChild(m);
    }
    const links=document.createElement("div");links.className="coverage-links";
    for(const item of [["Official data",source.source_url],["Public search",source.portal_url],["Monthly reports",source.reports_url]]){
      const url=safeLink(item[1]);if(!url)continue;
      const a=document.createElement("a");a.href=url;a.target="_blank";a.rel="noopener noreferrer";a.textContent=item[0]+" ↗";
      links.appendChild(a);
    }
    box.appendChild(links);panel.appendChild(box);
  }
}
async function load(){
  const status=el("snapshot-status");
  status.textContent="Loading official source snapshot…";
  try{
    const response=await fetch(DATA_URL+"?v="+Date.now(),{cache:"no-store"});
    if(!response.ok)throw new Error("Snapshot HTTP "+response.status);
    const data=await response.json();
    if(!data || !Array.isArray(data.permits) || !Array.isArray(data.sources))throw new Error("Invalid snapshot structure");
    snapshot=data;
    await loadBuilderResearch();
    text("source-feed-count",data.generated_at?String(data.sources.length):"—");
    if(!data.generated_at){
      status.textContent="First validated ingestion has not run yet.";
      for(const id of ["metric-total","metric-sites","metric-homes","metric-multis","metric-priority","metric-inspections"])text(id,"—");
      el("export").disabled=true;
    }else{
      const age=(Date.now()-new Date(data.generated_at).getTime())/3600000;
      const when=new Date(data.generated_at).toLocaleString("en-US",{dateStyle:"medium",timeStyle:"short"});
      status.textContent="Snapshot "+when+(age>48?" • STALE — refresh needed":" • Ready");
    }
    setCityOptions();
    applyFilters();
    await loadSalesReports();
  }catch(err){
    snapshot=null;filtered=[];filteredPermits=[];siteRowsById=new Map();builderResearch=new Map();builderResearchLoaded=false;text("source-feed-count","—");status.textContent="Snapshot unavailable — no live results claimed.";
    text("resultcount","Unable to load published snapshot; check GitHub Actions.");
    for(const id of ["metric-total","metric-sites","metric-homes","metric-multis","metric-priority","metric-inspections"])text(id,"—");
    renderTable([]);el("export").disabled=true;
    toast("Could not load agency-data snapshot.");
  }
  try{
    const response=await fetch(COVERAGE_URL,{cache:"no-store"});
    if(!response.ok)throw new Error("Coverage registry unavailable");
    const info=await response.json();
    let monitor=null;
    try{
      const result=await fetch(SOURCE_MONITOR_URL+"?v="+Date.now(),{cache:"no-store"});
      if(result.ok)monitor=await result.json();
    }catch(err){ /* Optional monitoring report; primary city results remain usable. */ }
    renderCoverage(info,monitor);
  }catch(err){
    text("coverage-grid","Source registry could not be loaded.");
  }
}

function validateLenexaPlanning(data){
  if(!data || data.verified_permit_feed!==false || data.permit_records_in_dataset!==0) return false;
  if(data.jurisdiction!=="Lenexa, KS" || !/^\d{4}-\d{2}-\d{2}$/.test(data.reviewed_on||""))return false;
  if(data.source_url!=="https://www.lenexa.com/Government/Boards-Commissions/Planning-Commission")return false;
  if(!Array.isArray(data.opportunities)||!data.opportunities.length||data.opportunities.length>150)return false;
  const ids=new Set();
  for(const o of data.opportunities){
    if(!o || typeof o.id!=="string" || !o.id.startsWith("lenexa-plan-")||ids.has(o.id))return false;
    ids.add(o.id);
    for(const key of ["project","location","category","planning_stage","proposed_work"]){
      if(typeof o[key]!=="string" || !o[key].trim())return false;
    }
    if(!["Pending","On hold"].includes(o.application_status))return false;
    if(!["address","approximate"].includes(o.location_precision))return false;
    if(o.permit_number!==null || o.permit_issue_date!==null || o.construction_start!==null)return false;
    if(o.source_url!==data.source_url)return false;
  }
  return true;
}
function planningRowLink(td,label,url){
  const target=safeLink(url);
  if(!target)return;
  const a=document.createElement("a");
  a.textContent=label;a.href=target;a.target="_blank";a.rel="noopener noreferrer";
  td.appendChild(a);
}
function renderLenexaPlanning(){
  const tbody=el("lenexa-rows");tbody.replaceChildren();
  if(!lenexaPlanning){
    const row=document.createElement("tr"),empty=cell(row,"Planning snapshot unavailable. See the official City Planning Commission list.","empty");
    empty.colSpan=7;tbody.appendChild(row);
    text("lenexa-count","Planning records unavailable");
    el("export-lenexa").disabled=true;return;
  }
  const q=el("lenexa-search").value.trim().toLowerCase();
  const state=el("lenexa-status").value,cat=el("lenexa-category").value;
  lenexaFiltered=lenexaPlanning.opportunities.filter(function(item){
    if(state && item.application_status!==state)return false;
    if(cat && item.category!==cat)return false;
    return !q || [item.project,item.location,item.proposed_work,item.planning_stage,item.category].some(function(x){return x.toLowerCase().includes(q);});
  });
  const frag=document.createDocumentFragment();
  for(const item of lenexaFiltered){
    const tr=document.createElement("tr");tr.className="planning-row";
    cell(tr,item.project,"planning-name");
    const loc=cell(tr,item.location,"planning-location");
    if(item.location_precision==="approximate"){
      const small=document.createElement("span");small.className="activity-note";
      small.textContent="Approximate location; not a verified street address";
      loc.appendChild(small);
    }
    cell(tr,item.category);
    cell(tr,item.proposed_work,"planning-detail");
    cell(tr,item.planning_stage,"city");
    cell(tr,item.application_status,"planning-status"+(item.application_status==="On hold"?" hold":""));
    const links=cell(tr,"","planning-links");
    planningRowLink(links,"City planning application list ↗",item.source_url);
    planningRowLink(links,"Search Lenexa permits ↗",LENEXA_PORTAL_URL);
    frag.appendChild(tr);
  }
  if(!lenexaFiltered.length){
    const tr=document.createElement("tr"),td=cell(tr,"No planning applications match these filters.","empty");td.colSpan=7;frag.appendChild(tr);
  }
  tbody.appendChild(frag);
  text("lenexa-count",lenexaFiltered.length+" displayed of "+lenexaPlanning.opportunities.length+
       " planning entries (excluded from issued-permit totals)");
  el("export-lenexa").disabled=!lenexaFiltered.length;
}
async function loadLenexaPlanning(){
  try{
    const result=await fetch(LENEXA_PLANNING_URL+"?v="+Date.now(),{cache:"no-store"});
    if(!result.ok)throw new Error("Planning snapshot unavailable");
    const d=await result.json();
    if(!validateLenexaPlanning(d))throw new Error("Planning data contract invalid");
    lenexaPlanning=d;
    const review=dateLocal(d.reviewed_on);
    const today=new Date();today.setHours(0,0,0,0);
    const age=review?Math.floor((today-review)/86400000):99999;
    text("lenexa-reviewed","City list reviewed "+d.reviewed_on+" • manually verified"+
         (age>30?" • STALE — recheck official source":" • check current city listing before outreach"));
    const select=el("lenexa-category");select.replaceChildren();
    const first=document.createElement("option");first.value="";first.textContent="All development types";select.appendChild(first);
    for(const name of Array.from(new Set(d.opportunities.map(function(x){return x.category;}))).sort()){
      const option=document.createElement("option");option.value=name;option.textContent=name;select.appendChild(option);
    }
    renderLenexaPlanning();
  }catch(e){
    lenexaPlanning=null;lenexaFiltered=[];
    text("lenexa-reviewed","Manual planning snapshot could not be loaded; verify city source.");
    renderLenexaPlanning();
  }
}
function exportLenexaPlanning(){
  if(!lenexaPlanning||!lenexaFiltered.length)return;
  const fields=[
    ["Review date","_reviewed_on"],["Project","project"],["Location","location"],
    ["Location precision","location_precision"],["Category","category"],
    ["Planning stage","planning_stage"],["Application status at review","application_status"],
    ["Proposed work","proposed_work"],["Source","source_url"],
    ["Permit number (unverified)","permit_number"],["Permit issue date (unverified)","permit_issue_date"]
  ];
  const lines=[fields.map(function(f){return csvEsc(f[0]);}).join(",")];
  for(const item of lenexaFiltered){
    lines.push(fields.map(function(f){return csvEsc(f[1]==="_reviewed_on"?lenexaPlanning.reviewed_on:item[f[1]]);}).join(","));
  }
  const blob=new Blob(["\ufeff"+lines.join("\r\n")],{type:"text/csv;charset=utf-8"});
  const url=URL.createObjectURL(blob),a=document.createElement("a");
  a.href=url;a.download="lenexa-planning-prospects-"+lenexaPlanning.reviewed_on+".csv";
  document.body.appendChild(a);a.click();a.remove();URL.revokeObjectURL(url);
}

document.addEventListener("DOMContentLoaded",function(){
  for(const id of fields){
    el(id).addEventListener(id==="search"?"input":"change",function(){
      if(id==="state")setCityOptions();
      applyFilters();
    });
  }
  el("reload").addEventListener("click",load);
  el("export").addEventListener("click",exportCsv);
  for(const id of ["lenexa-search","lenexa-status","lenexa-category"]){
    el(id).addEventListener(id==="lenexa-search"?"input":"change",renderLenexaPlanning);
  }
  el("export-lenexa").addEventListener("click",exportLenexaPlanning);
  load();
  loadLenexaPlanning();
});
