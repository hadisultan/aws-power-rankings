import json
import boto3

s3_client = boto3.client('s3')
gamesDict = {}
teamsDict = {}

def getKFactor(avgRating, priority=1000):
    priorityBias = 1.5 - 0.00005 * priority 
    if avgRating <= 1000:
        return 35
    if avgRating >= 2000:
        return 15
    return (avgRating - 1000)*(-0.025) + (35*(priorityBias))

def getTournamentRankings(tournamentId):
    global gamesDict
    global teamsDict
    tournamentGames = []
    for game in gamesDict:
        if gamesDict[game][0] == tournamentId:
            tournamentGames.append(gamesDict[game][1])
    tourteams = {}

    for game in tournamentGames:
        try:
            teamA = game["teams"][0]
            teamB = game["teams"][1]
            if teamA["id"] not in tourteams:
                tourteams[teamA["id"]] = 1000.0
            if teamB["id"] not in tourteams:
                tourteams[teamB["id"]] = 1000.0
            scoreA, scoreB = 0.5, 0.5
            if(teamA["result"]["outcome"] == "win"):
                scoreA, scoreB = 1, 0
            elif(teamA["result"]["outcome"] == "loss"):
                scoreA, scoreB = 0, 1
            ratingDiff = tourteams[teamA["id"]] - tourteams[teamB["id"]] 
            diffRatio = ratingDiff/400.0
            if diffRatio < 0:
                diffRatio = diffRatio * -1
            expected = 1/((10**diffRatio)+1)
            k = getKFactor((tourteams[teamA["id"]] + tourteams[teamB["id"]])/2, 1)
            changeA = k * (scoreA - expected)
            tourteams[teamA["id"]] = tourteams[teamA["id"]] + changeA
            changeB = k * (scoreB - expected)
            tourteams[teamB["id"]] = tourteams[teamB["id"]] + changeB
        except Exception as e:
            print("Error:", e)
    rankedTourTeams = sorted(tourteams, key=tourteams.get, reverse=True)
    teamsParsed = 0
    lastRank = 1
    lastElo = -1
    ret = []
    for i in rankedTourTeams:
        temp = {}
        temp["team_id"] = i
        temp["team_code"] = teamsDict[temp["team_id"]]["acronym"]
        temp["team_name"] = teamsDict[temp["team_id"]]["name"]
        if tourteams[i] == lastElo:
            temp["rank"] = lastRank
        else:
            temp["rank"] = teamsParsed + 1
        lastRank = temp['rank']
        temp['elo'] = tourteams[i]
        lastElo = temp['elo']
        teamsParsed += 1 
        ret.append(temp)
    return ret

def lambda_handler(event, context):
    global gamesDict
    global teamsDict
    params = event['queryStringParameters']
    stageParam = ""
    gamesDict = {}
    teamsDict = {}
    if "stage" in params:
        stageParam = params["stage"]
    bucket_name = 'globalpowerrankingsfilebucket'
    file_name = 'tournaments.json'
    s3_response = s3_client.get_object(Bucket=bucket_name, Key=file_name)
    file_data_text = s3_response["Body"].read().decode('utf-8')
    tournamentData = json.loads(file_data_text)
    for tournament in tournamentData:
        for stage in tournament["stages"]:
            if stageParam != "":
                if stageParam != stage["name"]:
                    continue
            for section in stage["sections"]:
                for match in section["matches"]:
                    for game in match["games"]:
                        gamesDict[game["id"]] = [tournament["id"], game]
    file_name = 'teams.json'
    s3_response = s3_client.get_object(Bucket=bucket_name, Key=file_name)
    file_data_text = s3_response["Body"].read().decode('utf-8')
    teamsData = json.loads(file_data_text)
    for i in teamsData:
        teamsDict[i["team_id"]] = i 

    ranks = getTournamentRankings(params["tournament_id"])
    
    http_res = {}
    http_res['statusCode'] = 200
    http_res['headers'] = {}
    http_res['headers']['Content-Type'] = 'application/json'
    print(len(ranks))
    print(len(teamsDict))
    print(len(gamesDict))
    http_res['body'] = json.dumps(ranks)
    return http_res