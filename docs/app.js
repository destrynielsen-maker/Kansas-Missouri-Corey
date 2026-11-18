"use strict";

const DATA_URL = "./data/permits.json";
const COVERAGE_URL = "./data/coverage.json";
const WORKFLOW_URL = "https://github.com/destrynielsen-maker/Kansas-Missouri-Corey/actions/workflows/refresh.yml";
const els = {};
const fields = ["search","state","city","category","days","score","sort"];
let snapshot = null;
let filtered = [];

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
    a.title=kind==="source"?"Raw agency record in machine-readable format":kind==="search"?"Public portal search: enter permit number; not a direct record":"Agency-published direct record";
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
function renderTable(rows){
  const tbody=el("leadrows"); tbody.replaceChildren();
  if (!rows.length){
    const tr=document.createElement("tr");
    const td=cell(tr,snapshot && snapshot.generated_at?"No permits match these filters. Try a larger date window or a different city.":"No verified data snapshot yet. Run the GitHub refresh workflow to populate this dashboard.","empty");
    td.colSpan=9; tbody.appendChild(tr); text("row-limit","");return;
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
    number.className="permitno";number.textContent=item.permit_number || "—";
    idCell.appendChild(number);
    if(item.project){
      const project=document.createElement("div");
      project.className="project";project.textContent=item.project;project.title=item.project;
      idCell.appendChild(project);
    }
    cell(tr,item.address || "Address not published");
    cell(tr,item.jurisdiction || "—","city");
    const typecell=cell(tr,"");
    const pill=document.createElement("span");
    pill.className="type " + (item.category==="Single-family"?"Single-family":item.category==="Multifamily"?"Multifamily":item.category==="Commercial"?"Commercial":"");
    pill.textContent=item.category||"Other";
    typecell.appendChild(pill);
    cell(tr,money(item.valuation));
    linkCell(tr,item.permit_url,item.link_kind==="record"?"View permit ↗":"Search permit ↗",item.link_kind,item.permit_number);
    linkCell(tr,item.source_url,"Raw source ↗","source");
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
  const today=new Date();today.setHours(0,0,0,0);
  filtered=(snapshot.permits||[]).filter(function(p){
    if(state && p.state!==state) return false;
    if(city && p.jurisdiction!==city) return false;
    if(cat && p.category!==cat) return false;
    if((p.score||0)<score) return false;
    const d=dateLocal(p.issued);
    if(!d || Math.floor((today-d)/86400000)>days) return false;
    if(q && ![p.permit_number,p.address,p.jurisdiction,p.project,p.work_class,p.permit_type,p.county].some(function(x){return asString(x).toLowerCase().includes(q);}))return false;
    return true;
  });
  const order=el("sort").value;
  filtered.sort(function(a,b){
    if(order==="newest") return asString(b.issued).localeCompare(asString(a.issued))||b.score-a.score;
    if(order==="value") return (b.valuation||0)-(a.valuation||0)||b.score-a.score;
    return b.score-a.score||asString(b.issued).localeCompare(asString(a.issued));
  });
  text("resultcount",filtered.length.toLocaleString()+" qualifying permits • "+days+"-day view");
  text("metric-total",filtered.length.toLocaleString());
  text("metric-total-sub","Official permit records after filters");
  text("metric-homes",filtered.filter(function(x){return x.category==="Single-family";}).length.toLocaleString());
  text("metric-multis",filtered.filter(function(x){return x.category==="Multifamily";}).length.toLocaleString());
  text("metric-priority",filtered.filter(function(x){return x.score>=75;}).length.toLocaleString());
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
    ["Permit number","permit_number"],["Project","project"],["Address","address"],["Category","category"],
    ["Permit type","permit_type"],["Work class","work_class"],["Status","status"],["Valuation","valuation"],
    ["Units","units"],["Square feet","square_feet"],["Public permit / search","permit_url"],
    ["Link type","link_kind"],["Raw source row","source_url"]];
  const lines=[columns.map(function(x){return csvEsc(x[0]);}).join(",")];
  for(const r of filtered)lines.push(columns.map(function(x){return csvEsc(r[x[1]]);}).join(","));
  const blob=new Blob(["\ufeff"+lines.join("\r\n")],{type:"text/csv;charset=utf-8"});
  const url=URL.createObjectURL(blob);
  const a=document.createElement("a");a.href=url;a.download="kc-metro-permits-"+new Date().toISOString().slice(0,10)+".csv";
  document.body.appendChild(a);a.click();a.remove();URL.revokeObjectURL(url);
}
function renderCoverage(data){
  const panel=el("coverage-grid");panel.replaceChildren();
  const statuses=new Map((snapshot?.sources||[]).map(function(s){return [s.key,s];}));
  for(const source of data.sources||[]){
    const box=document.createElement("article");box.className="coverage-card";
    const head=document.createElement("div");head.className="coverage-head";
    const names=document.createElement("div");const name=document.createElement("strong");name.textContent=source.name;names.appendChild(name);
    const sub=document.createElement("small");sub.textContent=source.region;names.appendChild(sub);head.appendChild(names);
    const status=document.createElement("span");
    const live=statuses.get(source.key);
    status.className="status "+(live?"good":source.mode==="automated"?"pending":"");
    status.textContent=live?"Snapshot loaded":source.mode==="automated"?"Feed configured":"Portal only";
    head.appendChild(status);box.appendChild(head);
    const desc=document.createElement("p");
    desc.textContent=live ? (live.count+" recent records • latest issue "+(live.latest_issue||"unknown")) : source.note;
    box.appendChild(desc);
    const links=document.createElement("div");links.className="coverage-links";
    for(const item of [["Official data",source.source_url],["Public search",source.portal_url]]){
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
    if(!data.generated_at){
      status.textContent="First validated ingestion has not run yet.";
      for(const id of ["metric-total","metric-homes","metric-multis","metric-priority"])text(id,"—");
      el("export").disabled=true;
    }else{
      const age=(Date.now()-new Date(data.generated_at).getTime())/3600000;
      const when=new Date(data.generated_at).toLocaleString("en-US",{dateStyle:"medium",timeStyle:"short"});
      status.textContent="Snapshot "+when+(age>48?" • STALE — refresh needed":" • Ready");
    }
    setCityOptions();
    applyFilters();
  }catch(err){
    snapshot=null;filtered=[];status.textContent="Snapshot unavailable — no live results claimed.";
    text("resultcount","Unable to load published snapshot; check GitHub Actions.");
    for(const id of ["metric-total","metric-homes","metric-multis","metric-priority"])text(id,"—");
    renderTable([]);el("export").disabled=true;
    toast("Could not load agency-data snapshot.");
  }
  try{
    const response=await fetch(COVERAGE_URL,{cache:"no-store"});
    if(!response.ok)throw new Error("Coverage registry unavailable");
    renderCoverage(await response.json());
  }catch(err){
    text("coverage-grid","Source registry could not be loaded.");
  }
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
  load();
});
