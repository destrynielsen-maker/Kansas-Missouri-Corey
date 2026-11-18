"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");

const root = path.resolve(__dirname,"..");
const html = fs.readFileSync(path.join(root,"docs","index.html"),"utf8");
const code = fs.readFileSync(path.join(root,"docs","app.js"),"utf8");

for (const id of ["activity","followup","viewmode","source-feed-count","metric-inspections","metric-sites","leadrows","score","sort","days","export"]) {
  assert.ok(html.includes('id="'+id+'"'),"Missing dashboard control: "+id);
}
for (const header of ["Official activity","Other dates","Sales follow-up","Other permits at site","Raw source data"]) {
  assert.ok(html.includes(header),"Missing table column: "+header);
}
assert.ok(html.indexOf("<th>Permit record / search</th>") < html.indexOf("<th>Raw source row</th>"),
          "Sales action must precede machine source link.");
assert.ok(!/estimated.start.date/i.test(html),"Never describe estimated start date as reported fact");

const sandbox = {
  document: { addEventListener: function(){} },
  setTimeout, clearTimeout, console, Date
};
vm.createContext(sandbox);
vm.runInContext(code+"\nglobalThis.__tests={followupBand,evidenceKind,safeLink,csvEsc,groupSiteRows,siteKey};",sandbox,{timeout:1000});
const t=sandbox.__tests;
assert.equal(t.followupBand(0).key,"0-7");
assert.equal(t.followupBand(7).text,"Contact now");
assert.equal(t.followupBand(8).key,"8-30");
assert.equal(t.followupBand(30).key,"8-30");
assert.equal(t.followupBand(31).key,"31-90");
assert.equal(t.followupBand(91).key,"91+");
assert.equal(t.evidenceKind({inspection_evidence:"inspection_recorded",last_inspection_date:"2026-11-15"}),"inspection_recorded");
assert.equal(t.evidenceKind({inspection_evidence:"inspection_recorded",last_inspection_date:null}),"field_not_published");
assert.equal(t.evidenceKind({inspection_evidence:"date_not_reported"}),"date_not_reported");
assert.equal(t.evidenceKind({inspection_evidence:"field_not_published"}),"field_not_published");
assert.equal(t.safeLink("javascript:alert(1)"),null);
assert.equal(t.safeLink("http://example.org"),null);
assert.equal(t.safeLink("https://example.org/permit/1"),"https://example.org/permit/1");
assert.equal(t.csvEsc("=SUM(A1:A4)"),'"\'=SUM(A1:A4)"');
assert.equal(t.csvEsc('abc"def'),'"abc""def"');
console.log("Dashboard contract and timing behavior: PASS");


const sameSite={id:"a",site_group_id:"site-abc",permit_number:"A",address:"123 Main"};
const second={id:"b",site_group_id:"site-abc",permit_number:"B",address:"123 MAIN"};
const distinct={id:"c",site_group_id:"site-other",permit_number:"C",address:"125 Main"};
const missingId={id:"d",permit_number:"D",address:"123 MAIN"};
const groups=t.groupSiteRows([sameSite,second,distinct,missingId]);
assert.equal(groups.size,3,"Only server-confirmed same-address IDs may group");
assert.equal(groups.get("site-abc").length,2);
assert.notEqual(t.siteKey(missingId),t.siteKey(sameSite),"Never guess client-side matches");
console.log("Source-backed site group selection: PASS");

assert.ok(code.includes("Raw dataset ↗"),"Bulk source data should be explicitly labeled");
assert.ok(code.includes("source_url_scope"),"Source scope should survive exports");
