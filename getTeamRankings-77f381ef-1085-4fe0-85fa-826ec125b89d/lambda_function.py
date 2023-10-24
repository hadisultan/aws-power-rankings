import json
import boto3

s3_client = boto3.client('s3')
gamesDict = {}
teamsDict = {}
leaguesDict = {}
tournamentDict = {}

def getKFactor(avgRating, priority=1000):
    priorityBias = 1.5 - 0.00005 * priority 
    if avgRating <= 1000:
        return 35
    if avgRating >= 2000:
        return 15
    return (avgRating - 1000)*(-0.025) + (35*(priorityBias))

def lambda_handler(event, context):
    global gamesDict
    global teamsDict
    global leaguesDict
    global tournamentDict
    params = {}
    if "queryStringParameters" in event:
        if event['queryStringParameters'] != None:
            params = event['queryStringParameters']
    team_ids = params["team_ids"].split(",")
    gamesDict = {}
    teamsDict = {}
    leaguesDict = {}
    tournamentDict = {}
    bucket_name = 'globalpowerrankingsfilebucket'
    file_name = 'leagues.json'
    s3_response = s3_client.get_object(Bucket=bucket_name, Key=file_name)
    file_data_text = s3_response["Body"].read().decode('utf-8')
    leaguesData = json.loads(file_data_text)    
    
    for i in leaguesData:
        leaguesDict[i["id"]] = i
    for i in leaguesData:
        for j in i["tournaments"]:
            tournamentDict[j["id"]] = i["id"]
    
    
    file_name = 'tournaments.json'
    s3_response = s3_client.get_object(Bucket=bucket_name, Key=file_name)
    file_data_text = s3_response["Body"].read().decode('utf-8')
    tournamentData = json.loads(file_data_text)
    for tournament in tournamentData:
        for stage in tournament["stages"]:
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
    
    teams = {}
    for game in gamesDict:
        gameData = gamesDict[game][1]
        teams[gameData["teams"][0]["id"]] = 1000.0    
        teams[gameData["teams"][1]["id"]] = 1000.0
    
    for game in gamesDict:
        try:
            gameData = gamesDict[game][1]
            try:
                teamA = gameData["teams"][0]
                teamB = gameData["teams"][1]
                scoreA, scoreB = 0.5, 0.5
                if(teamA["result"]["outcome"] == "win"):
                    scoreA, scoreB = 1, 0
                elif(teamA["result"]["outcome"] == "loss"):
                    scoreA, scoreB = 0, 1
            except:
                continue
            ratingDiff = teams[teamA["id"]] - teams[teamB["id"]] 
            diffRatio = ratingDiff/400.0
            if diffRatio < 0:
                diffRatio = diffRatio * -1
            expected = 1/((10**diffRatio)+1)
            try:
                priority = leaguesDict[tournamentDict[gamesDict[game][0]]]["priority"]
            except:
                priority = 1000
            k = getKFactor((teams[teamA["id"]] + teams[teamB["id"]])/2, priority = priority)
            changeA = k * (scoreA - expected)
            teams[teamA["id"]] = teams[teamA["id"]] + changeA
            changeB = k * (scoreB - expected)
            teams[teamB["id"]] = teams[teamB["id"]] + changeB
        except Exception as e:
            print("Error:", e)
    rankedTeams = sorted(teams, key=teams.get, reverse=True)
    print(rankedTeams)
    teamsParsed = 0
    lastRank = 1
    lastElo = -1
    ret = []
    for i in rankedTeams:
        if i in team_ids:
            temp = {}
            temp["team_id"] = i
            temp["team_code"] = teamsDict[temp["team_id"]]["acronym"]
            temp["team_name"] = teamsDict[temp["team_id"]]["name"]
            if teams[i] == lastElo:
                temp["rank"] = lastRank
            else:
                temp["rank"] = teamsParsed + 1
            lastRank = temp['rank']
            temp['elo'] = teams[i]
            lastElo = temp['elo']
            teamsParsed += 1 
            ret.append(temp)
    http_res = {}
    http_res['statusCode'] = 200
    http_res['headers'] = {}
    http_res['headers']['Content-Type'] = 'application/json'
    print(len(teamsDict))
    print(len(gamesDict))
    http_res['body'] = json.dumps(ret)
    return http_res