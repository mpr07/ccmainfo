#!/usr/bin/python
import argparse
import bs4
import json
import logging
import requests
import re
import sys
import ssl
from urllib.request import Request
import urllib.request

TMP_FILE = 'ccmainfo.json'

TITLE = "Titol"
INFO_LINK = "Info"
HQ_VIDEO = "HQ"
MQ_VIDEO = "MQ"
MQ_VIDEO2 = "MQ(alt.)"
ST_VIDEO = "Stream"
SUBTITLE_1 = "Subs1"
SUBTITLE_2 = "Subs2"

# Ignore SSL certificate errors
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE


name_urlbase = "http://www.tv3.cat/pvideo/FLV_bbd_dadesItem_MP4.jsp?idint="
hq_urlbase = "http://www.tv3.cat/pvideo/FLV_bbd_media.jsp?QUALITY=H&PROFILE=IPTV&FORMAT=MP4GES&ID="
mpd_urlbase = "https://dinamics.ccma.cat/pvideo/media.jsp?media=video&format=dm&idint="
subs1_urlbase = "http://dinamics.ccma.cat/pvideo/media.jsp?media=video&version=0s&profile=tv&idint="
subs2_urlbase = "http://www.tv3.cat/p3ac/p3acOpcions.jsp?idint="

SUPER3_URL = "www.ccma.cat/tv3/super3/"
SUPER3_FILTER = "media-object"
SX3_URL = "www.ccma.cat/tv3/sx3/"
SX3_URL2 = "www.ccma.cat/Comu/standalone/tv3_sx3_item_fitxa-programa_videos/"
SX3_FILTER = "C-llistatVideo"
TV3_URL = "www.ccma.cat/tv3/"
TV3_FILTER = "F-capsaImatge"
V_3CAT_URL = "www.ccma.cat/3cat/"
V_3CAT_FILTER = "keyframe_info__l44O6"
C_3CAT_URL = "https://www.ccma.cat/3cat/tot-cataleg/"
C_3CAT_FILTER = "poster_textWrapper__IvJ42"

hT = False

###########
# Logging
logger = logging.getLogger('ccmainfo_main')
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.WARNING)
# end internal config
############
capis = []

def quali(x):
    y = x[0]
    try:
        ax = y[:-1]
        xi = int(ax)
        return xi
    except:
        return 9999

def cli_parse():
	parser = argparse.ArgumentParser(description='CCMA.cat INFO')
	parser.add_argument('--batch', dest='batch', nargs='?', default=False,
						help='Run without asking for url')
	parser.add_argument('--debug', dest='verbose', action='store_true',
						help='Debug mode')
	parser.set_defaults(verbose=False)
	args = parser.parse_args()
	return args
	
def getTxt(url):
	fhhhh = open(url, "r+", encoding="utf8")
	lsst = fhhhh.readlines()
	urlaltt = ""
	ii = 0
	while (ii < len(lsst)):
		urlaltt += lsst[ii]
		ii = ii + 1;
	return urlaltt

def get_url(args):
	if not args.batch:
		url = input("Write your URL: ")
	else:
		url = args.batch
	if url.find(".html") > -1:
		logger.debug("TV3 link")
		hT = True
		return url, TV3_FILTER
	elif url.find(SUPER3_URL) > -1:
		logger.debug("SUPER3 link")
		return url, SUPER3_FILTER
	elif url.find(SX3_URL) > -1:
		logger.debug("SX3 link")
		return url, SX3_FILTER
	elif url.find(SX3_URL2) > -1:
		logger.debug("SX3 link2")
		return url, SX3_FILTER
	elif url.find(TV3_URL) > -1:
		logger.debug("TV3 link")
		return url, TV3_FILTER
	elif url.find(V_3CAT_URL) > -1 and url.find(C_3CAT_URL) == -1:
		logger.debug("3CAT link")
		return url, V_3CAT_FILTER
	elif url.find(C_3CAT_URL) > -1:
		logger.debug("3CAT link")
		return url, C_3CAT_FILTER
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


def sx3_video_tag(tag):
	return tag.name == "a" and tag.parent.name == "li" and tag.parent.has_attr("class") and SX3_FILTER in tag.parent.get("class")


