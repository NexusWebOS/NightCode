export function pathParts(path='') {
  const parts = String(path).replaceAll('\\','/').split('/').filter(Boolean);
  if(parts.some(p=>p==='..'||p==='.'||/[\x00-\x1f]/.test(p))) throw Error('Use a path inside the selected folder.');
  return parts;
}
export function joinPath(...parts) {return pathParts(parts.filter(Boolean).join('/')).join('/');}
export function leaf(path) {return pathParts(path).at(-1)||'';}
export function parentPath(path) {return pathParts(path).slice(0,-1).join('/');}
export function copyName(name,n=1){const i=name.lastIndexOf('.');const split=i>0?i:name.length;return `${name.slice(0,split)} (copy${n>1?' '+n:''})${name.slice(split)}`;}
export function bytes(n=0){if(!Number.isFinite(n))return '—';if(n<1024)return n+' B';const i=Math.min(Math.floor(Math.log(n)/Math.log(1024)),4);return (n/1024**i).toFixed(n/1024**i<10?1:0)+' '+['B','KB','MB','GB','TB'][i];}
export function tokenize(input){const tokens=[];const re=/"([^"\\]*(?:\\.[^"\\]*)*)"|'([^']*)'|(\S+)/g;let m;while((m=re.exec(input)))tokens.push(m[1]!==undefined?m[1].replace(/\\"/g,'"'):m[2]??m[3]);if((input.match(/"/g)||[]).length%2||(input.match(/'/g)||[]).length%2)throw Error('Close the quote around your filename.');return tokens;}
export function selectedEntries(pane){return pane.entries.filter(e=>pane.selected.has(e.id));}
export function sortEntries(entries){return entries.sort((a,b)=>Number(b.directory)-Number(a.directory)||a.name.localeCompare(b.name,undefined,{numeric:true}));}
export function isAbort(e){return e.name==='AbortError';}
export function checkAbort(signal){if(signal?.aborted)throw new DOMException('Stopped by operator','AbortError');}
export const nativeExports={
 'application/vnd.google-apps.document':['application/pdf','.pdf'],
 'application/vnd.google-apps.spreadsheet':['application/vnd.openxmlformats-officedocument.spreadsheetml.sheet','.xlsx'],
 'application/vnd.google-apps.presentation':['application/pdf','.pdf'],
 'application/vnd.google-apps.drawing':['image/png','.png']
};
