// Render model HTML only in a browser job with no publishing credentials.
import {pathToFileURL} from 'node:url';
import {mkdir,readFile} from 'node:fs/promises';
import path from 'node:path';
const {chromium}=await import(pathToFileURL(path.join(process.env.RENDER_PACKAGE_PATH,'node_modules/playwright/index.mjs')));
const folder=process.env.PROTOTYPE_DIR;
const html=await readFile(path.join(folder,'index.html'),'utf8');
const browser=await chromium.launch({headless:true});
await mkdir(process.env.SCREENSHOT_DIR,{recursive:true});
try {
 for(const [name,width,height] of [['desktop',1100,900],['mobile',390,844]]) {
  const context=await browser.newContext({viewport:{width,height},serviceWorkers:'block'});
  await context.route('**/*',route=>route.abort());
  const page=await context.newPage();const errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.setContent(html,{waitUntil:'load'});
  await page.evaluate(()=>document.fonts.ready);
  const text=await page.locator('body').innerText();
  if(text.trim().length<20)throw new Error('Prototype content missing');
  if(await page.locator('button,select,input').count()<2)throw new Error('Interactive controls missing');
  if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+4))throw new Error('Horizontal overflow at '+width);
  if(errors.length)throw new Error('Prototype script errors: '+errors.join(';'));
  await page.screenshot({path:path.join(process.env.SCREENSHOT_DIR,name+'.png'),fullPage:true});
  await context.close();
 }
} finally {await browser.close();}
