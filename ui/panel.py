"""
web_panel.py — Info panel for Stock JSON Clipper V3.0.

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
  :root {
    --bg: #0b0e11;
    --bg2: #11161c;
    --surface: #181c24;
    --surface2: #1f2430;
    --border: #2a3040;
    --border2: #363d50;
    --text: #bcc3cd;
    --text1: #e6e9ef;
    --text2: #7e8594;
    --text3: #515766;
    --green: #2ebd59;
    --green-bg: rgba(46,189,89,0.12);
    --red: #f0534b;
    --red-bg: rgba(240,83,75,0.12);
    --orange: #f0a040;
    --orange-bg: rgba(240,160,64,0.12);
    --blue: #5098f0;
    --blue-bg: rgba(80,152,240,0.12);
    --purple: #9d7aef;
    --purple-bg: rgba(157,122,239,0.1);
    --radius: 10px;
    --radius-sm: 6px;
    --shadow: 0 1px 3px rgba(0,0,0,0.3);
    --font: -apple-system, BlinkMacSystemFont, "Microsoft YaHei", "PingFang SC",
             "Segoe UI", "Helvetica Neue", sans-serif;
    --font-mono: "Cascadia Code", "Fira Code", "JetBrains Mono", "Consolas", monospace;
  }

  * { box-sizing: border-box; margin: 0; padding: 0; }
  html, body { height: 100%; }

  body {
    font-family: var(--font);
    font-size: 13px;
    background: var(--bg);
    color: var(--text);
    line-height: 1.55;
    overflow-x: hidden;
    -webkit-user-select: none;
    user-select: none;
  }

  ::-webkit-scrollbar { width: 4px; }
  ::-webkit-scrollbar-track { background: transparent; }
  ::-webkit-scrollbar-thumb { background: var(--border2); border-radius: 4px; }
  ::-webkit-scrollbar-thumb:hover { background: var(--text3); }

  /* ---- Header ---- */
  .header {
    background: linear-gradient(165deg, #12192a 0%, #151e2e 40%, #111726 100%);
    padding: 16px 20px 14px;
    border-bottom: 1px solid var(--border);
    text-align: center;
    position: relative;
    overflow: hidden;
  }
  .header::before {
    content: '';
    position: absolute;
    top: -30px; right: -20px;
    width: 100px; height: 100px;
    background: radial-gradient(circle, rgba(80,152,240,0.06) 0%, transparent 70%);
    pointer-events: none;
  }
  .header .logo {
    font-size: 16px; font-weight: 800; color: #fff; letter-spacing: 0.5px;
  }
  .header .logo .ver {
    font-size: 10px; color: var(--blue); margin-left: 7px; font-weight: 500;
    background: var(--blue-bg); padding: 1px 6px; border-radius: 3px;
  }
  .header .desc { font-size: 11px; color: var(--text3); margin-top: 3px; letter-spacing: 0.2px; }

  /* ---- Search ---- */
  .search-section {
    padding: 14px 16px 12px;
    background: var(--bg2);
    border-bottom: 1px solid var(--border);
  }
  .search-row {
    display: -webkit-flex; display: flex;
    gap: 8px;
    -webkit-align-items: center; align-items: center;
  }
  .search-input-wrap {
    -webkit-flex: 1; flex: 1;
    position: relative;
  }
  .search-input-wrap::before {
    content: '\1F50D';
    position: absolute;
    left: 11px; top: 50%;
    -webkit-transform: translateY(-50%); transform: translateY(-50%);
    font-size: 13px; opacity: 0.4; pointer-events: none; z-index: 1;
  }
  .search-input-wrap input {
    width: 100%;
    background: var(--surface);
    color: #fff;
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    padding: 9px 12px 9px 32px;
    font-size: 14px;
    font-family: var(--font);
    outline: none;
    -webkit-transition: all 0.2s; transition: all 0.2s;
    box-shadow: inset 0 1px 2px rgba(0,0,0,0.2);
  }
  .search-input-wrap input:focus {
    border-color: var(--blue);
    box-shadow: 0 0 0 3px rgba(80,152,240,0.12), inset 0 1px 2px rgba(0,0,0,0.2);
  }
  .search-input-wrap input::-webkit-input-placeholder { color: var(--text3); }
  .search-input-wrap input::placeholder { color: var(--text3); }

  select {
    background: var(--surface);
    color: var(--text1);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    padding: 9px 8px;
    font-size: 13px;
    font-family: var(--font);
    outline: none;
    cursor: pointer;
    min-width: 72px;
    -webkit-transition: border-color 0.2s; transition: border-color 0.2s;
    -webkit-appearance: none; appearance: none;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='%237e8594' d='M6 8L1 3h10z'/%3E%3C/svg%3E");
    background-repeat: no-repeat;
    background-position: right 6px center;
    padding-right: 22px;
  }
  select:focus { border-color: var(--blue); }

  .btn-search {
    background: linear-gradient(135deg, #4d8aee 0%, #3b6fd4 100%);
    color: #fff;
    border: none;
    border-radius: var(--radius-sm);
    padding: 9px 20px;
    font-size: 13px;
    font-weight: 600;
    font-family: var(--font);
    cursor: pointer;
    -webkit-transition: all 0.2s; transition: all 0.2s;
    white-space: nowrap;
    box-shadow: 0 2px 6px rgba(59,111,212,0.25);
    letter-spacing: 0.3px;
  }
  .btn-search:hover { -webkit-transform: translateY(-1px); transform: translateY(-1px); box-shadow: 0 4px 12px rgba(59,111,212,0.35); }
  .btn-search:active { -webkit-transform: translateY(0); transform: translateY(0); }
  .btn-search:disabled { opacity: 0.45; cursor: not-allowed; -webkit-transform: none; transform: none; box-shadow: none; }
  .btn-add-code {
    background: var(--blue-bg); color: var(--blue);
    border: 1px dashed rgba(80,152,240,0.3); border-radius: var(--radius-sm);
    width: 38px; height: 38px; font-size: 20px; font-weight: 700;
    cursor: pointer; -webkit-transition: all 0.2s; transition: all 0.2s;
    flex-shrink: 0; line-height: 1;
  }
  .btn-add-code:hover { background: rgba(80,152,240,0.2); border-style: solid; }
  .btn-remove-code {
    background: none; border: none; color: var(--text3); cursor: pointer;
    font-size: 18px; padding: 0 6px; flex-shrink: 0; line-height: 1;
    -webkit-transition: color 0.15s; transition: color 0.15s;
  }
  .btn-remove-code:hover { color: var(--red); }

  .search-options {
    display: -webkit-flex; display: flex;
    gap: 16px; margin-top: 8px;
    font-size: 11px; color: var(--text2);
    -webkit-align-items: center; align-items: center;
  }
  .search-options label {
    display: -webkit-flex; display: flex;
    -webkit-align-items: center; align-items: center;
    gap: 5px; cursor: pointer;
    -webkit-transition: color 0.15s; transition: color 0.15s;
  }
  .search-options label:hover { color: var(--text); }
  .search-options input[type="checkbox"] { accent-color: var(--blue); cursor: pointer; width: 14px; height: 14px; }

  /* ---- Status ---- */
  .status-line {
    display: -webkit-flex; display: flex;
    -webkit-align-items: center; align-items: center;
    gap: 9px; padding: 7px 18px;
    font-size: 11px; color: var(--text2);
    background: var(--bg);
    border-bottom: 1px solid var(--border);
  }
  .status-dot {
    width: 8px; height: 8px;
    border-radius: 50%;
    -webkit-flex-shrink: 0; flex-shrink: 0;
  }
  .status-dot.on { background: var(--green); box-shadow: 0 0 6px rgba(46,189,89,0.5); }
  .status-dot.off { background: var(--text3); }
  .status-dot.fetching { background: var(--orange); box-shadow: 0 0 6px rgba(240,160,64,0.5); -webkit-animation: pulse 0.7s infinite; animation: pulse 0.7s infinite; }
  @-webkit-keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.15; } }
  @keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.15; } }

  /* ---- Tabs ---- */
  .tabs {
    display: -webkit-flex; display: flex;
    gap: 0;
    padding: 0 14px;
    background: var(--bg2);
    border-bottom: 1px solid var(--border);
  }
  .tab-btn {
    background: none; border: none;
    border-bottom: 2px solid transparent;
    color: var(--text2);
    padding: 11px 16px;
    font-size: 13px; font-weight: 500;
    font-family: var(--font);
    cursor: pointer;
    -webkit-transition: all 0.2s; transition: all 0.2s;
    position: relative;
  }
  .tab-btn:hover { color: var(--text1); }
  .tab-btn.active { color: #fff; border-bottom-color: var(--blue); font-weight: 600; }

  .tab-content { display: none; -webkit-animation: fadeIn 0.2s; animation: fadeIn 0.2s; }
  .tab-content.active { display: block; }
  @-webkit-keyframes fadeIn { from { opacity: 0; -webkit-transform: translateY(4px); transform: translateY(4px); } to { opacity: 1; -webkit-transform: translateY(0); transform: translateY(0); } }
  @keyframes fadeIn { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: translateY(0); } }

  .main-area { padding: 14px 14px 8px; }

  /* ---- Card ---- */
  .card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 15px 17px;
    margin-bottom: 10px;
    contain: layout style;
    box-shadow: var(--shadow);
    -webkit-transition: border-color 0.2s; transition: border-color 0.2s;
  }
  .card:hover { border-color: var(--border2); }
  .card-header {
    display: -webkit-flex; display: flex;
    -webkit-justify-content: space-between; justify-content: space-between;
    -webkit-align-items: center; align-items: center;
    margin-bottom: 12px;
  }
  .card-title { font-size: 15px; font-weight: 700; color: #fff; }
  .card-title .code { color: var(--text2); font-weight: 400; margin-left: 8px; font-size: 13px; }

  .meta-tags {
    display: -webkit-flex; display: flex;
    gap: 6px; -webkit-flex-wrap: wrap; flex-wrap: wrap;
    margin-bottom: 12px;
  }
  .meta-tag {
    background: var(--surface2);
    color: var(--text2);
    padding: 3px 10px; border-radius: 5px;
    font-size: 11px; white-space: nowrap;
    border: 1px solid var(--border);
  }
  .meta-tag .val { color: var(--text1); font-weight: 500; }

  /* Indicator table */
  .ind-table { width: 100%; border-collapse: collapse; font-size: 12px; }
  .ind-table td { padding: 7px 10px; border-bottom: 1px solid rgba(255,255,255,0.04); vertical-align: top; }
  .ind-table tr:last-child td { border-bottom: none; }
  .ind-table .lbl { color: var(--text2); white-space: nowrap; width: 34%; font-size: 11px; }
  .ind-table .val { color: var(--text1); font-weight: 600; font-family: var(--font-mono); font-size: 13px; }
  .ind-table .val.up { color: var(--green); }
  .ind-table .val.down { color: var(--red); }
  .ind-table .note { color: var(--text3); font-size: 10px; font-weight: 400; padding-left: 6px; }

  .card-actions { display: -webkit-flex; display: flex; gap: 8px; margin-top: 12px; -webkit-flex-wrap: wrap; flex-wrap: wrap; }
  .card-actions button {
    background: var(--surface2); color: var(--text1);
    border: 1px solid var(--border); border-radius: var(--radius-sm);
    padding: 8px 15px; font-size: 12px; font-family: var(--font);
    cursor: pointer; font-weight: 500;
    -webkit-transition: all 0.2s; transition: all 0.2s;
    letter-spacing: 0.2px;
  }
  .card-actions button:hover { background: #2a3142; border-color: var(--border2); }
  .card-actions button:active { -webkit-transform: scale(0.97); transform: scale(0.97); }
  .card-actions button.btn-primary {
    background: var(--blue-bg); color: var(--blue);
    border-color: rgba(80,152,240,0.3); font-weight: 600;
  }
  .card-actions button.btn-primary:hover { background: rgba(80,152,240,0.2); border-color: rgba(80,152,240,0.5); }

  /* Empty state */
  .empty-state { text-align: center; padding: 48px 24px; color: var(--text3); }
  .empty-state .icon { font-size: 44px; margin-bottom: 12px; opacity: 0.6; }
  .empty-state .hint { font-size: 12px; color: var(--text2); margin-top: 6px; line-height: 1.7; }

  /* History */
  .history-table { width: 100%; border-collapse: collapse; font-size: 12px; }
  .history-table th {
    text-align: left; padding: 6px 10px;
    border-bottom: 2px solid var(--border);
    color: var(--text2); font-weight: 600; font-size: 10px;
    text-transform: uppercase; letter-spacing: 0.5px;
  }
  .history-table td { padding: 6px 10px; border-bottom: 1px solid rgba(255,255,255,0.03); }
  .history-table tr:hover td { background: rgba(255,255,255,0.015); }
  .history-table .status-ok { color: var(--green); font-weight: 500; }
  .history-table .status-err { color: var(--red); font-weight: 500; }
  .history-table .status-cache { color: var(--blue); font-weight: 500; }
  .history-table .status-pend { color: var(--orange); font-weight: 500; }
  .history-table .empty { text-align: center; color: var(--text3); padding: 20px; }

  /* Settings */
  .setting-item { margin-bottom: 14px; }
  .setting-item label {
    display: block; font-size: 10px; color: var(--text2);
    margin-bottom: 4px; text-transform: uppercase;
    letter-spacing: 0.6px; font-weight: 600;
  }
  .setting-item .setting-hint { font-size: 10px; color: var(--text3); margin-top: 3px; }
  .setting-item input[type="text"],
  .setting-item input[type="number"] {
    background: var(--bg); color: var(--text1);
    border: 1px solid var(--border); border-radius: var(--radius-sm);
    padding: 8px 11px; font-size: 13px; font-family: var(--font);
    outline: none; width: 100%;
    -webkit-transition: all 0.2s; transition: all 0.2s;
  }
  .setting-item input:focus { border-color: var(--blue); box-shadow: 0 0 0 3px rgba(80,152,240,0.1); }
  .setting-item input[type="number"] { width: 130px; }

  .btn-row { display: -webkit-flex; display: flex; gap: 8px; margin-top: 10px; }
  .btn-row button {
    background: var(--surface2); color: var(--text1);
    border: 1px solid var(--border); border-radius: var(--radius-sm);
    padding: 8px 15px; font-size: 12px; font-family: var(--font);
    cursor: pointer; -webkit-transition: all 0.2s; transition: all 0.2s;
  }
  .btn-row button:hover { background: #2a3142; }
  .btn-row button.btn-danger { color: var(--red); }
  .btn-row button.btn-danger:hover { background: var(--red-bg); border-color: rgba(240,83,75,0.4); }

  /* Toggle switch */
  .toggle-wrap {
    display: -webkit-flex; display: flex;
    -webkit-align-items: center; align-items: center;
    gap: 10px; cursor: pointer;
  }
  .toggle-sw {
    width: 38px; height: 22px;
    background: var(--border2); border-radius: 11px;
    position: relative; cursor: pointer;
    -webkit-transition: all 0.25s; transition: all 0.25s;
  }
  .toggle-sw.on { background: var(--green); box-shadow: 0 0 8px rgba(46,189,89,0.3); }
  .toggle-sw::after {
    content: ''; position: absolute;
    top: 2px; left: 2px;
    width: 18px; height: 18px;
    background: #fff; border-radius: 50%;
    -webkit-transition: -webkit-transform 0.25s; transition: transform 0.25s;
    box-shadow: 0 1px 3px rgba(0,0,0,0.3);
  }
  .toggle-sw.on::after { -webkit-transform: translateX(16px); transform: translateX(16px); }

  /* Textarea */
  textarea {
    width: 100%; min-height: 90px;
    background: var(--bg); color: var(--text1);
    border: 1px solid var(--border); border-radius: var(--radius-sm);
    padding: 11px; font-size: 12px; font-family: var(--font-mono);
    resize: vertical; outline: none;
    -webkit-transition: all 0.2s; transition: all 0.2s;
    box-shadow: inset 0 1px 2px rgba(0,0,0,0.2);
  }
  textarea:focus { border-color: var(--blue); box-shadow: 0 0 0 3px rgba(80,152,240,0.1), inset 0 1px 2px rgba(0,0,0,0.2); }

  /* Toast */
  .toast {
    position: fixed; bottom: 24px; left: 50%;
    -webkit-transform: translateX(-50%) translateY(20px); transform: translateX(-50%) translateY(20px);
    background: #2a3140; color: #fff;
    padding: 10px 24px; border-radius: 22px;
    font-size: 12px; font-weight: 500;
    opacity: 0; pointer-events: none; z-index: 999;
    box-shadow: 0 4px 20px rgba(0,0,0,0.4);
    -webkit-transition: all 0.3s; transition: all 0.3s;
    border: 1px solid var(--border);
  }
  .toast.show { opacity: 1; -webkit-transform: translateX(-50%) translateY(0); transform: translateX(-50%) translateY(0); }
  .toast.error { background: #3d1a1a; color: #fca5a5; border-color: rgba(240,83,75,0.3); }

  /* Error Banner */
  .error-banner {
    display: none; margin: 8px 14px;
    padding: 11px 15px;
    background: var(--red-bg);
    border: 1px solid rgba(240,83,75,0.25);
    border-radius: var(--radius-sm);
    font-size: 12px; color: #fca5a5;
    word-break: break-all;
    -webkit-user-select: text; user-select: text;
  }
  .error-banner.show { display: block; -webkit-animation: fadeIn 0.2s; animation: fadeIn 0.2s; }
  .error-banner .err-title { font-weight: 700; color: #f0534b; margin-bottom: 5px; font-size: 13px; }
  .error-banner .err-detail {
    color: var(--text2); font-size: 11px; font-family: var(--font-mono);
    white-space: pre-wrap; max-height: 130px; overflow-y: auto;
    margin-top: 5px; line-height: 1.5;
  }
  .error-banner .err-close {
    float: right; color: var(--text2); font-size: 16px;
    line-height: 1; cursor: pointer; padding: 0 5px;
    -webkit-transition: color 0.15s; transition: color 0.15s;
  }
  .error-banner .err-close:hover { color: #fff; }

  .footer {
    text-align: center; color: var(--text3);
    font-size: 10px; padding: 10px 8px; opacity: 0.4;
    letter-spacing: 0.2px;
  }
</style>
</head>
<body>

<div class="header">
  <div class="logo">📈 Stock JSON Clipper<span class="ver">V3.0</span></div>
  <div class="desc">A股数据桥梁 · 纯本地运行 · 一键生成AI分析JSON</div>
</div>

<!-- Search -->
<div class="search-section">
  <div id="codeInputs">
    <div class="search-row">
      <div class="search-input-wrap">
        <input type="text" class="codeInput" placeholder="输入代码，如 000001 或 SH600519"
               maxlength="10" autofocus autocomplete="off">
      </div>
      <button class="btn-add-code" onclick="addCodeInput()" title="添加对比股票">+</button>
    </div>
  </div>
  <div class="search-row" style="margin-top:6px;">
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
           style="width:55px;background:var(--surface);color:var(--text1);border:1px solid var(--border);
                  border-radius:var(--radius-sm);padding:9px 4px;font-size:12px;font-family:var(--font-mono);
                  text-align:center;outline:none;" title="K线条数">
    <button class="btn-search" id="searchBtn" onclick="onSearch()">查询</button>
  </div>
</div>

<!-- Status -->
<div class="status-line">
  <div class="status-dot on" id="statusDot"></div>
  <span id="statusText">剪贴板监控运行中 — 在股票软件复制代码即可自动识别</span>
</div>

<!-- Error Banner -->
<div class="error-banner" id="errorBanner" onclick="(function(e){if(e.target.classList.contains('err-close'))document.getElementById('errorBanner').classList.remove('show')})(event)">
  <span class="err-close">&times;</span>
  <div class="err-title" id="errTitle">⚠ 错误</div>
  <div class="err-detail" id="errDetail"></div>
</div>

<!-- Tabs -->
<div class="tabs">
  <button class="tab-btn active" data-tab="data">📊 数据查询</button>
  <button class="tab-btn" data-tab="settings">⚙️ 设置</button>
</div>

<!-- ====== Tab: 数据查询 ====== -->
<div class="tab-content active" id="tab-data">
  <div class="main-area">

    <!-- Result Card -->
    <div id="resultCard" class="card" style="display:none;">
      <div class="card-header">
        <div class="card-title" id="rcTitle">--<span class="code"></span></div>
        <span style="font-size:11px;color:var(--text3);" id="rcPeriod"></span>
      </div>
      <div class="meta-tags" id="rcMeta"></div>

      <!-- Indicators -->
      <div id="chartContainer" style="margin-bottom:10px;overflow-x:auto;"></div>
      <table class="ind-table" id="rcIndicators"></table>

      <hr style="border-color:var(--border);margin:12px 0;">
      <div class="card-actions">
        <button class="btn-primary" onclick="onCopyJSON()">📋 复制JSON</button>
        <button onclick="onSaveFile()">💾 保存文件</button>
        <button onclick="onSmartAnalyze()" style="background:var(--purple-bg);color:var(--purple);border-color:rgba(157,122,239,0.3);">🤖 AI分析</button>
        <button onclick="onFullAnalyze()" style="background:rgba(240,160,64,0.12);color:var(--orange);border-color:rgba(240,160,64,0.3);">🧠 深度分析</button>
      </div>
      <details style="margin-top:8px;font-size:11px;color:var(--text2);">
        <summary style="cursor:pointer;">📐 通达信公式（可选）</summary>
        <textarea id="formulaInput" placeholder="粘贴选股公式&#10;例: CROSS(MA(C,5),MA(C,20)) AND RSI(6)>50" style="min-height:50px;margin-top:6px;"></textarea>
      </details>
    </div>

    <div id="emptyResult">
      <div class="empty-state">
        <div class="icon">📡</div>
        <div>暂无查询数据</div>
        <div class="hint">在上方输入股票代码点击「查询」<br>或在通达信/同花顺中 Ctrl+C 复制代码自动识别<br><br><span style="color:var(--text3);">支持: 000001（日线）/ W:000001（周线）/ M:000001（月线）/ #000001（保存文件）</span></div>
      </div>
    </div>

    <!-- History -->
    <div class="card" style="margin-top:6px;">
      <div style="font-size:13px;font-weight:600;color:var(--text1);margin-bottom:8px;">📜 最近查询记录</div>
      <table class="history-table">
        <thead><tr><th>时间</th><th>代码</th><th>名称</th><th>状态</th></tr></thead>
        <tbody id="historyBody">
          <tr class="empty"><td colspan="4">暂无记录 — 查询或复制股票代码后自动显示</td></tr>
        </tbody>
      </table>
    </div>
  </div>
</div>

<!-- ====== Tab: 设置 ====== -->
<div class="tab-content" id="tab-settings">
  <div class="main-area">
    <div class="card">
      <div class="card-title" style="font-size:13px;margin-bottom:10px;">🔌 剪贴板监控</div>
      <div class="toggle-wrap" onclick="onToggleMonitor()">
        <div class="toggle-sw on" id="clipboardToggle"></div>
        <span style="font-size:13px;">启用剪贴板自动识别</span>
      </div>
      <div class="setting-hint" style="color:var(--text3);font-size:11px;margin-top:4px;">
        关闭后仅可通过上方搜索框手动输入代码查询
      </div>
    </div>

    <div class="card">
      <div class="card-title" style="font-size:13px;margin-bottom:10px;">📊 数据设置</div>
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

    <div class="card">
      <div class="card-title" style="font-size:13px;margin-bottom:10px;">⚡ 高级设置</div>
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

    <div class="btn-row" style="padding:0 0 10px 0;">
      <button class="btn-danger" onclick="onClearCache()">🗑 清空数据缓存</button>
    </div>
  </div>
</div>

<!-- ====== Tab: AI分析 ====== -->
<div class="tab-content" id="tab-formula">
  <div class="main-area">
    <div class="card">
      <div class="card-title" style="font-size:13px;margin-bottom:10px;">🤖 通达信公式 → AI分析提示词</div>
      <div style="font-size:12px;color:var(--text2);margin-bottom:8px;">
        将通达信选股公式粘贴到下方，系统会自动解析公式要素，结合当前股票的技术指标，
        生成一份专业的AI分析提示词。将提示词粘贴到 ChatGPT / DeepSeek / Claude 对话框即可获得分析。
      </div>
      <textarea id="formulaInput" placeholder="在此粘贴通达信选股公式&#10;例如: CROSS(MA(收盘价,5), MA(收盘价,20)) AND RSI(6) 大于 50&#10;&#10;支持: MA均线 / MACD / RSI / BOLL布林带 / CROSS金叉死叉 / 比较运算"></textarea>
      <div class="card-actions" style="margin-top:10px;">
        <button class="btn-primary" onclick="onGeneratePrompt()">✨ 生成选股分析提示词</button>
        <button onclick="onQuickAnalyze()">📊 快速技术分析（无需公式）</button>
        <button onclick="document.getElementById('formulaInput').value=''">清空公式</button>
      </div>
      <div style="font-size:10px;color:var(--text3);margin-top:6px;">
        提示词将自动复制到剪贴板，直接粘贴到AI对话框使用。生成前请先查询股票数据。
      </div>
    </div>
  </div>
</div>


<div class="toast" id="toast"></div>
<div class="footer">Stock JSON Clipper V3.0 · GPL-3.0 · 数据来源: 腾讯财经/新浪财经/东方财富</div>

<script>
// ============================================================
// Global Error Handler — show all JS errors in UI
// ============================================================
window._showError = function(title, detail) {
  var banner = document.getElementById('errorBanner');
  document.getElementById('errTitle').textContent = '⚠ ' + (title || '错误');
  document.getElementById('errDetail').textContent = detail || '';
  banner.classList.add('show');
  // Also toast
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
  // Also dump to status bar for immediate visibility
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
// Search — with dynamic multi-input
// ============================================================
var _maxInputs = 6;

function addCodeInput() {
  var container = document.getElementById('codeInputs');
  var count = container.querySelectorAll('.codeInput').length;
  if (count >= _maxInputs) { showToast('最多对比' + _maxInputs + '只股票'); return; }
  var row = document.createElement('div');
  row.className = 'search-row';
  row.style.marginTop = '6px';
  row.innerHTML = '<div class="search-input-wrap"><input type="text" class="codeInput" placeholder="添加对比股票…" maxlength="10" autocomplete="off"></div><button class="btn-remove-code" onclick="this.parentElement.remove()" title="移除">&times;</button>';
  container.appendChild(row);
}

function getCodeInputs() {
  var inputs = document.querySelectorAll('.codeInput');
  var codes = [];
  for (var i = 0; i < inputs.length; i++) {
    var v = inputs[i].value.trim();
    if (v) codes.push(v);
  }
  return codes;
}

function toStockApiCode(raw) {
  var c = raw.trim().toUpperCase().replace(/[#WM:]/g, '');
  // Already has prefix
  if (/^(SH|SZ|HK|US)/.test(c)) return c;
  // 6-digit A-share: detect market
  if (/^\d{6}$/.test(c)) return (c.startsWith('60') || c.startsWith('68')) ? 'SH' + c : 'SZ' + c;
  // 5-digit HK stock
  if (/^\d{5}$/.test(c)) return 'HK' + c;
  return null;
}

function onSearch() {
  var raws = getCodeInputs();
  if (!raws.length) { showToast('请输入股票代码'); return; }
  // Multi-stock comparison
  if (raws.length > 1) { return onCompare(raws); }

  var code = toStockApiCode(raws[0]);
  if (!code) { showToast('无效代码。支持: 000001 / SH600519 / HK00700'); return; }

  var period = document.getElementById('searchPeriod').value;
  var count = parseInt(document.getElementById('searchCount').value) || 250;
  count = Math.max(5, Math.min(9999, count));
  var isIntraday = /min$/.test(period);
  var btn = document.getElementById('searchBtn');
  btn.disabled = true; btn.textContent = '查询中…';

  document.getElementById('statusDot').className = 'status-dot fetching';
  document.getElementById('statusText').textContent = '正在拉取 ' + code + '…';

  function doCompute(klines, stockInfo) {
    pywebview.api.compute_indicators(code, klines, stockInfo, period).then(function(detail) {
      window._currentResult = detail;
      renderResultCard(detail);
      renderChart(klines, period);
      document.getElementById('statusText').textContent = (stockInfo.name || code) + ' | ' + klines.length + '条';
      document.getElementById('statusDot').className = 'status-dot on';
      btn.disabled = false; btn.textContent = '查询';
    });
  }

  try {
    if (isIntraday) {
      // Intraday: use EastMoney via Python
      pywebview.api.fetch_intraday(code, period, count).then(function(klines) {
        if (!klines || !klines.length) { window._showError('无数据', '分时数据暂无'); btn.disabled = false; btn.textContent = '查询'; return; }
        StockApi.stocks.auto.getStock(code).then(function(stock) {
          doCompute(klines, {name: stock.name || code});
        }).catch(function() {
          doCompute(klines, {name: code});
        });
      });
    } else {
      // Day/Week/Month: stock-api
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

// Multi-stock comparison
function onCompare(raws) {
  var codes = raws.map(toStockApiCode).filter(Boolean);
  if (codes.length < 2) { showToast('至少输入2个有效代码，用逗号分隔'); return; }
  if (codes.length > 6) { showToast('最多对比6只股票'); return; }

  var period = document.getElementById('searchPeriod').value;
  var count = parseInt(document.getElementById('searchCount').value) || 250;
  count = Math.max(5, Math.min(9999, count));
  var isIntraday = /min$/.test(period);
  var btn = document.getElementById('searchBtn');
  btn.disabled = true; btn.textContent = '对比中…';
  document.getElementById('statusDot').className = 'status-dot fetching';
  document.getElementById('statusText').textContent = '正在对比 ' + codes.join(', ') + '…';

  function doCompare(items) {
    pywebview.api.compare_indicators(items, period).then(function(data) {
      window._currentResult = data;
      renderCompareCard(data, period);
      document.getElementById('statusText').textContent = codes.length + '只对比完成';
      document.getElementById('statusDot').className = 'status-dot on';
      btn.disabled = false; btn.textContent = '查询';
    });
  }

  if (isIntraday) {
    // Intraday: fetch via Python EastMoney API
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
// Unified SVG chart — K-line + MACD + RSI in one canvas
// ============================================================
var CHART_COLORS = {up: '#ff6b6b', dn: '#4ddf7c', grid: '#2a3040', text: '#515766'};

function buildChartSVG(klines, period, W, showVol, showMACD, showRSI) {
  if (!klines || klines.length < 2) return '';
  var closes = klines.map(function(k){return k.close;});
  var macdData = showMACD ? calcMACDSeries(closes) : null;
  var rsiData = showRSI ? calcRSISeries(closes, 6) : null;

  var sections = 1 + (showVol?1:0) + (showMACD?1:0) + (showRSI?1:0);
  var pH = 200, vH = showVol ? 40 : 0, mH = showMACD ? 50 : 0, rH = showRSI ? 40 : 0;
  var gap = 10, totalH = pH + vH + mH + rH + gap * (sections - 1) + 10;
  var offY = 5, stepX = W / klines.length, barW = Math.max(1.5, stepX * 0.7);

  var highs = klines.map(function(k){return k.high;}), lows = klines.map(function(k){return k.low;});
  var maxP = Math.max.apply(null, highs), minP = Math.min.apply(null, lows), pR = maxP - minP || 1;
  var volMax = Math.max.apply(null, klines.map(function(k){return k.volume||0;})) || 1;

  function scale(vals, h, top) { var mx=Math.max.apply(null,vals)||1,mn=Math.min.apply(null,vals)||0,r=mx-mn||1; return function(v){return top+(mx-v)/r*h;}; }
  var py = scale(highs.concat(lows), pH, offY);
  var vy = showVol ? scale(klines.map(function(k){return k.volume||0;}), vH, offY+pH+gap) : null;
  var my = showMACD ? scale(macdData.dif.concat(macdData.dea).concat(macdData.bar), mH, offY+pH+vH+gap) : null;
  var ry = showRSI ? scale(rsiData, rH, offY+pH+vH+mH+gap) : null;

  var svg = [];
  svg.push('<svg width=\"'+W+'\" height=\"'+totalH+'\" style=\"display:block;cursor:crosshair;font-family:var(--font-mono);\">');

  // Price grid + candles + volume
  for (var i=0;i<=4;i++) { var y=offY+pH*i/4; svg.push('<line x1=\"0\" y1=\"'+y+'\" x2=\"'+W+'\" y2=\"'+y+'\" stroke=\"'+CHART_COLORS.grid+'\" stroke-width=\"0.5\" opacity=\"0.35\"/>'); svg.push('<text x=\"'+(W+6)+'\" y=\"'+(y+4)+'\" fill=\"'+CHART_COLORS.text+'\" font-size=\"10\">'+(maxP-pR*i/4).toFixed(2)+'</text>'); }
  for (var i=0;i<klines.length;i++) {
    var k=klines[i], up=k.close>=k.open, clr=up?CHART_COLORS.up:CHART_COLORS.dn;
    var cx=10+i*stepX+(stepX-barW)/2, oy2=py(k.open), cy2=py(k.close), hy2=py(k.high), ly2=py(k.low);
    svg.push('<line x1=\"'+(cx+barW/2)+'\" y1=\"'+hy2+'\" x2=\"'+(cx+barW/2)+'\" y2=\"'+ly2+'\" stroke=\"'+clr+'\" stroke-width=\"1\"/>');
    svg.push('<rect x=\"'+cx+'\" y=\"'+Math.min(oy2,cy2)+'\" width=\"'+barW+'\" height=\"'+Math.max(Math.abs(cy2-oy2),1)+'\" fill=\"'+clr+'\" rx=\"1\"/>');
    if (showVol) { var vh2=(k.volume||0)/volMax*vH; svg.push('<rect x=\"'+cx+'\" y=\"'+(offY+pH+gap+vH-vh2)+'\" width=\"'+barW+'\" height=\"'+Math.max(vh2,0.5)+'\" fill=\"'+clr+'\" opacity=\"0.2\" rx=\"1\"/>'); }
    if (showMACD&&macdData.bar[i]!=null) { var mb=macdData.bar[i]; var zy=my(0),by=my(mb); svg.push('<rect x=\"'+cx+'\" y=\"'+Math.min(zy,by)+'\" width=\"'+barW+'\" height=\"'+Math.max(Math.abs(by-zy),0.5)+'\" fill=\"'+(mb>=0?CHART_COLORS.up:CHART_COLORS.dn)+'\" opacity=\"0.5\" rx=\"1\"/>'); }
  }
  // MACD lines
  if (showMACD) {
    svg.push('<line x1=\"0\" y1=\"'+my(0)+'\" x2=\"'+W+'\" y2=\"'+my(0)+'\" stroke=\"var(--border)\" stroke-width=\"1\"/>');
    for (var i=1;i<klines.length;i++) { var x1=10+(i-1)*stepX+stepX/2,x2=10+i*stepX+stepX/2; if(macdData.dif[i]!=null&&macdData.dif[i-1]!=null)svg.push('<line x1=\"'+x1+'\" y1=\"'+my(macdData.dif[i-1])+'\" x2=\"'+x2+'\" y2=\"'+my(macdData.dif[i])+'\" stroke=\"#f0a040\" stroke-width=\"1.3\"/>'); if(macdData.dea[i]!=null&&macdData.dea[i-1]!=null)svg.push('<line x1=\"'+x1+'\" y1=\"'+my(macdData.dea[i-1])+'\" x2=\"'+x2+'\" y2=\"'+my(macdData.dea[i])+'\" stroke=\"#5098f0\" stroke-width=\"1.3\"/>'); }
  }
  // RSI line
  if (showRSI) {
    [30,50,70].forEach(function(v){var yv=ry(v);svg.push('<line x1=\"0\" y1=\"'+yv+'\" x2=\"'+W+'\" y2=\"'+yv+'\" stroke=\"var(--border)\" stroke-width=\"0.5\" stroke-dasharray=\"3,6\" opacity=\"0.4\"/>');});
    for (var i=1;i<klines.length;i++){if(rsiData[i]!=null&&rsiData[i-1]!=null){var rx1=10+(i-1)*stepX+stepX/2,rx2=10+i*stepX+stepX/2;svg.push('<line x1=\"'+rx1+'\" y1=\"'+ry(rsiData[i-1])+'\" x2=\"'+rx2+'\" y2=\"'+ry(rsiData[i])+'\" stroke=\"#a78bfa\" stroke-width=\"1.5\"/>');}}
  }
  // Labels
  svg.push('<text x=\"4\" y=\"'+(totalH-3)+'\" fill=\"'+CHART_COLORS.text+'\" font-size=\"9\">'+(klines[0].date||'')+'</text>');
  svg.push('<text x=\"'+(W-4)+'\" y=\"'+(totalH-3)+'\" fill=\"'+CHART_COLORS.text+'\" font-size=\"9\" text-anchor=\"end\">'+(klines[klines.length-1].date||'')+'</text>');
  if (showMACD) svg.push('<text x=\"4\" y=\"'+(offY+pH+gap-2)+'\" fill=\"var(--text2)\" font-size=\"9\">MACD(12,26,9)</text>');
  if (showRSI) svg.push('<text x=\"4\" y=\"'+(offY+pH+vH+gap+mH+gap-2)+'\" fill=\"var(--text2)\" font-size=\"9\">RSI(6)</text>');
  svg.push('<line class=\"crosshair\" x1=\"0\" y1=\"0\" x2=\"0\" y2=\"'+pH+'\" stroke=\"var(--text1)\" stroke-width=\"1\" stroke-dasharray=\"4,2\" opacity=\"0\" style=\"pointer-events:none;\"/>');
  svg.push('<rect x=\"10\" y=\"0\" width=\"'+(W-10)+'\" height=\"'+pH+'\" fill=\"transparent\" onmousemove=\"chartHover(event)\" onmouseout=\"hideTooltip()\"/>');
  svg.push('</svg>');
  return {html: svg.join(''), totalH: totalH};
}

var _chartShowMACD = true, _chartShowRSI = true;
function renderChart(klines, period) {
  var c = document.getElementById('chartContainer');
  if (!c) return;
  if (!klines || klines.length < 2) { c.innerHTML = ''; return; }
  var W = c.clientWidth - 70;
  var closes = klines.map(function(k){return k.close;});
  var chart = buildChartSVG(klines, period, W, true, _chartShowMACD, _chartShowRSI);
  var toggleBtns = '<div style=\"margin-bottom:4px;display:flex;gap:8px;font-size:10px;\">' +
    '<label style=\"cursor:pointer;color:var(--text2);\"><input type=\"checkbox\" onchange=\"toggleIndicator(0)\" ' + (_chartShowMACD?'checked':'') + '> MACD</label>' +
    '<label style=\"cursor:pointer;color:var(--text2);\"><input type=\"checkbox\" onchange=\"toggleIndicator(1)\" ' + (_chartShowRSI?'checked':'') + '> RSI</label>' +
    '</div>';
  c.innerHTML = toggleBtns + '<div style=\"position:relative;cursor:pointer;\" onclick=\"openLargeChart()\" title=\"点击查看大图\">' +
    '<div id=\"chartTooltip\" style=\"display:none;position:absolute;background:var(--surface);border:1px solid var(--border2);border-radius:6px;padding:8px 10px;font-size:10px;font-family:var(--font-mono);color:var(--text1);pointer-events:none;z-index:10;box-shadow:0 4px 12px rgba(0,0,0,0.4);white-space:nowrap;line-height:1.7;\"></div>' +
    chart.html + '</div>';
  c._klines = klines; c._stepX = W / klines.length; c._PW = W;
  c._macdData = _chartShowMACD ? calcMACDSeries(closes) : null;
  c._rsiData = _chartShowRSI ? calcRSISeries(closes, 6) : null;
}

// Large chart modal
function openLargeChart() {
  var c = document.getElementById('chartContainer');
  if (!c || !c._klines) return;
  var klines = c._klines, W = Math.min(1000, screen.width - 80);
  var chart = buildChartSVG(klines, 'daily', W, true, true, true);
  var overlay = document.createElement('div');
  overlay.id = 'chartOverlay';
  overlay.style.cssText = 'position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.85);z-index:9999;display:flex;align-items:center;justify-content:center;overflow:auto;padding:20px;';
  var title = (window._currentResult && window._currentResult.meta) ? (window._currentResult.meta.code + ' ' + window._currentResult.meta.name) : 'K-line Chart';
  overlay.innerHTML = '<div style=\"background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:12px;max-width:' + (W+80) + 'px;\">' +
    '<div style=\"display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;\">' +
    '<span style=\"color:var(--text1);font-size:13px;font-weight:700;\">' + title + '</span>' +
    '<button onclick=\"this.parentElement.parentElement.parentElement.remove()\" style=\"background:none;border:none;color:var(--text2);font-size:20px;cursor:pointer;\">x</button>' +
    '</div>' +
    '<div style=\"overflow-x:auto;\">' + chart.html + '</div></div>';
  overlay.addEventListener('click', function(e) { if (e.target === overlay) overlay.remove(); });
  document.body.appendChild(overlay);
}

// Indicator series for sub-charts
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

// Hover: works anywhere on X-axis
function chartHover(e) {
  var el = e.target;
  while (el && !el._klines) { try { if (el.getAttribute && el.getAttribute('data-klines')) break; } catch(ex) {} el = el.parentNode; }
  if (!el) return;
  var klines = el._klines;
  var stepX = el._stepX;
  if (!klines && el.getAttribute('data-klines')) {
    try { klines = JSON.parse(el.getAttribute('data-klines').replace(/&apos;/g, "'").replace(/&quot;/g, '"')); } catch(ex) {}
    stepX = parseFloat(el.getAttribute('data-stepx')) || 0;
  }
  if (!klines || !stepX) return;
  var rect = el.getBoundingClientRect();
  var x = e.clientX - rect.left - 10;
  var i = Math.floor(x / stepX);
  if (i < 0) i = 0; if (i >= klines.length) i = klines.length - 1;
  var k = klines[i];
  var tip = el.querySelector('[id^=cmpTip]') || document.getElementById('chartTooltip');
  if (!tip) return;
  var up = k.close >= k.open, clr = up ? CHART_COLORS.up : CHART_COLORS.dn;
    var macd = el._macdData, rsi = el._rsiData;
  if (!macd && klines && klines.length > 30) {
    var c2 = klines.map(function(k){return k.close;});
    macd = calcMACDSeries(c2); rsi = calcRSISeries(c2, 6);
  }
  var D = function(v,d){return v!=null?Number(v).toFixed(d):'--';};
  tip.innerHTML = '<div style="font-weight:700;color:'+clr+';">'+ (k.date||'') +'</div>' +
    '<table style="font-size:10px;">' +
    '<tr><td style="color:var(--text2);padding-right:6px;">开</td><td>'+ (k.open||0).toFixed(2) +'</td>'+
    '<td style="color:var(--text2);padding:0 3px;">高</td><td>'+ (k.high||0).toFixed(2) +'</td></tr>'+
    '<tr><td style="color:var(--text2);">低</td><td>'+ (k.low||0).toFixed(2) +'</td>'+
    '<td style="color:var(--text2);">收</td><td style="color:'+clr+';font-weight:700;">'+ (k.close||0).toFixed(2) +'</td></tr>'+
    '<tr><td style="color:var(--text2);">量</td><td>'+ ((k.volume||0)/10000).toFixed(1) +'万</td>'+
    '<td style="color:var(--text2);">幅</td><td>'+ ((k.open>0?(k.close-k.open)/k.open*100:0)).toFixed(2) +'%</td></tr>'+
    '<tr><td colspan="4" style="padding-top:4px;border-top:1px solid var(--border);"></td></tr>'+
    '<tr><td style="color:#f0a040;">DIF</td><td>'+ D(macd&&macd.dif?macd.dif[i]:null,4) +'</td>'+
    '<td style="color:#5098f0;">DEA</td><td>'+ D(macd&&macd.dea?macd.dea[i]:null,4) +'</td></tr>'+
    '<tr><td style="color:'+(macd&&macd.bar&&macd.bar[i]>=0?CHART_COLORS.up:CHART_COLORS.dn)+';font-weight:600;">BAR</td><td style="color:'+(macd&&macd.bar&&macd.bar[i]>=0?CHART_COLORS.up:CHART_COLORS.dn)+';">'+ D(macd&&macd.bar?macd.bar[i]:null,4) +'</td>'+
    '<td style="color:#a78bfa;">RSI</td><td style="color:#a78bfa;">'+ D(rsi?rsi[i]:null,1) +'</td></tr>'+
    '</table>';
  tip.style.display = 'block';
  var tx = e.clientX - rect.left + 15;
  if (tx + 140 > rect.width) tx = e.clientX - rect.left - 150;
  tip.style.left = tx + 'px';
  tip.style.top = Math.max(0, e.clientY - rect.top - 100) + 'px';
  var ch = document.querySelector('.crosshair') || document.getElementById('crosshair');
  if (ch) { var cx = 10 + i * stepX + stepX/2; ch.setAttribute('x1',cx); ch.setAttribute('x2',cx); ch.setAttribute('opacity','1');
}
}
function hideTooltip() {
  var tip = document.getElementById('chartTooltip'); if (tip) tip.style.display = 'none';
  var ch = document.querySelector('.crosshair') || document.getElementById('crosshair'); if (ch) ch.setAttribute('opacity','0');
}

function toggleChartSize(el) {
  var svg = el.querySelector('svg');
  if (!svg) return;
  var curW = parseInt(svg.getAttribute('width')) || 0;
  // Toggle between normal and 2x width
  if (curW < 500) {
    svg.setAttribute('width', Math.min(curW * 2, 900));
    svg.style.maxWidth = '100%';
  } else {
    svg.setAttribute('width', curW / 2);
    svg.style.maxWidth = '';
  }
}

function renderCompareCard(data, period) {
  document.getElementById('emptyResult').style.display = 'none';
  document.getElementById('resultCard').style.display = 'block';
  document.getElementById('rcTitle').innerHTML = '多股对比 <span class="code">' + data.items.length + '只</span>';
  var pLabels = {daily:'日线', weekly:'周线', monthly:'月线', '1min':'1分', '5min':'5分', '15min':'15分', '30min':'30分', '60min':'60分'};
  document.getElementById('rcPeriod').textContent = pLabels[period] || period;
  document.getElementById('chartContainer').innerHTML = '';

  var tags = '';
  for (var i = 0; i < data.items.length; i++) {
    var item = data.items[i];
    tags += '<span class="meta-tag">' + item.code.replace(/^(SZ|SH)/,'') + ' <span class="val">' + item.name + '</span></span>';
  }
  document.getElementById('rcMeta').innerHTML = tags;

  var rows = '';
  function crow(label, vals, unit, note) {
    unit = unit || ''; note = note || '';
    rows += '<tr><td class="lbl">' + label + '<span class="note">' + note + '</span></td>';
    for (var i = 0; i < vals.length; i++) {
      var v = vals[i];
      if (v !== null && v !== undefined && !isNaN(v)) v = Number(v).toFixed(2);
      else v = '--';
      rows += '<td class="val">' + v + unit + '</td>';
    }
    rows += '</tr>';
  }

  rows += '<tr style="font-weight:700;color:var(--blue);"><td class="lbl">指标</td>';
  for (var i = 0; i < data.items.length; i++) {
    rows += '<td class="val" style="color:var(--blue);">' + data.items[i].code.replace(/^(SZ|SH)/,'') + '</td>';
  }
  rows += '</tr>';

  var names=[], ma5s=[], ma20s=[], difs=[], deas=[], bars=[], rsi6s=[], rsi12s=[], changes=[], vols=[], maxCs=[], minCs=[];
  for (var i = 0; i < data.items.length; i++) {
    var ind=data.items[i].indicators, sum=data.items[i].summary, macd=ind.macd||{};
    names.push(data.items[i].name);
    ma5s.push(ind.ma5); ma20s.push(ind.ma20);
    difs.push(macd.dif); deas.push(macd.dea); bars.push(macd.bar);
    rsi6s.push(ind.rsi_6); rsi12s.push(ind.rsi_12);
    changes.push(sum.period_change); vols.push(sum.avg_volume);
    maxCs.push(sum.max_close); minCs.push(sum.min_close);
  }

  crow('名称', names, '', '');
  crow('数据条数', data.items.map(function(x){return x.count;}), '', '');
  crow('MA5', ma5s, '', '短期趋势');
  crow('MA20', ma20s, '', '中期趋势');
  crow('MACD DIF', difs, '', '快线');
  crow('MACD DEA', deas, '', '慢线');
  crow('MACD BAR', bars, '', '动能柱');
  crow('RSI(6)', rsi6s, '', '超买超卖');
  crow('RSI(12)', rsi12s, '', '中长期');
  crow('涨跌幅', changes, '%', '区间');
  crow('最高', maxCs, '', '');
  crow('最低', minCs, '', '');
  crow('均量', vols.map(function(v){return v?Math.round(v):'--';}), '', '平均成交量');

  // Full mini-charts for each stock
  var chartHtml = '<div style=\"display:flex;flex-direction:column;gap:10px;margin-bottom:12px;\">';
  for (var i = 0; i < data.items.length; i++) {
    var item = data.items[i], kls = item.klines || [];
    if (kls.length < 2) continue;
    var cmpW = Math.max(300, document.getElementById('chartContainer').clientWidth - 80);
    var cmpChart = buildChartSVG(kls, period, cmpW, true, true, true);
    var divId = 'cmpChart_' + i;
    var tipId = 'cmpTip_' + i;
    var jsonData = JSON.stringify(kls).replace(/'/g, '&apos;').replace(/"/g, '&quot;');
    chartHtml += '<div data-klines=\"' + jsonData + '\" data-stepx=\"' + (cmpW/kls.length) + '\" style=\"background:var(--surface);border:1px solid var(--border);border-radius:6px;padding:6px 4px 2px;overflow-x:auto;position:relative;\">';
    chartHtml += '<div id=\"'+tipId+'\" style=\"display:none;position:absolute;background:var(--surface);border:1px solid var(--border2);border-radius:6px;padding:8px 10px;font-size:10px;font-family:var(--font-mono);color:var(--text1);pointer-events:none;z-index:10;box-shadow:0 4px 12px rgba(0,0,0,0.4);white-space:nowrap;line-height:1.7;\"></div>';
    chartHtml += '<div style=\"font-size:10px;font-weight:700;color:var(--text1);padding:0 6px 2px;\">'+item.code.replace(/^(SZ|SH)/,'')+' <span style=\"color:var(--text2);font-weight:400;\">'+item.name+'</span></div>';
    chartHtml += '<div style=\"overflow-x:auto;\">'+cmpChart.html+'</div></div>';
  }
  chartHtml += '</div>';

  document.getElementById('rcIndicators').innerHTML = chartHtml + '<table class="ind-table">' + rows + '</table>';
}

document.addEventListener('keydown', function(e) {
  if (e.key === 'Enter' && e.target.classList.contains('codeInput')) onSearch();
});

// ============================================================
// Result Card
// ============================================================
function renderResultCard(detail) {
  if (!detail) return;
  var meta = detail.meta || {};
  var ind = detail.indicators || {};
  var sum = detail.summary || {};
  var macd = ind.macd || {};
  var boll = ind.boll || {};

  document.getElementById('emptyResult').style.display = 'none';
  document.getElementById('resultCard').style.display = 'block';

  // Title
  var name = meta.name || '--';
  var code = meta.code || '--';
  document.getElementById('rcTitle').innerHTML = name + '<span class="code">' + code + '</span>';

  // Period label
  var pLabels = {daily:'日线', weekly:'周线', monthly:'月线', '1min':'1分钟', '5min':'5分钟', '15min':'15分钟', '30min':'30分钟', '60min':'60分钟'};
  document.getElementById('rcPeriod').textContent = pLabels[meta.period] || meta.period || '';

  // Meta tags
  var tags = '';
  if (meta.market) tags += '<span class="meta-tag">市场: <span class="val">' + meta.market + '</span></span>';
  if (meta.industry && meta.industry !== 'GP-A') tags += '<span class="meta-tag">行业: <span class="val">' + meta.industry + '</span></span>';
  if (meta.pe_ttm !== undefined && meta.pe_ttm > 0)
    tags += '<span class="meta-tag">市盈率(PE): <span class="val">' + meta.pe_ttm.toFixed(2) + '</span></span>';
  if (meta.total_mv !== undefined && meta.total_mv > 0) {
    var mv = meta.total_mv;
    var mvStr = mv >= 1e8 ? (mv/1e8).toFixed(0) + '亿' : (mv/1e4).toFixed(0) + '万';
    tags += '<span class="meta-tag">总市值: <span class="val">' + mvStr + '</span></span>';
  }
  if (meta.start_date) tags += '<span class="meta-tag">数据区间: <span class="val">' + meta.start_date + ' ~ ' + meta.end_date + '</span></span>';
  document.getElementById('rcMeta').innerHTML = tags;

  // Indicator table
  var rows = '';
  function row(label, val, unit, note) {
    unit = unit || '';
    note = note || '';
    var v = '--';
    var cls = '';
    if (val !== null && val !== undefined && !isNaN(val)) {
      v = Number(val).toFixed(2);
    }
    rows += '<tr><td class="lbl">' + label + '</td><td class="val ' + cls + '">' + v + unit + '<span class="note">' + note + '</span></td></tr>';
  }

  // Price
  row('最新收盘价', sum.max_close ? (ind.ma5 || '') : '', '', '最近交易日收盘价');

  // MA
  row('5日均线 (MA5)', ind.ma5, '', '短期趋势参考');
  row('10日均线 (MA10)', ind.ma10, '', '短期趋势参考');
  row('20日均线 (MA20)', ind.ma20, '', '中期趋势参考');
  row('60日均线 (MA60)', ind.ma60, '', '长期趋势参考（季线）');

  // MACD
  row('MACD快线 (DIF)', macd.dif, '', '指数平滑异同平均线 — 快线（12日EMA）');
  row('MACD慢线 (DEA)', macd.dea, '', '指数平滑异同平均线 — 慢线（9日DIF均线）');
  row('MACD柱状线 (BAR)', macd.bar, '', '红柱=多头动能，绿柱=空头动能');

  // RSI
  row('相对强弱指标 RSI(6)', ind.rsi_6, '', '6日RSI — >80超买区，<20超卖区');
  row('相对强弱指标 RSI(12)', ind.rsi_12, '', '12日RSI — 中长期超买超卖判断');

  // BOLL
  row('布林带上轨 (BOLL Upper)', boll.upper, '', '压力位参考 — 价格触及上轨可能回调');
  row('布林带中轨 (BOLL Mid)', boll.mid, '', '20日均线 — 多空平衡位');
  row('布林带下轨 (BOLL Lower)', boll.lower, '', '支撑位参考 — 价格触及下轨可能反弹');

  // Summary
  row('区间涨跌幅', sum.period_change, '%', '选中时间范围内的价格变动百分比');
  row('年化波动率', sum.volatility, '%', '年化标准差 — 衡量风险程度');
  row('区间最高收盘价', sum.max_close, '', '选中范围内最高收盘价');
  row('区间最低收盘价', sum.min_close, '', '选中范围内最低收盘价');
  row('平均成交量', (sum.avg_volume || 0), '手', '选中范围内日均成交量');

  document.getElementById('rcIndicators').innerHTML = rows;
}

// ============================================================
// Card actions
// ============================================================
function onFullAnalyze() {
  if (!window._currentResult) { showToast('请先查询股票数据'); return; }
  var r = window._currentResult;
  // Comparison mode
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
    var ta = document.createElement('textarea'); ta.value = prompt;
    document.body.appendChild(ta); ta.select(); document.execCommand('copy'); document.body.removeChild(ta);
    showToast('对比深度分析提示词已复制！');
    return;
  }
  // Single stock mode
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
  var ta = document.createElement('textarea');
  ta.value = prompt; document.body.appendChild(ta); ta.select();
  document.execCommand('copy'); document.body.removeChild(ta);
  showToast('深度分析提示词已复制！（含完整K线数据）');
}

function onSmartAnalyze() {
  var formula = document.getElementById('formulaInput').value.trim();
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

function onCopyJSON() {
  pywebview.api.copy_last_json().then(function(r) {
    if (r && r.success) showToast('JSON已复制到剪贴板');
    else showToast((r && r.error) || '暂无数据');
  });
}

function onSaveFile() {
  pywebview.api.save_last_to_file().then(function(r) {
    if (r && r.success) {
      showToast('已保存文件: ' + r.filename);
    } else {
      showToast((r && r.error) || '保存失败');
      if (r && r.detail) window._showError('保存失败', r.error + '\n\n' + r.detail);
    }
  });
}

// ============================================================
// ============================================================
// Settings
// ============================================================
function onToggleMonitor() {
  pywebview.api.toggle_clipboard_monitor().then(function(isOn) {
    var el = document.getElementById('clipboardToggle');
    if (isOn) { el.classList.add('on'); }
    else { el.classList.remove('on'); }
    showToast(isOn ? '剪贴板监控已开启 — 复制股票代码即可自动识别' : '剪贴板监控已暂停 — 您仍可手动输入代码查询');
  });
}

function onClearCache() { pywebview.api.clear_cache(); showToast('数据缓存已清空，下次查询将重新拉取最新数据'); }

function onConfigChange(key, value) {
  pywebview.api.set_config(key, value);
  showToast('设置已保存: ' + key);
}

// ============================================================
// Polling
// ============================================================
function refreshHistory() {
  pywebview.api.get_history().then(function(data) {
    var tbody = document.getElementById('historyBody');
    if (!data || data.length === 0) {
      tbody.innerHTML = '<tr class="empty"><td colspan="4">暂无记录 — 查询或复制股票代码后自动显示</td></tr>';
      return;
    }
    var rows = '';
    for (var i = 0; i < data.length; i++) {
      var r = data[i];
      var icons = {success: 'ok', error: 'err', cached: 'cache', pending: 'pend'};
      var labels = {success: '成功', error: '失败', cached: '缓存', pending: '排队中'};
      var cls = 'status-' + (icons[r.status] || 'pend');
      var label = (labels[r.status] || r.status) + ' ' + (r.message || '');
      rows += '<tr><td>' + r.time + '</td><td>' + r.code + '</td><td>' + (r.name || '-') + '</td><td class="' + cls + '">' + label + '</td></tr>';
    }
    tbody.innerHTML = rows;
  });
}

function refreshStatus() {
  var dot = document.getElementById('statusDot');
  dot.className = 'status-dot on';
  document.getElementById('statusText').textContent = 'stock-api ready | 输入代码查询';
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
// Init
// ============================================================
// ============================================================
// Adaptive polling — adjusts interval based on state
// ============================================================
(function() {
  var FAST = 400, NORMAL = 3000, SLOW = 10000;
  var _interval = NORMAL;
  var _timer = null;
  var _lastHistory = '';

  function poll() {
    if (typeof pywebview === 'undefined' || !pywebview.api) { _timer = setTimeout(poll, 200); return; }
    // Batch: refresh both in one rAF
    var doRefresh = function() {
      refreshStatus();
      // Skip history if data unchanged
      pywebview.api.get_history().then(function(data) {
        var key = JSON.stringify(data);
        if (key !== _lastHistory) {
          _lastHistory = key;
          var tbody = document.getElementById('historyBody');
          if (!data || data.length === 0) {
            tbody.innerHTML = '<tr class="empty"><td colspan="4">暂无记录</td></tr>';
            return;
          }
          var rows = '';
          for (var i = 0; i < data.length; i++) {
            var r = data[i];
            var icons = {success: 'ok', error: 'err', cached: 'cache', pending: 'pend'};
            var labels = {success: '成功', error: '失败', cached: '缓存', pending: '排队中'};
            var cls = 'status-' + (icons[r.status] || 'pend');
            rows += '<tr><td>' + r.time + '</td><td>' + r.code + '</td><td>' + (r.name || '-') + '</td><td class="' + cls + '">' + (labels[r.status] || r.status) + ' ' + (r.message || '') + '</td></tr>';
          }
          tbody.innerHTML = rows;
        }
      });
      if (!window._pollFast) {
        pywebview.api.get_last_result_detail().then(function(detail) {
          if (detail && detail.meta && detail.meta.code) {
            window._currentResult = detail;
            renderResultCard(detail);
          }
        });
      }
    };

    window.requestAnimationFrame(doRefresh);

    // Adaptive: fast when polling result, slow when hidden
    var next = window._pollFast ? FAST :
               (document.hidden ? SLOW : NORMAL);
    if (next !== _interval) { _interval = next; }
    _timer = setTimeout(poll, _interval);
  }

  // Visibility change → adjust interval immediately
  document.addEventListener('visibilitychange', function() {
    if (!document.hidden) {
      _interval = window._pollFast ? FAST : NORMAL;
      clearTimeout(_timer);
      _timer = setTimeout(poll, 100);
    }
  });

  // Start
  // Delay first poll until pywebview is likely ready
  _timer = setTimeout(poll, 800);
})();

// Safe API caller — waits for pywebview to be ready
function _api(method) {
  return function() {
    var args = arguments;
    if (typeof pywebview === 'undefined' || !pywebview.api) {
      return Promise.reject(new Error('pywebview not ready'));
    }
    return pywebview.api[method].apply(pywebview.api, args);
  };
}

(function init() {
  function _ready(cb, retries) {
    retries = retries || 0;
    if (typeof pywebview !== 'undefined' && pywebview.api) { cb(); return; }
    if (retries > 50) return; // give up after 5s
    setTimeout(function() { _ready(cb, retries + 1); }, 100);
  }
  _ready(function() {
    loadConfig();
    refreshHistory();
    refreshStatus();
    pywebview.api.get_last_result_detail().then(function(detail) {
      if (detail && detail.meta && detail.meta.code) { window._currentResult = detail; renderResultCard(detail); }
    });
  });
  setTimeout(function() { var inp = document.querySelector('.codeInput'); if (inp) inp.focus(); }, 400);
})();

// ============================================================
</script>
</body>
</html>
"""


# ============================================================
# Python-side API exposed to JS
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

    def generate_prompt(self, formula_text: str) -> Dict[str, Any]:
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
            title="Stock JSON Clipper V3.0",
            html=PANEL_HTML,
            width=560,
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
