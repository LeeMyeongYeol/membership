/* ====== 설정 ====== */
const API_BASE = "http://127.0.0.1:8000";
const TMDB_API_KEY_FRONT = "ddd654eb8622a67e04f93f613653426d"; // TMDb 프론트 키(유사작/백엔드 실패 시)

/* ====== 카테고리 ====== */
const GENRES=["Action (액션)","Adventure (모험)","Animation (애니메이션)","Comedy (코미디)","Crime (범죄)","Drama (드라마)","Fantasy (판타지)","Historical (사극/역사)","Horror (공포)","Musical (뮤지컬)","Mystery (미스터리)","Romance (로맨스)","Sci-Fi (SF / 공상과학)","Thriller (스릴러)","War (전쟁)","Western (서부극)","Documentary (다큐멘터리)","Family (가족)","Biography (전기)","Sport (스포츠)"];
const REGIONS=["한국영화","해외영화","일본영화","중국영화","프랑스영화","OTT 전용 영화"];
const THEMES=["Now Playing (현재 상영작)","Upcoming (개봉 예정작)","Top Rated (평점 높은 순)","Popular (인기순)","Classic (고전 명작)","Indie (독립영화)","Short Film (단편영화)","LGBTQ+","Noir / Neo-noir","Superhero (히어로)","Time Travel / Space / Cyberpunk","Zombie / Monster / Disaster"];

/* ====== DOM ====== */
const openBtn=document.getElementById("openBtn");
const closeBtn=document.getElementById("closeBtn");
const clearAllBtn=document.getElementById("clearAllBtn");
const panel=document.getElementById("panel");
const tokenList=document.getElementById("tokenList");
const queryInput=document.getElementById("query");
const chipsGenre=document.getElementById("chipsGenre");
const chipsRegion=document.getElementById("chipsRegion");
const chipsTheme=document.getElementById("chipsTheme");
const gridEl=document.getElementById("movie-list");
const statusEl=document.getElementById("status");
const sentinel=document.getElementById("sentinel");
const selNamesCount=document.getElementById("selNamesCount");
const selNameChips=document.getElementById("selNameChips");
const clearSelBtnTop=document.getElementById("clearSelBtnTop");
const selCountEl=document.getElementById("selCount");
const recommendBtn=document.getElementById("recommendBtn");
const clearSelBtnBottom=document.getElementById("clearSelBtnBottom");

/* ====== 상태 ====== */
let tokens=[]; let currentItems=[]; let selected=[];
let loading=false; let noMore=false;
let mode="popular";              // "popular" | "discover" | "search"
let queryState={ q:"", lang:"", page:1 };

const REGION_LANG={ "한국영화":"ko","해외영화":"en","일본영화":"ja","중국영화":"zh","프랑스영화":"fr" };

/* ====== 유틸 ====== */
function keyOf(item){ if(item.source==="TMDb" && item.id) return `tmdb:${item.id}`; const t=(item.title||"").toLowerCase(); return `title:${t}|${item.year||""}`; }
function isSelected(item){ return selected.some(s=> keyOf(s)===keyOf(item)); }
function posterUrl(path){ return path ? `https://image.tmdb.org/t/p/w500${path}` : ""; }

/* ====== 선택 이름칩 ====== */
function renderSelectedNames(){
  selNameChips.innerHTML="";
  for(const s of selected){
    const chip=document.createElement("span");
    chip.className="name-chip";
    chip.title=s.title||"";
    chip.innerHTML=`<span class="nm">${s.title||"(제목 없음)"}</span>`;
    const x=document.createElement("button");
    x.className="x"; x.textContent="✕";
    x.onclick=()=>{
      selected = selected.filter(v=> keyOf(v)!==keyOf(s));
      renderSelectionBar();
      renderPosters(currentItems,true); // 카드 테두리 갱신
      renderSelectedNames();
    };
    chip.appendChild(x);
    selNameChips.appendChild(chip);
  }
  selNamesCount.textContent=`${selected.length}/10`;
}

