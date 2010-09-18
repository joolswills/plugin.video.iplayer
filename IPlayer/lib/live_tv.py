import cgi, os, sys, urllib, re
import xml.dom.minidom as dom
import logging
import xbmcplugin, xbmcgui, xbmc
from datetime import date
from operator import itemgetter

from iplayer2 import get_provider, httpget, get_protocol, get_port

# it would be nice to scrape what's on now - at least when the items are first created.

THUMB_DIR      = os.path.join(os.getcwd(), 'resources', 'media')

# note that cbbc and cbeebies use bbc three/four whilst they are offline
# channel id : order, stream id, display name, logo
# note: some channel ids used in www urls are different from the stream urls
live_tv_channels = {
    'bbc_one_london' : (1, 'bbc_one_live', 'BBC One', 'bbc_one.png'),
    'bbc_two_england': (2, 'bbc_two_live', 'BBC Two', 'bbc_two.png'),
    'bbc_three' : (3, 'bbc_three_live', 'BBC Three', 'bbc_three.png'),
    'bbc_four' : (4, 'bbc_four_live', 'BBC Four', 'bbc_four.png'),
    'cbbc' : (5, 'bbc_three_live', 'CBBC', 'cbbc.png'),
    'cbeebies' : (6, 'bbc_four_live', 'Cbeebies', 'cbeebies.png'),
    'bbc_news24' : (7, 'journalism_bbc_news_channel', 'BBC News', 'bbc_news24.png'),
    'bbc_parliament' : (8, 'bbc_parliament_live', 'BBC Parliament', 'bbc_parliament.png'),
    'bbc_alba' : (9, 'bbc_alba_live', 'BBC ALBA', 'bbc_alba.png'),
    'bbc_redbutton' : (10, 'bbc_redbutton_live', 'BBC Red Button', 'bbc_one.png')
    }

def parseXML(url):
    xml = httpget(url)
    doc = dom.parseString(xml)
    root = doc.documentElement
    return root

def fetch_stream_info(channel, bitrate, req_provider):
    (sort, stream_id, label, thumb) = live_tv_channels[channel]

    if bitrate == 480: quality = 'iplayer_streaming_h264_flv_lo_live'
    elif bitrate == 800: quality = 'iplayer_streaming_h264_flv_live'
    elif bitrate >= 1500: quality = 'iplayer_streaming_h264_flv_high_live'

    # bbc news 24 is only available as 800kbit maximum currently
    if channel == "bbc_news24":
        if bitrate < 800 : quality = 'journalism_uk_stream_h264_flv_lo_live'
        else : quality = 'journalism_uk_stream_h264_flv_med_live'

    if channel == "bbc_parliament" or channel == "bbc_alba":
        quality = 'iplayer_streaming_vp6_flv_lo_live'

    surl = 'http://www.bbc.co.uk/mediaselector/4/mtis/stream/%s/%s/%s' % (stream_id, quality, req_provider)
    logging.info("getting media information from %s" % surl)
    root = parseXML(surl)
    mbitrate = 0
    url = ""
    media = root.getElementsByTagName( "media" )[0]

    conn  = media.getElementsByTagName( "connection" )[0]

    # rtmp streams
    identifier  = conn.attributes['identifier'].nodeValue
    server      = conn.attributes['server'].nodeValue
    auth        = conn.attributes['authString'].nodeValue
    supplier    = conn.attributes['supplier'].nodeValue

    # not always listed for some reason
    try: 
        application = conn.attributes['application'].nodeValue
    except:
        application = 'live'

    params = dict(protocol = get_protocol(), port = get_port(), server = server, auth = auth, ident = identifier, app = application)

    if supplier == "akamai" or supplier == "limelight":
        if supplier == "akamai":
            url = "%(protocol)s://%(server)s:%(port)s/%(app)s/?%(auth)s playpath=%(ident)s?%(auth)s" % params
        if supplier == "limelight":
            url = "%(protocol)s://%(server)s:%(port)s/ app=%(app)s?%(auth)s tcurl=%(protocol)s://%(server)s:%(port)s/%(app)s?%(auth)s playpath=%(ident)s" % params
        url += " swfurl=http://www.bbc.co.uk/emp/10player.swf swfvfy=1 live=1"

    return (url)


def play_stream(channel, bitrate, showDialog):
    bitrate = int(bitrate)
    # check to see if bbcthree/cbbc or bbcfour/cbeebies is on the air?    
    if channel == 'bbc_three' or channel == 'bbc_four' or channel == 'cbeebies' or channel == 'cbbc':
        surl = 'http://www.bbc.co.uk/iplayer/tv/'+channel
        cstr = httpget(surl)
        off_air_message = re.compile('<h2 class="off-air">.+?</span>(.+?)</a></h2>').findall(cstr)
        if off_air_message:
            pDialog = xbmcgui.Dialog()
            pDialog.ok('IPlayer', 'Channel is currently Off Air')
            return

    provider = get_provider()
    
    # check for red button usage
    if channel == 'bbc_redbutton':
        pDialog = xbmcgui.Dialog()
        if not pDialog.yesno("BBC Red Button Live Stream", "This will only work when the stream is broadcasting.", "If it is not on, xbmc may retry indefinately (crash)", "Do you want to try anyway?"):
            return

    url = fetch_stream_info(channel, bitrate, provider)

    if url == "":
        Dialog = xbmcgui.Dialog()
        pDialog.ok('IPlayer', "Sorry, stream is currently unavailable")

    if showDialog:
        pDialog = xbmcgui.DialogProgress()
        pDialog.create('IPlayer', 'Loading live stream info')
        xbmc.sleep(50)

    if showDialog: pDialog.update(50, 'Starting Stream')
    # build listitem to display whilst playing
    (sort, stream_id, label, thumb) = live_tv_channels[channel]
    listitem = xbmcgui.ListItem(label = label + ' - Live')
    listitem.setIconImage('defaultVideo.png')
    listitem.setThumbnailImage(os.path.join(THUMB_DIR, thumb))

    play = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
    play.clear()
    play.add(url,listitem)
    player = xbmc.Player(xbmc.PLAYER_CORE_DVDPLAYER)
    player.play(play)
    if showDialog: pDialog.close()
    
def make_url(channel=None):
    base = sys.argv[0]
    d = {}
    if channel: d['label'] = channel
    d['pid'] = 0       
    params = urllib.urlencode(d, True)
    return base + '?' + params    

def list_channels():
    handle = int(sys.argv[1])
    xbmcplugin.addSortMethod(handle=handle, sortMethod=xbmcplugin.SORT_METHOD_NONE )

    channels = sorted(live_tv_channels.items(), key=itemgetter(1))
    for id, (sort, stream_id, label, thumb) in channels:
        url = make_url(channel = id)
        listitem = xbmcgui.ListItem(label=label)
        listitem.setIconImage('defaultVideo.png')
        listitem.setThumbnailImage(os.path.join(THUMB_DIR, thumb))        
        ok = xbmcplugin.addDirectoryItem(
            handle = handle, 
            url = url,
            listitem = listitem,
            isFolder = False,
        )

    xbmcplugin.endOfDirectory(handle=handle, succeeded=True)

##############################################
if __name__ == '__main__':
    args = cgi.parse_qs(sys.argv[2][1:])
    channel = args.get('label', [None])[0]
    if channel and channel != '':
        play_stream(channel,800)
    else:
        list_channels()
