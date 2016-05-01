from bottle import route, run, template, static_file, get, post, request
import os
import subprocess

from bottle import static_file
@route('/static/<filepath:path>')
def server_static(filepath):
    return static_file(filepath, root=os.path.join(os.path.dirname(__file__), 'static'))

import sendRest2Racm


@get('/beep')
def light():
    print 'beep'
    sendRest2Racm.main()
    return 'trolled'

run(host='localhost', port=8080)
