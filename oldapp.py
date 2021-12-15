from flask import Flask, request
from google.cloud import speech
from google.cloud import storage
import requests
import json
from firebase import Firebase
from google.cloud import firestore
from google.oauth2 import service_account
import calendar;
import time;

credentials = service_account.Credentials.from_service_account_file('./catalobyte-311413-firebase-adminsdk-tgh22-37ce53aabf.json')

config = {
    "apiKey": "AIzaSyCIss0SDAyB60qBnH1Q0gkG3J6ZGScqfqw",
    "authDomain": "catalobyte-311413.firebaseapp.com",
    "projectId": "catalobyte-311413",
    "databaseURL": "https://catalobyte-311413-default-rtdb.firebaseio.com",
    "storageBucket": "catalobyte-311413.appspot.com",
    "messagingSenderId": "975841552634",
    "appId": "1:975841552634:web:c74547697c03aa7c118143",
    "measurementId": "G-T17P4MGWRL"
}

firebase = Firebase(config)

auth = firebase.auth()
email = "dsa4fdsgf7hgh44w77was@wudfsagfd4.com"
password = '4AS45dsfsdf4fggf44dw47dfd4'

#storage_client = storage.Client()
#storage_client = storage.Client.from_service_account_json('foidito-1612614792460-02ebd4e2a71d.json')
speech_client = speech.SpeechClient()
bucket_json = storage.Client().get_bucket('catalobyte-json')
bucket_txt = storage.Client().get_bucket('catalobyte-texto')

app = Flask(__name__)

@app.route("/", methods=["POST"])
def speechproc():

    random_uid = calendar.timegm(time.gmtime())

    login = auth.sign_in_with_email_and_password(email, password)
    id_token = login['idToken']

    headers = {"Authorization": "Bearer "+id_token}
    response = requests.get('https://us-east1-catalobyte-311413.cloudfunctions.net/aewqop/woasf', headers=headers)
    jwt_token = response.text

    data = request.get_json()
    gs_uri = data['gs_uri']
    index_manticore = data['index_manticore']
    userUid = data['foldername'] # folder = firebase-uuid do front-end
    file_id = data['file_id'] # id-numerico randomico gerado no front-end e que é a Key do document no firebase arquivos/audios/

    audio = speech.RecognitionAudio(uri=gs_uri)
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.FLAC,
        sample_rate_hertz=16000,
        language_code="pt-BR",
        enable_speaker_diarization=True,
        enable_automatic_punctuation=True,
        diarization_speaker_count=2,
        model='default',
    )

    operation = speech_client.long_running_recognize(config=config, audio=audio)
    response = operation.result()
    result = response.results[-1]
    words_info = result.alternatives[0].words

    resp = ""
    for r in response.results:
        resp += r.alternatives[0].transcript
        resp += " "

    print('Textoooo completo: \n')
    print(resp)
    print('----------------------------------------------- \n')

    json_saida = []
    for word_info in words_info:
        json_saida.append({"p":word_info.word, "o": word_info.speaker_tag, "t": word_info.start_time.seconds})

    print(json_saida)



    

    operation = speech_client.long_running_recognize(config=config, audio=audio)
    response = operation.result()

    resp = ""
    for result in response.results:
        resp += result.alternatives[0].transcript
        resp += " "

    uuid_file = random_uid
    headers = {"Authorization": f"Bearer {jwt_token}", "Content-Type":"application/json"}
    data_index = {"widasl":index_manticore, "text":f"{resp}", "pathfile":f"{userUid}", "uuid_file":  uuid_file}
    requests.post('http://35.211.142.130:80/ita', data=json.dumps(data_index), headers=headers)




    '''
    some_json_object = {'foo': list()}
    for i in range(0, 5):
        some_json_object['foo'].append(i)
    blob = bucket_json.blob('text.json')
    blob.upload_from_string(data=json.dumps(some_json_object),content_type='application/json')
    '''


    texto_completo = "ola teste texto txt arquivo"
    blob = bucket_txt.blob('apenas-text.txt')
    blob.upload_from_string(data=texto_completo,content_type='text/plain')


    '''


    gravar no Storage apenas
    e cria trigger para que quando gravar lá, faz o restante: grava no manticore, update firebase 



    '''

    db = firestore.Client(credentials=credentials)
    doc_ref = db.collection(u'arquivos').document(f"{userUid}").collection(u'audios').document(f"{file_id}")
    doc_ref.update({"transcrito":True, "uuid_file": f"{uuid_file}"})

    return "ok"

if __name__ == "__main__":
    # Used when running locally only. When deploying to Cloud Run,
    # a webserver process such as Gunicorn will serve the app.
    app.run(host="localhost", port=8080, debug=True)
