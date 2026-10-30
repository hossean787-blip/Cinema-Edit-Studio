#!/usr/bin/env node
/* Cinema Edit Studio real-browser smoke. Synthetic public-domain FFmpeg test sources only. */
const {chromium} = require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');

async function main() {
 const origin=process.env.CINEMA_URL||'http://127.0.0.1:8765';
 const binary=process.env.CHROMIUM_BIN;
 const source=process.env.CINEMA_TEST_VIDEO;
 if(!source||!fs.existsSync(source))throw Error('CINEMA_TEST_VIDEO is required');
 const output=process.env.CINEMA_QA_OUT||path.join(process.cwd(),'qa-browser-artifacts');
 fs.mkdirSync(output,{recursive:true});
 const browser=await chromium.launch({headless:true,
   ...(binary?{executablePath:binary}:{}),
   args:['--no-sandbox','--disable-dev-shm-usage']});
 const page=await browser.newPage({viewport:{width:1440,height:900},deviceScaleFactor:1});
 const issues=[];
 page.on('pageerror',e=>issues.push(e.message));
 page.on('console',m=>{if(m.type()==='error')issues.push(m.text())});
 page.on('response',r=>{if(r.status()>=400)issues.push('HTTP '+r.status()+' '+r.url())});
 try{
   await page.goto(origin,{waitUntil:'domcontentloaded'});
   await page.waitForSelector('.project-item',{timeout:20000});
   assert.match(await page.title(),/CINEMA EDIT STUDIO/);
   await page.locator('#new').click();
   await page.locator('#upload').setInputFiles(source);
   await page.waitForFunction(()=>document.querySelectorAll('[data-shot]').length>=1,null,{timeout:30000});
   await page.locator('#upload').setInputFiles({name:'clip_second.mp4',mimeType:'video/mp4',
     buffer:fs.readFileSync(source)});
   try {
     await page.waitForFunction(()=>document.querySelectorAll('[data-shot]').length>=2,null,{timeout:30000});
   } catch(e) {
     console.error('Upload diagnostics:',{shots:await page.locator('[data-shot]').count(),
       uploadStatus:await page.locator('#upload-status').textContent(),
       footer:await page.locator('#footer-status').textContent(),errors:issues});
     throw e;
   }
   await page.locator('[data-shot="1"]').click();
   await page.locator('#cspeed').fill('0.7');
   await page.locator('#cspeed').dispatchEvent('change');
   await page.locator('#cramp').check();
   await page.locator('#cup').click();
   await page.locator('#project-title').fill('Browser acceptance test');
   await page.locator('#resolution').selectOption('720x1280');
   await page.locator('#save').click();
   const projectId=await page.locator('.project-item.active').getAttribute('data-project');
   assert(projectId);
   const saved=await (await page.request.get(origin+'/api/projects/'+projectId)).json();
   assert.equal(saved.shots.length,2);
   assert.equal(saved.shots[0].speed,0.7);
   assert.equal(saved.shots[0].ramp,true);
   await page.screenshot({path:path.join(output,'editor_desktop.png'),fullPage:true});
   await page.locator('#render').click();
   let state={};
   for(let i=0;i<180;i++){
     await page.waitForTimeout(300);
     const jobs=await (await page.request.get(origin+'/api/projects/'+projectId+'/jobs')).json();
     if(jobs.jobs?.length){
        state=jobs.jobs[0];
        if(state.status==='done'||state.status==='failed')break;
     }
   }
   assert.equal(state.status,'done',JSON.stringify(state));
   const response=await page.request.get(origin+state.video_url);
   assert.equal(response.status(),200);
   const payload=await response.body();
   assert(payload.length>1000);
   await page.waitForFunction(()=>document.querySelectorAll('#render-actions a').length===2,null,{timeout:15000});
   assert.equal(await page.locator('#render-actions a').count(),2);
   await page.screenshot({path:path.join(output,'editor_rendered.png'),fullPage:true});
   await page.reload();
   await page.waitForSelector('[data-shot="1"]',{timeout:20000});
   assert.equal(await page.locator('[data-shot]').count(),2);
   await page.setViewportSize({width:390,height:844});
   await page.screenshot({path:path.join(output,'editor_mobile.png'),fullPage:true});
   const horizontalOverflow=await page.evaluate(()=>document.documentElement.scrollWidth>window.innerWidth);
   assert.equal(horizontalOverflow,false,'mobile horizontal overflow');
   // Chromium sometimes emits harmless media decoding warnings; page JS exceptions remain fatal.
   assert.equal(issues.filter(x=>!x.includes('Failed to load resource')).length,0,issues.join('\n'));
   const result={browser:'Chromium',http:true,editor:true,clip_count:2,
       speed_ramp:true,persist:true,full_decode_in_ci:'handled by server test',
       output_download_bytes:payload.length,mobile_390px_no_overflow:true,
       page_errors:issues};
   fs.writeFileSync(path.join(output,'browser_qa.json'),JSON.stringify(result,null,2));
   console.log(JSON.stringify(result,null,2));
 }finally{await browser.close()}
}
main().catch(e=>{console.error(e.stack);process.exitCode=1});
