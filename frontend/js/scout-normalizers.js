/*
    MatchIQ Scout - Normalizers Module
    Normalizzazione player/eventi e calcoli frontend scout.
*/

function normalizePlayers(players=[]){
  if(!Array.isArray(players)) return [];

  return players
    .filter(p => p && (p.name || p.player_name || p.player?.name))
    .map((p,i) => {
      const rawName = p.name || p.player_name || p.player?.name || `Player ${i+1}`;
      const rawTeam = typeof p.team === "string" ? p.team : (p.team?.name || p.team_name || p.club || "Team");
      const rawRole = p.role || p.position || p.pos || "MID";

      const scoutScore = clamp(num(p.scout_score ?? p.scoutScore ?? p.score ?? p.rating_score ?? 0),0,99);
      const rating = clamp(num(p.rating ?? p.rating_api ?? 6.5),0,10);

      let threat = num(p.threat ?? p.xThreat ?? p.x_threat ?? p.xthreat ?? p.danger ?? p.danger_score ?? p.offensive_danger,0);
      let creativity = num(p.creativity ?? p.creative_score ?? p.creativeScore ?? p.chance_creation ?? p.keyPassImpact,0);
      let pressure = num(p.pressure ?? p.pressure_score ?? p.pressing ?? p.aggression ?? p.defensive_pressure,0);
      let momentum = num(p.momentum ?? p.momentum_score ?? p.form,0);
      let fatigue = num(p.fatigue ?? p.fatigue_score ?? p.tiredness,0);
      let stamina = num(p.stamina,0);
      let impactScore = num(p.impact_score ?? p.impact ?? p.live_impact ?? p.impactScore,0);

      const goals = intNum(p.goals);
      const assists = intNum(p.assists);
      const shots = intNum(p.shots ?? p.shots_total);
      const shotsOnTarget = intNum(p.shots_on_target ?? p.shots_on);
      const keyPasses = intNum(p.key_passes ?? p.keyPasses);
      const dribbles = intNum(p.dribbles ?? p.dribbles_success);
      const tackles = intNum(p.tackles);
      const interceptions = intNum(p.interceptions);
      const duelsWon = intNum(p.duels_won);
      const minutes = intNum(p.minutes);

      const roleValue = cleanRole(rawRole);

      if(threat <= 0){
        threat = calcThreatFrontend(roleValue, shots, shotsOnTarget, goals, keyPasses, dribbles, rating);
      }

      if(creativity <= 0){
        creativity = calcCreativityFrontend(roleValue, keyPasses, assists, dribbles, rating);
      }

      if(pressure <= 0){
        pressure = calcPressureFrontend(roleValue, tackles, interceptions, duelsWon, rating);
      }

      if(momentum <= 0){
        momentum = clamp(rating * 7 + threat * .22 + creativity * .16 + pressure * .10 + goals * 12 + assists * 8,1,99);
      }

      if(fatigue <= 0){
        const matchMinute = getMatch()?.minute || 60;
        fatigue = clamp((minutes || matchMinute) * .45 + pressure * .10 + dribbles * 1.3 + tackles * 1.7,8,94);
      }

      if(stamina <= 0){
        stamina = clamp(100 - fatigue,1,100);
      }

      if(impactScore <= 0){
        impactScore = clamp(scoutScore * .28 + threat * .22 + creativity * .16 + pressure * .10 + momentum * .16 + stamina * .08 + goals * 7 + assists * 5,1,99);
      }

      const clean = {
        id:String(p.id || p.player_id || p.player?.id || `${rawName}_${i}`),
        name:cleanText(rawName),
        photo:cleanText(p.photo || p.player?.photo || "",""),
        team:cleanText(rawTeam,"Team"),
        role:roleValue,
        rating,

        goals,
        assists,
        shots,
        shots_on_target:shotsOnTarget,
        key_passes:keyPasses,
        dribbles,
        tackles,
        interceptions,
        fouls:intNum(p.fouls),
        duels_won:duelsWon,
        minutes,

        threat:clamp(threat,1,99),
        creativity:clamp(creativity,1,99),
        pressure:clamp(pressure,1,99),
        momentum:clamp(momentum,1,99),
        fatigue:clamp(fatigue,1,99),
        stamina:clamp(stamina,1,100),
        scout_score:scoutScore > 0
          ? scoutScore
          : clamp(rating*8 + threat*.20 + creativity*.18 + pressure*.10 + momentum*.24 + stamina*.08 + goals*8 + assists*5,1,99),
        impact_score:clamp(impactScore,1,99),

        signal_type:cleanText(p.signal_type || p.signalType || guessSignalFrontend(threat,creativity,pressure,impactScore),"watch"),
        signal:cleanText(p.signal || p.ai_signal || guessSignalLabelFrontend(threat,creativity,pressure,impactScore),"AI Watch"),
        level:cleanText(p.level || "DEVELOPING"),
        data_quality:cleanText(p.data_quality || "frontend-normalized"),
        data_source:cleanText(p.data_source || "frontend_mapping"),
        is_estimated:Boolean(p.is_estimated),
        real_data:Boolean(p.real_data),
        danger_creator:Boolean(p.danger_creator),
        hidden_gem:Boolean(p.hidden_gem),
        ai_summary:cleanText(p.ai_summary || "")
      };

      return clean;
    })
    .sort((a,b) => b.scout_score - a.scout_score);
}

