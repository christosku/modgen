#create a web server using flask
from flask import Flask, request, render_template
from flask_socketio import SocketIO, emit, send
from caseconverter import snakecase
import configparser
import sys
import os
import shutil
import subprocess
import shlex
import base64
import re
import json


app = Flask(__name__)

#Disable caching
app.config['TEMPLATES_AUTO_RELOAD'] = True
socketio = SocketIO(app)

config = configparser.ConfigParser()

pluginCategories = [
    "DelayPlugin",
    "DistortionPlugin",
    "DynamicsPlugin",
    "FilterPlugin",
    "GeneratorPlugin",
    "MIDIPlugin",
    "ModulatorPlugin",
    "ReverbPlugin",
    "SimulatorPlugin",
    "SpatialPlugin",
    "SpectralPlugin",
    "UtilityPlugin"
]

acceptedGenFilenames = [
    'gen_exported.cpp',
    'gen_exported.h'
]

acceptedRnboFilenames = [
    'rnbo_source.cpp',
    'description.json'
]

deviceList = [
    'modduox',
    'moddwarf'
]

@app.route("/", methods=["GET"])
def upload_page():
    return render_template(
                            "index.html", 
                            categoryLength = len(pluginCategories), 
                            pluginCategories = pluginCategories,
                            name = name,
                            brand = brand,
                            uri = uri,
                            category = category,
                            deviceLength = len(deviceList),
                            deviceList = deviceList,
                            device = device,
                            ip = ip,
                            inputs = inputs,
                            outputs = outputs
                           )