/* ====== 하단 바 ====== */
function renderSelectionBar(){
  selCountEl.textContent=String(selected.length);
  recommendBtn.disabled = selected.length===0;
}

/* ====== 선택 토글(카드 클릭만, 숨기지 않음) ====== */
function setSelected(item,on,cardEl){
  const k=keyOf(item);
  const exists=isSelected(item);
  if(on && !exists){
    if(selected.length>=10){ alert("최대 10개까지 선택할 수 있어요."); return false; }
    selected.push(item);
    cardEl?.classList.add("selected");  // ✅ 흰 테두리만
  }
  if(!on && exists){
    selected = selected.filter(s=> keyOf(s)!==k);
    cardEl?.classList.remove("selected");
  }
  renderSelectionBar();
  renderSelectedNames();
  return true;
}

/* ====== 카드 렌더 ====== */
function renderPosters(items, onlyUpdateSelection=false){
  if(!onlyUpdateSelection) gridEl.innerHTML="";
  const frag=document.createDocumentFragment();
  for(const m of items){
    const card=document.createElement("div");
    card.className="card";
    if(isSelected(m)) card.classList.add("selected"); // ✅ 포스터는 그대로, 흰 테두리만

    const img=document.createElement("img"); img.className="thumb"; img.alt=m.title; img.src=m.poster||"";
    const meta=document.createElement("div"); meta.className="meta";
    const title=document.createElement("div"); title.className="title"; title.textContent=m.title||"(제목 없음)";
    const badge=document.createElement("span"); badge.className="badge"; badge.textContent=m.source||"";
    const sub=document.createElement("div"); sub.className="sub"; sub.textContent=m.year||"";
    title.appendChild(badge); meta.append(title, sub);

    card.addEventListener("click",()=>{ const want=!isSelected(m); setSelected(m,want,card); });
    card.append(img,meta);
    frag.appendChild(card);
  }
  if(!onlyUpdateSelection) gridEl.appendChild(frag);
}

/* ====== API ====== */
async function apiGet(path,params={}){ const usp=new URLSearchParams(params); const r=await fetch(`${API_BASE}${path}?${usp}`); if(!r.ok) throw new Error(await r.text()); return r.json(); }
async function fetchPopularBackend(pageNum=1){ const {items}=await apiGet("/api/popular",{page:pageNum}); return items||[]; }
async function fetchPopularFront(pageNum=1){
  if(!TMDB_API_KEY_FRONT) throw new Error("No TMDb front key");
  const url=`https://api.themoviedb.org/3/movie/popular?api_key=${encodeURIComponent(TMDB_API_KEY_FRONT)}&language=ko-KR&region=KR&page=${pageNum}`;
  const r=await fetch(url); if(!r.ok) throw new Error("TMDb popular failed");
  const j=await r.json();
  return (j.results||[]).map(n=>({title:n.title||n.name||"",year:(n.release_date||n.first_air_date||"").slice(0,4),poster:posterUrl(n.poster_path),source:"TMDb",id:n.id}));
}

/* ====== 모드 공통 페치 ====== */
async function fetchByMode(page){
  if(mode==="popular"){
    try { return await fetchPopularBackend(page); }
    catch { return await fetchPopularFront(page); }
  } else if(mode==="discover"){
    const {items}=await apiGet("/api/discover/lang",{ lang:queryState.lang, page });
    return items||[];
  } else { // "search"
    const {items}=await apiGet("/api/search",{ q:queryState.q, source:"both", page });
    return items||[];
  }
}

/* ====== discover 필터 ====== */
function filterDiscover(list, extrasLower, textLower){
  if(!extrasLower.length && !textLower) return list;
  return list.filter(m=>{
    const title=(m.title||"").toLowerCase();
    const okExtra = extrasLower.every(k=> title.includes(k.split(" ")[0]));
    const okText  = textLower? title.includes(textLower): true;
    return okExtra && okText;
  });
}

