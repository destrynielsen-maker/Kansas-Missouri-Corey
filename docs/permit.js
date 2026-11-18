"use strict";
const PERMITS_URL="./data/permits.json",BUILDERS_URL="./data/builders.json";
function el(id){return document.getElementById(id);}
function put(id,value){
  const node=el(id);
  node.textContent=value===null||value===undefined||value===""?"Not published":String(value);
  if(value===null||value===undefined||value==="")node.classList.add("unavailable");
}
function safeUrl(url){
  return typeof url==="string" && /^https:\/\/[A-Za-z0-9.-]+(?=[:/]|$)/.test(url)?url:null;
}
function money(v){
  return Number.isFinite(v)&&v>0?"$"+Math.round(v).toLocaleString("en-US"):"Not published";
}
function formattedDate(v){return typeof v==="string"&&/^\d{4}-\d{2}-\d{2}$/.test(v)?v:null;}
function normalizeAddress(v){return String(v||"").trim().toUpperCase().replace(/[.,]/g,"").replace(/\s+/g," ");}
function verifiedResearch(permit,docs){
  if(!docs || !Array.isArray(docs.entries))return null;
  for(const r of docs.entries){
    if(r && r.id===permit.id && r.issued===permit.issued && r.jurisdiction===permit.jurisdiction &&
       normalizeAddress(r.address)===normalizeAddress(permit.address) &&
       typeof r.builder==="string" && r.builder && safeUrl(r.evidence_url) &&
       ["exact_address_listing","project_gc_announcement","planning_drawing"].includes(r.evidence_type))return r;
  }
  return null;
}
function evidenceLabel(kind){
  return kind==="project_gc_announcement"?"Named GC in project announcement"
    :kind==="planning_drawing"?"Company identified in planning drawing"
    :kind==="exact_address_listing"?"Builder in exact-address home listing":"Independent research";
}
function setLink(id,url,label){
  const node=el(id),valid=safeUrl(url);
  if(!valid){node.classList.add("hidden");node.removeAttribute("href");return;}
  node.href=valid;
  if(label)node.textContent=label;
  node.classList.remove("hidden");
}
function makeRelated(permit,all){
  const root=el("related");
  root.replaceChildren();
  const related=all.filter(function(other){
    return other.site_group_id && other.site_group_id===permit.site_group_id && other.jurisdiction===permit.jurisdiction;
  });
  put("groupnote",related.length>1
    ?related.length+" permits share the same normalized street address. They may be separate phases or projects."
    :"No other matching permits in the current 120-day snapshot.");
  if(related.length<2)return;
  for(const other of related){
    const link=document.createElement("a");
    link.href="./permit.html?id="+encodeURIComponent(other.id);
    link.textContent=other.permit_number+(other.id===permit.id?" (this record)":"");
    root.appendChild(link);
  }
}
function summary(permit,match){
  return [
    "Kansas–Missouri Construction Intelligence",
    "Permit: "+permit.permit_number,
    "Jurisdiction: "+permit.jurisdiction,
    "Site: "+permit.address,
    "Category: "+permit.category,
    "Work: "+(permit.work_class||permit.permit_type||"Not published"),
    "Issued: "+permit.issued,
    "Valuation: "+money(permit.valuation),
    "Builder research: "+(match?match.builder+" ("+evidenceLabel(match.evidence_type)+"; not city permit-confirmed)":"not verified"),
    "Public permit search: "+(permit.permit_url||"Not published"),
    "Original government source: "+(permit.source_url||"Not published"),
    "Project and contractor status must be confirmed with the issuing authority."
  ].join("\n");
}
async function copyText(value,id){
  try{
    if(!navigator.clipboard || !navigator.clipboard.writeText)throw new Error("Clipboard unavailable");
    await navigator.clipboard.writeText(value);
    const node=el(id),before=node.textContent;
    node.textContent="Copied ✓";
    setTimeout(function(){node.textContent=before;},1500);
  }catch(e){
    el(id).title="Clipboard unavailable; value: "+value.slice(0,60);
  }
}
async function load(){
  const params=new URLSearchParams(window.location.search);
  const id=params.get("id")||"";
  if(!/^[A-Za-z0-9:_\-.]{3,160}$/.test(id)){
    el("loading").classList.add("hidden");el("error").classList.remove("hidden");return;
  }
  let snapshot,builders=null;
  try{
    const result=await Promise.all([
      fetch(PERMITS_URL+"?v="+Date.now(),{cache:"no-store"}),
      fetch(BUILDERS_URL+"?v="+Date.now(),{cache:"no-store"}).catch(function(){return null;})
    ]);
    if(!result[0].ok)throw new Error("Unable to load the verified permit snapshot");
    snapshot=await result[0].json();
    if(!snapshot || !Array.isArray(snapshot.permits) || !snapshot.generated_at)throw new Error("Unexpected permit snapshot");
    if(result[1] && result[1].ok){
      try{builders=await result[1].json();}catch(e){builders=null;}
    }
  }catch(e){
    el("loading").textContent="Could not load the government permit snapshot. Open the dashboard and check the latest published refresh.";
    return;
  }
  const permit=snapshot.permits.find(function(p){return p.id===id;});
  if(!permit){
    el("loading").classList.add("hidden");el("error").classList.remove("hidden");return;
  }
  const match=verifiedResearch(permit,builders);
  put("crumb",permit.permit_number);put("jurisdiction",permit.jurisdiction);
  put("heading",permit.project||permit.address||permit.permit_number);
  document.title=permit.permit_number+" | Kansas–Missouri Permit Details";
  put("location",permit.address+" · "+permit.jurisdiction);
  put("category",permit.category);put("status",permit.status||"Status unavailable");
  put("permit",permit.permit_number);put("issued",formattedDate(permit.issued));
  put("valuation",money(permit.valuation));
  put("kind",permit.category);put("workclass",permit.work_class);
  put("permittype",permit.permit_type);put("project",permit.project);
  put("units",permit.units);put("squarefeet",permit.square_feet);
  put("parcel",permit.parcel_number);put("county",permit.county);
  put("statusfield",permit.status);put("score",permit.score);
  put("description",permit.project||permit.work_class||permit.permit_type||"Scope not published in selected city source");
  put("applied",formattedDate(permit.application_date));
  put("issue2",formattedDate(permit.issued));
  put("inspection",formattedDate(permit.last_inspection_date));
  put("expiry",formattedDate(permit.expiration_date));
  put("started",formattedDate(permit.start_date));
  put("inspectionkind",permit.inspection_evidence==="inspection_recorded"?"Inspection date recorded"
    :permit.inspection_evidence==="date_not_reported"?"Agency field blank":"No inspection date field");
  put("siteaddress",permit.address);
  put("issuer",permit.jurisdiction+" ("+permit.state+")");
  put("snapshotdate",String(snapshot.generated_at).replace("T"," ").slice(0,19)+" UTC");
  put("sitematch",permit.site_group_basis==="same_normalized_address"?"Exact normalized street address":"Address match not established");
  if(permit.address){
    setLink("maplink","https://www.google.com/maps/search/?api=1&query="+encodeURIComponent(permit.address+" "+permit.jurisdiction));
  }
  makeRelated(permit,snapshot.permits);
  put("builder",match?match.builder:"Builder not verified");
  put("builderbasis",match?evidenceLabel(match.evidence_type)+" · not city permit-confirmed":"No independently established builder/GC on this permit");
  put("builderqualification",match?match.qualification:"The selected official source does not provide a verified prime contractor field. Use the city permit search to investigate.");
  put("builderverify",match?"Sourced company, role not individually permit-verified":"Not established");
  setLink("builderlink",match?.evidence_url);
  setLink("official",permit.permit_url,permit.link_kind==="record"?"View official individual permit ↗":"Search permit on city website ↗");
  setLink("raw",permit.source_url,permit.source_url_scope==="dataset"?"Open source dataset ↗":"Open exact government data query ↗");
  setLink("origin",permit.source_home,"Open government's source index ↗");
  put("sourcescope",permit.source_url_scope==="dataset"
    ?"The source JSON is the city's full dataset, not an individually addressable permit record."
    :"The raw link identifies this permit in the city's published data; it is not a human-friendly official permit page.");
  el("copynumber").addEventListener("click",function(){copyText(permit.permit_number,"copynumber");});
  el("copysummary").addEventListener("click",function(){copyText(summary(permit,match),"copysummary");});
  el("loading").classList.add("hidden");el("page").classList.remove("hidden");
}
document.addEventListener("DOMContentLoaded",load);