#create a route that accepts POST requests with file uploads and saves them to disk
@app.route("/", methods=["POST"])
def upload():
    global name, brand, uri, category, device, ip
    if request.method == "POST":
        type = None
        if request.files:
            filenames = []
            uploaded_files = request.files.getlist("files")
            
            #check if we received exactly 2 files
            if len(uploaded_files) != 2:
                socketio.emit('response', {
                    'data': '''You must upload exactly 2 files: <strong>gen_exported.cpp</strong> and <strong>gen_exported.h</strong> for Gen or <strong>rnbo_source.cpp</strong> and <strong>description.json</strong> for RNBO'''})
                return "ok"
            
            #detect if the files are Gen or RNBO
            for file in uploaded_files:
                filenames.append(file.filename)
                if 'gen_exported.cpp' in filenames:
                    type = 'gen'
                    break
                elif 'rnbo_source.cpp' in filenames:
                    type = 'rnbo'
                    break
            if type:
                socketio.emit('response', {'data': 'Detected Plugin type: ' +type})
            else:
                socketio.emit('response', {'data': 'Could not detect plugin type', 'type': 'error'})
                return "ok"
            
            
            rootDirectory = "/home/modgen/mod-plugin-builder/max-"+type+"-plugins/"
            prepareDirectory(rootDirectory)
            #create a new folder to save the files
            directory = rootDirectory+'plugins/max-'+type+'-plugin/'
            if not os.path.exists(directory):
                os.makedirs(directory)
                
            for file in uploaded_files:
                #check if the file has one of the accepted filenames
                if (type == 'gen' and file.filename not in acceptedGenFilenames) or (type == 'rnbo' and file.filename not in acceptedRnboFilenames):
                    socketio.emit('response', {'data': 'Invalid filename: '+file.filename})
                    return "ok"

                if file.filename == 'gen_exported.cpp':
                    #get the inputs and outputs from the gen_exported.cpp file
                    filedata = file.stream.read().decode('utf-8')
                    file.stream.seek(0)
                    inputs = re.search('int gen_kernel_numins = (\d+);', filedata).group(1)
                    outputs = re.search('int gen_kernel_numouts = (\d+);', filedata).group(1)
                    socketio.emit('response', {'data': 'Detected '+inputs+' inputs and '+outputs+' outputs'})
                elif file.filename == 'description.json':
                    #get the inputs and outputs from the rnbo description json file
                    filedata = file.stream.read().decode('utf-8')
                    file.stream.seek(0)
                    #parse the json
                    rnboData = json.loads(filedata)
                    inputs = rnboData['numInputChannels']
                    outputs = rnboData['numOutputChannels']
                    midiInputs = rnboData['numMidiInputPorts']
                    midiOutputs = rnboData['numMidiOutputPorts']
                    cvPorts = []
                    find_cv_ports(rnboData['inlets'], cvPorts)
                    find_cv_ports(rnboData['outlets'], cvPorts)
                file.save(directory+file.filename)

                

            socketio.emit('response', {'data': 'Files uploaded successfully', 'type': 'success'})
            socketio.emit('response', {'data': 'Modifying Distrho Plugin Info', 'type': 'success'})


            #get the settings from the post form
            name = request.form.get('name')
            brand = request.form.get('brand')
            uri = request.form.get('uri')
            category = request.form.get('category')
            device = request.form.get('device')
            ip = request.form.get('ip')

            if request.form.get('save-settings') == 'true':
                saveSettings()

            #modify the plugin info
            with open('DistrhoPluginInfo.h', 'r') as infoFile:
                filedata = infoFile.read()
                filedata = filedata.replace('@brand@', brand)
                filedata = filedata.replace('@name@', name)
                filedata = filedata.replace('@uri@', uri)
                filedata = filedata.replace('@category@', 'lv2:'+category)
                filedata = filedata.replace('@inputs@', str(inputs))
                filedata = filedata.replace('@outputs@', str(outputs))
                if type == 'rnbo':
                    filedata = filedata.replace('@isrnboplugin@', '1')
                    if midiInputs > 0:
                        filedata = filedata.replace('@midiinput@', '1')
                    else:
                        filedata = filedata.replace('@midiinput@', '0')
                    if midiOutputs > 0:
                        filedata = filedata.replace('@midioutput@', '1')
                    else:
                        filedata = filedata.replace('@midioutput@', '0')
                    if len(cvPorts) > 0:
                        filedata = filedata.replace('@cvports@', '{'+','.join(str(cvPort) for cvPort in cvPorts)+'}')
                    else:
                        filedata = filedata.replace('@cvports@', '{}')

                else:
                    filedata = filedata.replace('@isrnboplugin@', '0')
                    filedata = filedata.replace('@midiinput@', '0')
                    filedata = filedata.replace('@midioutput@', '0')
                    filedata = filedata.replace('@cvports@', '{}')


            #write the file out again
            with open(directory+'DistrhoPluginInfo.h', 'w') as infoFile:
                infoFile.write(filedata)

            socketio.emit('response', {'data': 'Distrho Plugin Info modified successfully', 'type': 'success'})

            #build the plugin
            if buildPlugin(device, type) is False:
                socketio.emit('response', {'data': 'Failed to build plugin', 'type': 'error'})
                return "ok"
            
            #compress the plugin
            if compressPlugin(brand, name, type) is False:
                socketio.emit('response', {'data': 'Failed to compress plugin', 'type': 'error'})
                return "ok"

            if getBase64(type) is False:
                socketio.emit('response', {'data': 'Failed to get base64', 'type': 'error'})
                return "ok"
            
        else:
            socketio.emit('response', {'data': 'No files were selected', 'type': 'error'})
        return "ok"
    else:
        return "not a post request"



#create a route that accepts GET requests and returns a list of files in the current directory
@app.route("/files", methods=["GET"])
def files():
    import os
    files = os.listdir()
    return str(files)

@socketio.on('connect')
def test_connect():
    emit('response', {'data': 'Connected'})

def find_cv_ports(ports, cvPorts):
    for port in ports:
        if port['type'] == 'signal':
            if 'meta' in port and 'cv' in port['meta'] and port['meta']['cv'] == True:
                cvPorts.append(1)
            else:
                cvPorts.append(0)

def prepareDirectory(directory):
    #delete existing files and folders in the directory
    dirList = ['plugins', 'custom-ttl','presets','bin']
    for dir in dirList:
        if os.path.exists(directory+dir):
            for filename in os.listdir(directory+dir):
                file_path = os.path.join(directory+dir, filename)
                try:
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.unlink(file_path)
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                except Exception as e:
                    socketio.emit('response', {'data': 'Failed to delete %s. Reason: %s' % (file_path, e), type: 'error'})

