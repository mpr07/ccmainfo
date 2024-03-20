#!/usr/bin/python
import argparse
import bs4
import json
import logging
import requests
import re
import sys
import os
import ssl
from urllib.request import Request
import urllib.request
import subprocess as SP

TMP_FILE = 'tvginfo.json'
AUVID = {True: "àudio", False: "video"}

TITLE = "TITOL"
INFO_LINK = "INFO"
M3_VIDEO = "MASTER"
TS_VIDEO = "TS"
ST_VIDEO = "STREAM"
TS2_VIDEO = "TS2"
ST2_VIDEO = "STREAM2"
SUBTITLE_1 = "SUBS1"
SUBTITLE_2 = "Subs2"

# Ignore SSL certificate errors
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE


name_urlbase = "http://www.tv3.cat/pvideo/FLV_bbd_dadesItem_MP4.jsp?idint="
hq_urlbase = "http://www.tv3.cat/pvideo/FLV_bbd_media.jsp?QUALITY=H&PROFILE=IPTV&FORMAT=MP4GES&ID="
mpd_urlbase = "https://dinamics.ccma.cat/pvideo/media.jsp?media=video&format=dm&idint="
subs2_urlbase = "http://www.tv3.cat/p3ac/p3acOpcions.jsp?idint="

subs1_urlbase = "https://api-crtvg.interactvty.com/api/1.0/contents/"

SUPER3_URL = "https://xabarin.gal/videos/"
SUPER3_ROOT = "https://xabarin.gal"
SUPER3_FILTER = "list-vertical-item"

hT = False

###########
# Logging
logger = logging.getLogger('tvginfo_main')
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.WARNING)
# end internal config
############
capis = []

def getStTs(mast):
    bs = mast.rsplit("/",1)[0]
    T = (bs+"/media-1/stream.m3u8", bs+"/media-1/media.ts", bs+"/media-2/stream.m3u8", bs+"/media-2/media.ts")
    return T

def getEpNum(nm):
    try:
        enm = nm.split("Capítulo ")[1].strip()
    except:
        enm = "?"
    return enm

def downloadMedia(tsLink, nm, shw, aud=False, pth="./"):
    nm2 = remove_invalid_win_chars(nm, '\/:*?"<>|')
    shw2 = remove_invalid_win_chars(shw, '\/:*?"<>|')
    if not pth.endswith("/"):
        pth += "/"
    try:
        os.mkdir(pth+shw2)
    except:
        pass
    if aud:
        SP.call(['ffmpeg', '-i', tsLink, '-vn', '-acodec', 'copy', pth+shw2+"/"+nm2+'.aac'])
    else:
        SP.call(['ffmpeg', '-i', tsLink, '-c', 'copy', pth+shw2+"/"+nm2+'.mp4'])

def cli_parse():
    parser = argparse.ArgumentParser(description='CRTVG.GAL INFO')
    parser.add_argument('--batch', dest='batch', nargs='?', default=False,
                        help='Run without asking for url')
    parser.add_argument('--debug', dest='verbose', action='store_true',
                        help='Debug mode')
    parser.add_argument('--down', dest='down', action='store_true',
                        help='Download files')
    parser.add_argument('--adown', dest='adown', action='store_true',
                        help='Ask to download files')
    parser.add_argument('--audio', dest='audio', action='store_true',
                        help='Ask to download files')
    parser.add_argument('--dpath', dest='dpath', nargs='?', default=False,
                        help='Path per baixar els continguts')
    parser.add_argument('--ndown', dest='ndown', nargs='?', default=False,
                        help='Nombre de continguts a baixar')
    parser.set_defaults(verbose=False,down=False,adown=False,audio=False)
    args = parser.parse_args()
    return args

def get_url(args):
    if not args.batch:
        url = input("Write your URL: ")
    else:
        url = args.batch
    if url.find(".html") > -1:
        logger.debug("TV3 link")
        hT = True
        return url, SUPER3_FILTER
    elif url.find(SUPER3_URL) > -1:
        logger.debug("SUPER3 link")
        return url, SUPER3_FILTER
    else:
        logger.error("Given URL is not supported.")
        sys.exit(5)

def load_json():
    try:
        json_file = open(TMP_FILE, "r").read()
        j = json.loads(json_file)
        logger.info("Using old temporary list")
    except:
        logger.info("Creating new temporary list")
        j = []
    return j

def create_json(jin):
    j = json.loads(json.dumps(jin))
    logger.info("Rewriting temporary list")
    try:
        with open(TMP_FILE, 'w') as outfile:
            json.dump(j, outfile)
        logger.debug("Done rewriting temporary list")
    except:
        logger.error("Failed to write the temporary list.")
        sys.exit(1)


def remove_invalid_win_chars(value, deletechars):
    for c in deletechars:
        value = value.replace(c, '')
    return value

