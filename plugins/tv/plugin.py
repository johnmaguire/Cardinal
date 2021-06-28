from datetime import datetime
import logging

from twisted.internet import defer
from twisted.internet.threads import deferToThread
import requests

from cardinal.decorators import command
from cardinal.decorators import help


class ShowNotFoundException(Exception):
    pass


@defer.inlineCallbacks
def fetch_show(show):
    r = yield deferToThread(
        requests.get,
        "https://api.tvmaze.com/singlesearch/shows",
        params={"q": show}
    )

    if r.status_code == 404:
        raise ShowNotFoundException
    r.raise_for_status()

    data = r.json()

    network = None
    if data['network']:
        network = data['network']['name']
        country = data['network']['country']
        if country:
            country = country['code']
    elif data['webChannel']:
        network = data['webChannel']['name']
        country = data['webChannel']['country']
        if country:
            country = country['code']

    schedule = None
    if data['schedule']:
        schedule = ', '.join(data['schedule']['days'])

        time = data['schedule']['time']
        if time:
            am_pm = "AM"
            hour, minute = data['schedule']['time'].split(":", 1)
            hour = int(hour)
            if hour >= 13:
                hour -= 12
                am_pm = "PM"
            time = "{}:{} {}".format(hour, minute, am_pm)

            schedule += " @ {} EST".format(time)

    next_episode = data.get('_links', {}) \
        .get('nextepisode', {}) \
        .get('href', None)
    previous_episode = data.get('_links', {}) \
        .get('previousepisode', {}) \
        .get('href', None)

    imdb_url = None
    if data['externals']['imdb']:
        imdb_url = "https://imdb.com/title/{}".format(
            data['externals']['imdb']
        )

    return {
        'name': data['name'],
        'network': network,
        'country': country,
        'status': data['status'],
        'schedule': schedule,
        'imdb_url': imdb_url,
        '_links': {
            'next_episode': next_episode,
            'previous_episode': previous_episode,
        }
    }


def format_data_full(show, next_episode, previous_episode):
    # Format header
    header = show['name']
    if show['network'] and show['country']:
        header += " [{} - {}]".format(show['country'], show['network'])
    elif show['network'] or show['country']:
        header += " [{}]".format(
            show['network'] if show['network'] else show['country']
        )
    # don't show schedule if the next episode isn't announced
    if show['schedule'] and next_episode is not None:
        header += " - {}".format(show['schedule'])
    header += " - [{}]".format(show['status'])

    # Build messages
    messages = [header]
    messages.append("Last Episode: {}".format(
        format_episode(previous_episode)
    ))
    if show['status'] != 'Ended':
        messages.append("Next Episode: {}".format(
            format_episode(next_episode)
        ))
    if show['imdb_url']:
        messages.append(show['imdb_url'])

    return messages


def format_data_short(show, next_episode):
    title = show['name']
    if show['network']:
        title += " - " + show['network']

    if show['status'] == 'Ended':
        next_ep = "Show Ended"
    else:
        next_ep = "Next Episode: {}".format(
            format_episode(next_episode)
        )

    return "[ {} | {} ]".format(title, next_ep)


@defer.inlineCallbacks
def fetch_episode(uri):
    r = yield deferToThread(
        requests.get,
        uri,
    )
    r.raise_for_status()

    data = r.json()
    return {
        'name': data['name'],
        'season': data['season'],
        'episode': data['number'],
        'airdate': (datetime.fromisoformat(data['airdate'])
                    if data['airdate'] else
                    None),
    }


def format_episode(data):
    if data is None:
        return 'TBA'

    if data['season'] and data['episode']:
        ep_marker = "S{:0>2}E{:0>2}".format(data['season'], data['episode'])
    # hopefully nothing is missing a season also...
    else:
        ep_marker = "Season {:0>2} Special".format(data['season'])

    airdate = data['airdate'].strftime("%d %b %Y") \
        if data['airdate'] else \
        "TBA"

    return "{} - {} [{}]".format(ep_marker, data['name'], airdate)


class TVPlugin:
    def __init__(self, cardinal, config):
        self.logger = logging.getLogger(__name__)
        self.cardinal = cardinal

        if config is None:
            config = {}

        self.default_output = config.get('default_output', 'short')
        self.private_output = config.get('private_output', 'full')
        self.channels = config.get('channels', {})

    def get_output_format(self, channel):
        chantypes = self.cardinal.supported.getFeature("CHANTYPES") or ('#',)
        if channel[0] not in chantypes:
            return self.private_output

        # Fetch channel-specific output format, or default
        return self.channels.get(channel, {}) \
            .get('output', self.default_output)

    @command('ep')
    @help('Get air date info for a TV show.')
    @help('Syntax: @ep <tv show>')
    @defer.inlineCallbacks
    def next_air_date(self, cardinal, user, channel, msg):
        try:
            show = msg.split(' ', 1)[1].strip()
        except IndexError:
            cardinal.sendMsg(channel, "Syntax: .ep <tv show>")
            return

        try:
            show = yield fetch_show(show)
        except ShowNotFoundException:
            cardinal.sendMsg(
                channel,
                "Couldn't find anything for '{}'".format(show)
            )
            return
        except Exception:
            self.logger.exception("Error reaching TVMaze")
            cardinal.sendMsg(channel, "Error reaching TVMaze")
            return

        # Fetch next & previous episode info
        next_episode = None
        if show['_links']['next_episode']:
            next_episode = yield fetch_episode(
                show['_links']['next_episode'])

        if self.get_output_format(channel) == 'short':
            messages = [format_data_short(show, next_episode)]
        else:
            previous_episode = None
            if show['_links']['previous_episode']:
                previous_episode = yield fetch_episode(
                    show['_links']['previous_episode'])

            messages = format_data_full(show, next_episode, previous_episode)

        # Show Name [Network] - [Status]
        #  - or -
        # Show Name [UK - Network] - Date @ Time EST - [Status]
        # Last Episode: S05E10 - Nemesis Games [12 May 2021]
        # Next Episode: S05E11 - Mourning [19 May 2021]
        # https://imdb.com/tt1234123
        for message in messages:
            cardinal.sendMsg(channel, message)


entrypoint = TVPlugin
