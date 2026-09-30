#!/usr/bin/env python3
"""Generate M2 documents: 10 contract PDFs + 10 scout transcripts, into data/."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_pdf import write_pdf

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CDIR = os.path.join(ROOT, "data", "contracts")
TDIR = os.path.join(ROOT, "data", "transcripts")
os.makedirs(CDIR, exist_ok=True)
os.makedirs(TDIR, exist_ok=True)

# player_id, name, nationality, position, club, start, end, wage(EURm), release(EURm), tier, transfer_status, ref
CONTRACTS = [
 ("p_saka","Bukayo Saka","England","Right Winger (RW)","Acme Sports FC","1 July 2023","30 June 2027",12,180,"First Team","Not For Sale","AS-CTR-SAKA-2023"),
 ("p_rice","Declan Rice","England","Defensive Midfielder (DM)","Acme Sports FC","1 July 2023","30 June 2028",14,200,"First Team","Not For Sale","AS-CTR-RICE-2023"),
 ("p_saliba","William Saliba","France","Centre Back (CB)","Acme Sports FC","1 July 2024","30 June 2027",9.5,150,"First Team","Not For Sale","AS-CTR-SALI-2024"),
 ("p_odegaard","Martin Odegaard","Norway","Attacking Midfielder (AM)","Acme Sports FC","1 July 2023","30 June 2028",11,160,"First Team","Not For Sale","AS-CTR-ODEG-2023"),
 ("p_gabriel","Gabriel Magalhaes","Brazil","Centre Back (CB)","Acme Sports FC","1 July 2022","30 June 2027",9,120,"First Team","Not For Sale","AS-CTR-GABR-2022"),
 ("p_raya","David Raya","Spain","Goalkeeper (GK)","Acme Sports FC","1 July 2024","30 June 2028",7.5,80,"First Team","Not For Sale","AS-CTR-RAYA-2024"),
 # targets — current-club contracts (release clause is the transfer lever)
 ("p_roque","Vitor Roque","Brazil","Striker (ST)","Palmeiras","1 January 2025","31 December 2029",4.5,60,"Target","Monitoring","PAL-CTR-ROQU-2025"),
 ("p_alvarez","Julian Alvarez","Argentina","Striker (ST)","Atletico Madrid","1 August 2024","30 June 2028",12,120,"Target","Monitoring","ATM-CTR-ALVA-2024"),
 ("p_olise","Michael Olise","France","Right Winger (RW)","Bayern Munich","1 July 2024","30 June 2029",10,90,"Target","Monitoring","FCB-CTR-OLIS-2024"),
 ("p_tonali","Sandro Tonali","Italy","Defensive Midfielder (DM)","Newcastle United","1 July 2023","30 June 2028",9,70,"Target","Monitoring","NEW-CTR-TONA-2023"),
]

for pid,name,nat,pos,club,start,end,wage,rel,tier,tstatus,ref in CONTRACTS:
    lines = [
     ("H2","PROFESSIONAL PLAYING CONTRACT"),("SP",""),
     ("P",f"This Professional Playing Contract is made between {club} (\"the Club\") and the Player named below, governing the terms of employment and registration."),("SP",""),
     ("H2","1. PARTIES"),
     ("P",f"Player Name: {name}"),("P",f"Player ID: {pid}"),
     ("P",f"Nationality: {nat}"),("P",f"Primary Position: {pos}"),("SP",""),
     ("H2","2. TERM OF AGREEMENT"),
     ("P",f"Contract Start Date: {start}"),("P",f"Contract End Date: {end}"),
     ("P","This agreement remains in force until the Contract End Date unless terminated or extended in accordance with the clauses herein."),("SP",""),
     ("H2","3. REMUNERATION"),
     ("P",f"Basic Wage: EUR {wage:,.0f},000,000 per year, payable in equal monthly instalments." if wage==int(wage) else f"Basic Wage: EUR {wage} million per year, payable in equal monthly instalments."),
     ("P","Performance bonuses apply per the Club bonus schedule (Appendix A)."),("SP",""),
     ("H2","4. RELEASE CLAUSE"),
     ("P",f"The Player shall be subject to a fixed release clause of EUR {rel},000,000 (EUR {rel} million). Any club meeting this amount in a single written offer may open negotiations with the Player directly."),("SP",""),
     ("H2","5. TIER & STATUS"),
     ("P",f"Squad Tier: {tier}"),("P",f"Transfer Status: {tstatus}"),("SP",""),
     ("P",f"Signed on behalf of {club}. Document reference {ref}. Last updated 12 August 2025."),
    ]
    fn = os.path.join(CDIR, f"contract_{pid.replace('p_','')}.pdf")
    write_pdf(fn, f"{club} - Player Contract", lines)
    print("PDF ", os.path.basename(fn))

# scout transcripts — (filename stem, player, id, scout, date, fixture, minutes, status, body)
TRANSCRIPTS = [
 ("roque","Vitor Roque","p_roque","Marco Bianchi","2025-07-28","Serie A friendly vs Boca Juniors","72","Priority",
  "Right, note on Vitor Roque. Explosive number nine, lives on the last shoulder, and his first five yards are frightening. Two goals today, both from pure penalty-box instinct — reacts to loose balls quicker than anyone on the pitch. Pressing is relentless, sets the tone from the front. Where he needs work is link play: he can be wasteful with his back to goal and his hold-up game is raw. At twenty he's got time. System fit is strong for a vertical, transition-heavy attack, which is us. His release situation is favourable and at a sixty-million clause this is genuine value for a striker of this ceiling. Recommendation: priority target, move early before his price climbs."),
 ("barcola","Bradley Barcola","p_barcola","James Okafor","2025-08-02","Ligue 1 opener vs Lille","90","Active",
  "Bradley Barcola. Direct, frightening pace, genuine one-v-one threat off the left. When he commits the full-back he usually wins. End product has improved — a goal and an assist tonight. The knock is decision-making: he'll take the wrong option in the final third, shoot when the pass is on. Defensively willing but positionally naive. High ceiling, and he'd give us verticality we lack. Price is the concern — it'll be steep and Paris don't need to sell. Monitor and revisit in the winter."),
 ("olise","Michael Olise","p_olise","James Okafor","2025-08-05","Bundesliga vs Leipzig","85","Priority",
  "Michael Olise, and this one's easy. Elite creator from the right, both feet, set-piece value on top. He plays with his head up, always a picture in mind, and his weight of pass into the box is the best I've seen this season. Two assists and a wonderful free-kick. The only flag is durability — the injury history is real and worth a medical deep-dive. Tactically he's a perfect fit for an inside-forward role in our shape. He won't be cheap, premium fee territory, but for this quality I'd sanction it. Top of the wide-forward list."),
 ("alvarez","Julian Alvarez","p_alvarez","Marco Bianchi","2025-07-30","La Liga vs Real Sociedad","90","Monitoring",
  "Julian Alvarez. Relentless, and tactically the most intelligent forward on our lists. Two-footed finisher, drops to link, presses like a demon, and never hides. Scored a poacher's goal and made another with a clever reverse pass. Honestly there's very little to critique in his game. The issue is entirely off the pitch: he's expensive, the contract is long and well-protected, and Atletico have no reason to deal. Fit is excellent but feasibility is low. Keep monitoring, but temper expectations on availability."),
 ("rogers","Morgan Rogers","p_rogers","Priya Nair","2025-08-08","Premier League vs Brighton","90","Active",
  "Morgan Rogers. Big, powerful ball-carrier who glides through the half-spaces and draws fouls in dangerous areas. He's grown into a real Premier League player. End-product efficiency is up this season — a goal tonight and several chances created. Needs to sharpen his final ball under pressure and his defensive tracking can switch off. Good value now but the fee is rising fast with every good performance. Fit is strong as a left-sided eight or ten. Recommend we make a decision this window rather than wait."),
 ("brown","Nathaniel Brown","p_brown","Tomasz Kowalski","2025-08-06","Bundesliga vs Wolfsburg","90","Monitoring",
  "Nathaniel Brown, left-back. Athletic, modern full-back profile — big engine, gets up and down, and his overlapping runs stretch the pitch. Delivery is decent. Defensively he's raw: gets caught upfield, and his one-v-one defending needs coaching. But he's affordable, and as a depth option and project at left-back he makes sense. Not a starter for us yet. Recommendation: monitor, revisit as a value depth signing if our first choice moves on."),
 ("tonali","Sandro Tonali","p_tonali","Tomasz Kowalski","2025-08-09","Premier League vs Fulham","78","Active",
  "Sandro Tonali. Deep-lying orchestrator, and his range of passing is a genuine weapon — switches play, breaks lines, dictates tempo. Composed under the press, exactly the profile for our build-out from the back. He needs consistent minutes to hit top rhythm, and there are stamina questions late in games. Newcastle value him highly. Fit is excellent as a controlling six or left-sided eight. Recommend opening informal talks to understand his availability."),
 ("dowman","Max Dowman","p_dowman","Priya Nair","2025-08-11","U18 Premier League vs Chelsea","65","Active",
  "Max Dowman, and I'll say it plainly: generational. Fifteen years old and utterly fearless — takes players on in his own third, wins fouls, never intimidated. Technically off the charts, both feet, low centre of gravity. Obviously we manage minutes and load carefully at his age, and physically he'll fill out over the next two seasons. Long-term first-team projection is genuine. This is a talent to protect and develop internally, not sell. Highest-priority academy asset."),
 ("annous","Andre Annous","p_annous","Priya Nair","2025-08-11","U18 Premier League vs Chelsea","80","Monitoring",
  "Andre Annous, central midfielder. Calm under pressure, lovely first touch, and reads the game well beyond his seventeen years. Keeps possession ticking and rarely gives it away. Physically he's still developing — gets bullied in duels and his change of pace is average. Passing range is promising but not yet incisive. Track him across the season; if the physical side comes on, there's a squad player here in two or three years."),
 ("mosquera","Cristian Mosquera","p_mosquera","Alejandro Ferreira","2025-08-10","Pre-season friendly vs AC Milan","78","Priority",
  "Transcribing my note on Cristian Mosquera after watching him live today. Composed for a twenty-one year old centre-back, really comfortable stepping into midfield with the ball, breaks lines with a vertical pass most defenders his age don't attempt. Aggressive on the front foot, won almost everything in the air, recovery run timing is elite. Concerns: over-eager stepping out, got turned once, and he ball-watches on crosses — coachable, typical for his age. System fit is high: suits a high line and possession build-out, exactly what we run. Team and player style fit in the low-to-mid eighties. Strong buy-and-develop; priority target if the clause holds around thirty million. Want one more live viewing versus top opposition."),
]

for stem,name,pid,scout,date,fixture,mins,status,body in TRANSCRIPTS:
    txt = (f"ACME SPORTS — SCOUT NOTE (VOICE TRANSCRIPT)\n"
           f"Player: {name}\nPlayer ID: {pid}\nScout: {scout}\nDate: {date}\n"
           f"Fixture observed: {fixture} ({mins} minutes)\nStatus: {status}\n\nSUMMARY:\n{body}\n")
    fn = os.path.join(TDIR, f"scout_note_{stem}.txt")
    open(fn, "w").write(txt)
    print("TXT ", os.path.basename(fn))

print(f"\nGenerated {len(CONTRACTS)} contracts, {len(TRANSCRIPTS)} transcripts")