def main():
	args = cli_parse()
	if args.verbose:
		logger.setLevel(logging.DEBUG)
	url, parse_filter = get_url(args)
	js = load_json()
	if (url.endswith(".html")):
		html_doc = getTxt(url)	
	else:
		req = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
		html_doc = urllib.request.urlopen(req, context=ctx).read()
	soup = bs4.BeautifulSoup(html_doc, 'html.parser')
	logger.info("Parsing URL {}".format(url))
	try:
		if (parse_filter == SX3_FILTER):
			capis_meta = soup.find_all(sx3_video_tag)
		elif (parse_filter == C_3CAT_FILTER):
			#"id":5644386,
			p1 = re.compile('("id":)([0-9]*)(,)')
			capis2 = p1.findall(str(soup))
			capis_meta = []
			for capi2 in capis2:
				capis.append(capi2[1])
		else:
			capis_meta = soup.find_all('a', class_=parse_filter)
		for capi_meta in capis_meta:
			p = re.compile('/video/([0-9]*)/$')
			capis.append(p.search(capi_meta['href']).group(1))
	except:
		logger.error("Could not parse given url: "+url)
		sys.exit(2)

	capis.reverse()
	first_run = True
	new = False
	for capi in capis:
		logger.debug("Going for ID:{}".format(capi))
		try:
			req = Request(subs1_urlbase + capi, headers={'User-Agent': 'Mozilla/5.0'})
			html_doc = urllib.request.urlopen(req, context=ctx).read()
			soup = bs4.BeautifulSoup(html_doc, 'html.parser')
			j = json.loads(soup.text)
			show = j['informacio']['programa']
		except:
			logger.error("Something went very wrong, can't parse second level url. ID:"+capi)
			sys.exit(2)
		txt_file = list()
		txt_file2 = list()

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
				continue
		logger.debug("Going for multiple data.")
		# HEADER
		try:
			txt_file.append("{} {} ({})".format(show, j['informacio']['capitol'],
										   j['audiencies']['kantarst']['parametres']['ns_st_ddt']))
			txt_file2.append("{} {} ({})".format(show, j['informacio']['capitol'],
										   j['audiencies']['kantarst']['parametres']['ns_st_ddt']))
		except KeyError:
			try:
				txt_file.append("{} {}".format(show, j['informacio']['capitol']))
				txt_file2.append("{} {}".format(show, j['informacio']['capitol']))
			except KeyError:
				txt_file.append(show)
				txt_file2.append(show)
		# INFO
		txt_file.append("{}: {}".format(INFO_LINK, "{}{}".format(mpd_urlbase, capi)))
		txt_file2.append("{}: {}".format(INFO_LINK, "{}{}".format(mpd_urlbase, capi)))


		# TITLE
		try:
			#req = Request(subs1_urlbase + capi, headers={'User-Agent': 'Mozilla/5.0'})
			#html_doc = urllib.request.urlopen(req, context=ctx).read()
			#soup = bs4.BeautifulSoup(html_doc, 'html.parser')
			txt_file.append("{}: {}".format(TITLE, j['audiencies']['sitecatalyst']['nom'])) #j['audiencies']['sitecatalyst']['nom'] soup.title.text))
			txt_file2.append("{}: {}".format(TITLE, j['audiencies']['sitecatalyst']['nom']))#soup.title.text))
		except:
			try:
				txt_file.append("{}: {}".format(TITLE, j['informacio']['titol'])) #j['audiencies']['sitecatalyst']['nom'] soup.title.text))
				txt_file2.append("{}: {}".format(TITLE, j['informacio']['titol']))#soup.title.text))
			except:
				pass
		# MQ
		#try:
			#txt_file.append("{}: {}".format(MQ_VIDEO, soup.file.text))
		#except:
			#pass
		# MQalt + HQ
		try:
			i_hq, i_mq = "", ""
			i_aq = []
			for ul in j['media']['url']:
				try:
					if ul['label'] == "720p":
						i_hq = ul['file']
					elif ul['label'] == "480p":
						i_mq = ul['file']
					elif ul['label'] not in ["720p","480p"]:
						Ta = (ul['label'],ul['file'])
						i_aq.append(Ta)
				except:
					pass
			try:
				if (i_mq != ""):
					txt_file.append("{}: {}".format(MQ_VIDEO, i_mq))
			except:
				pass
			try:
				if (i_hq != ""):
					txt_file.append("{}: {}".format(HQ_VIDEO, i_hq))
			except:
				pass
			try:
				if (i_aq != []):
					i_aq.sort(key=quali)
					for i_q in i_aq:
						txt_file.append("{}: {}".format(i_q[0], i_q[1]))
			except:
				pass
		except KeyError:
			pass
		except TypeError:
			print(capi)

		# STREAM
		try:
			req2 = Request(mpd_urlbase + capi, headers={'User-Agent': 'Mozilla/5.0'})
			html_doc2 = urllib.request.urlopen(req2, context=ctx).read()
			soup2 = bs4.BeautifulSoup(html_doc2, 'html.parser')
			j2 = json.loads(soup2.text)
			
			for i in j2['media']['url']:
				if (i['label'] == "DASH"):
					txt_file2.append("{}: {}".format(ST_VIDEO, i['file']))
					break
			#aaaaaaaaaaaaaaaaa
		except:
			logger.error("Something went very wrong getting the stream url")
		# SUBS1
		try:
			txt_file.append("{}: {}".format(SUBTITLE_1, j['subtitols'][0]['url']))
		except KeyError:
			pass
		except TypeError:
			print(capi)
		# SUBS2
		try:
			req = Request(subs2_urlbase + capi, headers={'User-Agent': 'Mozilla/5.0'})
			html_doc = urllib.request.urlopen(req, context=ctx).read()
			soup = bs4.BeautifulSoup(html_doc, 'html.parser')
			txt_file.append("{}: {}".format(SUBTITLE_2, soup.sub['url']))
		except:
			pass
		txt_file.append("")
		txt_file.append("")
		txt_file.append("")
		txt_file2.append("")
		txt_file2.append("")
		txt_file2.append("")
		try:
			out_name_file = remove_invalid_win_chars(show, '\/:*?"<>|')
			outfile = open('%s.txt' % out_name_file, 'a')
			logger.info("Writing to {}".format(out_name_file))
			outfile.write('\n'.join(txt_file))
			outfile.close()
		except:
			logger.error("Writing episode to file failed.")
			sys.exit(1)
		try:
			out_name_file_st = remove_invalid_win_chars(show, '\/:*?"<>|')+"_ST"
			outfile_st = open('%s.txt' % out_name_file_st, 'a')
			logger.info("Writing to {}".format(out_name_file_st))
			outfile_st.write('\n'.join(txt_file2))
			outfile_st.close()
		except:
			logger.error("Writing episode stream to file failed.")
			sys.exit(1)
		js[pos].append(capi)
	create_json(js)


if __name__ == '__main__':
	main()