function calcThreatFrontend(role, shots, shotsOnTarget, goals, keyPasses, dribbles, rating){
  const base = {ATT:34,MID:26,DEF:12,GK:4}[role] || 20;
  return clamp(base + shots*7 + shotsOnTarget*12 + goals*24 + keyPasses*4 + dribbles*4 + Math.max(0,rating-6)*5,1,99);
}

function calcCreativityFrontend(role, keyPasses, assists, dribbles, rating){
  const base = {ATT:24,MID:38,DEF:16,GK:4}[role] || 22;
  return clamp(base + keyPasses*12 + assists*25 + dribbles*6 + Math.max(0,rating-6)*4,1,99);
}

function calcPressureFrontend(role, tackles, interceptions, duelsWon, rating){
  const base = {ATT:20,MID:34,DEF:44,GK:8}[role] || 28;
  return clamp(base + tackles*9 + interceptions*9 + duelsWon*5 + Math.max(0,rating-6)*3,1,99);
}

function guessSignalFrontend(threat,creativity,pressure,impact){
  if(impact >= 84) return "hot";
  if(threat >= 78) return "danger";
  if(pressure >= 78) return "pressure";
  if(creativity >= 76) return "gem";
  return "watch";
}

function guessSignalLabelFrontend(threat,creativity,pressure,impact){
  const t = guessSignalFrontend(threat,creativity,pressure,impact);

  if(t === "hot") return "Hot Player";
  if(t === "danger") return "High Threat Zone";
  if(t === "pressure") return "Pressure Trigger";
  if(t === "gem") return "Creative Hidden Gem";

  return "AI Watch";
}

function normalizeEvents(events){
  if(!Array.isArray(events)) return [];

  return events.map(e => ({
    id:String(e.id || uid()),
    minute:intNum(e.minute),
    type:cleanText(e.type || "ai"),
    label:cleanText(e.label || String(e.type || "AI").toUpperCase()),
    className:cleanText(e.className || eventClass(e.type)),
    playerId:e.playerId || e.player_id || "",
    playerName:cleanText(e.playerName || e.player_name || "Player"),
    title:cleanText(e.title || e.event || "Evento live"),
    desc:cleanText(e.desc || e.description || "Evento rilevato da MatchIQ AI.")
  }));
}

function eventClass(type){
  const t = String(type || "").toLowerCase();

  if(t.includes("goal")) return "goal";
  if(t.includes("chance") || t.includes("alert")) return "alert";
  if(t.includes("momentum") || t.includes("pressure")) return "momentum";

  return "";
}

function buildLocalSummary(players){
  return {
    total_players:players.length,
    avg_scout_score:avgField(players,"scout_score"),
    avg_threat:avgField(players,"threat"),
    avg_creativity:avgField(players,"creativity"),
    avg_pressure:avgField(players,"pressure"),
    avg_momentum:avgField(players,"momentum"),
    avg_stamina:avgField(players,"stamina")
  };
}