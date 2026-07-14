(function coordinateHomeIntelligence(){
  "use strict";

  const grid=document.getElementById("homeIntelligenceGrid");
  if(!grid)return;

  const selectors=[
    "#weeklyHomeBanner",
    "#patternHome",
    "#tacticalIdentityEntry",
    "#decisionEngineEntry",
    ".club-intelligence-entry"
  ];

  function collectCards(){
    selectors.forEach(selector=>{
      const card=document.querySelector(selector);
      if(card&&card.parentElement!==grid)grid.appendChild(card);
    });
  }

  collectCards();
  const observer=new MutationObserver(collectCards);
  observer.observe(document.body,{childList:true,subtree:true});
})();
