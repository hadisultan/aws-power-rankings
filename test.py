import json

def getKFactor(avgRating):
    if avgRating <= 1000:
        return 40
    if avgRating >= 2000:
        return 15
    return (avgRating - 1000)*(-0.025)+40

def getTournamentRankings(tournamentId):
    index, data = next(((index, d) for (index, d) in enumerate(tournamentData) if d["id"] == tournamentId), None)
    teams = {}
    for stage in data["stages"]:
        for section in stage["sections"]:
            for match in section["matches"]:
                teamA = match["teams"][0]
                teamB = match["teams"][1]
                if teamA["id"] not in teams:
                    teams[teamA["id"]] = 1000.0
                if teamB["id"] not in teams:
                    teams[teamB["id"]] = 1000.0
                winner = 0 
                scoreA, scoreB = 0.5, 0.5
                if(teamA["result"]["outcome"] == "win"):
                    winner = 1
                    scoreA, scoreB = 1, 0
                elif(teamA["result"]["outcome"] == "loss"):
                    winner = 2
                    scoreA, scoreB = 0, 1
                ratingDiff = teams[teamA["id"]] - teams[teamB["id"]] 
                diffRatio = ratingDiff/400.0
                if diffRatio < 0:
                    diffRatio = diffRatio * -1
                expected = 1/((10**diffRatio)+1)
                k = getKFactor((teams[teamA["id"]] + teams[teamB["id"]])/2)
                changeA = k * (scoreA - expected)
                teams[teamA["id"]] = teams[teamA["id"]] + changeA
                changeB = k * (scoreB - expected)
                teams[teamB["id"]] = teams[teamB["id"]] + changeB
    rankedTeams = sorted(teams, key=teams.get, reverse=True)
    for i in rankedTeams:
        print("{}: {}".format(i, teams[i]))
tournamentData = json.load(open("esports-data/tournaments.json"))
mappingData = json.load(open("esports-data/mapping_data.json"))
mappingDict = {}
for tournament in tournamentData:
    print(tournament["id"])
    getTournamentRankings(tournament["id"])
    print("\n")