/* ====== 최소 4개(한 줄) 보장 페치 ====== */
async function fetchAtLeastFour({firstPageUsed=false}={}){
  let acc=[]; let guard=0;
  while(acc.length < 4 && guard < 6 && !noMore){
    const batch = await fetchByMode(queryState.page);
    if(!batch.length){ noMore=true; break; }

    let list = batch;
    if(mode==="discover"){
      const extras=tokens.filter(t=>!REGION_LANG[t]).map(s=>s.toLowerCase());
      const text=(queryInput.value||"").trim().toLowerCase();
      list = filterDiscover(batch, extras, text);
    }

    acc.push(...list);
    queryState.page += 1;
    guard += 1;
  }
  return acc;
}

/* ====== 추천(유사작) – 투명 오버레이 없음 ====== */
const POSTER_BASE="https://image.tmdb.org/t/p/w500";
async function tmdbSimilarIds(tmdbId){
  const url=`https://api.themoviedb.org/3/movie/${tmdbId}/similar?api_key=${encodeURIComponent(TMDB_API_KEY_FRONT)}&language=ko-KR&page=1`;
  const r=await fetch(url); if(!r.ok) throw new Error("TMDb similar fail");
  const data=await r.json();
  return (data.results||[]).map(n=>({title:n.title||n.name||"",year:(n.release_date||n.first_air_date||"").slice(0,4),poster:n.poster_path?(POSTER_BASE+n.poster_path):"",source:"TMDb",id:n.id,tmdbId:n.id,popularity:n.popularity||0}));
}
function dedup(items){ const seen=new Set(), out=[]; for(const m of items){ const k=m.tmdbId?`tmdb:${m.tmdbId}`:keyOf(m); if(seen.has(k)) continue; seen.add(k); out.push(m);} return out; }
async function recommendSimilar(){
  if(selected.length===0) return;
  statusEl.textContent="비슷한 영화 불러오는 중…";
  const bag=[];
  for(const base of selected){ try{ const tid=base.id; if(!tid) continue; const sims=await tmdbSimilarIds(tid); bag.push(...sims);}catch(e){ console.warn("similar fail",e);} }
  const exclude=new Set(selected.map(keyOf));
  let cands=bag.filter(m=>!exclude.has(keyOf(m)));
  const score=new Map();
  for(const m of cands){ const k=`tmdb:${m.tmdbId||m.id||m.title}`; const prev=score.get(k)||{item:m,count:0,pop:0}; prev.count+=1; prev.pop=Math.max(prev.pop,m.popularity||0); score.set(k,prev); }
  const ranked=[...score.values()].sort((a,b)=>(b.count-a.count)||(b.pop-a.pop)).map(x=>x.item);
  currentItems=dedup(ranked).slice(0,40);
  statusEl.textContent=`추천 결과 ${currentItems.length}개`;
  renderPosters(currentItems);
}

/* ====== 태그/칩 ====== */
function appendToken(text){ const t=(text||"").trim(); if(!t) return; if(!tokens.includes(t)){ tokens.push(t); renderTokens(); performSearch(false); } queryInput.focus(); }
function renderTokens(){
  tokenList.innerHTML="";
  tokens.forEach((t,i)=>{ const chip=document.createElement("span"); chip.className="token-chip";
    const label=document.createElement("span"); label.textContent=t;
    const x=document.createElement("button"); x.innerHTML="✕";
    x.onclick=()=>{ tokens.splice(i,1); renderTokens(); performSearch(false); };
    chip.append(label,x); tokenList.appendChild(chip); });
}
function renderChips(container,list){ container.innerHTML=""; list.forEach(name=>{ const b=document.createElement("button"); b.className="chip"; b.textContent=name; b.onclick=()=>appendToken(name); container.appendChild(b); }); }
const pickedRegion=()=> tokens.find(t=>REGION_LANG[t])||null;
const freeText=()=> (queryInput.value||"").trim();