def compressPlugin(brand, name, type):
    #build the plugin
    exportPath = '/home/modgen/mod-plugin-builder/max-'+type+'-plugins/bin/max-'+type+'-plugin.lv2'
    socketio.emit('response', {'data': 'Compressing Plugin'})
    if not os.path.exists(exportPath):
        socketio.emit('response', {'data': 'Plugin not found', 'type': 'error'})
        return False
    #rename the plugin
    pluginName = snakecase(brand)+'-'+snakecase(name)+'.lv2'
    pluginPath = '/home/modgen/mod-plugin-builder/max-'+type+'-plugins/bin/'+pluginName
    os.rename(exportPath, pluginPath)
    command = 'tar zhcf max-'+type+'-plugin.tar.gz '+pluginName
    try:
        process = subprocess.Popen(
            shlex.split(command),
            shell=False, 
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=r'/home/modgen/mod-plugin-builder/max-'+type+r'-plugins/bin'
            )
    except:
        socketio.emit('response', {'data': 'ERROR {} while running {}'.format(sys.exc_info()[1], command), 'type': 'error'})
        return False
    while True:
        output = process.stdout.readline()
        errors = process.stderr.readline()
        if process.poll() is not None:
            break
        if output:
            socketio.emit('response', {'data': output.strip().decode(), 'type': 'info'})
        if errors:
            socketio.emit('response', {'data': errors.strip().decode(), 'type': 'error'})
            return False
    socketio.emit('response', {'data': 'Plugin compressed successfully', 'type': 'success'})
    return True

#convert the tar to base64 and send it to the client

def getBase64(type):
    if not os.path.exists('/home/modgen/mod-plugin-builder/max-'+type+'-plugins/bin/max-'+type+'-plugin.tar.gz'):
        socketio.emit('response', {'data': 'Compressed plugin file not found', 'type': 'error'})
        return False
    with open('/home/modgen/mod-plugin-builder/max-'+type+'-plugins/bin/max-'+type+'-plugin.tar.gz', 'rb') as file:
        encoded = base64.encodebytes(file.read()).decode('utf-8')
        socketio.emit('response', {'data': encoded, 'type': 'plugin'})
    return True

def saveSettings():
    config['Default']['name'] = name
    config['Default']['brand'] = brand
    config['Default']['uri'] = uri
    config['Default']['category'] = category
    config['Default']['device'] = device
    config['Default']['ip'] = ip
    config['Default']['inputs'] = inputs
    config['Default']['outputs'] = outputs

    with open('settings.ini', 'w') as configfile:
        config.write(configfile)

def buildPlugin(target, type):
    #build the plugin
    socketio.emit('response', {'data': 'Building Plugin'})
    command = 'make ' + target
    try:
        process = subprocess.Popen(
            shlex.split(command),
            shell=False, 
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=r'/home/modgen/mod-plugin-builder/max-'+type+r'-plugins/'
            )
    except:
        socketio.emit('response', {'data': 'ERROR {} while running {}'.format(sys.exc_info()[1], command), 'type': 'error'})
        return False
    while True:
        output = process.stdout.readline()
        errors = process.stderr.readline()
        if process.poll() is not None:
            break
        if output:
            socketio.emit('response', {'data': output.strip().decode(), 'type': 'build'})
        if errors:
            socketio.emit('response', {'data': errors.strip().decode(), 'type': 'warning'})
    socketio.emit('response', {'data': 'Plugin built successfully', 'type': 'success'})
    return True

#if the settings.ini file does not exist, create it with some default values
if not os.path.exists('settings.ini'):
    config['Default'] = {}
    name='ExampleName'
    brand='ExampleBrand'
    uri='http://example.com/example'
    category='UtilityPlugin'
    device='modduox'
    ip='192.168.51.1'
    inputs='2'
    outputs='2'
    saveSettings()
else:
    config.read('settings.ini')
    name = config['Default']['name']
    brand = config['Default']['brand']
    uri = config['Default']['uri']
    category = config['Default']['category']
    device = config['Default']['device']
    ip = config['Default']['ip']
    inputs = config['Default'].get('inputs','2')
    outputs = config['Default'].get('outputs','2')

if __name__ == "__main__":
    print('Starting server...')
    socketio.run(app, host='0.0.0.0', allow_unsafe_werkzeug=True)