#!/usr/bin/env python

from AgileCLU import AgileCLU
from optparse import OptionParser, OptionGroup
import sys, os.path, urllib, subprocess, time
import hashlib

from poster.encode import multipart_encode, get_body_size
from poster.streaminghttp import register_openers
from urllib2 import Request, urlopen, URLError, HTTPError
import progressbar 

pbar = None
fname = None

def splitMultipart( fname, pieceSize=1048576 ):

	f = open( fname, 'rb')
	data = f.read()
	f.close()
	sha256 = hashlib.sha256(data).hexdigest()

	bytes = len(data)
	pieces = bytes/pieceSize

	if (bytes%pieceSize): pieces += 1
	
	# f = open('info.txt', 'w')
	# f.write(fname+','+'piece,'+str(pieces)+','+str(pieceSize)+"\n")
	# f.close()

	manifest = ''
	pieceNames = []
	pieceNum = 0
	for i in range(0, bytes+1, pieceSize):
		pieceNum += 1
		fn1 = "piece%s" % i
		pieceNames.append(fn1)
		f = open(fn1, 'wb')
		fn1sha=hashlib.sha256(data[i:i+ pieceSize]).hexdigest()
		print ("pieces%s: "+fn1sha) %i
		f.write(data[i:i+ pieceSize])
		f.close()
		if (manifest<>''): manifest = manifest+','
		manifest = manifest +  \
			'''{ ''' + \
			'''"piece": '''+str(pieceNum)+''', '''+ \
			'''"filename": "'''+fn1+'''", '''+ \
			'''"sha-256": "'''+fn1sha+'''", '''+ \
			'''"size": '''+str(len(data[i:i+ pieceSize]))+''', '''+ \
			'''"offset": '''+str(i)+''' '''+ \
			'''}'''
	
	jsonstr = '''{ "filename": "''' + fname + '''", "pieces": '''+str(pieces)+''', "sha-256": "'''+sha256+'''", "manifest": [ '''+manifest+''' ] }'''
	print jsonstr

def progress_callback(param, current, total):
	global pbar
	if (pbar==None):
		widgets = [ unicode(fname, errors='ignore').encode('utf-8'), ' ', progressbar.FileTransferSpeed(), ' [', progressbar.Bar(), '] ', progressbar.Percentage(), ' ', progressbar.ETA() ]
		pbar = progressbar.ProgressBar(widgets=widgets, maxval=total).start()
	try:
		pbar.update(current)
	except AssertionError, e:
		print e

def main(*arg):

	global fname, pbar
	# parse command line and associated helper

	parser = OptionParser( usage= "usage: %prog [options] object path", version="%prog (AgileCLU "+AgileCLU.__version__+")")
	parser.add_option("-v", "--verbose", action="store_true", dest="verbose", help="be verbose", default=False)
        parser.add_option("-l", "--login", dest="username", help="use alternate profile")

	group = OptionGroup(parser, "Handling Options")
	group.add_option("-r", "--rename", dest="filename", help="rename destination file")
	group.add_option("-c", "--mimetype", dest="mimetype", help="set MIME content-type")
	group.add_option("-t", "--time", dest="mtime", help="set optional mtime")
	group.add_option("-e", "--egress", dest="egress", help="set egress policy (PARTIAL, COMPLETE or POLICY)")
	group.add_option("-m", "--mkdir", action="store_true", help="create destination path, if it does not exist")
	group.add_option("-p", "--progress", action="store_true", help="show transfer progress bar")
	parser.add_option_group(group)
	
	config = OptionGroup(parser, "Configuration Option")
	config.add_option("--username", dest="username", help="Agile username")
	config.add_option("--password", dest="password", help="Agile password")
	config.add_option("--mapperurl", dest="mapperurl", help="Agile MT URL base")
	config.add_option("--apiurl", dest="apiurl", help="Agile API URL")
	config.add_option("--posturl", dest="posturl", help="Agile POST URL")
	config.add_option("--postmultiurl", dest="postmultiurl", help="Agile POST URL")
	parser.add_option_group(config)

	(options, args) = parser.parse_args()
	if len(args) != 2: parser.error("Wrong number of arguments. Exiting.")
	object = args[0]
	path = args[1]
	
	if (not os.path.isfile(object)):
		print "Local file object (%s) does not exist. Exiting." % localfile
		sys.exit(1)

	if options.username: agile = AgileCLU( options.username )
	else: agile = AgileCLU()

	localpath = os.path.dirname(object)
	localfile = os.path.basename(object)

	# REMOVED THE DESTINATION PATH CHECK FROM AGILEPOST #

	if options.filename: fname = options.filename
	else: fname = localfile

	print agile.token
	print fname
	print path
	print os.path.join(path,fname)

	r = agile.createMultipart( os.path.join(path,fname) )
	mpid = r['mpid']

	splitMultipart( fname, 524288 )

	
	agile.logout()
	exit(1)

	register_openers()

	# video/mpeg for m2ts
	if options.progress: 
		datagen, headers = multipart_encode( { 
			"uploadFile": open(object, "rb"), 
			"directory": path, 
			"basename": fname, 
			"expose_egress": "COMPLETE"
			}, cb=progress_callback)
	else: 
		datagen, headers = multipart_encode( { 
			"uploadFile": open(object, "rb"), 
			"directory": path, 
			"basename": fname, 
			"expose_egress": "COMPLETE"
			} )

	request = Request(agile.posturl, datagen, headers)
	request.add_header("X-Agile-Authorization", agile.token)

	if options.mimetype: mimetype = options.mimetype
	else: mimetype = 'auto'

	request.add_header("X-Content-Type", mimetype )

	success = False ; attempt = 0
	while not success:
		attempt += 1
		try: 
			result = urlopen(request).read() 
			if options.progress: pbar.finish()
			success = True
		except HTTPError, e: 
			if options.progress: pbar.finish()
			print '[!] HTTP Error: ', e.code
			pbar = None
			success = False
		except URLError, e: 
			if options.progress: pbar.finish()
			print '[!] URL Error: ', e.reason
			pbar = None
			success = False

	
	if options.verbose: 
		print "%s%s" % (agile.mapperurlstr(),urllib.quote(os.path.join(path,fname)))

	agile.logout()

if __name__ == '__main__':
    main()


