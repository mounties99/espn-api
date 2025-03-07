from .constant import NINE_CAT_STATS, POSITION_MAP, PRO_TEAM_MAP, STATS_MAP, STAT_ID_MAP
from espn_api.utils.utils import json_parsing
from datetime import datetime
from functools import cached_property

class Player(object):
    '''Player are part of team'''
    def __init__(self, data, year, pro_team_schedule = None, news = None):
        self.name = json_parsing(data, 'fullName')
        self.playerId = json_parsing(data, 'id')
        self.year = year
        self.position = POSITION_MAP[json_parsing(data, 'defaultPositionId') - 1]
        self.lineupSlot = POSITION_MAP.get(data.get('lineupSlotId'), '')
        self.eligibleSlots = [POSITION_MAP[pos] for pos in json_parsing(data, 'eligibleSlots')]
        self.acquisitionType = json_parsing(data, 'acquisitionType')
        self.proTeam = PRO_TEAM_MAP[json_parsing(data, 'proTeamId')]
        self.injuryStatus = json_parsing(data, 'injuryStatus')
        self.posRank = json_parsing(data, 'positionalRanking')
        self.stats = {}
        self.schedule = {}
        self.news = {}
        expected_return_date = json_parsing(data, 'expectedReturnDate')
        self.expected_return_date = datetime(*expected_return_date).date() if expected_return_date else None

        if pro_team_schedule:
            pro_team_id = json_parsing(data, 'proTeamId')
            pro_team = pro_team_schedule.get(pro_team_id, {})
            for key in pro_team:
                game = pro_team[key][0]
                team = game['awayProTeamId'] if game['awayProTeamId'] != pro_team_id else game['homeProTeamId']
                self.schedule[key] = { 'team': PRO_TEAM_MAP[team], 'date': datetime.fromtimestamp(game['date']/1000.0) }

        if news:
            news_feed = news.get("news", {}).get("feed", [])
            self.news = [
                {
                    "published": item.get("published", ""),
                    "headline": item.get("headline", ""),
                    "story": item.get("story", "")
                }
                for item in news_feed
            ]

        # add available stats

        player = data['playerPoolEntry']['player'] if 'playerPoolEntry' in data else data['player']
        self.injuryStatus = player.get('injuryStatus', self.injuryStatus)
        self.injured = player.get('injured', False)

        for split in  player.get('stats', []):
            if split['seasonId'] == year:
                id = self._stat_id_pretty(split['id'], split['scoringPeriodId'])
                applied_total = split.get('appliedTotal', 0)
                applied_avg =  round(split.get('appliedAverage', 0), 2)
                game = self.schedule.get(id, {})
                self.stats[id] = dict(applied_total=applied_total, applied_avg=applied_avg, team=game.get('team', None), date=game.get('date', None))
                if split.get('stats'):
                    if 'averageStats' in split.keys():
                        self.stats[id]['avg'] = {STATS_MAP.get(i, i): split['averageStats'][i] for i in split['averageStats'].keys() if STATS_MAP.get(i) != ''}
                        self.stats[id]['total'] = {STATS_MAP.get(i, i): split['stats'][i] for i in split['stats'].keys() if STATS_MAP.get(i) != ''}
                    else:
                        self.stats[id]['avg'] = None
                        self.stats[id]['total'] = {STATS_MAP.get(i, i): split['stats'][i] for i in split['stats'].keys() if STATS_MAP.get(i) != ''}
        self.total_points = self.stats.get(f'{year}_total', {}).get('applied_total', 0)
        self.avg_points = self.stats.get(f'{year}_total', {}).get('applied_avg', 0)
        self.projected_total_points= self.stats.get(f'{year}_projected', {}).get('applied_total', 0)
        self.projected_avg_points = self.stats.get(f'{year}_projected', {}).get('applied_avg', 0)

    def __repr__(self):
        return f'Player({self.name})'

    def _stat_id_pretty(self, id: str, scoring_period):
        id_type = STAT_ID_MAP.get(id[:2])
        return f'{id[2:]}_{id_type}' if id_type else str(scoring_period)

    @cached_property
    def nine_cat_averages(self):
        return {
            k: round(v, (3 if k in {'FG%', 'FT%'} else 1))
            for k, v in self.stats.get(f'{self.year}_total', {}).get("avg", {}).items()
            if k in NINE_CAT_STATS
        }
