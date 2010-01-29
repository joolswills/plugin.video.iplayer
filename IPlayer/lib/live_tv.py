import cgi, os, sys, urllib
import xml.dom.minidom as dom
import xbmcplugin, xbmcgui, xbmc

THUMB_DIR      = os.path.join(os.getcwd(), 'resources', 'media')

live_tv_channels = [
                    ('bbc_one_london', 'BBC One', 'bbc_one.png'),
                    ('bbc_two_england','BBC Two', 'bbc_two.png'),
                    ('bbc_three','BBC Three', 'bbc_three.png'),
                    ('bbc_four','BBC Four', 'bbc_four.png'),
                    ('cbbc','CBBC', 'cbbc.png'),
                    ('cbeebies','Cbeebies', 'cbeebies.png'),
                    ('bbc_news24','BBC News', 'bbc_news24.png'),
                    ('bbc_parliament','BBC Parliament', 'bbc_parliament.png')
                    ]

def fetch_stream_info(channel, bitrate):

    # read the simulcast xml
    cxml = 'http://www.bbc.co.uk/emp/simulcast/' + channel + '.xml'
    f = urllib.urlopen(cxml)
    cstr = f.read()
    f.close()

    # parse the simulcast xml
    doc = dom.parseString(cstr)
    root = doc.documentElement
    surl = ''
    mbitrate = 0
    
    for media in root.getElementsByTagName( "media" ):
        mbitrate    = media.attributes['bitrate'].nodeValue
        connection  = media.getElementsByTagName( "connection" )[0]
        simulcast   = connection.attributes['identifier'].nodeValue
        server      = connection.attributes['server'].nodeValue
        kind        = connection.attributes['kind'].nodeValue
        application = connection.attributes['application'].nodeValue
        
        surl = 'http://www.bbc.co.uk/mediaselector/4/gtis/?server=%s&identifier=%s&kind=%s&application=%s&cb=62605' % (server , simulcast, kind, application)        
        
        print "bitrates: Found %s Searching for %s" % (mbitrate, bitrate)
        if int(mbitrate) <= int(bitrate):
            # select the current bitrate if it equals or is less than the desired bitrate.
            # as the xml file lists streams in descending order of bit rate this ensures that the 
            # nearest bitrate to the desired one is selected
            break
    
    print 'Live Video Stream. Preference bitrate = %s,actual = %s' % (bitrate, mbitrate)
    
    # read the media selector xml
    print surl
    f    = urllib.urlopen(surl)
    xstr = f.read()
    f.close()
    
    # parse the media selector xml
    doc    = dom.parseString(xstr)
    root   = doc.documentElement
    token  = root.getElementsByTagName( "token" )[0].firstChild.nodeValue
    kind   = root.getElementsByTagName( "kind" )[0].firstChild.nodeValue
    server = root.getElementsByTagName( "server" )[0].firstChild.nodeValue
    identifier  = root.getElementsByTagName( "identifier" )[0].firstChild.nodeValue
    application = root.getElementsByTagName( "application" )[0].firstChild.nodeValue
    
    print 'token: ' + token, 'kind: ' + kind, 'server: ' + server, 'identifier: ' + identifier, 'application: ' + application
    url = "rtmp://%s:1935/%s/%s?auth=%s&aifp=xxxxxx" % (server, application, identifier, token)
    playpath = "%s?auth=%s&aifp=xxxxxx" % (identifier, token)
    return (url, playpath)


def play_stream(channel, bitrate, showDialog):
    (url, playpath) = fetch_stream_info(channel, bitrate)
    if showDialog:
        pDialog = xbmcgui.DialogProgress()
        pDialog.create('IPlayer', 'Loading live stream info')
        xbmc.sleep(50)
        
    if showDialog: pDialog.update(50, 'Starting Stream')
    
    item = xbmcgui.ListItem("BBC Live video")
    item.setProperty("SWFPlayer", 'http://www.bbc.co.uk/emp/9player.swf?revision=8812_8903')
    item.setProperty("PlayPath", playpath) 
    item.setProperty("IsLive", "true")               
                   
    play=xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
    play.clear()
    play.add(url,item)
    player = xbmc.Player(xbmc.PLAYER_CORE_AUTO)
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
     
    for j, (id, label, thumb) in enumerate(live_tv_channels):
        url = make_url(channel=id)
        listitem = xbmcgui.ListItem(label=label)
        listitem.setIconImage('defaultVideo.png')
        listitem.setThumbnailImage(os.path.join(THUMB_DIR, thumb))        
        ok = xbmcplugin.addDirectoryItem(
            handle=handle, 
            url=url,
            listitem=listitem,
            isFolder=False,
        )

    xbmcplugin.endOfDirectory(handle=handle, succeeded=True)



##############################################
if __name__ == '__main__':
    args = cgi.parse_qs(sys.argv[2][1:])
    channel = args.get('label', [None])[0]
    if channel and channel != '':
        play_stream(channel, 800)
    else:
        list_channels()