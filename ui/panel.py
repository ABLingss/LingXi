"""
web_panel.py — Info panel for Stock JSON Clipper V3.2.

Tahoe-inspired professional UI with full Chinese localization:
  - Every indicator label includes Chinese explanation
  - Clean card-based layout with visual hierarchy
  - Windows 7+ compatible (fallback-safe CSS)
  - Manual stock code search + clipboard status

JS ↔ Python bridge via webview.expose() API.
"""

import json
import threading
import os
import time
from typing import TYPE_CHECKING, Any, Dict, List, Optional

import webview

from core.logging_setup import get_logger

if TYPE_CHECKING:
    from core.clipper import StockClipper

log = get_logger("panel")


# ============================================================
# HTML Template
# ============================================================
PANEL_HTML = r"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta http-equiv="X-UA-Compatible" content="IE=edge">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<script>"use strict";var StockApi=(()=>{var z=Object.defineProperty;var be=Object.getOwnPropertyDescriptor;var Pe=Object.getOwnPropertyNames;var Me=Object.prototype.hasOwnProperty;var Ke=(e,t)=>{for(var r in t)z(e,r,{get:t[r],enumerable:!0})},Ue=(e,t,r,n)=>{if(t&&typeof t=="object"||typeof t=="function")for(let o of Pe(t))!Me.call(e,o)&&o!==r&&z(e,o,{get:()=>t[o],enumerable:!(n=be(t,o))||n.enumerable});return e};var ve=e=>Ue(z({},"__esModule",{value:!0}),e);var ur={};Ke(ur,{StockApiError:()=>R,StockCodeError:()=>E,StockParseError:()=>D,StockRequestError:()=>a,default:()=>ar,stocks:()=>ee});var N="\u8BF7\u68C0\u67E5\u7EDF\u4E00\u4EE3\u7801\u662F\u5426\u6B63\u786E",te="\u672A\u5B9E\u73B0\u83B7\u53D6\u80A1\u7968\u6570\u636E",re="\u672A\u5B9E\u73B0\u83B7\u53D6\u80A1\u7968\u6570\u636E\u7EC4",ne="\u672A\u5B9E\u73B0\u83B7\u53D6 K \u7EBF\u6570\u636E",oe="\u672A\u5B9E\u73B0\u641C\u7D22\u80A1\u7968\u4EE3\u7801";var y={code:"---",name:"---",percent:0,now:0,low:0,high:0,yesterday:0};var R=class extends Error{constructor(t){super(t),this.name=new.target.name}},a=class extends R{},E=class extends R{},D=class extends R{};function O(){return!!globalThis.document}async function se(e){let r=globalThis.document,n=r?.head||r?.body||r?.documentElement;if(!r||!n)throw new a("Browser document is not available");await new Promise((o,s)=>{let i=r.createElement("script"),u=e.timeout||15e3,d=setTimeout(()=>{k(),s(new a(`Script request timed out after ${u}ms`))},u);function k(){clearTimeout(d),i.onload=null,i.onerror=null,i.parentNode?.removeChild?.(i)}i.async=!0,i.charset=e.charset||"utf-8",i.onload=()=>{k(),o()},i.onerror=()=>{k(),s(new a("Script request failed"))},i.src=e.url,n.appendChild(i)})}async function ie(e){let t=globalThis;await se(e);let r=t[e.variableName];return delete t[e.variableName],typeof r=="string"?r:""}async function ce(e){let t=globalThis,r=e.callbackParam||"callback",n=`stockApiJsonp${Date.now()}${Math.floor(Math.random()*1e5)}`,o;t[n]=s=>{o=s};try{let s=De(e.url,r,n);await se({charset:e.charset,timeout:e.timeout,url:s})}finally{delete t[n]}if(o===void 0)throw new a("JSONP response did not invoke callback");return o}function De(e,t,r){let n=e.includes("?")?"&":"?";return`${e}${n}${encodeURIComponent(t)}=${encodeURIComponent(r)}`}var Z=class{constructor(t){this.url=t;this.options={headers:{Accept:"*/*","User-Agent":"Mozilla/5.0 (compatible; stock-api/2.0)"},retries:2,timeout:15e3}}set(t,r){return this.options.headers[t]=r,this}responseType(t){return this}retries(t){return this.options.retries=t,this}timeout(t){return this.options.timeout=t,this}then(t,r){return this.send().then(t,r)}async send(){let t;for(let r=0;r<=this.options.retries;r++)try{return await Ae(this.url,this.options)}catch(n){t=n}throw t}};async function Ae(e,t){if(typeof globalThis.fetch!="function")throw new a("globalThis.fetch is not available");let r=new AbortController,n=setTimeout(()=>r.abort(),t.timeout);try{let o=await globalThis.fetch(e,{headers:He(t.headers),redirect:"follow",signal:r.signal}),s=o.status,i=await o.arrayBuffer(),u={body:i,headers:Ie(o.headers),status:s,text:new TextDecoder("utf-8").decode(i)};if(!o.ok)throw new a(`Request failed with status ${s}`);return u}catch(o){throw Be(o)?new a(`Request timed out after ${t.timeout}ms`):o}finally{clearTimeout(n)}}function He(e){let t=new Headers;for(let[r,n]of Object.entries(e))Fe(r)||t.set(r,n);return t}function Ie(e){let t={};return e.forEach((r,n)=>{t[n]=r}),t}function Fe(e){return qe()?["referer","user-agent"].includes(e.toLowerCase()):!1}function qe(){return"window"in globalThis&&"document"in globalThis}function Be(e){return e instanceof DOMException&&e.name==="AbortError"}var $e={get(e){return new Z(e)}},w=$e;var c={supported:!0},ae={supported:!1,note:"Sina requires a valid Referer that browser JavaScript cannot set. Use stocks.auto, Node.js, or a backend proxy."},pe={eastmoney:{browser:{kline:c,quote:c,search:c},node:{kline:c,quote:c,search:c},source:"eastmoney"},sina:{browser:{kline:c,quote:ae,search:ae},node:{kline:c,quote:c,search:c},source:"sina"},tencent:{browser:{kline:c,quote:c,search:c},node:{kline:c,quote:c,search:c},source:"tencent"}};function me(){return Object.values(pe).map(e=>({browser:ue(e.browser),node:ue(e.node),source:e.source}))}function g(e,t){let r=O()?"browser":"node",n=pe[e][r][t];if(!n.supported)throw new a(`${e} ${t} is not available in ${r}. ${n.note||""}`.trim())}function ue(e){return{kline:{...e.kline},quote:{...e.quote},search:{...e.search}}}var A={adjust:"none",count:120,period:"day"};function _(e={}){return{adjust:je(e.adjust),count:ze(e.count),period:Le(e.period)}}function M(e){let t=Number(e);return Number.isFinite(t)?t:0}function T(e){let t={close:M(e.close),date:e.date,high:M(e.high),low:M(e.low),open:M(e.open),source:e.source};return e.volume!==void 0&&(t.volume=M(e.volume)),t}function Le(e){return e||A.period}function je(e){return e||A.adjust}function ze(e){return e===void 0||!Number.isFinite(e)||e<=0?A.count:Math.floor(e)}function de(e){return Array.from(new Set(e))}function Ze(e){return e.toLowerCase()==="gbk"?"gb18030":e}var Qe={decode(e,t){return new TextDecoder(Ze(t)).decode(e)}},le=Qe;function K(e,t){return{...e,source:t}}function h(e){return de(e.filter(t=>t!==""))}function ge(e){return{...y,code:e}}function Ge(e){return e.split(`;
`).filter(t=>t!=="")}function Q(e){let[,t=""]=e.split("=");return t}function Je(e,t){return Q(e).replace('"',"").split(t)}function H(e){async function t(o){let s=h(o);if(s.length===0)return[];g(e.source,"quote");let i=e.quote.codeTransform.transforms(s),u=await r(e.quote,i),d=Ge(u);return s.map((k,v)=>{let x=i[v],C=d.find(j=>j.includes(x))||"";if(e.quote.isMissing(C,x))return ge(k);let P=Je(C,e.quote.delimiter);return e.quote.parseStock(k,P)})}async function r(o,s){return O()&&o.browserRequestText?o.browserRequestText(s):fe({encoding:o.encoding,headers:o.headers,url:o.getUrl(s)})}let n={async getStock(o){let[s]=await t([o]);return s||ge(o)},getStocks:t,getKlines(o,s){return e.kline.getKlines(o,s)},async searchStocks(o){g(e.source,"search");let s=await Ve(e.search,o);return t(e.search.parseCodes(s))},async inspectStock(o){return G(e.source,o,n.getStock)}};return n}async function Ve(e,t){return O()&&e.browserRequestText?e.browserRequestText(t):fe({encoding:e.encoding,headers:e.headers,url:e.getUrl(t)})}async function G(e,t,r){try{let n=K(await r(t),e);return{code:t,source:e,status:Ye(n)?"success":"empty",stock:n}}catch(n){return{code:t,source:e,status:"error",error:We(n)}}}function Ye(e){return!!(e&&e.name!==y.name)}function We(e){return e instanceof Error?e.message:String(e)}async function fe(e){let t=w.get(e.url).responseType("blob");for(let[n,o]of e.headers||[])t.set(n,o);let r=await t;return le.decode(r.body,e.encoding)}function Se(e){let t=String(e).toUpperCase();if(t.startsWith("SH"))return`1.${t.slice("SH".length)}`;if(t.startsWith("SZ"))return`0.${t.slice("SZ".length)}`;throw new E(N)}var Xe={transform:Se,transforms(e){return e.map(Se)}},J=Xe;function ke(e,t){let r=rt(t),n=st(t),o=U(t?.f170??t?.f3);return{code:et(e),name:tt(t),percent:o?o/100:r&&n?r/n-1:0,now:r,low:nt(t),high:ot(t),yesterday:n}}function et(e){return String(e).toUpperCase()}function tt(e){return String(e?.f58||e?.f14||"---")}function rt(e){return U(e?.f43??e?.f2)}function nt(e){return U(e?.f45??e?.f16)}function ot(e){return U(e?.f44??e?.f15)}function st(e){return U(e?.f60??e?.f18)}function U(e){if(e==null||e==="-")return 0;let t=Number(e);return Number.isFinite(t)?t:0}var it="f43,f44,f45,f57,f58,f60,f170",ct="f51,f52,f53,f54,f55,f56",at="D43BF722C8E33BDC906FB84D85E326E8",ut=4e3,pt="push2delay.eastmoney.com",Ee="push2his.eastmoney.com",mt=[Ee,"7.push2his.eastmoney.com","33.push2his.eastmoney.com","63.push2his.eastmoney.com","91.push2his.eastmoney.com"];function dt(e){return`https://searchapi.eastmoney.com/api/suggest/get?input=${encodeURIComponent(e)}&type=14&token=${at}`}async function V(e){let t=h(e);return t.length===0?[]:(g("eastmoney","quote"),Promise.all(t.map(gt)))}var he={async getStock(e){let[t]=await V([e]);return t||ye(e)},getStocks:V,async getKlines(e,t){return lt(e,t)},async searchStocks(e){g("eastmoney","search");let r=((await Et(e)).QuotationCodeTable?.Data||[]).map(ht).filter(Boolean);return V(r)},async inspectStock(e){return G("eastmoney",e,he.getStock)}};async function lt(e,t){g("eastmoney","kline");let r=_(t),n=J.transform(e),o=`https://${Ee}/api/qt/stock/kline/get?fields1=f1,f2,f3,f4,f5,f6&fields2=${ct}&ut=7eea3edcaed734bea9cbfc24409ed989&klt=${St(r.period)}&fqt=${kt(r.adjust)}&secid=${encodeURIComponent(n)}&beg=19700101&end=20500101&lmt=${r.count}`;return((await yt(o,mt)).data?.klines||[]).map(u=>{let[d,k,v,x,C,P]=u.split(",");return T({close:v,date:d,high:x,low:C,open:k,source:"eastmoney",volume:P})})}async function gt(e){let t=J.transform(e),r=`https://${pt}/api/qt/stock/get?fltt=2&invt=2&secid=${encodeURIComponent(t)}&fields=${it}`,n=await ft(r);return!n?.f57&&!n?.f58?ye(e):ke(e,n)}async function ft(e){let r=(await Y(e,1)).data;if(r?.f57||r?.f58)return r}async function Y(e,t=0){let r;for(let n=0;n<=t;n++)try{let o=await w.get(e).set("Accept","application/json,text/plain,*/*").set("Referer","https://quote.eastmoney.com/").retries(0).timeout(ut);return JSON.parse(o.text)}catch(o){r=o}throw r}function St(e){switch(e){case"week":return"102";case"month":return"103";default:return"101"}}function kt(e){switch(e){case"qfq":return"1";case"hfq":return"2";default:return"0"}}async function Et(e){let t=dt(e);return O()?ce({callbackParam:"cb",url:t}):Y(t,1)}function ht(e){let t=e.QuoteID||"",r=e.Code||t.split(".")[1]||"",n=e.MktNum||t.split(".")[0]||"";return r?n==="1"?`SH${r}`:n==="0"?`SZ${r}`:"":""}function ye(e){return{...y,code:e}}async function yt(e,t){let r;for(let n of t)try{return await Y(wt(e,n))}catch(o){r=o}throw r}function wt(e,t){let r=new URL(e);return r.hostname=t,r.toString()}var I=he;var Rt={SH:{name:0,now:3,low:5,high:4,yesterday:2},SZ:{name:0,now:3,low:5,high:4,yesterday:2},HK:{name:1,now:6,low:5,high:4,yesterday:3},US:{name:0,now:1,low:7,high:6,yesterday:26}};function we(e,t){let r=Rt[e.slice(0,2)],n=r?F(t,r.now):0,o=r?F(t,r.yesterday):0;return{code:String(e).toUpperCase(),name:r?Ot(t,r.name):"---",percent:n?n/o-1:0,now:n,low:r?F(t,r.low):0,high:r?F(t,r.high):0,yesterday:o}}function F(e,t){return Number(e[t]||0)}function Ot(e,t){return String(e[t]||"---")}function q(e){function t(n,o){let s=e.inputPrefixes[n];if(o.indexOf(s)!==0)throw new E(e.marketErrors?.[n]||e.unknownError);let i=o.replace(s,""),u=e.formatOutputCode?e.formatOutputCode(n,i):i;return e.outputPrefixes[n]+u}let r={transform(n){let o=xt(n,e.inputPrefixes);if(!o)throw new E(e.unknownError);return t(o,n)},transforms(n){return n.map(o=>r.transform(o))},SZTransform(n){return t("SZ",n)},SHTransform(n){return t("SH",n)},HKTransform(n){return t("HK",n)},USTransform(n){return t("US",n)}};return r}function xt(e,t){return Object.keys(t).find(r=>e.startsWith(t[r]))}var bt=q({inputPrefixes:{SZ:"SZ",SH:"SH",HK:"HK",US:"US"},outputPrefixes:{SZ:"sz",SH:"sh",HK:"hk",US:"gb_"},unknownError:N,formatOutputCode(e,t){return e==="US"?t.toLowerCase():t}}),W=bt;var Re=[["Referer","https://finance.sina.com.cn/"]];function Pt(e){return`https://hq.sinajs.cn/list=${e.join(",")}`}function Mt(e){return`https://suggest3.sinajs.cn/suggest/type=2&key=${encodeURIComponent(e)}`}function Kt(e,t){return`https://quotes.sina.cn/cn/api/json_v2.php/CN_MarketData.getKLineData?symbol=${e}&scale=${Dt(t.period)}&ma=no&datalen=${t.count}`}async function Ut(e,t){g("sina","kline");let r=_(t);if(r.adjust!=="none")return[];let n=W.transform(e),o=await vt(Kt(n,r));return Array.isArray(o)?o.map(s=>T({close:s.close,date:s.day||"",high:s.high,low:s.low,open:s.open,source:"sina",volume:s.volume})):[]}async function vt(e){let t=await w.get(e).set("Accept","application/json,text/plain,*/*").set("Referer","https://finance.sina.com.cn/");return JSON.parse(t.text)}function Dt(e){switch(e){case"week":return"1200";case"month":return"7200";default:return"240"}}var At=H({kline:{getKlines:Ut},source:"sina",quote:{codeTransform:W,delimiter:",",encoding:"gb18030",headers:Re,getUrl(e){return Pt(e)},isMissing(e){return Q(e)==='""'},parseStock(e,t){return we(e,t)}},search:{encoding:"gb18030",headers:Re,getUrl(e){return Mt(e)},parseCodes(e){let r=e.replace('var suggestvalue="',"").replace('";',"").split(";").flatMap(n=>{let o=n.split(",")[0];if(o.indexOf("us")===0)return["US"+o.replace("us","")];if(o.indexOf("sz")===0)return["SZ"+o.replace("sz","")];if(o.indexOf("sh")===0)return["SH"+o.replace("sh","")];if(o.indexOf("hk")===0)return["HK"+o.replace("hk","")];if(o.indexOf("of")===0){let s=o.replace("of","");return["SZ"+s,"SH"+s]}return[]});return h(r)}}}),B=At;function Oe(e,t){let r=Ft(t),n=$t(t);return{code:Ht(e),name:It(t),percent:r?r/n-1:0,now:r,low:qt(t),high:Bt(t),yesterday:n}}function Ht(e){return String(e).toUpperCase()}function It(e){return String(e[1]||"---")}function Ft(e){return $(e,3)}function qt(e){return $(e,34)}function Bt(e){return $(e,33)}function $t(e){return $(e,4)}function $(e,t){return Number(e[t]||0)}var Qt=q({inputPrefixes:{SZ:"SZ",SH:"SH",HK:"HK",US:"US"},outputPrefixes:{SZ:"sz",SH:"sh",HK:"hk",US:"us"},unknownError:N,formatOutputCode(e,t){return e==="HK"||e==="US"?t.toUpperCase():t}}),X=Qt;function xe(e){return`https://smartbox.gtimg.cn/s3/?v=2&t=all&c=1&q=${encodeURIComponent(e)}`}async function Gt(e){return`v_hint="${await ie({charset:"gbk",url:xe(e),variableName:"v_hint"})}"`}async function Jt(e,t){g("tencent","kline");let r=_(t),n=X.transform(e),o=r.adjust==="none"?"kline/kline":"fqkline/get",i=`${r.adjust==="none"?"":r.adjust}${r.period}`,u=r.adjust==="none"?"":`,${r.adjust}`,d=`https://web.ifzq.gtimg.cn/appstock/app/${o}?param=${n},${r.period},,,${r.count}${u}`;return((await Vt(d)).data?.[n]?.[i]||[]).map(([x,C,P,j,_e,Te])=>T({close:P,date:x,high:j,low:_e,open:C,source:"tencent",volume:Te}))}async function Vt(e){let t=await w.get(e).set("Accept","application/json,text/plain,*/*");return JSON.parse(t.text)}var Yt=H({kline:{getKlines:Jt},source:"tencent",quote:{codeTransform:X,delimiter:"~",encoding:"gbk",getUrl(e){return`https://qt.gtimg.cn/q=${e.join(",")}`},isMissing(e,t){return!e.includes(t)},parseStock(e,t){return Oe(e,t)}},search:{browserRequestText:Gt,encoding:"gbk",getUrl(e){return xe(e)},parseCodes(e){let r=e.replace('v_hint="',"").replace('"',"").split("^").map(n=>{let[o,s]=n.split("~");switch(o){case"sz":return"SZ"+s;case"sh":return"SH"+s;case"hk":return"HK"+s;case"us":return"US"+s.split(".")[0].toUpperCase();default:return""}});return h(r)}}}),L=Yt;var Wt=[{name:"tencent",api:L},{name:"sina",api:B},{name:"eastmoney",api:I}];function Xt(e){let t={async getStock(r){return(await t.inspectStock(r)).stock},async getStocks(r){return Promise.all(h(r).map(n=>t.getStock(n)))},async getKlines(r,n){for(let o of tr(e)){let s=await rr(o,r,n);if(s.length>0)return s}return[]},async searchStocks(r){for(let n of e){let s=(await nr(n,r)).filter(or);if(s.length>0)return s.map(i=>K(i,n.name))}return[]},async inspectStock(r){let n=[],o,s="base";for(let u of e){let d=await u.api.inspectStock(r);n.push(d),!o&&d.status==="success"&&d.stock&&(o=d.stock,s=d.source)}let i=o||K({...y,code:r},"base");return{code:r,source:s,stock:i,sources:n}}};return t}var er=Xt(Wt);function tr(e){let t=new Map([["tencent",0],["sina",1],["eastmoney",2]]);return[...e].sort((r,n)=>(t.get(r.name)??Number.MAX_SAFE_INTEGER)-(t.get(n.name)??Number.MAX_SAFE_INTEGER))}async function rr(e,t,r){try{return await e.api.getKlines(t,r)}catch{return[]}}async function nr(e,t){try{return await e.api.searchStocks(t)}catch{return[]}}function or(e){return!!(e&&e.name!==y.name)}var Ce=er;var sr={async getStock(e){throw new Error(te)},async getStocks(e){throw new Error(re)},async getKlines(e,t){throw new Error(ne)},async searchStocks(e){throw new Error(oe)}},Ne=sr;var ir=["tencent","sina","eastmoney"];function cr(){return[...ir]}var ee={auto:Ce,base:Ne,eastmoney:I,getProviderCapabilities:me,getSources:cr,sina:B,tencent:L};var ar={stocks:ee};return ve(ur);})();
//# sourceMappingURL=stock-api.iife.min.js.map
</script>
<style>
  /* ============================================================
     V3.2 Design System — Premium Trading Dashboard
     ============================================================ */
  :root {
    --bg: #060b10;
    --bg2: #0a1018;
    --surface: #0f1720;
    --surface2: #151e2a;
    --surface3: #1b2533;
    --border: #1e2d3d;
    --border2: #2a3a4d;
    --text: #9aa4b2;
    --text1: #dfe4ea;
    --text2: #6b7685;
    --text3: #3d4755;
    --accent: #5b9cf5;
    --accent-bg: rgba(91,156,245,0.1);
    --green: #22c55e;
    --green-bg: rgba(34,197,94,0.1);
    --red: #ef4444;
    --red-bg: rgba(239,68,68,0.1);
    --gold: #f59e0b;
    --gold-bg: rgba(245,158,11,0.1);
    --purple: #8b5cf6;
    --purple-bg: rgba(139,92,246,0.1);
    --radius: 12px;
    --radius-sm: 8px;
    --radius-xs: 5px;
    --shadow: 0 1px 3px rgba(0,0,0,0.4);
    --shadow-lg: 0 8px 30px rgba(0,0,0,0.5);
    --font: -apple-system, BlinkMacSystemFont, "Microsoft YaHei", "PingFang SC", "Segoe UI", "Helvetica Neue", sans-serif;
    --font-mono: "Cascadia Code", "Fira Code", "JetBrains Mono", "Consolas", monospace;
    --transition: 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  }

  * { box-sizing: border-box; margin: 0; padding: 0; }
  html, body { height: 100%; scroll-behavior: smooth; }

  body {
    font-family: var(--font);
    font-size: 14px;
    background: var(--bg);
    color: var(--text);
    line-height: 1.55;
    overflow-x: hidden;
    -webkit-user-select: none;
    user-select: none;
    -webkit-font-smoothing: antialiased;
  }

  ::-webkit-scrollbar { width: 5px; }
  ::-webkit-scrollbar-track { background: transparent; }
  ::-webkit-scrollbar-thumb { background: var(--border2); border-radius: 3px; }
  ::-webkit-scrollbar-thumb:hover { background: var(--text3); }

  ::selection { background: rgba(91,156,245,0.25); color: #fff; }

  /* ---- Header ---- */
  .header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 14px 20px;
    background: var(--surface);
    border-bottom: 1px solid var(--border);
    position: sticky; top: 0; z-index: 100;
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    background: rgba(15,23,32,0.92);
  }
  .header-left { display: flex; align-items: center; gap: 10px; }
  .header .logo-icon {
    width: 32px; height: 32px;
    background: linear-gradient(135deg, var(--accent), #3b82f6);
    border-radius: 8px;
    display: flex; align-items: center; justify-content: center;
    font-size: 16px;
    box-shadow: 0 2px 8px rgba(91,156,245,0.3);
  }
  .header .logo-text { font-size: 15px; font-weight: 700; color: #fff; letter-spacing: 0.3px; }
  .header .logo-ver {
    font-size: 10px; color: var(--accent); margin-left: 2px; font-weight: 600;
    background: var(--accent-bg); padding: 2px 7px; border-radius: 4px;
    letter-spacing: 0.5px;
  }
  .header-right { display: flex; align-items: center; gap: 10px; }
  .header .status-pill {
    display: flex; align-items: center; gap: 6px;
    font-size: 11px; color: var(--text2);
    background: var(--surface2); padding: 5px 12px; border-radius: 20px;
    border: 1px solid var(--border);
  }
  .status-dot {
    width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0;
  }
  .status-dot.on { background: var(--green); box-shadow: 0 0 6px rgba(34,197,94,0.5); }
  .status-dot.off { background: var(--text3); }
  .status-dot.fetching { background: var(--gold); box-shadow: 0 0 6px rgba(245,158,11,0.5); animation: pulse 0.7s infinite; }

  @keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.15; } }
  @keyframes fadeInUp { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
  @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
  @keyframes slideDown { from { opacity: 0; transform: translateY(-10px); max-height: 0; } to { opacity: 1; transform: translateY(0); max-height: 400px; } }
  @keyframes shimmer { 0% { background-position: -400px 0; } 100% { background-position: 400px 0; } }

  /* ---- Search ---- */
  .search-section {
    padding: 14px 18px;
    background: var(--bg2);
    border-bottom: 1px solid var(--border);
  }
  .chip-row {
    display: flex; flex-wrap: wrap; gap: 6px;
    margin-bottom: 8px; min-height: 0;
  }
  .chip-row:empty { display: none; }
  .stock-chip {
    display: flex; align-items: center; gap: 5px;
    background: var(--accent-bg);
    border: 1px solid rgba(91,156,245,0.2);
    border-radius: 20px;
    padding: 5px 8px 5px 12px;
    font-size: 12px; font-weight: 500; color: var(--accent);
    animation: fadeInUp 0.2s ease;
  }
  .stock-chip .chip-code { font-weight: 700; }
  .chip-remove {
    background: none; border: none; color: var(--text3);
    cursor: pointer; font-size: 16px; line-height: 1; padding: 0 2px;
    transition: color var(--transition);
  }
  .chip-remove:hover { color: var(--red); }

  .search-row {
    display: flex; gap: 8px; align-items: center;
  }
  .search-input-wrap {
    flex: 1; position: relative;
  }
  .search-input-wrap .search-icon {
    position: absolute; left: 12px; top: 50%;
    transform: translateY(-50%);
    font-size: 14px; opacity: 0.35; pointer-events: none; z-index: 1;
  }
  .search-input-wrap input {
    width: 100%;
    background: var(--surface);
    color: #fff;
    border: 1px solid var(--border);
    border-radius: 22px;
    padding: 10px 14px 10px 36px;
    font-size: 14px; font-family: var(--font);
    outline: none;
    transition: all var(--transition);
    box-shadow: inset 0 1px 3px rgba(0,0,0,0.3);
  }
  .search-input-wrap input:focus {
    border-color: var(--accent);
    box-shadow: 0 0 0 3px rgba(91,156,245,0.12), inset 0 1px 3px rgba(0,0,0,0.3);
  }
  .search-input-wrap input::placeholder { color: var(--text3); }

  select {
    background: var(--surface);
    color: var(--text1);
    border: 1px solid var(--border);
    border-radius: 22px;
    padding: 10px 24px 10px 12px;
    font-size: 13px; font-family: var(--font);
    outline: none; cursor: pointer;
    transition: border-color var(--transition);
    -webkit-appearance: none; appearance: none;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='%236b7685' d='M6 8L1 3h10z'/%3E%3C/svg%3E");
    background-repeat: no-repeat;
    background-position: right 8px center;
  }
  select:focus { border-color: var(--accent); }

  .count-input {
    width: 72px;
    background: var(--surface); color: var(--text1);
    border: 1px solid var(--border); border-radius: 22px;
    padding: 10px 6px; font-size: 13px; font-family: var(--font-mono);
    text-align: center; outline: none;
    transition: border-color var(--transition);
  }
  .count-input:focus { border-color: var(--accent); }

  .btn-search {
    background: linear-gradient(135deg, #5b9cf5, #3b82f6);
    color: #fff; border: none;
    border-radius: 22px;
    padding: 10px 22px;
    font-size: 13px; font-weight: 600; font-family: var(--font);
    cursor: pointer;
    transition: all var(--transition);
    white-space: nowrap;
    box-shadow: 0 2px 8px rgba(59,130,246,0.3);
    letter-spacing: 0.3px;
  }
  .btn-search:hover { transform: translateY(-1px); box-shadow: 0 4px 14px rgba(59,130,246,0.4); }
  .btn-search:active { transform: translateY(0); }
  .btn-search:disabled { opacity: 0.5; cursor: not-allowed; transform: none; box-shadow: none; }

  .btn-add {
    background: var(--accent-bg); color: var(--accent);
    border: 1px dashed rgba(91,156,245,0.3); border-radius: 50%;
    width: 36px; height: 36px; font-size: 20px; font-weight: 600;
    cursor: pointer; transition: all var(--transition);
    flex-shrink: 0; display: flex; align-items: center; justify-content: center;
  }
  .btn-add:hover { background: rgba(91,156,245,0.18); border-style: solid; }

  /* ---- Tab Bar ---- */
  .tab-bar {
    display: flex; gap: 0;
    padding: 0 16px;
    background: var(--bg2);
    border-bottom: 1px solid var(--border);
    position: sticky; top: 57px; z-index: 99;
    background: rgba(10,16,24,0.92);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
  }
  .tab-btn {
    background: none; border: none;
    color: var(--text2);
    padding: 12px 18px;
    font-size: 13px; font-weight: 500; font-family: var(--font);
    cursor: pointer;
    transition: all var(--transition);
    position: relative;
    border-bottom: 2px solid transparent;
    margin-bottom: -1px;
  }
  .tab-btn:hover { color: var(--text1); }
  .tab-btn.active {
    color: #fff; font-weight: 600;
    border-bottom-color: var(--accent);
  }
  .tab-btn .tab-icon { margin-right: 5px; font-size: 14px; }

  .tab-content { display: none; animation: fadeInUp 0.25s ease; }
  .tab-content.active { display: block; }

  /* ---- Dashboard Hero ---- */
  .dashboard-hero {
    display: none;
    margin: 14px 16px 0;
    padding: 18px 20px;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    box-shadow: var(--shadow);
  }
  .dashboard-hero.show { display: block; animation: fadeInUp 0.3s ease; }
  .hero-top {
    display: flex; justify-content: space-between; align-items: flex-start;
    margin-bottom: 14px;
  }
  .hero-name {
    font-size: 20px; font-weight: 700; color: #fff;
    letter-spacing: 0.3px;
  }
  .hero-code {
    font-size: 13px; color: var(--text2); font-weight: 400; margin-left: 8px;
    font-family: var(--font-mono);
  }
  .hero-tags { display: flex; gap: 6px; flex-wrap: wrap; }
  .hero-tag {
    font-size: 10px; padding: 3px 10px; border-radius: 12px;
    font-weight: 500;
  }
  .hero-tag.market { background: var(--accent-bg); color: var(--accent); }
  .hero-tag.industry { background: var(--purple-bg); color: var(--purple); }
  .hero-tag.period { background: var(--surface2); color: var(--text2); }

  .hero-price-row {
    display: flex; align-items: baseline; gap: 12px; margin-bottom: 12px;
  }
  .hero-price {
    font-size: 32px; font-weight: 800; font-family: var(--font-mono);
    letter-spacing: -1px;
  }
  .hero-price.up { color: var(--red); }
  .hero-price.down { color: var(--green); }
  .hero-change {
    font-size: 16px; font-weight: 700; font-family: var(--font-mono);
    padding: 4px 10px; border-radius: 6px;
  }
  .hero-change.up { color: #fff; background: var(--red); }
  .hero-change.down { color: #fff; background: var(--green); }
  .hero-change.neutral { color: var(--text2); background: var(--surface2); }

  .hero-stats {
    display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px;
  }
  .hero-stat {
    background: var(--surface2);
    border-radius: var(--radius-sm);
    padding: 10px 12px;
    border: 1px solid var(--border);
  }
  .hero-stat .stat-label { font-size: 10px; color: var(--text2); margin-bottom: 3px; text-transform: uppercase; letter-spacing: 0.5px; }
  .hero-stat .stat-value { font-size: 14px; font-weight: 700; color: var(--text1); font-family: var(--font-mono); }

  /* ---- Chart Section ---- */
  .chart-section {
    margin: 12px 16px 0;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    box-shadow: var(--shadow);
    overflow: hidden;
  }
  .chart-header {
    display: flex; justify-content: space-between; align-items: center;
    padding: 10px 16px;
    background: var(--surface2);
    border-bottom: 1px solid var(--border);
  }
  .chart-title { font-size: 12px; font-weight: 600; color: var(--text1); letter-spacing: 0.3px; }
  .chart-toggles { display: flex; gap: 12px; }
  .chart-toggles label {
    font-size: 11px; color: var(--text2); cursor: pointer;
    display: flex; align-items: center; gap: 4px;
    transition: color var(--transition);
  }
  .chart-toggles label:hover { color: var(--text1); }
  .chart-toggles input[type="checkbox"] { accent-color: var(--accent); cursor: pointer; }
  .chart-body {
    padding: 8px 4px 4px;
    position: relative;
    overflow-x: auto;
    cursor: crosshair;
  }
  .chart-body svg { display: block; }

  .chart-tooltip {
    display: none; position: absolute;
    background: rgba(21,30,42,0.96);
    border: 1px solid var(--border2);
    border-radius: var(--radius-sm);
    padding: 10px 14px;
    font-size: 11px; font-family: var(--font-mono);
    color: var(--text1);
    pointer-events: none; z-index: 10;
    box-shadow: 0 8px 24px rgba(0,0,0,0.5);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    white-space: nowrap; line-height: 1.7;
  }
  .chart-tooltip .tt-date { font-size: 12px; font-weight: 700; margin-bottom: 4px; }
  .chart-tooltip table { font-size: 10px; }
  .chart-tooltip td { padding: 0 4px; }
  .chart-tooltip .tt-label { color: var(--text2); }
  .chart-tooltip .tt-divider { border-top: 1px solid var(--border); }

  .chart-legend {
    display: flex; gap: 14px; padding: 6px 16px 8px;
    font-size: 10px; color: var(--text2);
    border-top: 1px solid var(--border);
  }
  .chart-legend span { display: flex; align-items: center; gap: 4px; }
  .chart-legend .legend-dot { width: 8px; height: 2px; border-radius: 1px; }

  /* ---- Indicator Cards ---- */
  .indicator-grid {
    display: none;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
    margin: 10px 16px;
  }
  .indicator-grid.show { display: grid; }

  .ind-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    padding: 12px 14px;
    transition: all var(--transition);
    box-shadow: var(--shadow);
  }
  .ind-card:hover { border-color: var(--border2); }
  .ind-card .ind-label {
    font-size: 11px; color: var(--text2); font-weight: 500;
    margin-bottom: 4px; letter-spacing: 0.3px;
  }
  .ind-card .ind-value {
    font-size: 18px; font-weight: 700; font-family: var(--font-mono);
    color: var(--text1);
  }
  .ind-card .ind-value.up { color: var(--red); }
  .ind-card .ind-value.down { color: var(--green); }
  .ind-card .ind-value.warn { color: var(--gold); }
  .ind-card .ind-note { font-size: 10px; color: var(--text3); margin-top: 3px; }
  .ind-card .ind-gauge {
    margin-top: 6px; height: 4px; background: var(--surface2);
    border-radius: 2px; overflow: hidden;
  }
  .ind-card .ind-gauge-fill {
    height: 100%; border-radius: 2px;
    transition: width 0.5s ease;
  }
  .ind-card .ind-gauge-fill.rsi-overbought { background: var(--red); }
  .ind-card .ind-gauge-fill.rsi-neutral { background: var(--accent); }
  .ind-card .ind-gauge-fill.rsi-oversold { background: var(--green); }
  .ind-card .ind-gauge-fill.boll-wide { background: var(--purple); }

  /* Full-width cards for summary stats */
  .ind-card.full { grid-column: 1 / -1; }
  .summary-row {
    display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px;
  }

  /* ---- Action Bar ---- */
  .action-bar {
    display: none;
    margin: 10px 16px;
    gap: 8px;
    flex-wrap: wrap;
  }
  .action-bar.show { display: flex; }

  .btn-action {
    background: var(--surface2); color: var(--text1);
    border: 1px solid var(--border); border-radius: 22px;
    padding: 9px 18px; font-size: 12px; font-family: var(--font);
    cursor: pointer; font-weight: 500;
    transition: all var(--transition);
    letter-spacing: 0.2px;
    display: flex; align-items: center; gap: 6px;
  }
  .btn-action:hover { background: var(--surface3); border-color: var(--border2); transform: translateY(-1px); box-shadow: 0 2px 8px rgba(0,0,0,0.3); }
  .btn-action:active { transform: scale(0.97); }
  .btn-action.btn-accent {
    background: var(--accent-bg); color: var(--accent);
    border-color: rgba(91,156,245,0.3); font-weight: 600;
  }
  .btn-action.btn-accent:hover { background: rgba(91,156,245,0.18); border-color: rgba(91,156,245,0.5); }
  .btn-action.btn-purple {
    background: var(--purple-bg); color: var(--purple);
    border-color: rgba(139,92,246,0.3); font-weight: 600;
  }
  .btn-action.btn-purple:hover { background: rgba(139,92,246,0.15); }
  .btn-action.btn-gold {
    background: var(--gold-bg); color: var(--gold);
    border-color: rgba(245,158,11,0.3); font-weight: 600;
  }
  .btn-action.btn-gold:hover { background: rgba(245,158,11,0.15); }

  /* ---- History ---- */
  .history-section {
    margin: 0 16px 12px;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    box-shadow: var(--shadow);
    overflow: hidden;
  }
  .history-header {
    display: flex; justify-content: space-between; align-items: center;
    padding: 10px 16px;
    background: var(--surface2);
    border-bottom: 1px solid var(--border);
  }
  .history-title { font-size: 12px; font-weight: 600; color: var(--text1); letter-spacing: 0.3px; }
  .history-list { max-height: 240px; overflow-y: auto; }
  .history-item {
    display: flex; align-items: center; gap: 12px;
    padding: 9px 16px;
    border-bottom: 1px solid rgba(255,255,255,0.02);
    font-size: 12px;
    transition: background var(--transition);
  }
  .history-item:hover { background: rgba(255,255,255,0.015); }
  .history-item:last-child { border-bottom: none; }
  .history-time { color: var(--text3); font-family: var(--font-mono); font-size: 11px; min-width: 48px; }
  .history-code {
    font-weight: 600; color: var(--accent); min-width: 70px;
    font-family: var(--font-mono);
  }
  .history-name { color: var(--text1); flex: 1; font-weight: 500; }
  .history-status {
    font-size: 10px; font-weight: 600; padding: 2px 8px; border-radius: 10px;
    letter-spacing: 0.3px;
  }
  .history-status.ok { background: var(--green-bg); color: var(--green); }
  .history-status.err { background: var(--red-bg); color: var(--red); }
  .history-status.cache { background: var(--accent-bg); color: var(--accent); }
  .history-status.pend { background: var(--gold-bg); color: var(--gold); }

  .history-empty {
    text-align: center; padding: 32px 20px; color: var(--text3);
  }
  .history-empty .empty-icon { font-size: 32px; margin-bottom: 8px; opacity: 0.5; }
  .history-empty .empty-text { font-size: 12px; }

  /* ---- Empty State ---- */
  .empty-state {
    display: flex; flex-direction: column; align-items: center; justify-content: center;
    padding: 56px 24px; text-align: center;
  }
  .empty-state .empty-illustration {
    width: 120px; height: 120px; margin-bottom: 16px;
    border-radius: 50%;
    background: var(--surface2);
    display: flex; align-items: center; justify-content: center;
    font-size: 52px; opacity: 0.7;
    border: 1px solid var(--border);
  }
  .empty-state h3 { font-size: 15px; color: var(--text1); font-weight: 600; margin-bottom: 6px; }
  .empty-state p { font-size: 12px; color: var(--text2); line-height: 1.8; max-width: 360px; }

  /* ---- Tab: Formula ---- */
  .formula-section {
    margin: 14px 16px;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 18px;
    box-shadow: var(--shadow);
  }
  .formula-section .section-title { font-size: 14px; font-weight: 700; color: #fff; margin-bottom: 10px; }
  .formula-section .section-desc { font-size: 12px; color: var(--text2); margin-bottom: 12px; line-height: 1.6; }

  textarea {
    width: 100%; min-height: 90px;
    background: var(--bg); color: var(--text1);
    border: 1px solid var(--border); border-radius: var(--radius-sm);
    padding: 12px; font-size: 12px; font-family: var(--font-mono);
    resize: vertical; outline: none;
    transition: all var(--transition);
    box-shadow: inset 0 1px 3px rgba(0,0,0,0.3);
  }
  textarea:focus { border-color: var(--accent); box-shadow: 0 0 0 3px rgba(91,156,245,0.1), inset 0 1px 3px rgba(0,0,0,0.3); }

  /* ---- Settings ---- */
  .settings-section {
    padding: 14px 16px;
  }
  .setting-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 16px 18px;
    margin-bottom: 10px;
    box-shadow: var(--shadow);
  }
  .setting-card .card-title { font-size: 13px; font-weight: 700; color: #fff; margin-bottom: 12px; }
  .setting-item { margin-bottom: 14px; }
  .setting-item:last-child { margin-bottom: 0; }
  .setting-item label {
    display: block; font-size: 10px; color: var(--text2);
    margin-bottom: 5px; text-transform: uppercase;
    letter-spacing: 0.6px; font-weight: 600;
  }
  .setting-item .setting-hint { font-size: 10px; color: var(--text3); margin-top: 4px; }
  .setting-item input[type="text"],
  .setting-item input[type="number"] {
    background: var(--bg); color: var(--text1);
    border: 1px solid var(--border); border-radius: var(--radius-sm);
    padding: 9px 12px; font-size: 13px; font-family: var(--font);
    outline: none; width: 100%;
    transition: all var(--transition);
  }
  .setting-item input:focus { border-color: var(--accent); box-shadow: 0 0 0 3px rgba(91,156,245,0.1); }
  .setting-item input[type="number"] { width: 140px; }

  .toggle-wrap {
    display: flex; align-items: center; gap: 10px; cursor: pointer;
  }
  .toggle-sw {
    width: 40px; height: 24px;
    background: var(--border2); border-radius: 12px;
    position: relative; cursor: pointer;
    transition: all 0.25s ease;
  }
  .toggle-sw.on { background: var(--green); box-shadow: 0 0 10px rgba(34,197,94,0.3); }
  .toggle-sw::after {
    content: ''; position: absolute;
    top: 2px; left: 2px;
    width: 20px; height: 20px;
    background: #fff; border-radius: 50%;
    transition: transform 0.25s ease;
    box-shadow: 0 1px 4px rgba(0,0,0,0.3);
  }
  .toggle-sw.on::after { transform: translateX(16px); }

  /* ---- Alert Cards ---- */
  .alert-item {
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    padding: 12px 14px;
    margin-bottom: 6px;
    transition: all var(--transition);
  }
  .alert-item:hover { border-color: var(--border2); }
  .alert-item.triggered { border-color: var(--red); box-shadow: 0 0 12px rgba(239,68,68,0.15); }
  .alert-top {
    display: flex; justify-content: space-between; align-items: center;
    margin-bottom: 8px;
  }
  .alert-name { font-size: 14px; font-weight: 700; color: var(--text1); }
  .alert-status {
    font-size: 10px; font-weight: 600; padding: 3px 10px; border-radius: 10px;
  }
  .alert-status.monitoring { background: var(--green-bg); color: var(--green); }
  .alert-status.triggered { background: var(--red-bg); color: var(--red); }
  .alert-status.paused { background: var(--surface3); color: var(--text2); }
  .alert-prices {
    display: flex; align-items: center; gap: 10px; font-size: 12px;
  }
  .alert-price-up { color: var(--red); font-weight: 600; }
  .alert-price-down { color: var(--green); font-weight: 600; }
  .alert-actions { display: flex; gap: 6px; margin-top: 8px; }

  .btn-sm {
    font-size: 10px; padding: 4px 10px; border-radius: 4px; cursor: pointer;
    font-family: var(--font); transition: all var(--transition);
    border: 1px solid var(--border);
  }
  .btn-sm.test { background: var(--surface3); color: var(--text2); }
  .btn-sm.test:hover { background: var(--accent-bg); color: var(--accent); border-color: rgba(91,156,245,0.3); }
  .btn-sm.delete { background: rgba(239,68,68,0.1); color: var(--red); border-color: rgba(239,68,68,0.2); }
  .btn-sm.delete:hover { background: rgba(239,68,68,0.2); }

  .btn-primary {
    background: var(--accent-bg); color: var(--accent);
    border: 1px solid rgba(91,156,245,0.3);
    border-radius: 22px;
    padding: 10px 22px;
    font-size: 13px; font-weight: 600; font-family: var(--font);
    cursor: pointer;
    transition: all var(--transition);
  }
  .btn-primary:hover { background: rgba(91,156,245,0.18); border-color: rgba(91,156,245,0.5); }
  .btn-danger {
    background: transparent; color: var(--red);
    border: 1px solid rgba(239,68,68,0.2);
    border-radius: 22px;
    padding: 9px 18px; font-size: 12px; font-family: var(--font);
    cursor: pointer;
    transition: all var(--transition);
  }
  .btn-danger:hover { background: var(--red-bg); border-color: rgba(239,68,68,0.4); }

  /* ---- Toast ---- */
  .toast {
    position: fixed; bottom: 28px; left: 50%;
    transform: translateX(-50%) translateY(20px);
    background: var(--surface3); color: #fff;
    padding: 11px 26px; border-radius: 24px;
    font-size: 12px; font-weight: 500;
    opacity: 0; pointer-events: none; z-index: 9999;
    box-shadow: 0 6px 24px rgba(0,0,0,0.5);
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    border: 1px solid var(--border2);
  }
  .toast.show { opacity: 1; transform: translateX(-50%) translateY(0); }
  .toast.error { background: rgba(239,68,68,0.15); color: #fca5a5; border-color: rgba(239,68,68,0.3); }

  /* ---- Error Banner ---- */
  .error-banner {
    display: none; margin: 8px 16px;
    padding: 12px 16px;
    background: var(--red-bg);
    border: 1px solid rgba(239,68,68,0.25);
    border-radius: var(--radius-sm);
    font-size: 12px; color: #fca5a5;
    word-break: break-all;
    -webkit-user-select: text; user-select: text;
  }
  .error-banner.show { display: block; animation: fadeIn 0.2s ease; }
  .error-banner .err-title { font-weight: 700; color: #ef4444; margin-bottom: 5px; font-size: 13px; }
  .error-banner .err-detail {
    color: var(--text2); font-size: 11px; font-family: var(--font-mono);
    white-space: pre-wrap; max-height: 130px; overflow-y: auto;
    margin-top: 5px; line-height: 1.5;
  }
  .error-banner .err-close {
    float: right; color: var(--text2); font-size: 18px;
    line-height: 1; cursor: pointer; padding: 0 5px;
    transition: color var(--transition);
  }
  .error-banner .err-close:hover { color: #fff; }

  /* ---- Modal ---- */
  .modal-overlay {
    display: none; position: fixed; top: 0; left: 0; right: 0; bottom: 0;
    background: rgba(0,0,0,0.85); z-index: 9998;
    align-items: center; justify-content: center;
    backdrop-filter: blur(4px);
    -webkit-backdrop-filter: blur(4px);
  }
  .modal-overlay.show { display: flex; animation: fadeIn 0.2s ease; }
  .modal-content {
    background: var(--surface);
    border: 1px solid var(--border2);
    border-radius: var(--radius);
    padding: 16px;
    max-width: 95vw;
    box-shadow: var(--shadow-lg);
  }
  .modal-header {
    display: flex; justify-content: space-between; align-items: center;
    margin-bottom: 12px;
  }
  .modal-title { font-size: 14px; font-weight: 700; color: #fff; }
  .modal-close {
    background: none; border: none; color: var(--text2);
    font-size: 22px; cursor: pointer; line-height: 1;
    transition: color var(--transition);
  }
  .modal-close:hover { color: #fff; }

  /* ---- Skeleton Loading ---- */
  .skeleton {
    background: linear-gradient(90deg, var(--surface2) 0%, var(--surface3) 50%, var(--surface2) 100%);
    background-size: 400px 100%;
    animation: shimmer 1.5s infinite;
  }

  /* ---- Footer ---- */
  .footer {
    text-align: center; color: var(--text3);
    font-size: 10px; padding: 12px 8px; opacity: 0.4;
    letter-spacing: 0.2px;
  }
</style>
</head>
<body>

<!-- Header -->
<header class="header">
  <div class="header-left">
    <div class="logo-icon">📈</div>
    <span class="logo-text">Stock JSON Clipper</span>
    <span class="logo-ver">V3.2</span>
  </div>
  <div class="header-right">
    <div class="status-pill" id="statusPill">
      <div class="status-dot on" id="statusDot"></div>
      <span id="statusText">就绪</span>
    </div>
  </div>
</header>

<!-- Search -->
<div class="search-section">
  <div class="chip-row" id="chipRow"></div>
  <div class="search-row">
    <div class="search-input-wrap">
      <span class="search-icon">🔍</span>
      <input type="text" class="codeInput" id="mainSearchInput"
             placeholder="输入代码，如 000001 或 SH600519"
             maxlength="10" autofocus autocomplete="off">
    </div>
    <button class="btn-add" onclick="addChip()" title="添加对比股票">+</button>
  </div>
  <div class="search-row" style="margin-top:8px;">
    <select id="searchPeriod">
      <option value="1min">1分</option>
      <option value="5min">5分</option>
      <option value="15min">15分</option>
      <option value="30min">30分</option>
      <option value="60min">60分</option>
      <option value="daily" selected>日线</option>
      <option value="weekly">周线</option>
      <option value="monthly">月线</option>
    </select>
    <input type="number" id="searchCount" value="250" min="5" max="9999"
           class="count-input" title="K线条数">
    <button class="btn-search" id="searchBtn" onclick="onSearch()">查询</button>
  </div>
</div>

<!-- Error Banner -->
<div class="error-banner" id="errorBanner" onclick="if(event.target.classList.contains('err-close'))document.getElementById('errorBanner').classList.remove('show')">
  <span class="err-close">&times;</span>
  <div class="err-title" id="errTitle">⚠ 错误</div>
  <div class="err-detail" id="errDetail"></div>
</div>

<!-- Tab Bar -->
<nav class="tab-bar">
  <button class="tab-btn active" data-tab="overview"><span class="tab-icon">📊</span>概览</button>
  <button class="tab-btn" data-tab="formula"><span class="tab-icon">🤖</span>AI分析</button>
  <button class="tab-btn" data-tab="alerts"><span class="tab-icon">🔔</span>预警</button>
  <button class="tab-btn" data-tab="settings"><span class="tab-icon">⚙️</span>设置</button>
</nav>

<!-- ====== Tab: 概览 ====== -->
<div class="tab-content active" id="tab-overview">

  <!-- Dashboard Hero -->
  <div class="dashboard-hero" id="dashboardHero">
    <div class="hero-top">
      <div>
        <span class="hero-name" id="heroName">--</span>
        <span class="hero-code" id="heroCode"></span>
      </div>
      <div class="hero-tags" id="heroTags"></div>
    </div>
    <div class="hero-price-row">
      <span class="hero-price" id="heroPrice">--</span>
      <span class="hero-change" id="heroChange">--</span>
    </div>
    <div class="hero-stats" id="heroStats"></div>
  </div>

  <!-- Chart -->
  <div class="chart-section" id="chartSection" style="display:none;">
    <div class="chart-header">
      <span class="chart-title">📈 K线图 <span style="color:var(--text2);font-weight:400;" id="chartPeriodLabel"></span></span>
      <div class="chart-toggles">
        <label><input type="checkbox" checked onchange="toggleIndicator(0)"> MACD</label>
        <label><input type="checkbox" checked onchange="toggleIndicator(1)"> RSI</label>
      </div>
    </div>
    <div class="chart-body" id="chartBody" onclick="openLargeChart()" title="点击查看大图">
      <div class="chart-tooltip" id="chartTooltip"></div>
    </div>
    <div class="chart-legend" id="chartLegend" style="display:none;">
      <span><span class="legend-dot" style="background:var(--gold);"></span> MA5</span>
      <span><span class="legend-dot" style="background:var(--purple);"></span> MA20</span>
      <span><span class="legend-dot" style="background:var(--accent);"></span> DIF</span>
      <span><span class="legend-dot" style="background:var(--text2);"></span> DEA</span>
      <span><span class="legend-dot" style="background:#a78bfa;"></span> RSI</span>
    </div>
  </div>

  <!-- Indicator Cards -->
  <div class="indicator-grid" id="indicatorGrid"></div>

  <!-- Action Bar -->
  <div class="action-bar" id="actionBar">
    <button class="btn-action btn-accent" onclick="onCopyJSON()">📋 复制JSON</button>
    <button class="btn-action" onclick="onSaveFile()">💾 保存文件</button>
    <button class="btn-action btn-purple" onclick="onSmartAnalyze()">🤖 AI分析</button>
    <button class="btn-action btn-gold" onclick="onFullAnalyze()">🧠 深度分析</button>
    <div style="flex-basis:100%;margin-top:4px;">
      <div style="font-size:11px;color:var(--text2);margin-bottom:4px;font-weight:500;">📐 通达信公式（可选，粘贴后点AI分析）</div>
      <textarea id="formulaInput" placeholder="粘贴选股公式&#10;例: CROSS(MA(C,5),MA(C,20)) AND RSI(6)>50" style="min-height:70px;width:100%;font-size:12px;"></textarea>
    </div>
  </div>

  <!-- Empty State -->
  <div class="empty-state" id="emptyState">
    <div class="empty-illustration">📡</div>
    <h3>暂无查询数据</h3>
    <p>在上方输入股票代码点击「查询」<br>或在通达信/同花顺中复制代码自动识别<br><br><span style="color:var(--text3);">支持: 000001（日线）/ W:000001（周线）/ M:000001（月线）/ #000001（保存文件）</span></p>
  </div>

  <!-- History -->
  <div class="history-section">
    <div class="history-header">
      <span class="history-title">📜 最近查询记录</span>
      <span style="font-size:10px;color:var(--text3);" id="historyCount"></span>
    </div>
    <div class="history-list" id="historyList">
      <div class="history-empty">
        <div class="empty-icon">📋</div>
        <div class="empty-text">暂无记录 — 查询或复制股票代码后自动显示</div>
      </div>
    </div>
  </div>
</div>

<!-- ====== Tab: AI分析 ====== -->
<div class="tab-content" id="tab-formula">
  <div class="formula-section">
    <div class="section-title">🤖 通达信公式 → AI分析提示词</div>
    <div class="section-desc">
      将通达信选股公式粘贴到下方，系统会自动解析公式要素，结合当前股票的技术指标，
      生成一份专业的AI分析提示词。将提示词粘贴到 ChatGPT / DeepSeek / Claude 对话框即可获得分析。
    </div>
    <textarea id="formulaInputTab" placeholder="在此粘贴通达信选股公式&#10;例如: CROSS(MA(收盘价,5), MA(收盘价,20)) AND RSI(6) 大于 50&#10;&#10;支持: MA均线 / MACD / RSI / BOLL布林带 / CROSS金叉死叉 / 比较运算"></textarea>
    <div style="display:flex;gap:8px;margin-top:12px;flex-wrap:wrap;">
      <button class="btn-action btn-accent" onclick="onTabGeneratePrompt()">✨ 生成选股分析提示词</button>
      <button class="btn-action" onclick="onTabQuickAnalyze()">📊 快速技术分析（无需公式）</button>
      <button class="btn-action" onclick="document.getElementById('formulaInputTab').value=''" style="color:var(--text2);">清空公式</button>
    </div>
    <div style="font-size:10px;color:var(--text3);margin-top:8px;">
      提示词将自动复制到剪贴板，直接粘贴到AI对话框使用。生成前请先查询股票数据。
    </div>
  </div>
</div>

<!-- ====== Tab: 预警 ====== -->
<div class="tab-content" id="tab-alerts">
  <div class="settings-section">
    <div class="setting-card">
      <div class="card-title">🔔 价格预警</div>
      <div class="toggle-wrap" onclick="onToggleAlerts()" style="margin-bottom:14px;">
        <div class="toggle-sw on" id="alertsMasterToggle"></div>
        <span style="font-size:14px;">启用后台价格监控</span>
      </div>
      <div class="setting-hint" style="color:var(--text3);font-size:11px;margin-bottom:8px;">
        关闭面板后仍在后台运行，触发阈值时弹出托盘通知
      </div>

      <div id="alertList">
        <div id="alertEmptyHint" style="text-align:center;color:var(--text3);padding:16px 0;font-size:13px;">
          暂无自选股<br><span style="font-size:11px;">点击下方按钮添加，阈值留空则仅显示报价不预警</span>
        </div>
      </div>

      <button class="btn-primary" onclick="onShowAddAlert()" style="margin-top:8px;">＋ 添加股票</button>

      <div id="alertAddForm" style="display:none;margin-top:10px;padding:14px;background:var(--surface2);border:1px solid var(--border);border-radius:var(--radius-sm);animation:slideDown 0.3s ease;">
        <div style="font-size:14px;font-weight:700;margin-bottom:10px;color:var(--text1);">添加自选股</div>
        <div class="setting-item">
          <label>股票代码（6位数字，自动补全SH/SZ）</label>
          <input type="text" id="alertCode" placeholder="例如: 600519" maxlength="10" style="width:100%;font-size:14px;padding:10px;">
        </div>
        <div class="setting-item">
          <label>股票名称（选填，留空自动获取）</label>
          <input type="text" id="alertName" placeholder="例如: 贵州茅台" maxlength="16" style="width:100%;font-size:14px;padding:10px;">
        </div>
        <div class="setting-item">
          <label>📈 上限提醒价（元，不设则留空）</label>
          <input type="number" id="alertUpper" placeholder="例如: 1600" step="0.01" min="0" style="width:100%;font-size:14px;padding:10px;">
        </div>
        <div class="setting-item">
          <label>📉 下限提醒价（元，不设则留空）</label>
          <input type="number" id="alertLower" placeholder="例如: 1400" step="0.01" min="0" style="width:100%;font-size:14px;padding:10px;">
        </div>
        <div style="display:flex;gap:8px;margin-top:10px;">
          <button class="btn-primary" onclick="onSaveAlert()">💾 保存</button>
          <button class="btn-action" onclick="onCancelAddAlert()">取消</button>
        </div>
      </div>
    </div>
  </div>
</div>

<!-- ====== Tab: 设置 ====== -->
<div class="tab-content" id="tab-settings">
  <div class="settings-section">
    <div class="setting-card">
      <div class="card-title">🔌 剪贴板监控</div>
      <div class="toggle-wrap" onclick="onToggleMonitor()">
        <div class="toggle-sw on" id="clipboardToggle"></div>
        <span style="font-size:13px;">启用剪贴板自动识别</span>
      </div>
      <div class="setting-hint" style="color:var(--text3);font-size:11px;margin-top:4px;">
        关闭后仅可通过上方搜索框手动输入代码查询
      </div>
    </div>

    <div class="setting-card">
      <div class="card-title">📊 数据设置</div>
      <div class="setting-item">
        <label>默认拉取K线条数（5 ~ 9999）</label>
        <input type="number" id="defaultCount" min="5" max="9999" value="250"
               onchange="onConfigChange('default_count', parseInt(this.value))">
        <div class="setting-hint">数值越大包含的历史数据越多，但JSON越长</div>
      </div>
      <div class="setting-item">
        <label>JSON文件保存目录（留空 = 程序所在目录）</label>
        <input type="text" id="saveDirectory" placeholder="例如: D:\股票数据" style="width:100%;"
               onchange="onConfigChange('save_directory', this.value)">
        <div class="setting-hint">修改后点击「💾 保存为JSON文件」时将保存到新目录</div>
      </div>
    </div>

    <div class="setting-card">
      <div class="card-title">⚡ 高级设置</div>
      <div class="setting-item">
        <label>剪贴板轮询间隔（秒，0.2 ~ 5）</label>
        <input type="number" id="pollInterval" min="0.2" max="5" step="0.1" value="0.5"
               onchange="onConfigChange('poll_interval', parseFloat(this.value))">
        <div class="setting-hint">每0.5秒检查一次剪贴板。调大可以减少CPU占用</div>
      </div>
      <div class="setting-item">
        <label>数据缓存时间（秒，10 ~ 3600）</label>
        <input type="number" id="cacheTTL" min="10" max="3600" value="300"
               onchange="onConfigChange('cache_ttl', parseInt(this.value))">
        <div class="setting-hint">同一代码在缓存时间内重复查询将直接返回缓存结果，不消耗API请求</div>
      </div>
    </div>

    <div style="padding:0 0 10px 0;">
      <button class="btn-danger" onclick="onClearCache()">🗑 清空数据缓存</button>
    </div>
  </div>
</div>

<!-- Toast -->
<div class="toast" id="toast"></div>

<!-- Chart Modal -->
<div class="modal-overlay" id="chartModal" onclick="if(event.target===this)closeModal()">
  <div class="modal-content" id="chartModalContent"></div>
</div>

<div class="footer">Stock JSON Clipper V3.2 · GPL-3.0 · 数据来源: 腾讯财经/新浪财经/东方财富</div>

<script>
// ============================================================
// Global Error Handler
// ============================================================
window._showError = function(title, detail) {
  var banner = document.getElementById('errorBanner');
  document.getElementById('errTitle').textContent = '⚠ ' + (title || '错误');
  document.getElementById('errDetail').textContent = detail || '';
  banner.classList.add('show');
  var toast = document.getElementById('toast');
  toast.textContent = title || detail || '未知错误';
  toast.classList.add('show', 'error');
  clearTimeout(toast._timeout);
  toast._timeout = setTimeout(function() { toast.classList.remove('show', 'error'); }, 6000);
};

window.onerror = function(msg, url, line, col, err) {
  var detail = msg;
  if (url) detail += '\n文件: ' + url;
  if (line) detail += '\n行: ' + line + (col ? ':' + col : '');
  if (err && err.stack) detail += '\n\n' + err.stack;
  window._showError('JavaScript 运行时错误', detail);
  return false;
};

window.addEventListener('unhandledrejection', function(e) {
  var detail = (e.reason ? (e.reason.message || String(e.reason)) : 'Promise rejected');
  if (e.reason && e.reason.stack) detail += '\n\n' + e.reason.stack;
  window._showError('异步错误', detail);
  var st = document.getElementById('statusText');
  if (st) st.textContent = 'ERROR: ' + detail.substring(0, 100);
});

// ============================================================
// Tab switching
// ============================================================
(function() {
  var btns = document.querySelectorAll('.tab-btn');
  for (var i = 0; i < btns.length; i++) {
    btns[i].addEventListener('click', function() {
      var tab = this.dataset.tab;
      var allBtns = document.querySelectorAll('.tab-btn');
      for (var j = 0; j < allBtns.length; j++) allBtns[j].classList.remove('active');
      var allTabs = document.querySelectorAll('.tab-content');
      for (var k = 0; k < allTabs.length; k++) allTabs[k].classList.remove('active');
      this.classList.add('active');
      document.getElementById('tab-' + tab).classList.add('active');
    });
  }
})();

// ============================================================
// Chip-based multi-stock search
// ============================================================
var _maxStocks = 6;
var _chipCodes = [];

function addChip(raw) {
  var v = (typeof raw === 'string') ? raw : document.getElementById('mainSearchInput').value.trim();
  if (!v) { showToast('请输入股票代码'); return; }
  var code = toStockApiCode(v);
  if (!code) { showToast('无效代码格式'); return; }
  if (_chipCodes.length >= _maxStocks) { showToast('最多对比' + _maxStocks + '只股票'); return; }
  if (_chipCodes.indexOf(code) >= 0) { showToast('已添加该股票'); return; }
  _chipCodes.push(code);
  document.getElementById('mainSearchInput').value = '';
  document.getElementById('mainSearchInput').focus();
  renderChips();
}

function removeChip(index) {
  _chipCodes.splice(index, 1);
  renderChips();
}

function renderChips() {
  var row = document.getElementById('chipRow');
  var html = '';
  for (var i = 0; i < _chipCodes.length; i++) {
    var display = _chipCodes[i].replace(/^(SH|SZ)/, '');
    html += '<div class="stock-chip"><span class="chip-code">' + display + '</span><button class="chip-remove" onclick="removeChip(' + i + ')">&times;</button></div>';
  }
  row.innerHTML = html;
}

function getSearchCodes() {
  if (_chipCodes.length > 0) return _chipCodes.slice();
  var v = document.getElementById('mainSearchInput').value.trim();
  if (!v) return [];
  var code = toStockApiCode(v);
  return code ? [code] : [];
}

function toStockApiCode(raw) {
  var c = raw.trim().toUpperCase().replace(/[#WM:]/g, '');
  if (/^(SH|SZ|HK|US)/.test(c)) return c;
  if (/^\d{6}$/.test(c)) return (c.startsWith('60') || c.startsWith('68')) ? 'SH' + c : 'SZ' + c;
  if (/^\d{5}$/.test(c)) return 'HK' + c;
  return null;
}

// ============================================================
// Search
// ============================================================
function onSearch() {
  var codes = getSearchCodes();
  if (!codes.length) { showToast('请输入股票代码'); return; }

  if (codes.length > 1) { return onCompare(codes); }

  var code = codes[0];
  var period = document.getElementById('searchPeriod').value;
  var count = parseInt(document.getElementById('searchCount').value) || 250;
  count = Math.max(5, Math.min(9999, count));
  var isIntraday = /min$/.test(period);
  var btn = document.getElementById('searchBtn');
  btn.disabled = true; btn.textContent = '查询中…';

  document.getElementById('statusDot').className = 'status-dot fetching';
  document.getElementById('statusText').textContent = '拉取 ' + code + '…';

  function doCompute(klines, stockInfo) {
    pywebview.api.compute_indicators(code, klines, stockInfo, period).then(function(detail) {
      window._currentResult = detail;
      renderDashboard(detail);
      renderChart(detail.data, period);
      document.getElementById('statusText').textContent = (stockInfo.name || code) + ' | ' + klines.length + '条';
      document.getElementById('statusDot').className = 'status-dot on';
      btn.disabled = false; btn.textContent = '查询';
    });
  }

  try {
    if (isIntraday) {
      pywebview.api.fetch_intraday(code, period, count).then(function(klines) {
        if (!klines || !klines.length) { window._showError('无数据', '分时数据暂无'); btn.disabled = false; btn.textContent = '查询'; return; }
        StockApi.stocks.auto.getStock(code).then(function(stock) {
          doCompute(klines, {name: stock.name || code});
        }).catch(function() {
          doCompute(klines, {name: code});
        });
      });
    } else {
      var sp = {daily:'day', weekly:'week', monthly:'month'};
      Promise.all([
        StockApi.stocks.auto.getKlines(code, {period: sp[period] || 'day', count: count}),
        StockApi.stocks.auto.getStock(code)
      ]).then(function(results) {
        doCompute(results[0], {name: results[1].name, now: results[1].now, percent: results[1].percent,
                                high: results[1].high, low: results[1].low, yesterday: results[1].yesterday});
      }).catch(function(e) {
        window._showError('查询失败', (e && e.message) || String(e));
        btn.disabled = false; btn.textContent = '查询';
        document.getElementById('statusDot').className = 'status-dot on';
      });
    }
  } catch(e) { window._showError('错误', String(e)); btn.disabled = false; btn.textContent = '查询'; }
}

function onCompare(codes) {
  if (codes.length < 2) { showToast('至少输入2个有效代码'); return; }
  if (codes.length > 6) { showToast('最多对比6只股票'); return; }

  var period = document.getElementById('searchPeriod').value;
  var count = parseInt(document.getElementById('searchCount').value) || 250;
  count = Math.max(5, Math.min(9999, count));
  var isIntraday = /min$/.test(period);
  var btn = document.getElementById('searchBtn');
  btn.disabled = true; btn.textContent = '对比中…';
  document.getElementById('statusDot').className = 'status-dot fetching';
  document.getElementById('statusText').textContent = '对比 ' + codes.join(', ') + '…';

  function doCompare(items) {
    pywebview.api.compare_indicators(items, period).then(function(data) {
      window._currentResult = data;
      renderCompareDashboard(data, period);
      document.getElementById('statusText').textContent = codes.length + '只对比完成';
      document.getElementById('statusDot').className = 'status-dot on';
      btn.disabled = false; btn.textContent = '查询';
    });
  }

  if (isIntraday) {
    var promises = codes.map(function(c) {
      return pywebview.api.fetch_intraday(c, period, count).then(function(klines) {
        return StockApi.stocks.auto.getStock(c).then(function(s) {
          return {code: c, klines: klines, stock: s};
        }).catch(function() {
          return {code: c, klines: klines, stock: {name: c}};
        });
      });
    });
    Promise.all(promises).then(doCompare).catch(function(e) {
      window._showError('对比失败', String(e)); btn.disabled = false; btn.textContent = '查询';
    });
  } else {
    var sp = {daily:'day', weekly:'week', monthly:'month'};
    var kp = sp[period] || 'day';
    var tasks = [];
    for (var i = 0; i < codes.length; i++) {
      tasks.push(StockApi.stocks.auto.getKlines(codes[i], {period: kp, count: count}));
      tasks.push(StockApi.stocks.auto.getStock(codes[i]));
    }
    Promise.all(tasks).then(function(results) {
      var items = [];
      for (var i = 0; i < codes.length; i++) {
        items.push({code: codes[i], klines: results[i*2], stock: results[i*2+1]});
      }
      doCompare(items);
    }).catch(function(e) {
      window._showError('对比失败', (e && e.message) || String(e));
      btn.disabled = false; btn.textContent = '查询';
      document.getElementById('statusDot').className = 'status-dot on';
    });
  }
}

// ============================================================
// Dashboard Rendering
// ============================================================
function renderDashboard(detail) {
  if (!detail) return;
  var meta = detail.meta || {};
  var ind = detail.indicators || {};
  var sum = detail.summary || {};
  var macd = ind.macd || {};
  var boll = ind.boll || {};

  document.getElementById('emptyState').style.display = 'none';

  // Hero
  var hero = document.getElementById('dashboardHero');
  hero.classList.add('show');
  document.getElementById('heroName').textContent = meta.name || '--';
  document.getElementById('heroCode').textContent = meta.code || '';

  // Tags
  var tagsHtml = '';
  var pLabels = {daily:'日线', weekly:'周线', monthly:'月线', '1min':'1分钟', '5min':'5分钟', '15min':'15分钟', '30min':'30分钟', '60min':'60分钟'};
  if (meta.market) tagsHtml += '<span class="hero-tag market">' + meta.market + '</span>';
  if (meta.industry && meta.industry !== 'GP-A') tagsHtml += '<span class="hero-tag industry">' + meta.industry + '</span>';
  tagsHtml += '<span class="hero-tag period">' + (pLabels[meta.period] || meta.period || '') + '</span>';
  document.getElementById('heroTags').innerHTML = tagsHtml;

  // Price
  var priceEl = document.getElementById('heroPrice');
  var changeEl = document.getElementById('heroChange');
  var lastClose = (detail.data && detail.data.length) ? detail.data[detail.data.length-1].close : 0;
  var prevClose = (detail.data && detail.data.length > 1) ? detail.data[detail.data.length-2].close : lastClose;
  var chg = prevClose ? ((lastClose - prevClose) / prevClose * 100) : 0;
  var chgCls = chg > 0 ? 'up' : (chg < 0 ? 'down' : 'neutral');
  priceEl.textContent = '¥' + lastClose.toFixed(2);
  priceEl.className = 'hero-price ' + (chg >= 0 ? 'up' : 'down');
  changeEl.textContent = (chg >= 0 ? '▲' : '▼') + ' ' + Math.abs(chg).toFixed(2) + '%';
  changeEl.className = 'hero-change ' + (chg >= 0 ? 'up' : 'down');

  // Stats
  var statsHtml = '';
  statsHtml += '<div class="hero-stat"><div class="stat-label">最高</div><div class="stat-value" style="color:var(--red);">' + (sum.max_close ? sum.max_close.toFixed(2) : '--') + '</div></div>';
  statsHtml += '<div class="hero-stat"><div class="stat-label">最低</div><div class="stat-value" style="color:var(--green);">' + (sum.min_close ? sum.min_close.toFixed(2) : '--') + '</div></div>';
  statsHtml += '<div class="hero-stat"><div class="stat-label">涨跌幅</div><div class="stat-value" style="color:' + (sum.period_change >= 0 ? 'var(--red)' : 'var(--green)') + ';">' + (sum.period_change != null ? sum.period_change.toFixed(2) + '%' : '--') + '</div></div>';
  statsHtml += '<div class="hero-stat"><div class="stat-label">均量</div><div class="stat-value">' + (sum.avg_volume ? Math.round(sum.avg_volume).toLocaleString() : '--') + '</div></div>';
  document.getElementById('heroStats').innerHTML = statsHtml;

  // Chart
  document.getElementById('chartSection').style.display = 'block';
  document.getElementById('chartLegend').style.display = 'flex';

  // Indicator Cards
  var grid = document.getElementById('indicatorGrid');
  grid.classList.add('show');
  var cards = '';

  function icard(label, value, unit, note, cls) {
    unit = unit || ''; note = note || ''; cls = cls || '';
    var v = (value !== null && value !== undefined && !isNaN(value)) ? Number(value).toFixed(2) : '--';
    return '<div class="ind-card"><div class="ind-label">' + label + '</div><div class="ind-value ' + cls + '">' + v + unit + '</div><div class="ind-note">' + note + '</div></div>';
  }

  function icardRSI(label, value, note) {
    var v = (value !== null && value !== undefined && !isNaN(value)) ? Number(value) : null;
    var vStr = v !== null ? v.toFixed(1) : '--';
    var cls = v !== null ? (v > 70 ? 'warn' : (v < 30 ? 'down' : '')) : '';
    var gaugeCls = v !== null ? (v > 70 ? 'rsi-overbought' : (v < 30 ? 'rsi-oversold' : 'rsi-neutral')) : '';
    var gauge = v !== null ? '<div class="ind-gauge"><div class="ind-gauge-fill ' + gaugeCls + '" style="width:' + Math.min(100, Math.max(0, v)) + '%;"></div></div>' : '';
    return '<div class="ind-card"><div class="ind-label">' + label + '</div><div class="ind-value ' + cls + '">' + vStr + '</div>' + gauge + '<div class="ind-note">' + note + '</div></div>';
  }

  function icardBOLL(label, upper, mid, lower) {
    return '<div class="ind-card full"><div class="ind-label">' + label + '</div><div style="display:flex;gap:20px;margin-top:4px;">' +
      '<div><span style="font-size:10px;color:var(--red);">上轨</span><br><span style="font-size:16px;font-weight:700;font-family:var(--font-mono);color:var(--red);">' + (upper != null ? upper.toFixed(2) : '--') + '</span></div>' +
      '<div><span style="font-size:10px;color:var(--accent);">中轨</span><br><span style="font-size:16px;font-weight:700;font-family:var(--font-mono);color:var(--accent);">' + (mid != null ? mid.toFixed(2) : '--') + '</span></div>' +
      '<div><span style="font-size:10px;color:var(--green);">下轨</span><br><span style="font-size:16px;font-weight:700;font-family:var(--font-mono);color:var(--green);">' + (lower != null ? lower.toFixed(2) : '--') + '</span></div>' +
      '</div><div class="ind-note">布林带压力支撑位</div></div>';
  }

  // Row 1: MA cards
  cards += icard('MA5 均线', ind.ma5, '', '5日短期趋势');
  cards += icard('MA20 均线', ind.ma20, '', '20日中期趋势');

  // Row 2: MACD
  var macdBarCls = macd.bar >= 0 ? 'up' : 'down';
  cards += icard('MACD DIF', macd.dif, '', '快线（12日EMA）');
  cards += icard('MACD BAR', macd.bar, '', '动能柱（红多绿空）', macdBarCls);

  // Row 3: RSI
  cards += icardRSI('RSI (6日)', ind.rsi_6, '>80超买 <20超卖');
  cards += icardRSI('RSI (12日)', ind.rsi_12, '中长期超买超卖');

  // Row 4: BOLL (full width)
  cards += icardBOLL('BOLL 布林带 (20,2)', boll.upper, boll.mid, boll.lower);

  // Row 5: Summary
  cards += icard('区间涨跌幅', sum.period_change, '%', '选中范围价格变动');
  cards += icard('年化波动率', sum.volatility, '%', '风险度量指标');

  grid.innerHTML = cards;

  // Action bar
  document.getElementById('actionBar').classList.add('show');
}

// ============================================================
// Compare Dashboard
// ============================================================
function renderCompareDashboard(data, period) {
  document.getElementById('emptyState').style.display = 'none';
  document.getElementById('dashboardHero').classList.add('show');

  var pLabels = {daily:'日线', weekly:'周线', monthly:'月线', '1min':'1分', '5min':'5分', '15min':'15分', '30min':'30分', '60min':'60分'};
  document.getElementById('heroName').textContent = data.items.length + '只股票对比';
  document.getElementById('heroCode').textContent = '';
  document.getElementById('heroTags').innerHTML = '<span class="hero-tag period">' + (pLabels[period] || period) + '</span>';
  document.getElementById('heroPrice').textContent = data.items.length + '只对比';
  document.getElementById('heroChange').textContent = '⌛';
  document.getElementById('heroChange').className = 'hero-change neutral';

  // Stats: show each stock's change%
  var statsHtml = '';
  for (var i = 0; i < data.items.length; i++) {
    var item = data.items[i];
    var s = item.summary || {};
    var chg = s.period_change || 0;
    statsHtml += '<div class="hero-stat"><div class="stat-label">' + item.code.replace(/^(SZ|SH)/,'') + '</div><div class="stat-value" style="color:' + (chg >= 0 ? 'var(--red)' : 'var(--green)') + ';">' + (chg >= 0 ? '+' : '') + chg.toFixed(2) + '%</div></div>';
  }
  document.getElementById('heroStats').innerHTML = statsHtml;

  // Chart: show individual charts
  document.getElementById('chartSection').style.display = 'block';
  document.getElementById('chartLegend').style.display = 'flex';
  var chartHtml = '';
  for (var i = 0; i < data.items.length; i++) {
    var item = data.items[i];
    if (!item.klines || item.klines.length < 2) continue;
    var cmpW = Math.max(300, document.getElementById('chartBody').clientWidth - 40 || 560);
    var cmpChart = buildChartSVG(item.klines, period, cmpW, true, true, true, '_cmp'+i);
    chartHtml += '<div style="margin:6px 0 2px;font-size:11px;font-weight:700;color:var(--text1);padding:0 6px;">' + item.code.replace(/^(SZ|SH)/,'') + ' <span style="color:var(--text2);font-weight:400;">' + item.name + '</span></div>';
    chartHtml += '<div style="overflow-x:auto;margin-bottom:14px;">' + cmpChart.html + '</div>';
  }
  document.getElementById('chartBody').innerHTML = '<div class="chart-tooltip" id="chartTooltip"></div>' + chartHtml;
  document.getElementById('chartPeriodLabel').textContent = pLabels[period] || period;

  // Indicator grid: comparison table
  var grid = document.getElementById('indicatorGrid');
  grid.classList.add('show');
  var rows = '';

  function crow(label, vals, unit, note) {
    unit = unit || ''; note = note || '';
    var r = '<div class="ind-card full"><div class="ind-label">' + label + '<span style="font-weight:400;margin-left:4px;">' + note + '</span></div><div style="display:grid;grid-template-columns:repeat(' + vals.length + ',1fr);gap:12px;margin-top:4px;">';
    for (var i = 0; i < vals.length; i++) {
      var v = vals[i];
      if (v !== null && v !== undefined && !isNaN(v)) v = Number(v).toFixed(2);
      else v = '--';
      r += '<div style="font-size:14px;font-weight:700;font-family:var(--font-mono);color:var(--text1);">' + v + unit + '</div>';
    }
    r += '</div></div>';
    return r;
  }

  var names=[], ma5s=[], ma20s=[], difs=[], deas=[], bars=[], rsi6s=[], rsi12s=[], changes=[], vols=[];
  for (var i = 0; i < data.items.length; i++) {
    var ind=data.items[i].indicators, sum=data.items[i].summary, macd=ind.macd||{};
    names.push(data.items[i].code.replace(/^(SZ|SH)/,''));
    ma5s.push(ind.ma5); ma20s.push(ind.ma20);
    difs.push(macd.dif); deas.push(macd.dea); bars.push(macd.bar);
    rsi6s.push(ind.rsi_6); rsi12s.push(ind.rsi_12);
    changes.push(sum.period_change); vols.push(sum.avg_volume ? Math.round(sum.avg_volume) : 0);
  }

  rows += crow('名称', names, '', '');
  rows += crow('MA5', ma5s, '', '短期趋势');
  rows += crow('MA20', ma20s, '', '中期趋势');
  rows += crow('MACD DIF', difs, '', '快线');
  rows += crow('MACD BAR', bars, '', '动能柱');
  rows += crow('RSI(6)', rsi6s, '', '超买超卖');
  rows += crow('RSI(12)', rsi12s, '', '中长期');
  rows += crow('涨跌幅', changes, '%', '区间');
  rows += crow('均量', vols, '', '平均成交量');

  grid.innerHTML = rows;

  document.getElementById('actionBar').classList.add('show');
}

// ============================================================
// SVG Chart Engine
// ============================================================
var CHART_COLORS = {up: '#ef4444', dn: '#22c55e', upGrad: 'rgba(239,68,68,0.25)', dnGrad: 'rgba(34,197,94,0.2)', grid: '#1e2d3d', text: '#3d4755', volUp: 'rgba(239,68,68,0.15)', volDn: 'rgba(34,197,94,0.12)'};

function buildChartSVG(klines, period, W, showVol, showMACD, showRSI, idSuffix) {
  if (!klines || klines.length < 2) return {html: '', totalH: 0};
  idSuffix = idSuffix || '';
  var closes = klines.map(function(k){return k.close;});
  var macdData = showMACD ? calcMACDSeries(closes) : null;
  var rsiData = showRSI ? calcRSISeries(closes, 6) : null;

  // MA lines
  var ma5 = calcMA(closes, 5);
  var ma20 = calcMA(closes, 20);

  var sections = 1 + (showVol?1:0) + (showMACD?1:0) + (showRSI?1:0);
  var pH = 210, vH = showVol ? 40 : 0, mH = showMACD ? 48 : 0, rH = showRSI ? 40 : 0;
  var gap = 8, totalH = pH + vH + mH + rH + gap * (sections - 1) + 14;
  var offY = 8, stepX = W / (klines.length + 1), barW = Math.max(1.8, stepX * 0.65);
  var marginL = 8;

  var highs = klines.map(function(k){return k.high;}), lows = klines.map(function(k){return k.low;});
  var allVals = highs.concat(lows);
  if (ma5) allVals = allVals.concat(ma5.filter(function(v){return v!=null;}));
  if (ma20) allVals = allVals.concat(ma20.filter(function(v){return v!=null;}));
  var maxP = Math.max.apply(null, allVals), minP = Math.min.apply(null, allVals), pR = maxP - minP || 1;
  var volMax = Math.max.apply(null, klines.map(function(k){return k.volume||0;})) || 1;

  function scale(vals, h, top) {
    var mx=Math.max.apply(null,vals.filter(function(v){return v!=null;}))||1;
    var mn=Math.min.apply(null,vals.filter(function(v){return v!=null;}))||0;
    var r=mx-mn||1;
    return function(v){return v==null ? null : top+(mx-v)/r*h;};
  }
  var py = scale(highs.concat(lows), pH - 20, offY + 10);
  var vy = showVol ? function(v){return offY+pH+gap+vH-(v||0)/volMax*vH;} : null;
  var my = showMACD ? function(v){return v==null?null:offY+pH+vH+gap*2+mH/2-(v/(Math.max.apply(null,macdData.dif.concat(macdData.dea).concat(macdData.bar.map(Math.abs)).filter(function(x){return x!=null;}))||1))*(mH/2-4);} : null;
  var ry = showRSI ? function(v){return v==null?null:offY+pH+vH+mH+gap*3+rH-4-(v/100)*rH;} : null;

  var svg = [];
  svg.push('<svg width="'+W+'" height="'+totalH+'" style="display:block;font-family:var(--font-mono);">');
  svg.push('<defs><linearGradient id="upGrad'+idSuffix+'" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="'+CHART_COLORS.up+'"/><stop offset="100%" stop-color="'+CHART_COLORS.upGrad+'"/></linearGradient><linearGradient id="dnGrad'+idSuffix+'" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="'+CHART_COLORS.dn+'"/><stop offset="100%" stop-color="'+CHART_COLORS.dnGrad+'"/></linearGradient></defs>');

  // Grid lines
  var gridLines = 5;
  for (var i=0;i<=gridLines;i++) {
    var y=offY+10+(pH-20)*i/gridLines;
    svg.push('<line x1="0" y1="'+y+'" x2="'+W+'" y2="'+y+'" stroke="'+CHART_COLORS.grid+'" stroke-width="0.5" opacity="0.3"/>');
    svg.push('<text x="'+(W+4)+'" y="'+(y+4)+'" fill="'+CHART_COLORS.text+'" font-size="9" text-anchor="start">'+(maxP-pR*i/gridLines).toFixed(2)+'</text>');
  }

  // Volume bars
  if (showVol) {
    for (var i=0;i<klines.length;i++) {
      var k=klines[i], up=k.close>=k.open, vClr=up?CHART_COLORS.volUp:CHART_COLORS.volDn, vY=vy(k.volume);
      svg.push('<rect x="'+(marginL+i*stepX+(stepX-barW)/2)+'" y="'+vY+'" width="'+barW+'" height="'+Math.max((k.volume||0)/volMax*vH,0.5)+'" fill="'+vClr+'" rx="1"/>');
    }
  }

  // MACD bars
  if (showMACD && macdData) {
    var zeroY = my(0);
    svg.push('<line x1="0" y1="'+zeroY+'" x2="'+W+'" y2="'+zeroY+'" stroke="'+CHART_COLORS.grid+'" stroke-width="1" opacity="0.5"/>');
    for (var i=0;i<klines.length;i++) {
      if (macdData.bar[i]==null) continue;
      var mb=macdData.bar[i], by=my(mb), bw=barW*0.7, bx=marginL+i*stepX+(stepX-barW)/2+(barW-bw)/2;
      svg.push('<rect x="'+bx+'" y="'+Math.min(zeroY,by)+'" width="'+bw+'" height="'+Math.max(Math.abs(by-zeroY),0.5)+'" fill="'+(mb>=0?CHART_COLORS.up:CHART_COLORS.dn)+'" opacity="0.55" rx="1"/>');
    }
  }

  // MACD lines
  if (showMACD && macdData) {
    for (var i=1;i<klines.length;i++) {
      if (macdData.dif[i]!=null && macdData.dif[i-1]!=null) {
        var x1=marginL+(i-0.5)*stepX, x2=marginL+(i+0.5)*stepX;
        svg.push('<line x1="'+x1+'" y1="'+my(macdData.dif[i-1])+'" x2="'+x2+'" y2="'+my(macdData.dif[i])+'" stroke="#f59e0b" stroke-width="1.2"/>');
      }
      if (macdData.dea[i]!=null && macdData.dea[i-1]!=null) {
        var x1=marginL+(i-0.5)*stepX, x2=marginL+(i+0.5)*stepX;
        svg.push('<line x1="'+x1+'" y1="'+my(macdData.dea[i-1])+'" x2="'+x2+'" y2="'+my(macdData.dea[i])+'" stroke="#6b7685" stroke-width="1" stroke-dasharray="2,2"/>');
      }
    }
  }

  // RSI line
  if (showRSI && rsiData) {
    [30,50,70].forEach(function(v){
      var yv=ry(v);
      svg.push('<line x1="0" y1="'+yv+'" x2="'+W+'" y2="'+yv+'" stroke="'+CHART_COLORS.grid+'" stroke-width="0.5" stroke-dasharray="3,4" opacity="0.35"/>');
    });
    for (var i=1;i<klines.length;i++) {
      if (rsiData[i]!=null && rsiData[i-1]!=null) {
        var rx1=marginL+(i-0.5)*stepX, rx2=marginL+(i+0.5)*stepX;
        svg.push('<line x1="'+rx1+'" y1="'+ry(rsiData[i-1])+'" x2="'+rx2+'" y2="'+ry(rsiData[i])+'" stroke="#a78bfa" stroke-width="1.4"/>');
      }
    }
    svg.push('<text x="4" y="'+(ry(30)-3)+'" fill="#22c55e" font-size="8">30</text>');
    svg.push('<text x="4" y="'+(ry(70)+9)+'" fill="#ef4444" font-size="8">70</text>');
  }

  // MA lines on price chart
  if (ma5) {
    for (var i=1;i<klines.length;i++) {
      if (ma5[i]!=null && ma5[i-1]!=null) {
        var mx1=marginL+(i-0.5)*stepX, mx2=marginL+(i+0.5)*stepX;
        svg.push('<line x1="'+mx1+'" y1="'+py(ma5[i-1])+'" x2="'+mx2+'" y2="'+py(ma5[i])+'" stroke="#f59e0b" stroke-width="1.3" opacity="0.8"/>');
      }
    }
  }
  if (ma20) {
    for (var i=1;i<klines.length;i++) {
      if (ma20[i]!=null && ma20[i-1]!=null) {
        var mx1=marginL+(i-0.5)*stepX, mx2=marginL+(i+0.5)*stepX;
        svg.push('<line x1="'+mx1+'" y1="'+py(ma20[i-1])+'" x2="'+mx2+'" y2="'+py(ma20[i])+'" stroke="#8b5cf6" stroke-width="1.3" opacity="0.8"/>');
      }
    }
  }

  // Candles (drawn after MAs so they're on top)
  for (var i=0;i<klines.length;i++) {
    var k=klines[i], up=k.close>=k.open, clr=up?CHART_COLORS.up:CHART_COLORS.dn;
    var cx=marginL+i*stepX+(stepX-barW)/2, oy2=py(k.open), cy2=py(k.close), hy2=py(k.high), ly2=py(k.low);
    // Wick
    svg.push('<line x1="'+(cx+barW/2)+'" y1="'+hy2+'" x2="'+(cx+barW/2)+'" y2="'+ly2+'" stroke="'+clr+'" stroke-width="1"/>');
    // Body with gradient
    var bodyH=Math.max(Math.abs(cy2-oy2),1);
    svg.push('<rect x="'+cx+'" y="'+Math.min(oy2,cy2)+'" width="'+barW+'" height="'+bodyH+'" fill="url(#'+(up?'upGrad':'dnGrad')+idSuffix+')" rx="1.5" stroke="'+clr+'" stroke-width="0.5"/>');
  }

  // Crosshair
  svg.push('<line id="crosshairLine" x1="0" y1="'+offY+'" x2="0" y2="'+(offY+pH)+'" stroke="var(--text1)" stroke-width="1" stroke-dasharray="4,2" opacity="0" style="pointer-events:none;"/>');

  // Date labels
  svg.push('<text x="'+marginL+'" y="'+(totalH-3)+'" fill="'+CHART_COLORS.text+'" font-size="9">'+(klines[0].date||'')+'</text>');
  svg.push('<text x="'+(W-4)+'" y="'+(totalH-3)+'" fill="'+CHART_COLORS.text+'" font-size="9" text-anchor="end">'+(klines[klines.length-1].date||'')+'</text>');

  // Section labels
  if (showMACD) svg.push('<text x="4" y="'+(offY+pH+gap-2)+'" fill="var(--text2)" font-size="9">MACD (12,26,9)</text>');
  if (showRSI) svg.push('<text x="4" y="'+(offY+pH+vH+gap+mH+gap-2)+'" fill="var(--text2)" font-size="9">RSI (6)</text>');

  svg.push('</svg>');
  return {html: svg.join(''), totalH: totalH, stepX: stepX};
}

function calcMA(data, period) {
  var result = [];
  for (var i=0;i<data.length;i++) {
    if (i<period-1) { result.push(null); continue; }
    var sum=0; for(var j=i-period+1;j<=i;j++) sum+=data[j];
    result.push(sum/period);
  }
  return result;
}

var _chartShowMACD = true, _chartShowRSI = true;
var _chartData = null;

function renderChart(klines, period) {
  if (!klines || klines.length < 2) { document.getElementById('chartBody').innerHTML = '<div class="chart-tooltip" id="chartTooltip"></div>'; return; }
  _chartData = {klines: klines, period: period};
  var pLabels = {daily:'日线', weekly:'周线', monthly:'月线', '1min':'1分', '5min':'5分', '15min':'15分', '30min':'30分', '60min':'60分'};
  document.getElementById('chartPeriodLabel').textContent = (pLabels[period] || period) + ' · ' + klines.length + '条';
  drawChart();
}

function drawChart() {
  if (!_chartData) return;
  var klines = _chartData.klines, period = _chartData.period;
  var body = document.getElementById('chartBody');
  var W = Math.max(body.clientWidth - 60, 300);
  var chart = buildChartSVG(klines, period, W, true, _chartShowMACD, _chartShowRSI);
  body.innerHTML = '<div class="chart-tooltip" id="chartTooltip"></div>' + chart.html;
  body._klines = klines;
  body._stepX = chart.stepX || (W / (klines.length + 1));
  body._PW = W;
  body._macdData = _chartShowMACD ? calcMACDSeries(klines.map(function(k){return k.close;})) : null;
  body._rsiData = _chartShowRSI ? calcRSISeries(klines.map(function(k){return k.close;}), 6) : null;

  // Attach hover
  var svg = body.querySelector('svg');
  if (svg) {
    svg.addEventListener('mousemove', chartHover);
    svg.addEventListener('mouseleave', hideTooltip);
  }
}

function toggleIndicator(idx) {
  if (idx === 0) _chartShowMACD = !_chartShowMACD;
  else _chartShowRSI = !_chartShowRSI;
  drawChart();
}

// ============================================================
// Tooltip & Crosshair
// ============================================================
function chartHover(e) {
  var body = document.getElementById('chartBody');
  var klines = body._klines;
  var stepX = body._stepX;
  if (!klines || !stepX) return;
  var rect = body.getBoundingClientRect();
  var x = e.clientX - rect.left - 8;
  var i = Math.round(x / stepX);
  if (i < 0) i = 0; if (i >= klines.length) i = klines.length - 1;
  var k = klines[i];
  var tip = document.getElementById('chartTooltip');
  if (!tip) return;
  var up = k.close >= k.open, clr = up ? CHART_COLORS.up : CHART_COLORS.dn;
  var macd = body._macdData, rsi = body._rsiData;
  var D = function(v,d){return v!=null?Number(v).toFixed(d):'--';};
  tip.innerHTML = '<div class="tt-date" style="color:'+clr+';">'+ (k.date||'') +'</div>' +
    '<table>' +
    '<tr><td class="tt-label">开</td><td style="color:var(--text1);">'+ (k.open||0).toFixed(2) +'</td>'+
    '<td class="tt-label" style="padding-left:6px;">高</td><td style="color:var(--text1);">'+ (k.high||0).toFixed(2) +'</td></tr>'+
    '<tr><td class="tt-label">低</td><td style="color:var(--text1);">'+ (k.low||0).toFixed(2) +'</td>'+
    '<td class="tt-label" style="padding-left:6px;">收</td><td style="color:'+clr+';font-weight:700;">'+ (k.close||0).toFixed(2) +'</td></tr>'+
    '<tr><td class="tt-label">量</td><td style="color:var(--text1);">'+ ((k.volume||0)/10000).toFixed(1) +'万</td>'+
    '<td class="tt-label" style="padding-left:6px;">幅</td><td style="color:var(--text1);">'+ (k.open>0?(k.close-k.open)/k.open*100:0).toFixed(2) +'%</td></tr>'+
    '<tr><td colspan="4"><div class="tt-divider" style="margin:4px 0;"></div></td></tr>'+
    '<tr><td class="tt-label" style="color:#f59e0b;">DIF</td><td style="color:#f59e0b;">'+ D(macd&&macd.dif?macd.dif[i]:null,4) +'</td>'+
    '<td class="tt-label" style="color:var(--text2);padding-left:6px;">DEA</td><td style="color:var(--text2);">'+ D(macd&&macd.dea?macd.dea[i]:null,4) +'</td></tr>'+
    '<tr><td class="tt-label" style="color:'+(macd&&macd.bar&&macd.bar[i]>=0?CHART_COLORS.up:CHART_COLORS.dn)+';">BAR</td><td style="color:'+(macd&&macd.bar&&macd.bar[i]>=0?CHART_COLORS.up:CHART_COLORS.dn)+';font-weight:600;">'+ D(macd&&macd.bar?macd.bar[i]:null,4) +'</td>'+
    '<td class="tt-label" style="color:#a78bfa;padding-left:6px;">RSI</td><td style="color:#a78bfa;font-weight:600;">'+ D(rsi?rsi[i]:null,1) +'</td></tr>'+
    '</table>';
  tip.style.display = 'block';
  var tx = e.clientX - rect.left + 15;
  if (tx + 150 > rect.width) tx = e.clientX - rect.left - 165;
  tip.style.left = tx + 'px';
  tip.style.top = Math.max(2, e.clientY - rect.top - 110) + 'px';

  var ch = document.getElementById('crosshairLine');
  if (ch) {
    var cx = 8 + i * stepX + stepX/2;
    ch.setAttribute('x1', cx); ch.setAttribute('x2', cx);
    ch.setAttribute('opacity', '1');
  }
}

function hideTooltip() {
  var tip = document.getElementById('chartTooltip'); if (tip) tip.style.display = 'none';
  var ch = document.getElementById('crosshairLine'); if (ch) ch.setAttribute('opacity', '0');
}

// ============================================================
// Large Chart Modal
// ============================================================
function openLargeChart() {
  if (!_chartData) return;
  var klines = _chartData.klines, period = _chartData.period;
  var W = Math.min(1100, screen.width - 80);
  var chart = buildChartSVG(klines, period, W, true, true, true);
  var title = (window._currentResult && window._currentResult.meta) ? (window._currentResult.meta.code + ' ' + window._currentResult.meta.name) : 'K线图';
  document.getElementById('chartModalContent').innerHTML =
    '<div class="modal-header"><span class="modal-title">📈 ' + title + '</span><button class="modal-close" onclick="closeModal()">&times;</button></div>' +
    '<div style="overflow-x:auto;">' + chart.html + '</div>';
  document.getElementById('chartModal').classList.add('show');
}

function closeModal() {
  document.getElementById('chartModal').classList.remove('show');
}

document.addEventListener('keydown', function(e) {
  if (e.key === 'Escape') closeModal();
  if (e.key === 'Enter' && (e.target.id === 'mainSearchInput' || e.target.classList.contains('codeInput'))) onSearch();
});

// ============================================================
// Indicator Calculations
// ============================================================
function calcMACDSeries(closes) {
  var ema12 = ema(closes, 12), ema26 = ema(closes, 26), dif=[], dea=[], bar=[];
  for (var i=0;i<closes.length;i++) {
    if (i<25) { dif.push(null); dea.push(null); bar.push(null); continue; }
    var d = ema12[i] - ema26[i]; dif.push(d);
    if (i<33) { dea.push(null); bar.push(null); continue; }
    var e = 0; for (var j=i-8;j<=i;j++) e += dif[j]||0; e /= 9;
    dea.push(e); bar.push(2*(d-e));
  }
  return {dif:dif, dea:dea, bar:bar};
}

function calcRSISeries(closes, period) {
  var rsi = [], gains = 0, losses = 0;
  for (var i=0;i<closes.length;i++) {
    if (i<period) { rsi.push(null); continue; }
    if (i===period) { for (var j=1;j<=period;j++) { var ch=closes[j]-closes[j-1]; if(ch>0) gains+=ch; else losses-=ch; } }
    else { var ch2=closes[i]-closes[i-1]; if(ch2>0) { gains=(gains*(period-1)+ch2)/period; losses=(losses*(period-1))/period; } else { gains=(gains*(period-1))/period; losses=(losses*(period-1)-ch2)/period; } }
    var rs = losses===0 ? 100 : gains/losses;
    rsi.push(100 - 100/(1+rs));
  }
  return rsi;
}

function ema(data, span) {
  var alpha = 2/(span+1), result = [];
  for (var i=0;i<data.length;i++) {
    if (i<span-1) { result.push(0); continue; }
    if (i===span-1) { var s=0; for(var j=0;j<span;j++) s+=data[j]; result.push(s/span); continue; }
    result.push(data[i]*alpha + result[i-1]*(1-alpha));
  }
  return result;
}

// ============================================================
// Actions
// ============================================================
function onCopyJSON() {
  pywebview.api.copy_last_json().then(function(r) {
    if (r && r.success) showToast('JSON已复制到剪贴板');
    else showToast((r && r.error) || '暂无数据');
  });
}

function onSaveFile() {
  pywebview.api.save_last_to_file().then(function(r) {
    if (r && r.success) showToast('已保存: ' + r.filename);
    else { showToast((r && r.error) || '保存失败'); if (r && r.detail) window._showError('保存失败', r.error + '\n\n' + r.detail); }
  });
}

function onSmartAnalyze() {
  var formula = document.getElementById('formulaInput').value.trim() || document.getElementById('formulaInputTab').value.trim();
  if (formula) {
    pywebview.api.generate_prompt(formula).then(function(r) {
      if (r && r.success) showToast('选股分析提示词已复制！');
      else showToast((r && r.error) || '失败');
    });
  } else {
    pywebview.api.quick_analysis_prompt().then(function(r) {
      if (r && r.success) showToast('技术分析提示词已复制！');
      else showToast((r && r.error) || '失败');
    });
  }
}

function onFullAnalyze() {
  if (!window._currentResult) { showToast('请先查询股票数据'); return; }
  var r = window._currentResult;
  if (r.items) {
    if (!r.items.length) { showToast('无数据'); return; }
    var prompt = '# 多股对比深度分析\n\n你是一位资深量化分析师。以下是对比数据：\n\n';
    for (var i = 0; i < r.items.length; i++) {
      var it = r.items[i], ind = it.indicators, s = it.summary, macd = ind.macd || {};
      prompt += '## ' + it.code + ' ' + it.name + '\n';
      prompt += '| 指标 | 数值 |\n|------|------|\n';
      prompt += '| MA5/MA20 | ' + (ind.ma5||'N/A') + ' / ' + (ind.ma20||'N/A') + ' |\n';
      prompt += '| MACD | DIF=' + (macd.dif||'N/A') + ' DEA=' + (macd.dea||'N/A') + ' BAR=' + (macd.bar||'N/A') + ' |\n';
      prompt += '| RSI(6/12) | ' + (ind.rsi_6||'N/A') + ' / ' + (ind.rsi_12||'N/A') + ' |\n';
      prompt += '| 涨跌幅 | ' + (s.period_change||0) + '% |\n';
      prompt += '| 波动率 | ' + (s.volatility||0) + '% |\n';
      prompt += '| 价格区间 | ' + (s.min_close||0) + ' ~ ' + (s.max_close||0) + ' |\n\n';
    }
    prompt += '请对比分析各股票强弱，给出排序和建议。';
    copyText(prompt);
    showToast('对比深度分析提示词已复制！');
    return;
  }
  var s = r.summary, ind = r.indicators, m = r.meta, macd = ind.macd || {}, boll = ind.boll || {};
  var prompt = '# 深度技术分析任务\n\n';
  prompt += '你是一位资深量化分析师。以下是 **' + m.code + ' ' + m.name + '** 的完整技术数据，请进行全面深度分析。\n\n';
  prompt += '## 📊 完整技术指标\n\n';
  prompt += '| 指标 | 数值 | 说明 |\n|------|------|------|\n';
  prompt += '| MA5/MA10/MA20/MA60 | ' + [ind.ma5, ind.ma10, ind.ma20, ind.ma60].map(function(v){return v!=null?v.toFixed(2):'N/A'}).join(' / ') + ' | 多周期均线 |\n';
  prompt += '| MACD DIF/DEA/BAR | ' + macd.dif + ' / ' + macd.dea + ' / ' + macd.bar + ' | 趋势动能 |\n';
  prompt += '| RSI(6)/RSI(12) | ' + (ind.rsi_6||'N/A') + ' / ' + (ind.rsi_12||'N/A') + ' | 超买超卖 |\n';
  prompt += '| BOLL | 上' + (boll.upper||'N/A') + ' 中' + (boll.mid||'N/A') + ' 下' + (boll.lower||'N/A') + ' | 布林带 |\n';
  prompt += '| 区间涨跌 | ' + s.period_change + '% | 区间波动 |\n';
  prompt += '| 最高/最低 | ' + s.max_close + ' / ' + s.min_close + ' | 区间极值 |\n';
  prompt += '| 年化波动率 | ' + s.volatility + '% | 风险度量 |\n';
  prompt += '| 平均成交量 | ' + (s.avg_volume||0) + ' | 流动性 |\n\n';
  prompt += '## 📈 完整K线数据\n\n```json\n' + JSON.stringify(r.data, null, 2) + '\n```\n\n';
  prompt += '## 📐 分析框架\n\n';
  prompt += '1. **趋势判断**: 均线排列 + MACD方向，给出多/空/震荡结论\n';
  prompt += '2. **支撑压力**: BOLL带 + 均线 + 区间极值，给出关键价位\n';
  prompt += '3. **量价关系**: 成交量趋势 + 价格配合度\n';
  prompt += '4. **形态识别**: 是否存在金叉/死叉/顶底背离/突破信号\n';
  prompt += '5. **风险评估**: 波动率 + RSI极端值 + 仓位建议\n';
  prompt += '6. **操作建议**: 方向/仓位/入场位/止损位/目标位\n\n';
  prompt += '请逐条分析并给出综合评分（1-10分）。';
  copyText(prompt);
  showToast('深度分析提示词已复制！（含完整K线数据）');
}

function copyText(text) {
  var ta = document.createElement('textarea');
  ta.value = text; document.body.appendChild(ta); ta.select();
  document.execCommand('copy'); document.body.removeChild(ta);
}

function onTabGeneratePrompt() {
  var formula = document.getElementById('formulaInputTab').value.trim();
  if (!formula) { showToast('请输入通达信公式'); return; }
  pywebview.api.generate_prompt(formula).then(function(r) {
    if (r && r.success) showToast('选股分析提示词已复制！');
    else showToast((r && r.error) || '生成失败');
  });
}

function onTabQuickAnalyze() {
  pywebview.api.quick_analysis_prompt().then(function(r) {
    if (r && r.success) showToast('技术分析提示词已复制！');
    else showToast((r && r.error) || '失败，请先查询股票');
  });
}

// ============================================================
// Settings
// ============================================================
function onToggleMonitor() {
  pywebview.api.toggle_clipboard_monitor().then(function(isOn) {
    var el = document.getElementById('clipboardToggle');
    if (isOn) { el.classList.add('on'); }
    else { el.classList.remove('on'); }
    showToast(isOn ? '剪贴板监控已开启' : '剪贴板监控已暂停');
  });
}

function onClearCache() { pywebview.api.clear_cache(); showToast('数据缓存已清空'); }
function onConfigChange(key, value) { pywebview.api.set_config(key, value); showToast('设置已保存: ' + key); }

// ============================================================
// Price Alert & Ticker
// ============================================================
function refreshAlerts() {
  pywebview.api.get_alerts().then(function(data) {
    if (!data || !data.success) return;
    var mt = document.getElementById('alertsMasterToggle');
    if (mt) { mt.className = 'toggle-sw ' + (data.enabled ? 'on' : 'off'); }
    renderAlertList(data.alerts || []);
  });
}

function renderAlertList(alerts) {
  var container = document.getElementById('alertList');
  var hint = document.getElementById('alertEmptyHint');
  if (!container) return;
  if (!alerts || alerts.length === 0) {
    container.innerHTML = '';
    if (hint) { container.appendChild(hint); hint.style.display = 'block'; }
    return;
  }
  if (hint) hint.style.display = 'none';
  var html = '';
  for (var i = 0; i < alerts.length; i++) {
    var a = alerts[i];
    var isTriggered = a.status === 'triggered_upper' || a.status === 'triggered_lower';
    var statusIcon = a.status === 'triggered_upper' ? '🔴' :
                     a.status === 'triggered_lower' ? '🟢' :
                     !a.enabled ? '⏸' : '●';
    var statusCls = isTriggered ? 'triggered' : (!a.enabled ? 'paused' : 'monitoring');
    var statusText = a.status === 'triggered_upper' ? '已触发(上限)' :
                     a.status === 'triggered_lower' ? '已触发(下限)' :
                     !a.enabled ? '已暂停' : '监控中';
    var upVal = a.price_upper != null ? parseFloat(a.price_upper).toFixed(2) : '未设';
    var loVal = a.price_lower != null ? parseFloat(a.price_lower).toFixed(2) : '未设';
    html += '<div class="alert-item ' + (isTriggered ? 'triggered' : '') + '">' +
      '<div class="alert-top">' +
        '<span class="alert-name">' + (a.name || a.code) + ' <span style="font-size:11px;color:var(--text2);font-weight:400;">' + a.code.replace(/^(SZ|SH)/,'') + '</span></span>' +
        '<span class="alert-status ' + statusCls + '">' + statusIcon + ' ' + statusText + '</span>' +
      '</div>' +
      '<div class="alert-prices">' +
        '<span class="alert-price-up">📈 上限: ' + upVal + '</span>' +
        '<span style="color:var(--text3);">|</span>' +
        '<span class="alert-price-down">📉 下限: ' + loVal + '</span>' +
      '</div>' +
      '<div class="alert-actions">' +
        '<button class="btn-sm test" onclick="onTestAlert(\'' + a.code + '\')">🔔 测试</button>' +
        '<button class="btn-sm delete" onclick="onDeleteAlert(\'' + a.code + '\')">✕ 删除</button>' +
      '</div>' +
    '</div>';
  }
  container.innerHTML = html;
}

function onToggleAlerts() {
  pywebview.api.toggle_alerts().then(function(r) {
    if (r.success) { showToast(r.enabled ? '后台监控已开启' : '后台监控已关闭'); refreshAlerts(); }
    else showToast('操作失败: ' + r.error);
  });
}

function onShowAddAlert() {
  document.getElementById('alertAddForm').style.display = 'block';
}

function onCancelAddAlert() {
  document.getElementById('alertAddForm').style.display = 'none';
  document.getElementById('alertCode').value = '';
  document.getElementById('alertName').value = '';
  document.getElementById('alertUpper').value = '';
  document.getElementById('alertLower').value = '';
}

function onSaveAlert() {
  var code = document.getElementById('alertCode').value.trim();
  var name = document.getElementById('alertName').value.trim();
  var up = document.getElementById('alertUpper').value.trim();
  var lo = document.getElementById('alertLower').value.trim();
  if (!code) { showToast('请输入股票代码'); return; }
  var upper = up ? parseFloat(up) : null;
  var lower = lo ? parseFloat(lo) : null;
  if (!upper && !lower) { showToast('至少设置一个阈值，或都留空仅看报价'); return; }
  if (upper !== null && lower !== null && upper <= lower) { showToast('上限必须大于下限'); return; }
  pywebview.api.save_alert(code, name, upper, lower, true).then(function(r) {
    if (r.success) { showToast('已保存'); onCancelAddAlert(); refreshAlerts(); }
    else showToast('保存失败: ' + r.error);
  });
}

function onDeleteAlert(code) {
  pywebview.api.delete_alert(code).then(function(r) {
    if (r.success) { showToast('已删除'); refreshAlerts(); }
    else showToast('删除失败: ' + r.error);
  });
}

function onTestAlert(code) {
  pywebview.api.test_alert_notification(code).then(function(r) {
    showToast(r.success ? '测试通知已发送' : '发送失败: ' + r.error);
  });
}

// ============================================================
// Toast
// ============================================================
function showToast(msg) {
  var el = document.getElementById('toast');
  el.textContent = msg;
  el.classList.add('show');
  clearTimeout(el._timeout);
  el._timeout = setTimeout(function() { el.classList.remove('show'); }, 3000);
}

// ============================================================
// History Polling
// ============================================================
function renderHistory(data) {
  var list = document.getElementById('historyList');
  if (!data || data.length === 0) {
    list.innerHTML = '<div class="history-empty"><div class="empty-icon">📋</div><div class="empty-text">暂无记录</div></div>';
    document.getElementById('historyCount').textContent = '';
    return;
  }
  document.getElementById('historyCount').textContent = data.length + '条';
  var html = '';
  for (var i = 0; i < data.length; i++) {
    var r = data[i];
    var icons = {success: 'ok', error: 'err', cached: 'cache', pending: 'pend'};
    var labels = {success: '成功', error: '失败', cached: '缓存', pending: '排队中'};
    var cls = 'history-status ' + (icons[r.status] || 'pend');
    html += '<div class="history-item">' +
      '<span class="history-time">' + r.time + '</span>' +
      '<span class="history-code">' + (r.code || '--') + '</span>' +
      '<span class="history-name">' + (r.name || '-') + '</span>' +
      '<span class="' + cls + '">' + (labels[r.status] || r.status) + '</span>' +
      '</div>';
  }
  list.innerHTML = html;
}

function refreshHistory() {
  pywebview.api.get_history().then(function(data) {
    renderHistory(data);
  });
}

function refreshStatus() {
  document.getElementById('statusDot').className = 'status-dot on';
  document.getElementById('statusText').textContent = '就绪';
}

function loadConfig() {
  pywebview.api.get_config().then(function(cfg) {
    if (!cfg) return;
    if (cfg.default_count) document.getElementById('defaultCount').value = cfg.default_count;
    if (cfg.poll_interval !== undefined) document.getElementById('pollInterval').value = cfg.poll_interval;
    if (cfg.cache_ttl !== undefined) document.getElementById('cacheTTL').value = cfg.cache_ttl;
    if (cfg.save_directory !== undefined) document.getElementById('saveDirectory').value = cfg.save_directory || '';
  });
  pywebview.api.is_monitoring().then(function(on) {
    var el = document.getElementById('clipboardToggle');
    if (on) { el.classList.add('on'); }
    else { el.classList.remove('on'); }
  });
}

// ============================================================
// Adaptive Polling
// ============================================================
(function() {
  var FAST = 500, NORMAL = 3000, SLOW = 12000;
  var _interval = NORMAL;
  var _timer = null;
  var _lastHistory = '';

  function poll() {
    if (typeof pywebview === 'undefined' || !pywebview.api) { _timer = setTimeout(poll, 200); return; }
    var doRefresh = function() {
      refreshStatus();
      pywebview.api.get_history().then(function(data) {
        var key = JSON.stringify(data);
        if (key !== _lastHistory) {
          _lastHistory = key;
          renderHistory(data);
        }
      });
      if (!window._pollFast) {
        pywebview.api.get_last_result_detail().then(function(detail) {
          if (detail && detail.meta && detail.meta.code) {
            window._currentResult = detail;
            renderDashboard(detail);
            renderChart(detail.data, detail.meta.period || 'daily');
          }
        });
      }
    };
    window.requestAnimationFrame(doRefresh);
    var next = window._pollFast ? FAST : (document.hidden ? SLOW : NORMAL);
    if (next !== _interval) { _interval = next; }
    _timer = setTimeout(poll, _interval);
  }

  document.addEventListener('visibilitychange', function() {
    if (!document.hidden) {
      _interval = window._pollFast ? FAST : NORMAL;
      clearTimeout(_timer);
      _timer = setTimeout(poll, 100);
    }
  });

  _timer = setTimeout(poll, 800);
})();

// ============================================================
// Init
// ============================================================
(function init() {
  function _ready(cb, retries) {
    retries = retries || 0;
    if (typeof pywebview !== 'undefined' && pywebview.api) { cb(); return; }
    if (retries > 50) return;
    setTimeout(function() { _ready(cb, retries + 1); }, 100);
  }
  _ready(function() {
    loadConfig();
    refreshHistory();
    refreshStatus();
    pywebview.api.get_alerts().then(function(data) {
      if (data && data.success) {
        var mt = document.getElementById('alertsMasterToggle');
        if (mt) mt.className = 'toggle-sw ' + (data.enabled ? 'on' : 'off');
        renderAlertList(data.alerts || []);
      }
    });
    pywebview.api.get_last_result_detail().then(function(detail) {
      if (detail && detail.meta && detail.meta.code) {
        window._currentResult = detail;
        renderDashboard(detail);
        renderChart(detail.data, detail.meta.period || 'daily');
      }
    });
  });
  setTimeout(function() { var inp = document.getElementById('mainSearchInput'); if (inp) inp.focus(); }, 400);
})();
</script>
</body>
</html>
"""
# ============================================================
class PanelAPI:
    """API class exposed to the PyWebView JavaScript context."""

    def __init__(self, clipper: "StockClipper") -> None:
        self._clipper = clipper
        self._last_json: str = ""
        self._last_result: Dict[str, Any] = {}
        self._search_history: list = []  # [{time, code, name, status, period, message}]

    def ping(self) -> str:
        return "pong"

    def compare_indicators(self, items: List[Dict], period: str = "daily") -> Dict[str, Any]:
        """Multi-stock comparison: compute indicators for each stock."""
        from data.indicators import calc_all_indicators
        from data.builder import build_summary
        results = []
        for item in items:
            code = item["code"]; klines = item["klines"]; stock = item["stock"]
            raw = code.replace("SH","").replace("SZ","").replace("HK","")
            market = "沪市" if (raw.startswith("60") or raw.startswith("68")) else "深市"
            if code.startswith("HK"): market = "港股"
            closes = [k.get("close", 0) for k in klines]
            results.append({
                "code": code, "name": stock.get("name", ""), "market": market,
                "indicators": calc_all_indicators(closes),
                "summary": build_summary(klines),
                "klines": klines, "count": len(klines),
            })
        data = {"items": results, "period": period}
        # Cache for copy/save + history
        import json as _json, time as _time
        self._last_result = data
        self._last_json = _json.dumps(data, ensure_ascii=False, indent=2)
        names = ", ".join(r["name"][:4] for r in results)
        self._search_history.insert(0, {
            "time": _time.strftime("%H:%M:%S"), "code": f"{len(results)}只对比",
            "name": names, "status": "success", "period": period,
            "message": f"{len(results)}只",
        })
        if len(self._search_history) > 10: self._search_history.pop()
        return data

    def fetch_intraday(self, code: str, period: str, count: int) -> List[Dict]:
        """Fetch intraday K-line from EastMoney (stock-api doesn't support minute periods)."""
        import requests, json as _json
        # Convert code to EastMoney secid
        raw = code.replace("SH","").replace("SZ","").replace("HK","")
        pre = "1" if (raw.startswith("60") or raw.startswith("68")) else "0"
        secid = f"{pre}.{raw}"
        klt_map = {"1min": 1, "5min": 5, "15min": 15, "30min": 30, "60min": 60}
        klt = klt_map.get(period, 1)
        try:
            resp = requests.get(
                "http://push2his.eastmoney.com/api/qt/stock/kline/get",
                params={"secid": secid, "klt": klt, "fqt": 1, "lmt": count,
                        "fields1": "f1,f2,f3,f4,f5,f6",
                        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
                        "end": "20500101", "ut": "fa5fd1943c7b386f172d6893dbfc10f1"},
                headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
            data = resp.json()
            klines = data.get("data", {}).get("klines", [])
            result = []
            for line in klines:
                parts = line.split(",")
                if len(parts) >= 7:
                    result.append({"date": parts[0], "open": float(parts[1]), "close": float(parts[2]),
                                   "high": float(parts[3]), "low": float(parts[4]), "volume": int(float(parts[5]))})
            return result
        except Exception:
            return []

    def compute_indicators(self, code: str, klines: List[Dict], stock_info: Dict, period: str = "daily") -> Dict[str, Any]:
        """JS→Python: compute technical indicators from stock-api kline data."""
        from data.indicators import calc_all_indicators
        from data.builder import build_summary

        # Market label
        raw = code.replace("SH","").replace("SZ","").replace("HK","")
        market = "沪市" if (raw.startswith("60") or raw.startswith("68")) else "深市"
        if code.startswith("HK"): market = "港股"

        closes = [k.get("close", 0) for k in klines]
        indicators = calc_all_indicators(closes)
        summary = build_summary(klines)

        result = {
            "meta": {
                "code": code,
                "name": stock_info.get("name", ""),
                "market": market,
                "industry": "",
                "pe_ttm": -1,
                "total_mv": -1,
                "period": period,
                "data_count": len(klines),
                "start_date": klines[0].get("date", "") if klines else "",
                "end_date": klines[-1].get("date", "") if klines else "",
            },
            "indicators": indicators,
            "summary": summary,
            "data": klines,
        }
        # Cache for copy/save
        import json as _json
        self._last_json = _json.dumps(result, ensure_ascii=False, indent=2)
        self._last_result = result
        # Track history
        import time as _time
        self._search_history.insert(0, {
            "time": _time.strftime("%H:%M:%S"), "code": code,
            "name": stock_info.get("name", ""), "status": "success",
            "period": "daily", "message": f"{len(klines)}条",
        })
        if len(self._search_history) > 10:
            self._search_history.pop()
        return result

    def get_history(self) -> List[Dict[str, Any]]:
        return self._search_history

    def get_config(self) -> Dict[str, Any]:
        cfg = self._clipper.get_config()
        return {
            "output_format": cfg.get("output_format", "json"),
            "default_count": cfg.get("default_count", 250),
            "poll_interval": cfg.get("poll_interval", 0.5),
            "cache_ttl": cfg.get("cache_ttl", 300),
            "save_directory": cfg.get("save_directory", ""),
        }

    def set_config(self, key: str, value: Any) -> None:
        self._clipper.set_config(key, value)

    def clear_cache(self) -> None:
        self._clipper.clear_cache()

    def toggle_clipboard_monitor(self) -> bool:
        return self._clipper.toggle_clipboard_monitor()

    def is_monitoring(self) -> bool:
        return self._clipper.is_monitoring()

    def get_status(self) -> str:
        return self._clipper.get_status()

    def get_last_result_detail(self) -> Optional[Dict[str, Any]]:
        return self._clipper.get_result_detail()

    def search_stock(self, code: str, period: str = "daily", save_mode: bool = False) -> Dict[str, Any]:
        import os, time as _time
        try:
            code = code.strip()
            request = None  # clipboard parsing removed in V3.0
            if request:
                actual_code, actual_period, actual_save = request.code, request.period, request.save_mode
            else:
                if not code.isdigit() or len(code) != 6:
                    return {"success": False, "error": "无效的股票代码，请输入6位数字"}
                actual_code, actual_period, actual_save = code, period, save_mode
            if period != "daily" and actual_period == "daily":
                actual_period = period
            if save_mode:
                actual_save = True

            result = self._clipper.fetch_manual(actual_code, actual_period)

            if actual_save:
                try:
                    self._clipper._fetch_queue.put_nowait(None)
                except Exception:
                    pass

            if result.status == "error":
                return {"success": False, "error": result.message}
            return {"success": True}
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            log.error("search_stock failed for %s: %s", code, e)
            return {
                "success": False,
                "error": f"{type(e).__name__}: {e}",
                "detail": tb,
            }

    def copy_last_json(self) -> Dict[str, Any]:
        import pyperclip
        if not self._last_json:
            return {"success": False, "error": "暂无数据，请先查询"}
        pyperclip.copy(self._last_json)
        return {"success": True}

    def _get_detail(self):
        """Get analysis detail, supporting both single and comparison modes."""
        r = self._last_result
        if not r: return None
        if "meta" in r: return r
        if "items" in r and r["items"]:
            it = r["items"][0]
            return {"meta": {"code": it["code"], "name": it["name"]},
                    "indicators": it["indicators"], "summary": it["summary"]}
        return None

    # ── V2 (legacy) prompt generators — keep for backward compatibility ──
    # Future: migrate onSmartAnalyze() and onFullAnalyze() to call
    # generate_analysis_package() (the V3 formula_engine) instead.

    def generate_prompt(self, formula_text: str) -> Dict[str, Any]:
        """[V2 legacy] Generate AI prompt from TDX formula using old formatter."""
        import traceback, pyperclip
        try:
            detail = self._get_detail()
            if not detail: return {"success": False, "error": "暂无数据，请先查询"}
            from modules.prompt.formula import generate_prompt as _gen
            m = detail["meta"]
            prompt = _gen(formula=formula_text, stock_code=m["code"], stock_name=m.get("name",""),
                          indicators=detail.get("indicators",{}), summary=detail.get("summary",{}))
            pyperclip.copy(prompt)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e), "detail": traceback.format_exc()}

    def quick_analysis_prompt(self) -> Dict[str, Any]:
        """[V2 legacy] Generate quick analysis prompt (no formula) using old formatter."""
        import traceback, pyperclip
        try:
            detail = self._get_detail()
            if not detail: return {"success": False, "error": "暂无数据，请先查询"}
            from modules.prompt.formula import generate_quick_prompt
            m = detail["meta"]
            prompt = generate_quick_prompt(code=m["code"], name=m.get("name",""),
                                           indicators=detail.get("indicators",{}), summary=detail.get("summary",{}))
            pyperclip.copy(prompt)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e), "detail": traceback.format_exc()}

    # ── V3 engine bridge ──

    def generate_analysis_package(self, formula: str = "") -> Dict[str, Any]:
        """[V3 engine] Generate a full AnalysisPackage using the formula_engine.

        This is the new entry point for formula-based and general AI analysis.
        Returns structured JSON that can be fed to an LLM API directly, or
        formatted as a markdown prompt for copy-paste.

        Args:
            formula: Optional TDX formula string. If empty, uses deep-analysis mode.

        Returns:
            {"success": True, "json": ..., "prompt": ...} or {"success": False, "error": ...}
        """
        import traceback
        try:
            r = self._last_result
            if not r:
                return {"success": False, "error": "暂无数据，请先查询"}

            from data.formula_engine import prepare

            # Build klines_map and stock_info_map from the last result
            klines_map: Dict[str, List] = {}
            stock_info_map: Dict[str, Dict] = {}

            if "meta" in r:
                # Single stock mode
                code = r["meta"]["code"]
                klines_map[code] = r.get("data", [])
                stock_info_map[code] = {
                    "name": r["meta"].get("name", ""),
                    "market": r["meta"].get("market", ""),
                    "period": r["meta"].get("period", "daily"),
                }
            elif "items" in r:
                # Comparison mode
                for item in r["items"]:
                    code = item["code"]
                    klines_map[code] = item.get("klines", [])
                    stock_info_map[code] = {
                        "name": item.get("name", ""),
                        "market": item.get("market", ""),
                        "period": item.get("period", "daily"),
                    }
            else:
                return {"success": False, "error": "未知的数据结构"}

            pkg = prepare(klines_map, stock_info_map, formula=formula if formula.strip() else None)
            return {
                "success": True,
                "json": pkg.to_json(),
                "prompt": pkg.to_prompt(),
                "scenario": pkg.scenario,
                "warnings": pkg.warnings,
            }
        except Exception as e:
            return {"success": False, "error": str(e), "detail": traceback.format_exc()}

    # ── Alert & Ticker API ──

    def get_alerts(self) -> Dict[str, Any]:
        """Return all alert configs + runtime states for the settings panel."""
        try:
            from core.config import load_alerts, get_alerts_config
            master = get_alerts_config()
            alerts_cfg = load_alerts()
            alerts_list = []
            engine = self._clipper._alert_engine
            for code, cfg in alerts_cfg.items():
                entry = {
                    "code": code,
                    "name": cfg.name,
                    "enabled": cfg.enabled,
                    "price_upper": cfg.price_upper,
                    "price_lower": cfg.price_lower,
                    "upper_triggered": cfg.upper_triggered,
                    "lower_triggered": cfg.lower_triggered,
                    "current_price": None,
                    "change_pct": None,
                    "status": "disabled" if not cfg.enabled else "normal",
                    "last_update": cfg.last_update,
                }
                # Runtime state from engine
                if engine and code in engine._states if hasattr(engine, '_states') else {}:
                    pass  # states not exposed directly — use triggered flags
                if cfg.upper_triggered:
                    entry["status"] = "triggered_upper"
                elif cfg.lower_triggered:
                    entry["status"] = "triggered_lower"
                alerts_list.append(entry)
            return {
                "success": True,
                "enabled": master.get("enabled", True),
                "poll_interval": master.get("poll_interval", 5),
                "max_alerts": master.get("max_alerts", 10),
                "alerts": alerts_list,
            }
        except Exception as e:
            import traceback
            return {"success": False, "error": str(e), "detail": traceback.format_exc()}

    def save_alert(self, code: str, name: str, price_upper: Optional[float],
                   price_lower: Optional[float], enabled: bool = True) -> Dict:
        """Create or update a single alert."""
        try:
            code = code.strip().upper()
            # Auto-prefix SH/SZ
            raw = code.replace("SH", "").replace("SZ", "").replace("HK", "")
            if raw.isdigit() and len(raw) == 6:
                code = ("SH" if raw.startswith(("60", "68")) else "SZ") + raw
            elif not (code.startswith("SH") or code.startswith("SZ")):
                return {"success": False, "error": "无效的代码格式，请输入6位数字如 600519"}

            # Validate
            if price_upper is None and price_lower is None:
                return {"success": False, "error": "至少设置一个阈值（上限或下限），或都留空仅看报价"}
            if price_upper is not None and price_lower is not None and price_upper <= price_lower:
                return {"success": False, "error": "上限必须大于下限"}

            # Max alerts check
            from core.config import load_alerts, get_alerts_config, save_alert as save_alert_cfg
            existing = load_alerts()
            if code not in existing and len(existing) >= get_alerts_config().get("max_alerts", 10):
                return {"success": False, "error": f"最多{get_alerts_config().get('max_alerts', 10)}条预警"}

            from core.alert_engine import AlertConfig
            cfg = AlertConfig(
                code=code, name=name.strip() if name else "",
                enabled=enabled,
                price_upper=float(price_upper) if price_upper else None,
                price_lower=float(price_lower) if price_lower else None,
            )
            save_alert_cfg(cfg)
            if self._clipper._alert_engine:
                self._clipper._alert_engine.reload()
            return {"success": True}
        except Exception as e:
            import traceback
            return {"success": False, "error": str(e), "detail": traceback.format_exc()}

    def delete_alert(self, code: str) -> Dict:
        """Delete a single alert."""
        try:
            from core.config import delete_alert_config
            delete_alert_config(code)
            if self._clipper._alert_engine:
                self._clipper._alert_engine.reload()
            return {"success": True}
        except Exception as e:
            import traceback
            return {"success": False, "error": str(e), "detail": traceback.format_exc()}

    def toggle_alerts(self) -> Dict:
        """Toggle master alert switch."""
        try:
            from core.config import _save_alerts_config, get_alerts_config
            current = get_alerts_config()
            new_enabled = not current.get("enabled", True)
            _save_alerts_config({"enabled": new_enabled, "poll_interval": current.get("poll_interval", 5),
                                 "buffer_pct": current.get("buffer_pct", 2.0),
                                 "max_alerts": current.get("max_alerts", 10)})
            return {"success": True, "enabled": new_enabled}
        except Exception as e:
            import traceback
            return {"success": False, "error": str(e), "detail": traceback.format_exc()}

    def test_alert_notification(self, code: str) -> Dict:
        """Send a test tray notification."""
        try:
            icon = getattr(self._clipper, '_icon', None)
            if icon is None:
                return {"success": False, "error": "托盘图标尚未创建，请重启程序"}
            from core.config import load_alerts
            alerts = load_alerts()
            cfg = alerts.get(code)
            name = cfg.name if cfg else code
            icon.notify(
                f"这是测试通知。若看到此消息，表示预警通知功能正常。\n股票: {name}",
                title=f"🔔 测试通知 — {name}"
            )
            return {"success": True}
        except Exception as e:
            import traceback
            return {"success": False, "error": str(e), "detail": traceback.format_exc()}

    def save_last_to_file(self) -> Dict[str, Any]:
        if not self._last_json or not self._last_result:
            return {"success": False, "error": "暂无数据，请先查询"}
        try:
            r = self._last_result
            if "meta" in r:
                name = r["meta"].get("name", "未知")
                code = r["meta"]["code"]
            else:
                # Comparison mode: use first stock name
                items = r.get("items", [])
                name = items[0]["name"] if items else "对比"
                code = "compare_" + "_".join(i["code"] for i in items[:3])
            safe_name = name.replace("/", "_").replace("\\", "_").replace(" ", "")[:20]
            date_str = time.strftime("%Y%m%d")
            filename = f"{code}_{safe_name}_{date_str}.json"
            save_dir = self._clipper._config.get("save_directory", "")
            filepath = os.path.join(save_dir if (save_dir and os.path.isdir(save_dir)) else os.getcwd(), filename)
            os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(self._last_json)
            return {"success": True, "filename": filename}
        except Exception as e:
            import traceback
            return {"success": False, "error": str(e), "detail": traceback.format_exc()}

# ============================================================
# Panel manager
# ============================================================
_panel_window: "Optional[webview.Window]" = None
_panel_lock = threading.Lock()


def show_panel(clipper: "StockClipper") -> None:
    """Show or focus the info panel."""
    global _panel_window
    with _panel_lock:
        if _panel_window is not None:
            try:
                _panel_window.show()
                _panel_window.restore()
                return
            except Exception:
                _panel_window = None

        api = PanelAPI(clipper)

        _panel_window = webview.create_window(
            title="Stock JSON Clipper V3.2",
            html=PANEL_HTML,
            width=680,
            height=760,
            resizable=True,
            on_top=False,
            js_api=api,
        )

        def _on_closed():
            global _panel_window
            _panel_window = None

        _panel_window.events.closed += _on_closed

        # Pick GUI backend: Windows → edgechromium, Linux → gtk
        import sys as _sys
        gui = None
        if _sys.platform == "win32":
            gui = "edgechromium"
        elif _sys.platform == "linux":
            gui = "gtk"

        try:
            webview.start(gui=gui, debug=False)
        except Exception:
            # Fallback: let pywebview auto-detect
            webview.start(gui=None, debug=False)