def main():
    args = cli_parse()
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    url, parse_filter = get_url(args)
    #print(parse_filter)
    
    js = load_json()
    if (url.endswith(".html")):
        html_doc = getTxt(url)  
    else:
        req = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        authTk = urllib.request.urlopen(req, context=ctx).getheader("Set-Cookie").split(";")[0].split("auth-at=")[1]
        #print(authTk)
        html_doc = urllib.request.urlopen(req, context=ctx).read()
    soup = bs4.BeautifulSoup(html_doc, 'html.parser')
    #print(soup)
    logger.info("Parsing URL {}".format(url))
    #try:
    capis_meta = soup.find_all('a', class_=parse_filter)
    print(len(capis_meta))
    #print(capis_meta)
    if not args.ndown:
        dcount = len(capis_meta)
    else:
        dcount = int(args.ndown)
    capis2 = []
    for capi_meta in capis_meta:
        p = re.compile('/videos/detail/([0-9]*)-')
        capis.append(p.search(capi_meta['href']).group(1))
        capis2.append(SUPER3_ROOT+capi_meta['href'])
    #except:
        #logger.error("Could not parse given url")
        #sys.exit(2)

    #capis.reverse()
    #capis2.reverse()

    #print(capis2)
    c2i = 0
    first_run = True
    new = False
    show_old = ""
    for capi in capis:
        logger.debug("Going for ID:{}".format(capi))
        #try:
        req = Request(subs1_urlbase + capi + "/", headers={'User-Agent': 'Mozilla/5.0', 'Authorization': 'Bearer '+authTk})
        html_doc = urllib.request.urlopen(req, context=ctx).read()
        soup = bs4.BeautifulSoup(html_doc, 'html.parser')
        j = json.loads(soup.text)
        #print(soup.text)
        try:
            show = j['main_category']['name']
        except:
            if show_old == "":
                show = input("Nom de serie no trobat. Indiqueu nom: \n")
                show_old = show
            else:
                show = show_old
        # except:
        #     logger.error("Something went very wrong, can't parse second level url.")
        #     sys.exit(2)
        txt_file = list()

        if first_run:
            if show not in js:
                logger.debug("Show not in temporary file")
                js.append(show)
                js.append([])
                new = True
            pos = js.index(show) + 1
            first_run = False
        if not new:
            if capi in js[pos]:
                logger.debug("Episode already checked, skipping...")
                #c2i += 1
                #continue
        logger.debug("Going for multiple data.")
        # HEADER
        try:
            epnum = getEpNum(j['name'])
            txt_file.append("{} {} ({})".format(show, epnum, j['publish_date'].split("T")[0]))
        except:
            txt_file.append(show)
        # INFO
        try:
            txt_file.append("{}: {}".format(INFO_LINK, capis2[c2i]))
        except:
            pass

        # TITLE
        try:
            #req = Request(subs1_urlbase + capi, headers={'User-Agent': 'Mozilla/5.0'})
            #html_doc = urllib.request.urlopen(req, context=ctx).read()
            #soup = bs4.BeautifulSoup(html_doc, 'html.parser')
            txt_file.append("{}: {}".format(TITLE, j['name']))#soup.title.text))
        except:
            pass
        # MQ
        #try:
            #txt_file.append("{}: {}".format(MQ_VIDEO, soup.file.text))
        #except:
            #pass
        # MQalt + HQ
        try:
            txt_file.append("{}: {}".format(M3_VIDEO, j['content_resources'][0]['direct_url']))
            STS = getStTs(j['content_resources'][0]['direct_url'])
            txt_file.append("{}: {}".format(ST_VIDEO, STS[0]))
            txt_file.append("{}: {}".format(ST2_VIDEO, STS[2]))
            txt_file.append("{}: {}".format(TS_VIDEO, STS[1]))
            txt_file.append("{}: {}".format(TS2_VIDEO, STS[3]))
            if args.down and dcount > 0:
                try:
                    print("Link capturat. Baixant contingut...")
                    if not args.dpath:
                        downloadMedia(STS[1], j['name'], show, args.audio)
                    else:
                        downloadMedia(STS[1], j['name'], show, args.audio, args.dpath)
                except:
                    logger.error("Error baixant el .ts en local")
                dcount -= 1
            elif args.adown and dcount > 0:
                down = input("Link d'stream capturat. El vols baixar com a "+AUVID[args.audio]+"? [y/n]\n")
                if down == "y":
                    try:
                        if not args.dpath:
                            downloadMedia(STS[1], j['name'], show, args.audio)
                        else:
                            downloadMedia(STS[1], j['name'], show, args.audio, args.dpath)
                    except:
                        logger.error("Error baixant el .ts en local")
                dcount -= 1
        except KeyError:
            pass
        # SUBS1
        try:
            txt_file.append("{}: {}".format(SUBTITLE_1, j['content_resources'][0]['thumbnail_track_url']))
        except KeyError:
            pass
        except TypeError:
            print(capi)
        txt_file.append("")
        txt_file.append("")
        txt_file.append("")
        try:
            out_name_file = remove_invalid_win_chars(show, '\/:*?"<>|')
            outfile = open('%s.txt' % out_name_file, 'a')
            logger.info("Writing to {}".format(out_name_file))
            outfile.write('\n'.join(txt_file))
            outfile.close()
        except:
            logger.error("Writing episode to file failed.")
            sys.exit(1)
        js[pos].append(capi)
        c2i += 1
    create_json(js)


if __name__ == '__main__':
    main()