/* ====== 검색 ====== */
async function performSearch(closeAfter=false){
  const regionToken=pickedRegion(); const text=freeText(); let out=[];
  try{
    if(regionToken){
      mode="discover"; queryState={ q:"", lang:REGION_LANG[regionToken], page:1 };
      statusEl.textContent=`${regionToken} 불러오는 중…`;
      const {items:first} = await apiGet("/api/discover/lang",{ lang:queryState.lang, page:queryState.page });
      out = first || [];
      const extras=tokens.filter(t=>!REGION_LANG[t]).map(s=>s.toLowerCase());
      const tLower=text.toLowerCase();
      out = filterDiscover(out, extras, tLower);
      queryState.page = 2;

      if(out.length < 4){
        const more = await fetchAtLeastFour({firstPageUsed:true});
        out = [...out, ...more];
      }
    } else {
      const combined=[...tokens, text].filter(Boolean).join(" ").trim();
      if(combined){
        mode="search"; queryState={ q:combined, lang:"", page:1 };
        statusEl.textContent=`"${combined}" 검색 중…`;
        const {items:first} = await apiGet("/api/search",{ q:queryState.q, source:"both", page:queryState.page });
        out = first || [];
        queryState.page = 2;

        if(out.length < 4){
          const more = await fetchAtLeastFour({firstPageUsed:true});
          out = [...out, ...more];
        }
      } else {
        mode="popular"; queryState={ q:"", lang:"", page:1 };
        out = await fetchAtLeastFour({firstPageUsed:false}); // 인기작도 최소 4개
      }
    }

    currentItems = out;
    gridEl.innerHTML=""; renderPosters(currentItems);
    statusEl.textContent = `${currentItems.length}개 결과`;
    noMore=false;
    if(closeAfter) panel.hidden=true;
  }catch(e){ console.error(e); statusEl.textContent="검색 중 오류가 발생했습니다."; }
}

/* ====== 무한 스크롤: 최소 4개 이상씩 추가 ====== */
const io=new IntersectionObserver(async (entries)=>{
  const entry=entries[0];
  if(!entry.isIntersecting || loading || noMore) return;
  loading=true;
  try{
    const chunk = await fetchAtLeastFour({firstPageUsed:false});
    if(chunk.length===0){ noMore=true; }
    else{
      currentItems=[...currentItems, ...chunk];
      renderPosters(chunk); // append
      statusEl.textContent=`${currentItems.length}개 결과`;
    }
  }catch(e){ console.error(e); noMore=true; }
  finally{ loading=false; }
});
io.observe(sentinel);

/* ====== 이벤트 ====== */
recommendBtn.onclick=recommendSimilar;
openBtn.onclick=()=>{ panel.hidden=!panel.hidden; if(!panel.hidden){ setTimeout(()=>queryInput.focus(),0);} };
closeBtn.onclick=()=> panel.hidden=true;
clearAllBtn.onclick=()=>{ tokens=[]; renderTokens(); performSearch(false); };
queryInput.addEventListener("input",()=>performSearch(false));
queryInput.addEventListener("keydown", async (e)=>{
  if(e.key==="Backspace" && !queryInput.value && tokens.length){ tokens.pop(); renderTokens(); performSearch(false); }
  if(e.key==="Enter"){ e.preventDefault(); await performSearch(true); } // Enter로만 닫힘
});
clearSelBtnTop.onclick=clearAllSelected;
clearSelBtnBottom.onclick=clearAllSelected;
function clearAllSelected(){ selected=[]; renderSelectedNames(); renderSelectionBar(); renderPosters(currentItems,true); }

/* ====== 초기화 ====== */
(function init(){
  renderChips(chipsGenre,GENRES); renderChips(chipsRegion,REGIONS); renderChips(chipsTheme,THEMES);
  renderTokens(); renderSelectedNames(); renderSelectionBar();
  mode="popular"; queryState={ q:"", lang:"", page:1 }; noMore=false;
  fetchAtLeastFour({firstPageUsed:false}).then(list=>{
    currentItems = list;
    renderPosters(currentItems);
    statusEl.textContent = `${currentItems.length}개 결과`;
  });
})();
