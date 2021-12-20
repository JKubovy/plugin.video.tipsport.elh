# coding=utf-8
from datetime import datetime, timedelta
import _strptime
import time

FULL_NAMES = {
    u'H.Králové': u'Hradec Králové',
    u'M.Boleslav': u'Mladá Boleslav',
    u'K.Vary': u'Karlovy Vary',
    u'SR 20': u'Slovensko 20',
    u'L.Mikuláš': u'Liptovský Mikuláš',
    u'N.Zámky': u'Nové Zámky',
    u'HK Poprad': u'Poprad',
    u'B.Bystrica': u'Banská Bystrica',
    u'Fr.Místek': u'Frýdek-Místek',
    u'Ústí': u'Ústí nad Labem',
    u'Benátky': u'Benátky nad Jizerou',
    u'Č.Budějovice': u'České Budějovice'
}


class Match:
    """Class represents one match with additional information"""
    def __init__(self, name, competition, is_competition_with_logo, sport, url, start_time, status, not_started, score,
                 icon_name, minutes_enable_before_start):
        self.first_team, self.second_team, self.name = self.parse_name(name)
        self.competition = competition
        self.is_competition_with_logo = is_competition_with_logo
        self.sport = sport
        self.url = url
        self.start_time = start_time
        self.status = status
        self.started = not_started in ['false', False]
        self.score = score
        self.icon_name = icon_name
        self.minutes_enable_before_start = minutes_enable_before_start
        self.match_time = self.get_match_time()

    def get_match_time(self):
        datetime.now()
        match_time = datetime(*(time.strptime(self.start_time, '%H:%M')[0:6]))
        match_time = datetime.now().replace(hour=match_time.hour, minute=match_time.minute, second=0, microsecond=0)
        return match_time

    def is_stream_enabled(self):
        time_to_start = self.match_time - datetime.now()
        if time_to_start.days < 0:
            return True
        return time_to_start.seconds < timedelta(minutes=self.minutes_enable_before_start).seconds

    @staticmethod
    def get_full_name_if_possible(name):
        if name in FULL_NAMES:
            return FULL_NAMES[name]
        return name

    @staticmethod
    def parse_name(name):
        try:
            (first_team, second_team) = name.split('-')
            first_team = Match.get_full_name_if_possible(first_team)
            second_team = Match.get_full_name_if_possible(second_team)
            match_name = u'{first_team} - {second_team}'.format(first_team=first_team, second_team=second_team)
            return (first_team, second_team, match_name)
        except ValueError:
            return '', '', name
