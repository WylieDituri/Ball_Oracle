from django.shortcuts import render
from django.http import HttpResponse
import pandas as pd
import requests
import datetime
from nba_api.stats.endpoints import scoreboardv2
from nba_api.stats.endpoints import boxscoretraditionalv3
from nba_api.live.nba.endpoints import scoreboard
from nba_api.stats.endpoints import leaguestandingsv3
from nba_api.stats.endpoints import leagueleaders
from nba_api.stats.endpoints import teamdashboardbygeneralsplits
import numpy as np

playoff_flag = False

"""
Loads recent games for frontend access and game prediction
"""
def index(request):

    #current days games
    todayBoard = scoreboard.ScoreBoard().games.get_dict()
    today_games = []
    try:
        for game in todayBoard:
            home = game['homeTeam']
            away = game['awayTeam']
            to_add = [game['period'], game['gameClock'], game['gameStatusText'], game['gameLabel'], home['teamTricode'],
                      home['score'], away['teamTricode'], away['score']]
            today_games.append(to_add)
    except Exception as e:
        today_games = "error"

    #past ten games data
    today = datetime.datetime.now()
    today_format = today.strftime('%d-%m')
    past_games = []

    try:
        for x in range(10):

            # get daily scoreboard going backward
            today = today - datetime.timedelta(1)
            date = today.strftime('%Y-%m-%d')
            sb = scoreboardv2.ScoreboardV2(league_id="00", game_date=date, day_offset="0").game_header.get_dict()[
                'data']
            if len(sb) == 0:
                continue

            # iterate through all games on those days
            for y in range(len(sb)):
                box_score = boxscoretraditionalv3.BoxScoreTraditionalV3(game_id=sb[y][2]).team_stats.get_dict()['data']
                to_add = [sb[y][0][0:10], box_score[0][4], box_score[0][24], box_score[1][4], box_score[1][24]]
                past_games.append(to_add)
                if len(past_games) == 10:
                    break
            if len(past_games) == 10:
                break
    except Exception as e:
        past_games = []

    # upcoming games
    today = datetime.datetime.now()
    future_games = []
    try:
        for x in range(10):
            # get daily scoreboard going forward
            today = today + datetime.timedelta(1)
            date = today.strftime('%Y-%m-%d')
            sb = scoreboardv2.ScoreboardV2(league_id="00", game_date=date, day_offset="0").game_header.get_dict()['data']
            if len(sb) == 0:
                continue
            for y in range(len(sb)):
                score = prediction(sb[y][6], sb[y][7])
                to_add = [sb[y][0][0:10], sb[y][5][-3:], score['home'], sb[y][5][-6:-3], score['away']]
                future_games.append(to_add)
                if len(future_games) == 10:
                    break
            if len(future_games) == 10:
                break
    except Exception as e:
        future_games = []

    #context loading
    context = {
        'todayBoard': today_games,
        'pastBoard': past_games,
        'futureBoard': future_games,
        'todayFormat': today_format,
    }

    return render(request, 'home/games.html', context=context)


"""
Loads API calls for regular season data for frontend access
"""
def stats(request):
    today = datetime.datetime.now()
    year = int(today.strftime('%Y')) - 1
    team_header = ['TeamName', 'Record', 'Win %', 'L10', 'PPG', 'OPPG', 'Point Diff', 'Streak']

    #get current year regular season standings and stats
    standingsWest = []
    standingsEast = []
    try:
        standings_raw = leaguestandingsv3.LeagueStandingsV3(league_id="00", season=year, season_type="Regular Season").get_dict()['resultSets'][0]['rowSet']
        for team in standings_raw:
            if team[6] == 'West':
                standingsWest.append([team[4], team[17], team[15], team[20], team[58], team[59], team[60], team[37]])
            else:
                standingsEast.append([team[4], team[17], team[15], team[20], team[58], team[59], team[60], team[37]])
    except Exception as e:
        standingsWest = []
        standingsEast = []

    stat_leaders = []
    stat_header = ['PLAYER', 'TEAM', 'GP', 'MIN', 'FGM', 'FGA', 'FG_PCT', 'FG3M', 'FG3A', 'FG3_PCT', 'FTM', 'FTA', 'FT_PCT', 'OREB', 'DREB', 'REB', 'AST', 'STL', 'BLK', 'TOV', 'PF', 'PTS']
    try:
        leaders = leagueleaders.LeagueLeaders("00",'perGame').get_dict()['resultSet']['rowSet']
        x = 0
        for leader in leaders:
            stat_leaders.append(leader[2:])
            stat_leaders[x].pop(1)
            x += 1
    except Exception as e:
        stat_leaders = []

    #load context
    context = {
        'teamHeader': team_header,
        'regStandingsWest': standingsWest,
        'regStandingsEast': standingsEast,
        'statLeaders': stat_leaders,
        'statHeader': stat_header,
    }
    return render(request, 'home/stats.html', context=context)


"""
Basic prediction model, Neural Network model in development
"""
def prediction(homeID, awayID):
    predicted_score = {'home': 0, 'away': 0}

    #collect stats
    home_stats = teamdashboardbygeneralsplits.TeamDashboardByGeneralSplits(measure_type_detailed_defense='Advanced',
                                                                           per_mode_detailed='PerGame', plus_minus='Y',
                                                                           season_type_all_star='Playoffs',
                                                                           team_id=homeID).get_dict()['resultSets'][1]['rowSet'][0]
    away_stats = teamdashboardbygeneralsplits.TeamDashboardByGeneralSplits(measure_type_detailed_defense='Advanced',
                                                                           per_mode_detailed='PerGame', plus_minus='Y',
                                                                           season_type_all_star='Playoffs',
                                                                           team_id=awayID).get_dict()['resultSets'][1]['rowSet'][1]
    #assign random luck based on team ranks against each other
    home_team_betterness = 0
    rng = np.random.default_rng()
    for rank in home_stats[28:]:
        if int(rank) == 1:
            home_team_betterness += 1

    predicted_score['home'] = int((float(home_stats[24]) * (float(away_stats[9]) / float(home_stats[11]))) + (
                rng.random() * home_team_betterness))
    predicted_score['away'] = int((float(away_stats[24]) * (float(home_stats[9]) / float(away_stats[11]))) + (
                rng.random() * (19 - home_team_betterness)))

    return predicted_score
